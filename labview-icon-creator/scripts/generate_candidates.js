// Load as an expression in functions.exec; dependencies are injected, not global.
async function generateCandidates(config, deps) {
  const jobs = config.jobs;
  const limit = config.concurrency ?? 2;
  if (!Array.isArray(jobs) || !jobs.length || ![1, 2].includes(limit)) {
    throw new Error("Provide jobs and a generation concurrency of 1 or 2");
  }
  if (!config.python || !config.saver) throw new Error("Python and saver paths are required");
  if (new Set(jobs.map(j => j.destination)).size !== jobs.length) {
    throw new Error("Candidate destinations must be unique");
  }
  for (const job of jobs) {
    if (!job.candidate_id || !job.destination || (!job.prompt && !job.local_source)) {
      throw new Error("Every job needs an ID, destination, and prompt or local source");
    }
  }
  const quote = config.shell === "posix"
    ? value => "'" + String(value).replace(/'/g, "'\\''") + "'"
    : value => "'" + String(value).replace(/'/g, "''") + "'";
  const prefix = config.shell === "posix" ? "" : "& ";
  const base = prefix + quote(config.python) + " " + quote(config.saver);
  const results = new Array(jobs.length);
  let cursor = 0;
  async function worker() {
    while (cursor < jobs.length) {
      const index = cursor++;
      const job = jobs[index];
      let receiver;
      // Errors are returned per candidate. Siblings still finish, and retrying
      // only failed jobs cannot discard successful expensive generations.
      try {
        let saved;
        if (job.local_source) {
          saved = await deps.tools.exec_command({
            cmd: base + " --source " + quote(job.local_source) + " --output " + quote(job.destination),
            max_output_tokens: 300
          });
        } else {
          const previous = deps.loadResult ? deps.loadResult(job.candidate_id) : undefined;
          const result = previous ?? await deps.tools.image_gen__imagegen({
            prompt: job.prompt, transparent_background: config.background_mode === "transparent"
          });
          // Keep an expensive result available if filesystem transport fails.
          if (deps.retainResult) deps.retainResult(job.candidate_id, result);
          if (deps.showResult) deps.showResult(result);
          const payload = result.image_url ?? result.imageUrl;
          if (typeof payload !== "string" || payload.length > 64 * 1024 * 1024 ||
              !/^data:image\/png;base64,[A-Za-z0-9+/]+={0,2}$/.test(payload)) {
            throw new Error("Generator did not return a PNG data URL; use a supplied local artifact when available");
          }
          const process = await deps.tools.exec_command({
            cmd: base + " --stdin --output " + quote(job.destination),
            tty: true, yield_time_ms: 1, max_output_tokens: 300
          });
          if (process.session_id === undefined) {
            throw new Error("Runtime did not provide a writable stdin session: " + process.output);
          }
          receiver = process.session_id;
          let readyOutput = process.output;
          let readySession = process;
          let polls = 0;
          while (!readyOutput.includes("READY")) {
            if (++polls > 30) throw new Error("Timed out waiting for the source receiver");
            readySession = await deps.tools.write_stdin({session_id: readySession.session_id,
                                                        yield_time_ms: 1000, max_output_tokens: 300});
            readyOutput += readySession.output;
            if (readySession.session_id === undefined) throw new Error("Receiver exited before READY: " + readyOutput);
          }
          saved = await deps.tools.write_stdin({
            session_id: process.session_id, chars: payload + "\n",
            yield_time_ms: 1000, max_output_tokens: 300
          });
          let output = saved.output;
          // Windows ConPTY treats a bulk paste and the Enter key separately.
          // Send one explicit Enter after the payload, rather than shell chunks.
          if (config.shell !== "posix" && saved.session_id !== undefined) {
            saved = await deps.tools.write_stdin({session_id: saved.session_id, chars: "\r",
                                                 yield_time_ms: 1000, max_output_tokens: 300});
            output += saved.output;
          }
          polls = 0;
          while (saved.session_id !== undefined) {
            if (++polls > 30) throw new Error("Timed out saving the source; retained result is available for recovery");
            saved = await deps.tools.write_stdin({session_id: saved.session_id,
                                                 yield_time_ms: 1000, max_output_tokens: 300});
            output += saved.output;
          }
          saved.output = output;
          receiver = undefined;
        }
        if (saved.exit_code !== 0) throw new Error(saved.output || "Source transfer failed");
        // PTYs may add console control sequences and the READY handshake.
        const clean = saved.output.replace(/\x1b\][^\x07]*(?:\x07|\x1b\\)/g, "")
                                  .replace(/\x1b\[[0-?]*[ -/]*[@-~]/g, "");
        const receiptLine = clean.split(/\r?\n/).findLast(line => line.trim().startsWith("{"));
        results[index] = {candidate_id: job.candidate_id, status: "SAVED", receipt: JSON.parse(receiptLine ?? clean)};
        if (deps.retainResult) deps.retainResult(job.candidate_id, null);
      } catch (error) {
        if (receiver !== undefined) {
          try { await deps.tools.write_stdin({session_id: receiver, chars: "\u0003", max_output_tokens: 100}); }
          catch (_) { /* Receiver may already have exited; preserve the original failure. */ }
        }
        results[index] = {candidate_id: job.candidate_id, status: "FAIL", error: String(error.message ?? error)};
      }
      if (deps.notify) deps.notify({candidate_id: job.candidate_id, status: results[index].status});
    }
  }
  await Promise.all(Array.from({length: Math.min(limit, jobs.length)}, worker));
  return results;
}
