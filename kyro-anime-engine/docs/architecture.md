# KAE Architecture Status

This document tracks the implementation against the KAE blueprint. KAE is an
active 2D animation editor, not yet the complete universal procedural drawing
and animation platform described in the blueprint. The architecture below
distinguishes working features from planned systems so that existing behavior
is not mistaken for completed roadmap work.

## Implemented foundations

- **Project format and compatibility:** versioned `kae` JSON, legacy defaults,
  validation, stable-ID additive imports, and rejection of unsupported future
  project versions.
- **Editor workflow:** canvas drawing, layers, exposures, undo/redo, timeline,
  keyframes, transform editing, scene camera, and project save/load.
- **Drawing:** existing point strokes remain supported. Strokes can also use
  `M`, `L`, `Q`, `C`, and `Z` path commands. Rendering is shared by viewport
  and exports. Fill rules, line caps, and line joins are supported; path tuple
  structure is reusable from `formats/schemas/path.schema.json`.
- **Characters and animation:** character JSON import/generation, editable
  character-part layers, hierarchical rotation rigs, and transform/keyframe
  evaluation.
- **Production features:** scene-scoped effects, audio timeline metadata,
  PNG/GIF/sprite-sheet/WebM export, project JSON validation, and performance
  improvements for large imports and timelines.

## Blueprint coverage

| Blueprint area | Status | Notes |
| --- | --- | --- |
| Project load/save, compatibility, and validation | Partial | Project version compatibility and structural/semantic checks exist; there is no general migration registry, dependency resolver, or complete schema/reference validation pipeline. |
| Drawing and paths | Partial | Point strokes and Bézier commands render and edit. Dedicated tessellation, robust Boolean path operations, stroke expansion, gradients, patterns, textures, masks, and clipping are not implemented. |
| Scene graph | Partial | Ordered layers, exposures, transforms, visibility, cameras, and character rigs exist. General drawable groups and parent-child scene objects with composed world transforms do not. |
| Procedural characters | Partial | A configurable character generator produces editable parts. It is a focused generator, not the full anatomy-guided builder suite in the blueprint. |
| Character scenes | Partial | Characters can be imported and placed as layers; full character instances, lighting/material pipeline, and compositional scene graph are not implemented. |
| Animation | Partial | Timeline, exposures, transform interpolation, camera animation, and bone rotation tracks exist. IK, deformation, facial animation tracks, and path deformation do not. |
| Rendering and export | Partial | Browser Canvas renderer and several exports exist. Dedicated rasterizer/compositor, render cache, lighting/shadow pipeline, color management, and video export service are not implemented. |
| Performance and determinism | Partial | Large timeline/import bottlenecks have targeted fixes and effects use deterministic seeds. General geometry/layer caches and invalidation tracking do not exist. |
| Schemas | Partial | Core project, character, scene, animation, rig, effects, render, drawing, and path schemas exist. Separate style, palette, material, lighting, asset, audio, and export schemas remain roadmap work. |

## Next implementation order

1. Complete drawing foundation: reusable style schema, fill/stroke style
   coverage, compound contour rules, and focused rendering/geometry tests.
2. Add geometry operations: clipping/masks and tessellation only where the
   editor's supported drawing model needs them; keep the existing Canvas
   renderer as the compatibility path.
3. Extend the scene model with explicit drawable groups and parent-child
   transform composition, preserving current layer ordering and project loads.
4. Expand character generation as independently testable editable builders,
   then add character-instance placement to scenes.
5. Extend animation with explicit rig/IK/deformation data and evaluation before
   adding new editing UI.
6. Improve rendering/performance through measured cache invalidation and
   incremental redraws; avoid caching mutable geometry without invalidation.
7. Add dedicated schemas and APIs as each corresponding feature becomes
   executable, rather than introducing unused schema-only promises.

## Architectural constraints

- Preserve point-based drawings and existing project compatibility.
- Keep viewport and export rendering behavior aligned.
- Keep generated artwork editable in the normal drawing/scene model.
- Validate user documents with actionable paths and reject unsupported
  operations explicitly.
- Treat the blueprint as a target architecture, not a claim that every
  listed subsystem is already present.
