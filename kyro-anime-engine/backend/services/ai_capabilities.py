"""Machine-readable capability inventory for KAE's AI assistant.

Keep this registry aligned with backend/api routes and project schemas. It is
intentionally descriptive: the model may propose operations, but the server
must validate and execute them through the normal KAE services.
"""
from pathlib import Path
import json

import config



def _tags_for(text):
    """Stable semantic tags let the AI choose real KAE tools and fields by intent."""
    source = str(text).lower()
    groups = {
        "project": ("project", "save", "open", "workspace"),
        "scene": ("scene", "story", "shot", "composition"),
        "drawing": ("drawing", "vector", "stroke", "path", "fill", "color", "colour", "canvas", "brush"),
        "character": ("character", "face", "hair", "costume", "outfit", "expression", "silhouette"),
        "animation": ("animation", "cel", "frame", "keyframe", "motion", "pose", "playback"),
        "timeline": ("timeline", "marker", "range", "fps", "duration", "frame"),
        "rigging": ("rig", "bone", "skin", "weight", "constraint", "skeleton"),
        "camera": ("camera", "zoom", "pan", "focus", "lens", "fov"),
        "render": ("render", "export", "video", "webm", "output"),
        "validation": ("valid", "schema", "error", "constraint", "format"),
        "ai": ("ai", "model", "provider", "prompt", "story", "vision", "image"),
        "audio": ("audio", "sound", "voice", "dialogue", "music"),
        "effects": ("effect", "filter", "composite", "transition", "light", "shadow"),
        "assets": ("asset", "import", "reference", "texture", "image"),
    }
    tags = [tag for tag, words in groups.items() if any(word in source for word in words)]
    return tags or ["general"]

def _schema_inventory():
    items = []
    for path in sorted(config.SCHEMAS_DIR.glob("*.schema.json")):
        try:
            schema = json.loads(path.read_text(encoding="utf-8"))
            items.append({
                "name": path.name.removesuffix(".schema.json"),
                "title": schema.get("title", path.stem),
                "description": schema.get("description", ""),
                "required": schema.get("required", []),
                "properties": list((schema.get("properties") or {}).keys()),
                "tags": _tags_for(path.stem + " " + schema.get("title", "") + " " + schema.get("description", "")),
                "property_tags": {key: _tags_for(key + " " + str(value.get("description", ""))) for key, value in (schema.get("properties") or {}).items() if isinstance(value, dict)},
            })
        except (OSError, json.JSONDecodeError):
            continue
    return items


def get_capabilities():
    """Return truthful tool/API and native project-format metadata."""
    routes = [
        {"name": "projects.list", "method": "GET", "path": "/api/projects", "purpose": "List saved projects."},
        {"name": "projects.create", "method": "POST", "path": "/api/projects", "purpose": "Create a validated native KAE project."},
        {"name": "projects.read", "method": "GET", "path": "/api/projects/{project_id}", "purpose": "Read the full native project document."},
        {"name": "projects.save", "method": "PUT", "path": "/api/projects/{project_id}", "purpose": "Validate and save a full project document."},
        {"name": "scenes.list", "method": "GET", "path": "/api/projects/{project_id}/scenes", "purpose": "List scenes."},
        {"name": "scenes.create", "method": "POST", "path": "/api/projects/{project_id}/scenes", "purpose": "Create a scene using the scene service."},
        {"name": "drawings.list", "method": "GET", "path": "/api/projects/{project_id}/drawings", "purpose": "List drawings."},
        {"name": "drawings.create", "method": "POST", "path": "/api/projects/{project_id}/drawings", "purpose": "Create a drawing using the drawing service."},
        {"name": "drawings.update", "method": "PUT", "path": "/api/projects/{project_id}/drawings/{drawing_id}", "purpose": "Update a drawing."},
        {"name": "animations.list", "method": "GET", "path": "/api/projects/{project_id}/animations", "purpose": "List animation clips."},
        {"name": "animations.create", "method": "POST", "path": "/api/projects/{project_id}/animations", "purpose": "Create an animation clip."},
        {"name": "timeline.read", "method": "GET", "path": "/api/projects/{project_id}/timeline", "purpose": "Read timeline summary."},
        {"name": "timeline.keyframe", "method": "POST", "path": "/api/projects/{project_id}/timeline/keyframe", "purpose": "Create a validated timeline keyframe."},
        {"name": "rigs", "method": "GET/POST", "path": "/api/projects/{project_id}/rigs", "purpose": "Access character rig endpoints; inspect current route schema before use."},
        {"name": "schemas.list", "method": "GET", "path": "/api/schemas", "purpose": "Discover native KAE JSON schemas."},
        {"name": "rendering", "method": "GET/POST", "path": "/api/projects/{project_id}/render", "purpose": "Use supported project rendering operations."},
        {"name": "exports", "method": "GET/POST", "path": "/api/exports", "purpose": "Use supported export operations."},
        {"name": "ai.chat", "method": "POST", "path": "/api/ai/chat", "purpose": "Discuss KAE capabilities and the current project."},
        {"name": "ai.video.analyze", "method": "POST", "path": "/api/ai/video/analyze", "purpose": "Analyze timestamped JPEG frames sampled locally from a reference video."},
        {"name": "ai.video.reconstruction.plan", "method": "POST", "path": "/api/ai/video/reconstruction/plan", "purpose": "Propose bounded editable vector cels from sampled reference frames; does not mutate the project."},
        {"name": "ai.video.reconstruction.apply", "method": "POST", "path": "/api/ai/video/reconstruction/apply", "purpose": "Validate and add vector drawings on a new layer, preserving existing project art."},
        {"name": "ai.animation.plan", "method": "POST", "path": "/api/ai/animation/plan", "purpose": "Generate validated transform-keyframe operations for existing scene layers; does not mutate the project."},
        {"name": "ai.story.outline", "method": "POST", "path": "/api/ai/story/outline", "purpose": "Expand a story into continuity-aware scenes."},
        {"name": "ai.story.vector-plan", "method": "POST", "path": "/api/ai/story/vector-plan", "purpose": "Plan scene composition, then produce native vector-cel JSON."},
    ]
    for tool in routes:
        tool["tags"] = _tags_for(tool.get("name", "") + " " + tool.get("purpose", "") + " " + tool.get("path", ""))
    editor_actions = [
        {"name": "timeline.marker.create", "surface": "timeline", "purpose": "Add a named marker at a frame; optional color; use existing timeline marker controls.", "tags": ["timeline", "marker", "navigation"]},
        {"name": "timeline.marker.rename", "surface": "timeline", "purpose": "Rename a selected marker while preserving its frame.", "tags": ["timeline", "marker", "metadata"]},
        {"name": "timeline.marker.delete", "surface": "timeline", "purpose": "Delete a selected marker through the editor undo flow.", "tags": ["timeline", "marker", "delete"]},
        {"name": "timeline.preview_range.set", "surface": "timeline", "purpose": "Set inclusive preview start/end frames for playback and looping.", "tags": ["timeline", "playback", "range"]},
        {"name": "timeline.playback", "surface": "timeline", "purpose": "Play, pause, loop and scrub the current animation using native editor controls.", "tags": ["timeline", "animation", "playback"]},
        {"name": "drawing.vector_cels.apply", "surface": "canvas", "purpose": "Apply validated editable vector cels through kae:ai-draw-frames; creates a new drawing layer and preserves existing art.", "tags": ["drawing", "vector", "canvas", "animation", "apply"]},
        {"name": "animation.transform.plan", "surface": "timeline", "purpose": "Plan transform keyframes for existing layers using the AI animation plan endpoint, then request explicit apply.", "tags": ["animation", "timeline", "keyframe", "transform"]},
        {"name": "character.rig.inspect", "surface": "character", "purpose": "Inspect supported character and rig schema before proposing rig changes.", "tags": ["character", "rigging", "schema"]},
        {"name": "reference.image.generate", "surface": "ai_studio", "purpose": "Generate an optional concept image with the configured xKiro image model; pass it to the text model as a visual reference when supported.", "tags": ["ai", "image", "reference", "character", "design"]},
        {"name": "story.json.validate", "surface": "ai_studio", "purpose": "Validate complete JSON structure and native vector frame shape before exposing Move to Project.", "tags": ["ai", "validation", "json", "drawing"]},
    ]
    return {
        "engine": "Kyro Animation Engine (KAE)",
        "format": {"name": "kae", "versions": [1, 2]},
        "project_settings": {
            "width": {"type": "integer", "min": 16, "max": 8192, "unit": "pixels"},
            "height": {"type": "integer", "min": 16, "max": 8192, "unit": "pixels"},
            "fps": {"type": "number", "min_exclusive": 0, "max": 120, "unit": "frames/second"},
            "duration_frames": {"type": "integer", "min": 1},
            "duration_seconds_formula": "duration_frames / fps",
            "frame_indexing": "KAE timeline keyframes use zero-based frame positions unless a specific schema says otherwise.",
        },
        "safety": [
            "Never invent a tool, endpoint, field, or schema property.",
            "Do not claim a project was changed unless a KAE operation succeeded.",
            "Preserve unrelated project data and existing character identity.",
            "Validate dimensions, frame positions, and references before applying changes.",
            "Prefer a plan and request confirmation before broad destructive edits.",
        ],
        "tools": routes,
        "editor_actions": editor_actions,
        "schemas": _schema_inventory(),
    }


def build_system_context(project=None):
    capabilities = get_capabilities()
    context = json.dumps(capabilities, ensure_ascii=False, separators=(",", ":"))
    project_context = ""
    if isinstance(project, dict):
        # Avoid sending embedded media or huge project documents back to the model.
        summary = {
            "id": project.get("id"),
            "name": project.get("name"),
            "version": project.get("version"),
            "settings": project.get("settings", {}),
            "scenes": [
                {
                    "id": scene.get("id"),
                    "name": scene.get("name"),
                    "layers": [
                        {"id": layer.get("id"), "name": layer.get("name"), "type": layer.get("type")}
                        for layer in scene.get("layers", []) if isinstance(layer, dict)
                    ],
                }
                for scene in project.get("scenes", [])[:20] if isinstance(scene, dict)
            ] if isinstance(project.get("scenes"), list) else [],
            "drawings": [
                {"id": drawing_id, "name": drawing.get("name")}
                for drawing_id, drawing in list(project.get("drawings", {}).items())[:100]
                if isinstance(drawing, dict)
            ] if isinstance(project.get("drawings"), dict) else [],
            "characters": [
                {"id": c.get("id"), "name": c.get("name")}
                for c in project.get("characters", [])[:100] if isinstance(c, dict)
            ] if isinstance(project.get("characters"), list) else [],
            "rigs": [
                {"id": rig.get("id"), "name": rig.get("name")}
                for rig in project.get("rigs", [])[:100] if isinstance(rig, dict)
            ] if isinstance(project.get("rigs"), list) else [],
        }
        project_context = "\nCURRENT PROJECT SUMMARY:\n" + json.dumps(summary, ensure_ascii=False)
    return (
        "You are KAE's embedded animation-engine assistant, not a generic chatbot. "
        "Use only the capabilities and schema facts listed below. Understand canvas "
        "dimensions in pixels, FPS, frame counts, timeline positions, drawings, scenes, "
        "characters, rigs, and native .kae project constraints. When asked to modify a "
        "project, give a concrete, structured plan tied to real KAE capabilities. "
        "Do not claim you executed edits unless the application confirms execution. "
        "If a requested operation is not implemented, state that clearly and propose "
        "the closest supported alternative. Ask for creative direction after reference "
        "analysis. Preserve the user's stated timing and design choices.\n"
        "KAE CAPABILITY INVENTORY:\n" + context + project_context
    )
