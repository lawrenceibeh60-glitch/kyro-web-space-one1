"""Machine-readable capability inventory for KAE's AI assistant.

Keep this registry aligned with backend/api routes and project schemas. It is
intentionally descriptive: the model may propose operations, but the server
must validate and execute them through the normal KAE services.
"""
from pathlib import Path
import json

import config


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
            "scene_count": len(project.get("scenes", [])) if isinstance(project.get("scenes"), list) else 0,
            "drawing_count": len(project.get("drawings", {})) if isinstance(project.get("drawings"), dict) else 0,
            "character_count": len(project.get("characters", [])) if isinstance(project.get("characters"), list) else 0,
            "rig_count": len(project.get("rigs", [])) if isinstance(project.get("rigs"), list) else 0,
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
