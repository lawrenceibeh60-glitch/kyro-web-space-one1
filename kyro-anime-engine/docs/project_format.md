# Project Format

## Current format

Projects use a single JSON document with `format: "kae"` and `version: 1`. The
canonical structure and field constraints are defined by
[`formats/schemas/project.schema.json`](../formats/schemas/project.schema.json);
`formats/examples/project.json` is a complete example.

The backend import endpoint (`POST /api/projects/import`) accepts a project
document and validates it before saving. To import older/minimal project JSON,
missing `format` and `version` are set to the current values, missing settings
use the editor defaults, and missing drawings use an empty object. If `scenes`
is omitted, import creates a blank scene and drawing layer. Missing optional
`palette`, `characters`, `effects`, `rigs`, and `audio` collections become
empty arrays. Explicitly supplied but invalid values are rejected rather than
silently replaced.

Projects with a version newer than the running app supports are rejected on
import and save. This prevents an older editor from silently rewriting data
whose semantics it does not understand. Existing version 1 documents retain
their optional fields and drawing/layer references through save and reload.
The browser's **Import Files** workflow is additive: it preserves existing
components with conflicting IDs and skips audio metadata because the audio
bytes are stored separately.

## Validation and compatibility checks

Validation checks document structure, numeric limits, unique IDs, animation
tracks, and references such as layer exposures to drawings. Imports and saves
must pass validation before persistence. Regression coverage for legacy
defaults, unsupported future versions, and large import/reload round trips is
in `tests/test_project_compatibility.py`.
