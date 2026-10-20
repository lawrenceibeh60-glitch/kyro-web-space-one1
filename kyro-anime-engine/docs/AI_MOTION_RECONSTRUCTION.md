# KAE AI engine context and reference motion workflow

## What this adds

- `GET /api/ai/capabilities` exposes KAE's native project settings, API capabilities, and readable JSON-schema summaries.
- AI chat includes the capability inventory and a compact summary of the currently open project.
- The integrated AI Workspace can preview a local video, sample up to six timestamped JPEG frames in the browser, and send those frames (not the original video file) to the configured vision-capable chat model for analysis.
- `POST /api/ai/animation/plan` requests a structured transform-keyframe plan for existing scene layers. The server validates scene IDs, layer IDs, frame bounds, channels, easing modes, and numeric values before returning the plan.
- `POST /api/ai/video/reconstruction/plan` requests a small, bounded set of normalized vector contours from sampled frames. The server validates colors, path commands, coordinate ranges, stroke counts, and canvas scaling before returning editable vector cels.
- `POST /api/ai/video/reconstruction/apply` revalidates the plan and adds its drawings plus a new drawing layer with frame exposures. It preserves existing layers and artwork and runs the native project validator before saving.
- The user reviews the plan and explicitly applies it through KAE's existing timeline-script API. The plan endpoint itself does not modify the project.

## Current boundary

This is the first working reference-analysis and vector-cel reconstruction slice, not pixel-perfect video-to-anime reconstruction. It can analyze sampled frames, request a rough vector approximation for each sampled pose, create editable native vector drawings, and add those drawings as exposures on a new layer. It also supports transform-keyframe plans for existing layers. The reconstruction is limited to 2–6 sampled cels and 96 total strokes; it does not automatically segment a character into rigged parts, infer hidden anatomy perfectly, or generate every source-video frame. Results depend on the vision model's ability to return structured vector paths.

The configured chat model must support image inputs for video-frame analysis. If the provider rejects image inputs or returns an access denial, the UI surfaces the error; it must not attempt to evade provider security controls.

## API payload sketch

Video analysis:

```json
{
  "frames": [
    { "timestamp_seconds": 0.0, "data_url": "data:image/jpeg;base64,..." }
  ],
  "project": { "id": "example", "settings": { "width": 1920, "height": 1080, "fps": 24, "duration_frames": 120 } }
}
```

Animation plan generation:

```json
{
  "project_id": "example",
  "analysis": "Analysis returned by /api/ai/video/analyze",
  "direction": "Preserve the action, emphasize the jump, and slow the landing."
}
```

A plan is returned as `{ summary, ops, applied: false }`. Each operation uses the existing timeline-script shape:

```json
{
  "op": "set_key",
  "scene_id": "scene_1",
  "layer_id": "layer_1",
  "channel": "x",
  "time": 12,
  "value": 320,
  "ease": "ease_in_out"
}
```

All frame indices are zero-based and must fit inside the current project's duration. Only supported transform channels on existing layers are accepted.
