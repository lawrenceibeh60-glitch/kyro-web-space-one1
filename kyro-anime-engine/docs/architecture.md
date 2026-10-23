# KAE Architecture and Roadmap

## Product direction

KAE is a **2D-first procedural anime production editor with cinematic 2.5D tools**. The goal is a practical anime workflow: editable vector artwork, character parts, rigs, repeatable walk cycles, camera keyframes, layered depth, lighting, effects, and reliable export. A full 3D backend is an optional future extension, not a prerequisite for cinematic shots.

Use 2.5D for parallax, layered staging, camera trucking, dolly/zoom, roll, and depth-aware composition. A camera move alone cannot reveal the unseen side of a flat character drawing. Front-to-profile shots must use authored/generated alternate views, a turn-around model, or actual 3D geometry; the format and renderer must not pretend otherwise.

## Existing foundations

## Existing foundations

- **Project persistence:** versioned KAE JSON, safe legacy defaults, stable-ID imports, semantic validation, and rejection of unsupported future format versions.
- **Drawing and paths:** point strokes and M/L/Q/C/Z path commands, editable layers, fill rules, caps and joins.
- **Animation:** exposures, transform/opacity tracks, easing, timeline/keyframe tools, and hierarchical 2D bone-rotation tracks.
- **Camera and depth:** scene camera pan, roll, horizontal/vertical zoom tracks, pointer-anchored dolly, inverse pointer mapping, and layer-driven 2.5D parallax. Viewport and export share camera evaluation.
- **Production tools:** procedural character-part generation, scene lights, deterministic scene effects, timeline audio metadata/playback, and PNG/GIF/sprite-sheet/WebM export paths.
- **AI workspace:** provider-backed chat, sampled-frame reference analysis, proposed animation plans, vector reconstruction planning, and image-generation integration. AI provider credentials and model access depend on provider configuration and permissions.

## Blueprint status

| Blueprint area | Status | Notes |
| --- | --- | --- |
| Project load/save, compatibility, and validation | Partial | Version 1 to 2 migration, schema validation, and semantic/reference checks exist; a general migration registry and dependency resolver remain future work. |
| Drawing and paths | Partial | Point strokes and Bézier commands render and edit. Dedicated tessellation, robust Boolean path operations, stroke expansion, gradients, patterns, textures, masks, and clipping are not implemented. |
| Scene graph | Partial | Recursive group/child layers, hierarchy traversal and reparenting, inherited 2D transforms/opacity, nested timeline rows, and drag-and-drop grouping are implemented. Group-level offscreen compositing/blend isolation and complete world-space object evaluation remain future work. |
| Procedural characters | Partial | A configurable character generator produces editable parts. It is a focused generator, not the full anatomy-guided builder suite in the blueprint. |
| Character scenes | Partial | Characters can be imported and placed as layers; full character instances, lighting/material pipeline, and compositional scene graph are not implemented. |
| Animation | Partial | Timeline, exposures, transform interpolation, camera animation, bone rotation tracks, rotation constraints, and two-bone IK tooling exist. Mesh/puppet deformation, foot locking, automatic walk-cycle synthesis, and robust facial animation tracks remain future work. |
| Rendering and export | Partial | Browser Canvas renderer and several exports exist. A bounded render cache, color/levels/vignette processing, layer-aware Alpha Over, alpha-mask/matte compositing, depth-sorted layer compositing, and connected image sockets with cycle validation are implemented. Group-isolated blending, full color management, a dedicated rasterizer, and server-side video rendering remain future work. |
| Performance and determinism | Partial | Large timeline/import bottlenecks have targeted fixes and effects use deterministic seeds. General geometry/layer caches and invalidation tracking do not exist. |
| Schemas | Partial | Core project, character, scene, animation, rig, effects, render, drawing, and path schemas exist. Separate style, palette, material, lighting, asset, audio, and export schemas remain roadmap work. |

## Known limitations (do not present these as completed features)

| Area | Current limitation |
| --- | --- |
| 2.5D camera | Camera roll, pan, and zoom are not a true 3D orbit. There is no perspective camera or world-space 3D transform model. |
| Character motion | Rigs support hierarchical 2D rotation. IK, mesh/puppet deformation, foot locking, automatic walk-cycle synthesis, and robust facial animation tracks remain future work. |
| Procedural drawing | The character generator is a focused editable-part generator, not a complete anatomy-aware anime drawing system. |
| Scene graph | Nested groups and inherited 2D transforms/opacity now render and can be edited in the hierarchy. Group-level isolated blend effects and full world-transform editing/inspection remain incomplete. |
| Rendering | Canvas rendering supports current strokes, lights, and effects. Layer-aware Alpha Over, alpha-mask/matte compositing, Z-depth sorting, and a connected image-socket graph are available. Group-isolated blending, full shadow casting/materials, physical 3D depth-of-field, color management, and a dedicated rasterizer remain incomplete. |
| Format evolution | The custom validator handles semantic checks; a general migration registry and full runtime validation against every JSON Schema are not implemented. |

## Implementation order

1. **Protect the format:** keep schema references resolvable, validate camera fields and keyframes consistently, and add compatibility tests before adding fields. The current repair branch includes schema-reference integrity checks.
2. **Unify camera behavior:** centralize camera normalization, key insertion, dolly anchoring, and inverse pointer mapping. Keep viewport, picking, lights, rig overlays, and exports aligned.
3. **Build cinematic 2.5D:** make depth values meaningful and predictable, add camera shot presets only when their behavior is executable, and provide easing/hold controls for shot timing.
4. **Strengthen the scene graph:** recursive groups and parent-child 2D transform inheritance are implemented without changing the meaning of existing flat layer lists; group-isolated blending and full world-transform tooling remain follow-up work.
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


### Perspective 2.5D plane turns

Layers support an animated `rotation_y` channel in the range -180° to 180°. The renderer perspective-projects point strokes and Bézier path control points around the layer anchor (or canvas center), so a flat drawing can turn edge-on and reverse with perspective rather than using only a horizontal squash. Combine this with front/profile artwork crossfades for character turn shots. This is perspective-projected 2D artwork, not a volumetric 3D character mesh.
