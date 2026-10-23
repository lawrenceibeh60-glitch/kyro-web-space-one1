# KYRO Anime Engine (KAE)

2D animation app, Blender-style: Flask backend + vanilla-JS canvas editor. Pydroid friendly.

## Run
```
pip install flask pillow
python run.py
```
Open http://127.0.0.1:5000. Choose one of the editable animation demos or create a blank project.

## Built so far
1. `formats/` - JSON schemas + example project (one shared format)
2. `backend/` - Flask app, atomic project save/load, validation, `/api/projects`
3. `frontend/` - Blender-style editor shell: viewport, outliner, properties, undo/redo
4. Drawing - brush (smoothing, pressure), stroke eraser, per-layer frames
5. Animation - playback, keyframes with easing, move/rotate/scale tools, dope sheet, auto-key
6. Export - PNG sequence (zip), GIF, sprite sheet + JSON atlas, and browser-recorded WebM; frames use the same renderer as the editor. Pillow is only needed for GIF and sprite sheets. All UI icons are inline SVG (`frontend/js/ui/icons.js`).
7. Blender-style UI - workspaces (Draw / Animate / Edit), switchable areas (Outliner, Properties, Timeline, Graph Editor, History, Asset Browser), editable drawing exposures, onion skin, Edit mode for stroke points, undo history, preferences + keymap, auto-save option; named frame markers with ruler flags and marker navigation; inclusive preview-range playback with start/end controls
8. Drawing tools - line, rectangle, ellipse, vector fill, canvas eyedropper, HSV color wheel, project palette, and Grease Pencil presets
9. Drawing assets - search project drawings, save the current frame as an asset, import/export drawing JSON, and place independent copies on the timeline
10. Camera - per-scene pan and zoom, keyframed at the current frame; select Camera (`K`) to drag-pan and wheel-zoom around the pointer. Framing is applied consistently in the viewport and image/video exports
11. 2.5D depth - adjust each layer's camera influence to create parallax between distant backgrounds and foreground art
12. Scene lighting - add, position, color, and tune soft radial lights in the Output properties; lights render in the viewport and exports
13. Demo gallery - Bouncing Ball, Parallax Ridge, Pendulum Study, and Orbit Study open as separate editable projects
14. JSON characters - import `formats/examples/character.json` in the Project JSON pane; stable character and part IDs update vector artwork in place, while existing animation tracks survive reimports that omit tracks
15. Expanded drawing controls - polygon and star shape tools, draggable graph-editor keyframes, a dedicated Studio workspace, and Focus Canvas (`Shift+F`, `Escape` to restore). Panel split adjusters have been removed to keep the canvas unobstructed
16. Camera movement modes - select Camera (`K`), then Pan to truck the shot, Dolly to zoom with drag/wheel, or Roll to rotate with drag/wheel; camera rotation is keyframable and exported with the scene
17. Studio features - scene-scoped lightning, particle, speed-line, and camera-shake effects; editable hierarchical 2D character rigs with per-part rotation keys; a color/hairstyle/expression character generator; and synchronized timeline audio with WebM mixing
18. Additive multi-file JSON import - select multiple project and character documents in one batch; project components merge by stable IDs, and character documents update matching character IDs while retaining existing part animation. A different project identity or canvas setup requires confirmation
19. Bézier path strokes - JSON drawings and character parts may use M/L/Q/C/Z path commands; paths render in the viewport and exports and can be selected and edited in Edit mode, with configurable fill rules, line caps, and joins

### Character JSON

Each `kae-character` document contains an `id` plus vector `parts`. A part's strokes use the same point-based drawing format as the editor; its transform positions the part, and optional `tracks` animate it. Import a character using **Import Character** in the Project JSON pane, or `POST /api/projects/<project_id>/characters/import`. The first import adds each part as a normal timeline layer. Reimporting the same character ID updates its drawings without duplicating layers; matching part IDs keep their layer IDs and retain existing transform/animation data unless the JSON supplies replacements. Parts can be selected and animated with the regular layer tools and timeline.

Choose stable IDs for a character and each part, and keep their combined generated drawing/layer IDs under 64 characters. To place a character in a particular scene, include its `scene_id`; otherwise an update keeps its existing placement and a new character goes into the first scene. The canonical input format is described by `formats/schemas/character.schema.json`.

Use **Import Files** in the Project JSON pane to select several `.json` files at once. Full project documents merge drawings, scenes, layers, characters, effects, rigs, lights, and palette colors by stable IDs; conflicting project components keep the open project's version. Character documents use their stable character ID as an upsert key, so a matching ID updates art while preserving part animation omitted from the incoming document. Audio clip metadata is not merged because the audio bytes are stored separately from project JSON; import audio files from the Audio studio tab.

Project JSON uses `format: "kae"` version 2. Version 1 projects migrate on import/load/save; the import endpoint supplies safe defaults for omitted legacy fields, creates a blank scene if `scenes` is omitted, and rejects versions newer than the running app supports. See [docs/project_format.md](docs/project_format.md) for compatibility and validation behavior.

### Studio workspace

Choose **Studio** in the workspace bar to open the Effects, Rig, Character, and Audio tools.

- Effects are scene-scoped and frame-ranged. Lightning, particles, speed lines, and camera shake render through the same frame renderer used by exports. Intensity, color, count/speed where relevant, enable state, and active frame range are editable and undoable.
- Create a rig for an imported/generated character, attach one bone to each character part, set its pivot, and optionally parent it to another bone. A bone's rotation affects its part and descendants; use **Key** to animate rotation at the current frame.
- Generate a vector anime character with stable ID, hairstyle, expression, hair/eye/skin/outfit colors. Reusing its ID updates the same editable part layers and preserves existing animation.
- Import WAV, MP3, OGG, M4A, AAC, or WebM audio clips. Set timeline start frame, trim offset, and volume. Playback follows the timeline; browser-recorded WebM exports mix the active audio clips. PNG, GIF, and sprite exports are silent.


## AI provider connections

Open the editor and choose **AI Workspace**. The AI Provider Connection panel supports OpenAI, Anthropic/Claude, Groq, OpenRouter, Together AI, DeepSeek, Mistral, xAI, Cerebras, Fireworks AI, Perplexity, NVIDIA NIM, xKiro, and custom OpenAI-compatible endpoints.

1. Choose a provider and enter its API key.
2. Use **Load models** to query the provider's model list. If the provider does not expose a compatible model-list endpoint, KAE shows its curated fallback list.
3. Choose a model and press **Test & connect**. The indicator turns green only after a real model response; failures show red with a sanitized error.
4. Chat, video-frame analysis, and AI planning/reconstruction use the selected provider for the current browser tab session.

Keys are sent to the KAE server over HTTPS only when you invoke an AI feature. They are not saved to server-side files or database and are kept in browser session storage for the current tab session. Do not use this with an untrusted KAE host. Provider model availability, API access, pricing, and rate limits are controlled by each provider. Image generation still uses the existing xKiro image endpoint; provider switching for image generation is not implied by the chat connection indicator.

## Cinematic demo reel

From the home screen, choose **Watch cinematic demo** or open `demo.html`. The original 24-second procedural anime-inspired motion study is drawn live in a 1280×720 canvas with layered parallax, character motion, energy trails, and a cinematic HUD. Use **Record WebM** to record the live animation to a WebM video file on a browser/device that supports `MediaRecorder`; recording happens locally and the video is not uploaded.

## Shortcuts
`B` brush, `G` Grease Pencil, `E` eraser, `H` hand, `K` camera, `M` move, `R` rotate, `S` scale, `[` `]` size.
`L` line, `U` rectangle, `O` ellipse, `P` hexagon, `T` star, `F` vector fill, `C` eyedropper.
`Space` play, `I` key all, `Alt+I` unkey, `X` delete selected key, `Up/Down` jump key, `Left/Right` frame, `Home/End`.
`Tab` Edit mode, `A` select all points, `X` delete key/points.
`Shift+F` focus/restore the canvas, `Escape` restore panels, `Ctrl+Z` / `Ctrl+Shift+Z` undo/redo, `Ctrl+S` save, `Ctrl+E` export, `0` fit. Two fingers pan/zoom on touch.

## Remaining scaffold
The `engine/` tree contains additional planned modules that are not yet connected to the editor workflow.

See [docs/architecture.md](docs/architecture.md) for an honest blueprint status and remaining implementation roadmap.


## Anime production upgrade pass

This pass adds a small but important quality and usability improvement without replacing the native vector workflow:

- Generated characters include editable hair-sheen strokes, fringe highlights, jacket seams and buttons, sleeve-cuff seams, and shoe details. These remain ordinary strokes inside the existing stable character parts, so they can still be edited, rigged, and weighted.
- Studio effects include a screen-blended cinematic glow pass, frame-pulsed impact flashes, per-layer soft shadows, depth-aware blur between depth planes, alpha-based layer masks, and procedural facial blink/mouth animation for generated characters. These are saved as native scene effects and rendered in the same frame path used for previews and exports.
- Layers may define a vector `clip_path` in layer-local coordinates. Rig deformation uses a bounded per-stroke/per-rig frame cache for non-procedural poses, retaining only recent frames.
- The Object Inspector exposes a validated vector clipping-path editor with undoable apply/clear. Facial animation effects also support manually keyed neutral/smile/open mouth poses at exact timeline frames for dialogue timing, alongside procedural blinking and fallback mouth motion.
- The mobile layout now keeps the timeline's bottom-area height independent from desktop workspace presets. The workspace selector previously set `--slotC-h` on the root element, overriding the intended phone-sized timeline height; the editor now applies a mobile-specific local value, with portrait and landscape adjustments.
- Regression assertions verify the generated detail strokes and continue validating the character document against the canonical schema.

The current editor already contains the rigging, IK, weighted vector deformation, walk-cycle authoring, camera motion, scene effects, and export foundations listed above. These are not a promise of a full 3D renderer: KAE remains a 2D/2.5D production editor. True mesh deformation across arbitrary artwork, production-grade masks and advanced within-character depth-of-field/shadow controls, and pixel-perfect automatic video reconstruction still require separate validated implementation work.


## Character Line Tracement and procedural curve nodes

- In Studio → Rig, select a character rig and the character part the new bone should control. Enable **Character Line Tracement** and **Bone Rigging**, then draw from the joint/pivot toward the next joint. Releasing the pointer creates an editable rig bone with pivot, length, angle, and a parent link when an existing bone endpoint is close enough. The action is undoable through the normal editor history.
- The tool works with mouse, touch, or stylus through the viewport's existing world-coordinate pointer events. It draws a temporary guide only; it does not add permanent artwork.
- The Geometry Nodes workspace now includes Ellipse, Line, Bezier Curve, Subdivide, Smooth Curve, and Reverse Curve nodes. Their parameters are editable in the node inspector, and open curves render as open paths in the live preview. The project node-graph schema accepts these node types.
- Project import accepts `.kaa` as a JSON-based native project extension alongside `.json`. This is an extension-level compatibility step; it does not yet introduce a binary container or Base64 raster-asset pipeline.

Current scope note: Character Line Tracement creates and connects bones; accurate skin weights still need artist review, and automatic reconstruction of unseen head views is not implemented. Rig Studio supports saved linear/eased motion-path root clips alongside procedural walk cycles and existing two-bone IK constraints. The Geometry Nodes workspace remains a procedural vector-geometry graph rather than a full image compositor graph. The Rig Studio Pose Library now captures named bone-rotation poses and applies them as keys at the current frame while preserving other keyframes. Character Line Tracement snaps a new bone's start to nearby existing pivots/endpoints to make joint connections more reliable. Saved two-bone IK constraints now have constraint-specific schema validation, and Rig Studio can switch a saved target between IK solving and FK editing without deleting the target. Rig Studio also includes keyed head/face orientation controls for yaw, pitch foreshortening, roll, and depth scale; these write ordinary editable transform tracks on the active artwork layer.


### Editor guide settings and expanded procedural nodes

The Rig workspace now includes persistent viewport-only construction guides: grid, center axes, composition thirds, head proportion oval, and a simplified body pose guide. Guide color, opacity, and spacing are project-saved under `editor_settings.guides`; the overlay is separate from render/export output.

The procedural geometry node library adds regular polygon, grid, resample curve, translate geometry, deterministic noise deformation, and bounding-box generation, alongside the existing circle/rectangle/ellipse/line/Bézier/subdivide/smooth/reverse/transform/join/array/mirror/output nodes. Node search filters the available node types. These are evaluated 2D geometry operations, not a claim of full Blender Geometry Nodes compatibility.

**Validation note:** schema validation now accepts the new procedural node types and project-persisted guide settings. Browser regression coverage includes motion-path authoring/evaluation. The renderer now evaluates Color Grade, Levels/Contrast, and Cinematic Vignette as post-composite effects. This is a focused compositor pass, not a full node-based image compositor. The timeline uses requestAnimationFrame-coalesced drawing and virtualized visible rows; broader performance claims require profiling on real projects. True unseen-head reconstruction and fully automatic production-quality skin weights remain separate work.

The timeline also exposes an undoable project FPS selector (8, 12, 15, 24, 25, 30, 48, 50, or 60 FPS); changing rate stops active playback and the control resynchronizes after undo/redo. Existing timeline drawing is requestAnimationFrame-coalesced and its visible layer rows are virtualized.
