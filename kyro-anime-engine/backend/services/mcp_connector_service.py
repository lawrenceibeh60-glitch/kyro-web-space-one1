"""Provider-neutral MCP tools for KYRO Animation Engine."""
from copy import deepcopy
from datetime import datetime, timezone
import hmac
import os
import re

from backend.app.exceptions import ApiError
from backend.services import project_service, scene_service
from backend.services.validation_service import validate_project
from backend.storage import project_repository as repo

PROTOCOL_VERSION = "2025-11-25"
SUPPORTED_PROTOCOLS = {PROTOCOL_VERSION, "2025-06-18", "2025-03-26", "2024-11-05"}
ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def authenticate(authorization):
    expected = os.environ.get("KAE_MCP_API_KEY", "")
    if not expected:
        return False, "KAE_MCP_API_KEY is not configured"
    supplied = authorization[7:].strip() if isinstance(authorization, str) and authorization.lower().startswith("bearer ") else ""
    if not supplied or not hmac.compare_digest(supplied, expected):
        return False, "Invalid or missing bearer token"
    return True, ""


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _project(pid):
    if not isinstance(pid, str) or not pid.strip():
        raise ApiError(400, "project_id must be a non-empty string")
    return repo.load(pid)


def _valid_id(value, field):
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise ApiError(400, f"{field} must contain 1-64 letters, numbers, underscores, or hyphens")
    return value


def _save(pid, project):
    project["modified"] = _now()
    errors = validate_project(project)
    if errors:
        raise ApiError(422, "Project failed KAE validation", errors)
    repo.save(pid, project)
    return project


def _touch(pid):
    """Advance the project revision after scene_service mutations."""
    project = _project(pid)
    return _save(pid, project)


def _scene(project, scene_id=None):
    scenes = project.get("scenes", [])
    if scene_id is None:
        if not scenes:
            raise ApiError(422, "Project has no scenes")
        return scenes[0]
    for scene in scenes:
        if scene.get("id") == scene_id:
            return scene
    raise ApiError(404, f"Scene '{scene_id}' not found")


def list_tools():
    return [
        {"name":"kae_list_projects","title":"List KAE projects","description":"List available animation projects. Use this to find the project_id.","inputSchema":{"type":"object","properties":{},"additionalProperties":False},"annotations":{"readOnlyHint":True,"destructiveHint":False,"idempotentHint":True,"openWorldHint":False}},
        {"name":"kae_get_project","title":"Inspect KAE project","description":"Read a native KAE project, including settings, scenes, drawings and animation. Set include_drawings=false for a compact overview.","inputSchema":{"type":"object","properties":{"project_id":{"type":"string","minLength":1},"include_drawings":{"type":"boolean","default":True}},"required":["project_id"],"additionalProperties":False},"annotations":{"readOnlyHint":True,"destructiveHint":False,"idempotentHint":True,"openWorldHint":False}},
        {"name":"kae_get_scene_context","title":"Inspect scene and layers","description":"Read scene layers, exposures, drawing IDs and stroke counts before editing. If scene_id is omitted, returns the first scene.","inputSchema":{"type":"object","properties":{"project_id":{"type":"string","minLength":1},"scene_id":{"type":"string"},"include_strokes":{"type":"boolean","default":False}},"required":["project_id"],"additionalProperties":False},"annotations":{"readOnlyHint":True,"destructiveHint":False,"idempotentHint":True,"openWorldHint":False}},
        {"name":"kae_add_drawing","title":"Add vector drawing","description":"Create native editable KAE artwork from validated stroke/path JSON in project canvas coordinates. Paths may use M/L/Q/C/Z commands.","inputSchema":{"type":"object","properties":{"project_id":{"type":"string","minLength":1},"drawing_id":{"type":"string","pattern":"^[A-Za-z0-9_-]{1,64}$"},"name":{"type":"string","minLength":1,"maxLength":120},"strokes":{"type":"array","items":{"type":"object"}}},"required":["project_id","drawing_id","name","strokes"],"additionalProperties":False},"annotations":{"readOnlyHint":False,"destructiveHint":False,"idempotentHint":False,"openWorldHint":False}},
        {"name":"kae_append_strokes","title":"Draw on existing artwork","description":"Append editable strokes to an existing drawing. Stroke IDs must be unique within that drawing.","inputSchema":{"type":"object","properties":{"project_id":{"type":"string","minLength":1},"drawing_id":{"type":"string","minLength":1},"strokes":{"type":"array","minItems":1,"items":{"type":"object"}}},"required":["project_id","drawing_id","strokes"],"additionalProperties":False},"annotations":{"readOnlyHint":False,"destructiveHint":False,"idempotentHint":False,"openWorldHint":False}},
        {"name":"kae_create_drawing_layer","title":"Place drawing on timeline","description":"Create a scene layer exposing an existing drawing over a frame range so artwork can appear in the editor.","inputSchema":{"type":"object","properties":{"project_id":{"type":"string","minLength":1},"scene_id":{"type":"string"},"layer_id":{"type":"string","pattern":"^[A-Za-z0-9_-]{1,64}$"},"name":{"type":"string","minLength":1,"maxLength":120},"drawing_id":{"type":"string","minLength":1},"start_frame":{"type":"integer","minimum":0,"default":0},"length":{"type":"integer","minimum":1,"maximum":2000,"default":24}},"required":["project_id","scene_id","layer_id","name","drawing_id"],"additionalProperties":False},"annotations":{"readOnlyHint":False,"destructiveHint":False,"idempotentHint":False,"openWorldHint":False}},
        {"name":"kae_update_layer","title":"Update layer properties","description":"Update layer name, visibility, lock state, opacity, or transform while preserving artwork and animation tracks.","inputSchema":{"type":"object","properties":{"project_id":{"type":"string","minLength":1},"scene_id":{"type":"string","minLength":1},"layer_id":{"type":"string","minLength":1},"name":{"type":"string","maxLength":120},"visible":{"type":"boolean"},"locked":{"type":"boolean"},"opacity":{"type":"number","minimum":0,"maximum":1},"transform":{"type":"object","properties":{"x":{"type":"number"},"y":{"type":"number"},"rotation":{"type":"number"},"scale_x":{"type":"number"},"scale_y":{"type":"number"},"opacity":{"type":"number","minimum":0,"maximum":1},"anchor_x":{"type":"number"},"anchor_y":{"type":"number"}},"additionalProperties":False}},"required":["project_id","scene_id","layer_id"],"additionalProperties":False},"annotations":{"readOnlyHint":False,"destructiveHint":False,"idempotentHint":False,"openWorldHint":False}},
        {"name":"kae_delete_layer","title":"Delete layer","description":"Remove a layer from a scene. Requires confirm=true. Referenced drawings are not deleted.","inputSchema":{"type":"object","properties":{"project_id":{"type":"string","minLength":1},"scene_id":{"type":"string","minLength":1},"layer_id":{"type":"string","minLength":1},"confirm":{"type":"boolean"}},"required":["project_id","scene_id","layer_id","confirm"],"additionalProperties":False},"annotations":{"readOnlyHint":False,"destructiveHint":True,"idempotentHint":False,"openWorldHint":False}},
    ]


def _scene_context(pid, args):
    project = _project(pid)
    scene = _scene(project, args.get("scene_id"))
    layers = []
    for layer in scene.get("layers", []):
        item = deepcopy(layer)
        for exposure in item.get("exposures", []):
            drawing = project.get("drawings", {}).get(exposure.get("drawing"))
            if drawing:
                exposure["drawing_name"] = drawing.get("name", drawing.get("id"))
                exposure["stroke_count"] = len(drawing.get("strokes", []))
        layers.append(item)
    if not args.get("include_strokes", False):
        # Drawing payloads are returned through the drawing catalog, not duplicated in every exposure.
        pass
    return {"project_id":project.get("id"),"project_name":project.get("name"),"modified":project.get("modified"),"settings":project.get("settings",{}),"scene":{**{k:deepcopy(v) for k,v in scene.items() if k!="layers"},"layers":layers},"drawing_catalog":[{"id":key,"name":value.get("name",key),"stroke_count":len(value.get("strokes",[]))} for key,value in project.get("drawings",{}).items()]}


def call_tool(name, args):
    if not isinstance(args, dict):
        raise ApiError(400, "Tool arguments must be an object")
    if name == "kae_list_projects":
        return {"projects": project_service.list_projects()}
    if name == "kae_get_project":
        project = _project(args.get("project_id"))
        if not args.get("include_drawings", True):
            project = deepcopy(project)
            project["drawings"] = {key:{"id":value.get("id",key),"name":value.get("name",key),"stroke_count":len(value.get("strokes",[]))} for key,value in project.get("drawings",{}).items()}
        return project
    if name == "kae_get_scene_context":
        return _scene_context(args.get("project_id"), args)
    if name == "kae_add_drawing":
        pid = args.get("project_id")
        project = _project(pid)
        drawing_id = _valid_id(args.get("drawing_id"), "drawing_id")
        if drawing_id in project.setdefault("drawings", {}):
            raise ApiError(409, f"Drawing '{drawing_id}' already exists")
        drawing_name, strokes = args.get("name"), args.get("strokes")
        if not isinstance(drawing_name, str) or not drawing_name.strip() or len(drawing_name) > 120:
            raise ApiError(400, "name must be a non-empty string of at most 120 characters")
        if not isinstance(strokes, list):
            raise ApiError(400, "strokes must be an array")
        project["drawings"][drawing_id] = {"id":drawing_id,"name":drawing_name.strip(),"strokes":deepcopy(strokes)}
        _save(pid, project)
        return {"ok":True,"project_id":pid,"drawing_id":drawing_id,"stroke_count":len(strokes),"modified":project["modified"]}
    if name == "kae_append_strokes":
        pid, drawing_id = args.get("project_id"), args.get("drawing_id")
        project = _project(pid)
        drawing = project.get("drawings", {}).get(drawing_id)
        if not drawing:
            raise ApiError(404, f"Drawing '{drawing_id}' not found")
        strokes = args.get("strokes")
        if not isinstance(strokes, list) or not strokes:
            raise ApiError(400, "strokes must be a non-empty array")
        old_ids = {s.get("id") for s in drawing.get("strokes", []) if isinstance(s, dict)}
        new_ids = [s.get("id") for s in strokes if isinstance(s, dict)]
        if len(new_ids) != len(strokes) or any(not isinstance(sid, str) or not ID_RE.fullmatch(sid) for sid in new_ids):
            raise ApiError(400, "Every stroke must have a valid id")
        if len(set(new_ids)) != len(new_ids) or old_ids.intersection(new_ids):
            raise ApiError(409, "Stroke IDs must be unique within the drawing")
        drawing.setdefault("strokes", []).extend(deepcopy(strokes))
        _save(pid, project)
        return {"ok":True,"project_id":pid,"drawing_id":drawing_id,"added_strokes":len(strokes),"stroke_count":len(drawing["strokes"]),"modified":project["modified"]}
    if name == "kae_create_drawing_layer":
        pid = args.get("project_id")
        project = _project(pid)
        drawing_id = args.get("drawing_id")
        if drawing_id not in project.get("drawings", {}):
            raise ApiError(404, f"Drawing '{drawing_id}' not found")
        scene = _scene(project, args.get("scene_id"))
        layer_id = _valid_id(args.get("layer_id"), "layer_id")
        if any(layer.get("id") == layer_id for layer in scene.get("layers", [])):
            raise ApiError(409, f"Layer '{layer_id}' already exists")
        start = args.get("start_frame", 0)
        length = args.get("length", min(24, project.get("settings", {}).get("duration_frames", 24)))
        if isinstance(start, bool) or not isinstance(start, int) or start < 0:
            raise ApiError(400, "start_frame must be an integer >= 0")
        if isinstance(length, bool) or not isinstance(length, int) or not 1 <= length <= 2000:
            raise ApiError(400, "length must be an integer from 1 to 2000")
        duration = project.get("settings", {}).get("duration_frames", 1)
        if start + length > duration:
            raise ApiError(422, f"Exposure ends at frame {start + length}, beyond project duration {duration}; extend the project duration first")
        layer = {"id":layer_id,"name":str(args.get("name","AI Drawing Layer"))[:120],"type":"drawing","visible":True,"locked":False,"opacity":1,"depth":1,"blend":"normal","exposures":[{"start":start,"length":length,"drawing":drawing_id}],"tracks":{}}
        created = scene_service.add_layer(pid, scene["id"], layer)
        saved = _touch(pid)
        return {"ok":True,"project_id":pid,"scene_id":scene["id"],"layer":created,"modified":saved.get("modified")}
    if name == "kae_update_layer":
        pid, scene_id, layer_id = args.get("project_id"), args.get("scene_id"), args.get("layer_id")
        changes = {key:args[key] for key in ("name","visible","locked","opacity","transform") if key in args}
        if not changes:
            raise ApiError(400, "Provide at least one layer property to update")
        if "name" in changes and (not isinstance(changes["name"],str) or not changes["name"].strip() or len(changes["name"])>120):
            raise ApiError(400, "name must be a non-empty string of at most 120 characters")
        if "opacity" in changes and (isinstance(changes["opacity"],bool) or not isinstance(changes["opacity"],(int,float)) or not 0<=changes["opacity"]<=1):
            raise ApiError(400, "opacity must be between 0 and 1")
        updated = scene_service.update_layer(pid, scene_id, layer_id, changes)
        saved = _touch(pid)
        return {"ok":True,"project_id":pid,"scene_id":scene_id,"layer":updated,"modified":saved.get("modified")}
    if name == "kae_delete_layer":
        if args.get("confirm") is not True:
            raise ApiError(400, "Layer deletion requires confirm=true")
        pid, scene_id, layer_id = args.get("project_id"), args.get("scene_id"), args.get("layer_id")
        scene_service.delete_layer(pid, scene_id, layer_id)
        saved = _touch(pid)
        return {"ok":True,"project_id":pid,"scene_id":scene_id,"deleted_layer_id":layer_id,"modified":saved.get("modified")}
    raise ApiError(404, f"Unknown KAE tool '{name}'")


def _rpc(request_id, result=None, error=None):
    response = {"jsonrpc":"2.0","id":request_id}
    response["error" if error is not None else "result"] = error if error is not None else result
    return response


def handle_rpc(message):
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0" or not isinstance(message.get("method"), str):
        return _rpc(message.get("id") if isinstance(message,dict) else None, error={"code":-32600,"message":"Invalid Request"})
    method, request_id = message["method"], message.get("id")
    params = message.get("params") or {}
    if "id" not in message:
        if method.startswith("notifications/"):
            return None
    if method == "ping":
        return _rpc(request_id, {})
    if method == "initialize":
        requested = params.get("protocolVersion")
        version = requested if requested in SUPPORTED_PROTOCOLS else PROTOCOL_VERSION
        return _rpc(request_id, {"protocolVersion":version,"capabilities":{"tools":{"listChanged":False}},"serverInfo":{"name":"kyro-anime-engine","title":"KYRO Animation Engine","version":"1.0.0"},"instructions":"Inspect the project and scene before editing. KAE validates and saves native project changes; re-read the scene to verify the result."})
    if method == "tools/list":
        return _rpc(request_id, {"tools":list_tools()})
    if method == "tools/call":
        try:
            result = call_tool(params.get("name"), params.get("arguments", {}))
            import json
            return _rpc(request_id, {"content":[{"type":"text","text":json.dumps(result,ensure_ascii=False,separators=(",",":"))}],"structuredContent":result,"isError":False})
        except ApiError as exc:
            import json
            payload = {"error":exc.message,"details":exc.details or [],"status":exc.status}
            return _rpc(request_id, {"content":[{"type":"text","text":json.dumps(payload,ensure_ascii=False,separators=(",",":"))}],"structuredContent":payload,"isError":True})
        except Exception:
            import json
            payload = {"error":"KAE tool failed unexpectedly","details":["Check KAE server logs."]}
            return _rpc(request_id, {"content":[{"type":"text","text":json.dumps(payload)}],"structuredContent":payload,"isError":True})
    if "id" not in message:
        return None
    return _rpc(request_id, error={"code":-32601,"message":"Method not found"})
