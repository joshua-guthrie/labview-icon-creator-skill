// Offline contract tests: no image-generation service or shell is invoked.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const test = require('node:test');
const source = fs.readFileSync(path.join(__dirname, '../scripts/generate_candidates.js'), 'utf8');
const generate = vm.runInNewContext('(' + source + ')');
const config = count => ({python: "C:/Python's Folder/python.exe", saver: 'C:/skill/save_source.py',
  background_mode: 'white', concurrency: 2,
  jobs: Array.from({length: count}, (_, i) => ({candidate_id: String(i), prompt: 'one icon', destination: `C:/work/${i}.png`}))});

function mockTools() {
  const record = {active: 0, peak: 0, generated: 0, launched: 0, writes: 0, commands: [], shown: 0};
  const tools = {
    async image_gen__imagegen() {
      record.generated++; record.active++; record.peak = Math.max(record.peak, record.active);
      await new Promise(resolve => setImmediate(resolve));
      record.active--; return {image_url: 'data:image/png;base64,YWJj'};
    },
    async exec_command(args) {
      record.commands.push(args.cmd); record.launched++;
      return args.cmd.includes('--stdin') ? {session_id: record.launched, output: 'READY\n'}
        : {exit_code: 0, output: JSON.stringify({source_file: 'saved.png'})};
    },
    async write_stdin(args) {
      record.writes++;
      assert.equal(args.chars, 'data:image/png;base64,YWJj\n');
      return {exit_code: 0, output: JSON.stringify({source_file: 'saved.png'})};
    }
  };
  return {record, tools};
}

test('five independent sources run with a maximum of two generators and one stdin write each', async () => {
  const {record, tools} = mockTools();
  const result = await generate(config(5), {tools, showResult: () => record.shown++});
  assert.equal(record.peak, 2); assert.equal(record.generated, 5);
  assert.equal(record.launched, 5); assert.equal(record.writes, 5); assert.equal(record.shown, 5);
  assert.ok(result.every(r => r.status === 'SAVED'));
  assert.ok(record.commands.every(c => !c.includes('base64') && c.includes("Python''s Folder")));
});

test('concurrency one supports a sequential provider', async () => {
  const {record, tools} = mockTools(); const jobConfig = config(3); jobConfig.concurrency = 1;
  await generate(jobConfig, {tools}); assert.equal(record.peak, 1);
});

test('a failed transfer preserves the result and retry does not regenerate', async () => {
  const {record, tools} = mockTools(); const cache = new Map();
  const deps = {tools, loadResult: id => cache.get(id), retainResult: (id, value) => cache.set(id, value)};
  const normalWrite = tools.write_stdin;
  tools.write_stdin = async () => ({exit_code: 1, output: 'filesystem denied'});
  const failed = await generate(config(1), deps);
  assert.equal(failed[0].status, 'FAIL'); assert.ok(cache.get('0'));
  tools.write_stdin = normalWrite;
  const recovered = await generate(config(1), deps);
  assert.equal(recovered[0].status, 'SAVED'); assert.equal(record.generated, 1); assert.equal(cache.get('0'), null);
});

test('a failed candidate does not discard completed siblings', async () => {
  const {tools} = mockTools(); let calls = 0; const normal = tools.image_gen__imagegen;
  tools.image_gen__imagegen = async () => (++calls === 1 ? Promise.reject(new Error('backend failure')) : normal());
  const result = await generate(config(3), {tools});
  assert.equal(result.filter(r => r.status === 'FAIL').length, 1);
  assert.equal(result.filter(r => r.status === 'SAVED').length, 2);
});

test('supplied local artifacts are copied without image generation or stdin', async () => {
  const {record, tools} = mockTools(); const jobConfig = config(1); jobConfig.jobs[0].local_source = 'C:/artifact.png';
  await generate(jobConfig, {tools});
  assert.equal(record.generated, 0); assert.equal(record.writes, 0); assert.equal(record.launched, 1);
});

test('duplicate output paths and excessive concurrency are rejected before generation', async () => {
  const {record, tools} = mockTools(); const jobConfig = config(2);
  jobConfig.jobs[1].destination = jobConfig.jobs[0].destination;
  await assert.rejects(generate(jobConfig, {tools}), /unique/);
  jobConfig.concurrency = 3;
  await assert.rejects(generate(jobConfig, {tools}), /concurrency/);
  assert.equal(record.generated, 0);
});

test('PTY framing is cleaned and receipt chunks survive polling', async () => {
  const {record, tools} = mockTools(); let writes = 0;
  tools.write_stdin = async args => {
    writes++;
    if (writes === 1) return {session_id: args.session_id, output: ''};
    if (writes === 2) {
      assert.equal(args.chars, '\r');
      return {session_id: args.session_id,
        output: '\x1b]0;window\x07\x1b[H' + JSON.stringify({source_file: 'saved.png'}) + '\r\n'};
    }
    return {exit_code: 0, output: '\x1b[?9001l'};
  };
  const result = await generate(config(1), {tools});
  assert.equal(result[0].status, 'SAVED'); assert.equal(result[0].receipt.source_file, 'saved.png');
  assert.equal(writes, 3); assert.equal(record.generated, 1);
});

test('invalid generated payload is rejected before spawning a receiver', async () => {
  const {record, tools} = mockTools();
  tools.image_gen__imagegen = async () => ({image_url: 'data:image/png;base64,YWJj\nunexpected input'});
  const result = await generate(config(1), {tools});
  assert.equal(result[0].status, 'FAIL'); assert.equal(record.launched, 0);
});
