# Drawing Engine

Drawings are ordered vector strokes stored in `formats/schemas/drawing.schema.json`.
The original `points` form remains supported for brush/pen strokes and existing
projects. Curved artwork can instead use `commands`, an ordered list of path
tuples:

- `["M", x, y]` moves to the initial point and must be first.
- `["L", x, y]` draws a straight segment.
- `["Q", cx, cy, x, y]` draws a quadratic Bézier segment.
- `["C", c1x, c1y, c2x, c2y, x, y]` draws a cubic Bézier segment.
- `["Z"]` closes the current contour.

A stroke must use exactly one geometry representation (`points` or `commands`).
Coordinates are local to the layer, like point-based strokes. Existing style
properties such as `color`, `width`, `opacity`, and `fill` apply to either form. Optional
`line_cap` (`butt`, `round`, `square`) and `line_join` (`bevel`, `round`,
`miter`) control stroke ends and corners. `fill_rule` supports `nonzero` and
`evenodd`, which is useful for compound paths with holes. Paths use the shared
tuple and ordering rules in `formats/schemas/path.schema.json`.
The editor renders paths in the viewport and exports, includes them in drawing
asset previews and bounds, and lets Edit mode move path anchors and control
points. Deleting selected path handles removes that path stroke; point-based
strokes retain their existing per-point deletion behavior.

Backend validation checks command names, coordinate counts and values, command
ordering, path segments, and supported line/fill style values. Character-part
strokes use the same drawing-stroke schema and validation rules.
