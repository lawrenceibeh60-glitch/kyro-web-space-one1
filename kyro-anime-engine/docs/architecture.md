# KAE Architecture and Roadmap

## Product direction

KAE is a **2D-first procedural anime production editor with cinematic 2.5D tools**. The goal is a practical anime workflow: editable vector artwork, character parts, rigs, repeatable walk cycles, camera keyframes, layered depth, lighting, effects, and reliable export. A full 3D backend is an optional future extension, not a prerequisite for cinematic shots.

Use 2.5D for parallax, layered staging, camera trucking, dolly/zoom, roll, and depth-aware composition. A camera move alone cannot reveal the unseen side of a flat character drawing. Front-to-profile shots must use authored/generated alternate views, a turn-around model, or actual 3D geometry; the format and renderer must not pretend otherwise.

## Existing foundations

- **Project persistence:** versioned `kae` JSON, safe legacy defaults, stable-ID imports, semantic validation, and rejection of unsupported future format versions.
- **Drawing:** point strokes and M/L/Q/C/Z path commands; fill rules, caps, joins, editable layers, and shared viewport/export drawing logic.
- **Animation:** exposures, transform and opacity tracks, easing, timeline/keyframe tools, and hierarchical 2D bone-rotation tracks.
- **Camera and depth:** scene camera pan, roll, horizontal zoom, and (in the cinematic-camera repair branch) independent vertical zoom tracks; layer depth factors drive 2.5D parallax. The same camera evaluator is used by viewport and export rendering.
- **Production features:** procedural character-part generation, scene lights, deterministic scene effects, timeline audio metadata/playback, and PNG/GIF/sprite-sheet/WebM export paths.

## Known limitations (do not present these as completed features)

| Area | Current limitation |
| --- | --- |
| 2.5D camera | Camera roll, pan, and zoom are not a true 3D orbit. There is no perspective camera or world-space 3D transform model. |
| Character motion | Rigs support hierarchical 2D rotation. IK, mesh/puppet deformation, foot locking, automatic walk-cycle synthesis, and robust facial animation tracks remain future work. |
| Procedural drawing | The character generator is a focused editable-part generator, not a complete anatomy-aware anime drawing system. |
| Scene graph | Layers and depth exist, but general parented groups and complete world-transform composition are not implemented. |
| Rendering | Canvas rendering supports current strokes, lights, and effects. Full shadow casting, materials, depth of field, masks, clipping, color management, and a dedicated compositor are not implemented. |
| Format evolution | The custom validator handles semantic checks; a general migration registry and full runtime validation against every JSON Schema are not implemented. |

## Implementation order

1. **Protect the format:** keep schema references resolvable, validate camera fields and keyframes consistently, and add compatibility tests before adding fields.
2. **Unify camera behavior:** centralize camera normalization, key insertion, dolly anchoring, and inverse pointer mapping. Keep viewport, picking, lights, rig overlays, and exports aligned.
3. **Build cinematic 2.5D:** make depth values meaningful and predictable, add camera shot presets only when their behavior is executable, and provide easing/hold controls for shot timing.
4. **Strengthen the scene graph:** add optional drawable groups and parent-child transforms without changing the meaning of existing flat layer lists.
5. **Improve character production:** make generated parts editable, add alternate front/three-quarter/profile views, then develop repeatable walk-cycle clips with clear contact/passing/up/down poses.
6. **Expand rigging safely:** add constraints/IK and deformation only with evaluators, editing tools, validation, and tests—not schema-only promises.
7. **Improve rendering:** add measurable cache invalidation, then compositing, masks, depth-of-field, and shadow features with viewport/export parity.
8. **Consider true 3D only when needed:** introduce a separate 3D scene/object model and renderer behind a versioned capability boundary; do not overload 2D layer fields with fake 3D coordinates.

## Non-negotiable constraints

- Preserve existing valid version-1 projects and point-based drawings.
- Prefer additive fields with safe defaults; bump the project version only for incompatible semantics.
- Keep the JSON Schema, Python validator, editor evaluator, and exporter aligned.
- Make generated art editable in the same project model as hand-drawn art.
- Reject unsupported data with useful error paths instead of silently dropping it.
- Keep implementation claims tied to code and tests that actually exist.
