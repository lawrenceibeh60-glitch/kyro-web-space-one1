# Project Format

## Current format

<<<<<<< Updated upstream
Projects use a single JSON document with `format: "kae"` and `version: 1`. The canonical structure is described by the JSON Schema files in `formats/schemas/`; `formats/examples/project.json` is a complete example.

The root schema composes reusable drawing, scene, animation, character, rig, and effect definitions. Schema references are checked by `tests/test_schema_integrity.py` so an empty or renamed schema cannot silently break the format contract.

The backend import endpoint (`POST /api/projects/import`) accepts a project document and validates it before saving. To import older/minimal project JSON, missing `format` and `version` are set to the current values, missing settings use the editor defaults, and missing drawings use an empty object. If `scenes` is omitted, import creates a blank scene and drawing layer. Missing optional `palette`, `characters`, `effects`, `rigs`, and `audio` collections become empty arrays. Explicitly supplied but invalid values are rejected rather than silently replaced.

Projects with a version newer than the running app supports are rejected on import and save. This prevents an older editor from silently rewriting data whose semantics it does not understand. Existing version 1 documents retain their optional fields and drawing/layer references through save and reload. The browser's **Import Files** workflow is additive: it preserves existing components with conflicting IDs and skips audio metadata because the audio bytes are stored separately.

## Camera animation

Scene cameras support `x`, `y`, `rotation`, `scale_x`, and `scale_y` transform values and matching keyframe tracks. Missing `scale_y` defaults to `1`, preserving existing projects. Both zoom axes use the supported range `0.05..32`. This provides independent 2D scaling, not perspective projection or a true 3D orbit.

Camera tracks use the shared animation keyframe structure and must be ordered by increasing frame number. The viewport and renderer use the camera evaluator; camera pointer mapping must apply the inverse rotation and each scale axis independently.

## Validation and compatibility checks

Validation checks document structure, numeric limits, unique IDs, animation tracks, and references such as layer exposures to drawings. Imports and saves must pass validation before persistence. Regression coverage for legacy defaults, unsupported future versions, and large import/reload round trips is in `tests/test_project_compatibility.py`. Schema file/reference integrity and the supported camera-axis contract are covered by `tests/test_schema_integrity.py`.

A new format field should be added only when its runtime behavior exists. If a future change alters existing field semantics, add an explicit migration and compatibility tests rather than silently reinterpreting saved projects.


### Layer perspective yaw

Layer transforms and keyframe tracks may include `rotation_y` from -180 to 180 degrees. The renderer projects point and Bézier coordinates with a perspective plane transform. For a convincing character turn, use separate front/profile drawings and animate their opacity through the turn. The channel adds perspective to flat artwork; it does not create hidden back-side geometry.
=======
Projects use a single JSON document with `format: "kae"` and current
`version: 2`. The
canonical structure and field constraints are defined by
[`formats/schemas/project.schema.json`](../formats/schemas/project.schema.json);
`formats/examples/project.json` is a complete example.

The backend import endpoint (`POST /api/projects/import`) accepts a project
document and validates it before saving. To import older/minimal project JSON,
missing `format` is set to `kae`; an omitted `version` is treated as version 1
and migrated. Missing settings use the editor defaults, and missing drawings
use an empty object. If `scenes` is omitted, import creates a blank scene and
drawing layer. Missing optional `palette`, `styles`, `characters`, `effects`,
`rigs`, and `audio` collections become empty arrays. Explicitly supplied but
invalid values are rejected rather than silently replaced.

Projects with a version newer than the running app supports are rejected on
import and save. This prevents an older editor from silently rewriting data
whose semantics it does not understand. Existing version 1 documents retain
their optional fields and drawing/layer references through migration, save,
and reload. The version 1 to version 2 migration adds the optional reusable
`styles` collection without changing existing drawings, scenes, or keyframes.
Project parsing and serialization both run the migration; the JSON Schema
validator accepts both supported versions and the semantic validator checks
cross-references such as exposure-to-drawing IDs and unique IDs.
The browser's **Import Files** workflow is additive: it preserves existing
components with conflicting IDs and skips audio metadata because the audio
bytes are stored separately.

## Validation and compatibility checks

Validation checks document structure against the Draft 2020-12 schemas,
numeric limits, unique IDs, animation tracks, and references such as layer
exposures to drawings. Imports and saves must pass validation before
persistence. Regression coverage for legacy defaults, migration, unsupported
future versions, and large import/reload round trips is in
`tests/test_project_compatibility.py`.
>>>>>>> Stashed changes
