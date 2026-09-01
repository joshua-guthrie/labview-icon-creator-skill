# LabVIEW VI icon style guide

Read this reference before planning or generating concepts.

## Design target

The 1024×1024 source is a master; judge the design for 18–30 pixel use. Unless
the user explicitly overrides the style, use a white background, flat fills,
high contrast, clean centered geometry, generous margins, and no decorative
border, texture, scene, shadow, photographic treatment, or intentional gradient.
Do not include text or pseudo-text unless the requested meaning requires it.

Build each concept from one dominant idea and normally two or three primary
elements. Prefer strong silhouettes, thick features, clear separation, and
industry-standard action/status symbols. Keep essential plus, minus, X, check,
arrow, gear, wave, lock, or warning geometry large enough to survive at 30×18.

## Five distinct concepts

All five options must communicate the same requested function while differing
meaningfully in metaphor, composition, orientation, or symbol arrangement.
Minor color, stroke, or positioning variants of the same drawing are not
distinct. Useful approaches include object-plus-action, object-plus-status,
simplified metaphor, alternate orientation, and an equivalent standard symbol.

Before generation, replace a concept when it:

- needs more than three primary ideas, small text, or fine detail;
- is likely to be ambiguous at about 30 pixels;
- is substantially similar to another option;
- relies on color alone or an obscure metaphor;
- requires a detailed scene rather than icon geometry.

Concept-preflight rejection is routine planning, not a lessons-learned trigger.

## Source generation contract

Generate each concept in a separate image-generation call as an independent
full-resolution square raster image, defaulting to 1024×1024. Explicitly request
one icon only. Do not ask for a grid, sheet, collection, montage, numbered set,
or multiple alternatives in one image, and never crop such an image into source
assets.

Prompt for complete centered artwork with roughly 8–12% clear margin (5% is a
practical lower bound), strong foreground/background separation, simple solid
geometry, and no incidental letters or labels. The principal artwork should
generally occupy 55–85% of the useful canvas width or height.
