"""KAE AI workspace: provider-backed chat, video reference analysis and image generation."""
import json
import math
import os
import re
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from flask import Blueprint, jsonify, request

from backend.app.exceptions import ApiError
from backend.api.ai_providers import read_profile as read_provider_profile, completion as provider_completion
from backend.services.ai_capabilities import build_system_context, get_capabilities
from backend.services import timeline_service
from backend.storage import project_repository

bp = Blueprint("ai_studio", __name__)


def _load_api_key():
    env_key = os.environ.get("XKIRO_API_KEY", "").strip()
    if env_key:
        return env_key
    project_root = Path(__file__).resolve().parents[2]
    for key_file in (project_root / "xkiro.txt", project_root.parent / "xkiro.txt"):
        try:
            raw = key_file.read_text(encoding="utf-8")
        except OSError:
            continue
        for line in raw.splitlines():
            value = line.strip()
            if not value or value.startswith("#"):
                continue
            if value.startswith("XKIRO_API_KEY="):
                value = value.split("=", 1)[1].strip().strip("'").strip('"')
            if value:
                return value
    return ""


def _config(data=None):
    if isinstance(data, dict) and isinstance(data.get("provider_config"), dict):
        profile = read_provider_profile(data)
        image_model = os.environ.get("XKIRO_IMAGE_MODEL", "openai/gpt-image-2.5").strip()
        image_endpoint = os.environ.get("XKIRO_IMAGE_URL", "").strip() or f"{os.environ.get('XKIRO_BASE_URL', 'https://api.xkiro.com/v1').rstrip('/')}/images/generations"
        return profile["api_key"], profile["base_url"], profile["model"], image_model, image_endpoint
    key = _load_api_key()
    base = os.environ.get("XKIRO_BASE_URL", "https://api.xkiro.com/v1").rstrip("/")
    chat_model = os.environ.get("XKIRO_CHAT_MODEL", "mistralai/devstral-medium").strip()
    image_model = os.environ.get("XKIRO_IMAGE_MODEL", "openai/gpt-image-2.5").strip()
    image_endpoint = os.environ.get("XKIRO_IMAGE_URL", "").strip() or f"{base}/images/generations"
    return key, base, chat_model, image_model, image_endpoint

def _image_config(data=None):
    """Resolve the image provider and selected image model for this request."""
    raw = data.get("image_config") if isinstance(data, dict) else None
    if isinstance(raw, dict):
        provider = str(raw.get("provider") or "xkiro").strip().lower()
        if provider == "groq":
            raise ApiError(422, "Groq vision models can analyze images but do not generate them. Select xKiro for image generation.")
        if provider != "xkiro":
            raise ApiError(422, "KAE image generation currently supports xKiro's image-generation API.")
        key = str(raw.get("api_key") or "").strip()
        base = str(raw.get("base_url") or "https://api.xkiro.com/v1").strip().rstrip("/")
        model = str(raw.get("model") or "").strip()
        if not key:
            raise ApiError(400, "Enter an xKiro API key in Image Generation settings.")
        if not model:
            raise ApiError(400, "Choose an image-generation model before generating.")
        if base.lower() not in ("https://api.xkiro.com/v1", "https://api.xkiro.com"):
            raise ApiError(400, "Image generation requires the official xKiro API base URL (https://api.xkiro.com/v1).")
        api_base = base if base.endswith("/v1") else base + "/v1"
        return key, api_base + "/images/generations", model, api_base
    key, _, _, model, endpoint = _config()
    base = os.environ.get("XKIRO_BASE_URL", "https://api.xkiro.com/v1").rstrip("/")
    return key, endpoint, model, base


def _request_json(url, method="GET", payload=None, api_key="", timeout=30):
    headers = {"Accept": "application/json"}
    body = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode("utf-8")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(req, timeout=timeout) as response:
            raw = response.read(20 * 1024 * 1024)
        return json.loads(raw.decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read(2500).decode("utf-8", "replace")
        # Do not retry provider access denials: the provider/site owner must review them.
        if exc.code == 403 and ("1010" in detail or "browser_signature_banned" in detail):
            raise ApiError(502, "xKiro denied this request with Cloudflare Error 1010 (browser signature banned). Do not retry; contact xKiro support and provide the Ray ID. KAE will not attempt to bypass the provider restriction.") from exc
        raise ApiError(502, f"AI provider returned HTTP {exc.code}: {detail}") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ApiError(502, f"Could not reach or parse the AI provider: {exc}") from exc


def _chat_reply(result, model):
    choices = result.get("choices") or []
    content = choices[0].get("message", {}).get("content") if choices else None
    if isinstance(content, list):
        content = "\n".join(part.get("text", "") for part in content if isinstance(part, dict))
    if not isinstance(content, str) or not content.strip():
        raise ApiError(502, "The AI provider returned no text response")
    return content.strip(), result.get("model", model)


def _history_messages(history):
    messages = []
    if isinstance(history, list):
        for item in history[-12:]:
            if isinstance(item, dict) and item.get("role") in ("user", "assistant") and isinstance(item.get("content"), str):
                messages.append({"role": item["role"], "content": item["content"][:6000]})
    return messages


@bp.get("/ai/status")
def status():
    key, base, chat_model, image_model, _ = _config()
    return jsonify(
        configured=bool(key),
        provider="xKiro",
        base_url=base,
        chat_model=chat_model,
        image_configured=bool(key and image_model),
        image_model=image_model,
        capability_inventory="/api/ai/capabilities",
        video_analysis="/api/ai/video/analyze",
    )


@bp.get("/ai/capabilities")
def capabilities():
    """Expose the live KAE tool/schema inventory to the embedded AI workspace."""
    return jsonify(get_capabilities())


@bp.post("/ai/chat")
def chat():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError(400, "Request body must be a JSON object")
    message = data.get("message")
    if not isinstance(message, str) or not message.strip():
        raise ApiError(400, "A non-empty message is required")
    if len(message) > 12000:
        raise ApiError(413, "Message is too long (maximum 12000 characters)")

    key, base, model, _, _ = _config(data)
    if not key:
        raise ApiError(503, "xKiro is not configured. Set XKIRO_API_KEY in the server environment or add it to the ignored xkiro.txt file; never paste it into the browser.")
    project = data.get("project") if isinstance(data.get("project"), dict) else None
    messages = [{"role": "system", "content": build_system_context(project)}]
    messages.extend(_history_messages(data.get("history", [])))
    messages.append({"role": "user", "content": message.strip()})
    if isinstance(data.get("provider_config"), dict):
        reply, used_model = provider_completion(read_provider_profile(data), messages, temperature=0.3, timeout=90)
    else:
        result = _request_json(
            f"{base}/chat/completions",
            method="POST",
            payload={"model": model, "messages": messages, "temperature": 0.3},
            api_key=key,
            timeout=90,
        )
        reply, used_model = _chat_reply(result, model)
    return jsonify(reply=reply, model=used_model)


@bp.post("/ai/video/analyze")
def analyze_video_reference():
    """Analyze sampled video frames through a vision-capable chat model.

    The browser decodes the user's local video and sends a small set of timestamped
    JPEG frames. Raw video is not uploaded to a third-party provider.
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError(400, "Request body must be a JSON object")
    frames = data.get("frames")
    if not isinstance(frames, list) or not 1 <= len(frames) <= 8:
        raise ApiError(400, "Provide between 1 and 8 sampled video frames.")
    key, base, model, _, _ = _config(data)
    if not key:
        raise ApiError(503, "xKiro is not configured. Configure the key on the server.")
    project = data.get("project") if isinstance(data.get("project"), dict) else None
    content = [{
        "type": "text",
        "text": (
            "Analyze these timestamped frames sampled from one animation reference video. "
            "Describe the visible character(s), art style, background, camera changes, action "
            "phases, key poses, approximate timing, motion direction, and continuity. Distinguish "
            "observations from uncertain inferences. Do not claim to have seen frames that were "
            "not supplied. End by asking the artist what creative changes they want before "
            "reconstruction. Do not claim an animation has been created.\n"
            "Frame metadata: " + json.dumps([
                {"index": i, "timestamp_seconds": f.get("timestamp_seconds")}
                for i, f in enumerate(frames) if isinstance(f, dict)
            ])
        ),
    }]
    for index, frame in enumerate(frames):
        if not isinstance(frame, dict):
            raise ApiError(400, f"Frame {index + 1} is invalid.")
        image_data = frame.get("data_url")
        if not isinstance(image_data, str) or not image_data.startswith("data:image/jpeg;base64,"):
            raise ApiError(400, f"Frame {index + 1} must be a JPEG data URL.")
        if len(image_data) > 1_500_000:
            raise ApiError(413, f"Frame {index + 1} is too large; reduce the sample resolution.")
        content.append({
            "type": "image_url",
            "image_url": {"url": image_data, "detail": "high"},
        })
    messages = [
        {"role": "system", "content": build_system_context(project)},
        {"role": "user", "content": content},
    ]
    if isinstance(data.get("provider_config"), dict):
        reply, used_model = provider_completion(read_provider_profile(data), messages, temperature=0.2, timeout=120)
    else:
        result = _request_json(
            f"{base}/chat/completions",
            method="POST",
            payload={"model": model, "messages": messages, "temperature": 0.2},
            api_key=key,
            timeout=120,
        )
        reply, used_model = _chat_reply(result, model)
    return jsonify(analysis=reply, model=used_model, frames_analyzed=len(frames))




def _parse_model_json(raw):
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.rstrip().endswith("```"):
            cleaned = cleaned.rstrip()[:-3].strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ApiError(502, "AI returned invalid structured data. Reduce the clip complexity and try again.") from exc


def _validated_vector_frames(frames, width, height, coordinates_normalized=True):
    if not isinstance(frames, list) or not 1 <= len(frames) <= 6:
        raise ApiError(422, "Vector validation accepts between 1 and 6 sampled frames.")
    output = []
    total_strokes = 0
    for fi, frame in enumerate(frames):
        if not isinstance(frame, dict) or not isinstance(frame.get("strokes"), list):
            raise ApiError(422, f"Vector frame {fi + 1} must contain a strokes array.")
        strokes = []
        if not 1 <= len(frame["strokes"]) <= 64:
            raise ApiError(422, f"Vector frame {fi + 1} must contain 1 to 64 strokes.")
        for si, stroke in enumerate(frame["strokes"]):
            if not isinstance(stroke, dict):
                raise ApiError(422, f"Frame {fi + 1}, stroke {si + 1} is invalid.")
            color = stroke.get("color", "#222222")
            width_norm = stroke.get("width", 3)
            commands = stroke.get("commands")
            closed = stroke.get("closed", False)
            fill = stroke.get("fill")
            if not isinstance(color, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?", color):
                raise ApiError(422, f"Frame {fi + 1}, stroke {si + 1} has an invalid color.")
            if isinstance(width_norm, bool) or not isinstance(width_norm, (int, float)) or not math.isfinite(width_norm) or not (0.25 if coordinates_normalized else 0.1) <= width_norm <= (40 if coordinates_normalized else max(width, height) * 0.04):
                raise ApiError(422, f"Frame {fi + 1}, stroke {si + 1} has an invalid width.")
            if not isinstance(closed, bool):
                raise ApiError(422, f"Frame {fi + 1}, stroke {si + 1} has an invalid closed flag.")
            if fill is not None and (not isinstance(fill, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?", fill)):
                raise ApiError(422, f"Frame {fi + 1}, stroke {si + 1} has an invalid fill color.")
            if not isinstance(commands, list) or not 2 <= len(commands) <= 120:
                raise ApiError(422, f"Frame {fi + 1}, stroke {si + 1} must contain 2–120 path commands.")
            checked_commands = []
            for ci, command in enumerate(commands):
                if not isinstance(command, list) or not command or command[0] not in ("M", "L", "Q", "C", "Z"):
                    raise ApiError(422, f"Frame {fi + 1}, stroke {si + 1}, command {ci + 1} is unsupported.")
                kind = command[0]
                arity = {"M": 3, "L": 3, "Q": 5, "C": 7, "Z": 1}[kind]
                if len(command) != arity or (ci == 0 and kind != "M") or (ci > 0 and kind == "M"):
                    raise ApiError(422, f"Frame {fi + 1}, stroke {si + 1} has malformed path commands.")
                converted = [kind]
                for coordinate in command[1:]:
                    if isinstance(coordinate, bool) or not isinstance(coordinate, (int, float)) or not math.isfinite(coordinate) or not 0 <= coordinate <= (1000 if coordinates_normalized else (width if len(converted) % 2 == 1 else height)):
                        raise ApiError(422, f"Frame {fi + 1}, stroke {si + 1} coordinates must be normalized from 0 to 1000.")
                    converted.append(round((coordinate / 1000) * (width if len(converted) % 2 == 1 else height), 2) if coordinates_normalized else round(float(coordinate), 2))
                checked_commands.append(converted)
            strokes.append({
                "id": f"stroke_{fi + 1}_{si + 1}",
                "tool": "pen",
                "color": color,
                "width": max(0.1, round(float(width_norm) * max(width, height) / 1000, 2)) if coordinates_normalized else round(float(width_norm), 2),
                "opacity": 1,
                "closed": closed,
                "fill": fill,
                "commands": checked_commands,
            })
            total_strokes += 1
            if total_strokes > 360:
                raise ApiError(422, "Vector drawing exceeds the 360-stroke total limit.")
        output.append({"timestamp_seconds": frame.get("timestamp_seconds", fi), "strokes": strokes})
    return output


@bp.post("/ai/video/reconstruction/plan")
def plan_video_reconstruction():
    """Convert sampled reference frames into a bounded, editable native vector-cel plan."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError(400, "Request body must be a JSON object")
    frames = data.get("frames")
    if not isinstance(frames, list) or not 2 <= len(frames) <= 6:
        raise ApiError(400, "Provide between 2 and 6 sampled video frames.")
    direction = data.get("direction", "")
    if not isinstance(direction, str) or len(direction) > 8000:
        raise ApiError(413, "Creative direction must be text under 8000 characters.")
    project = data.get("project")
    if not isinstance(project, dict) or not isinstance(project.get("settings"), dict):
        raise ApiError(400, "A current KAE project context is required.")
    settings = project["settings"]
    width, height = settings.get("width"), settings.get("height")
    if not isinstance(width, int) or not isinstance(height, int) or not 16 <= width <= 8192 or not 16 <= height <= 8192:
        raise ApiError(400, "Project canvas dimensions are invalid.")
    key, base, model, _, _ = _config(data)
    if not key:
        raise ApiError(503, "xKiro is not configured. Configure the key on the server.")
    content = [{
        "type": "text",
        "text": (
            "Create a rough but editable vector-animation reconstruction of the subject across these sampled frames. "
            "Return ONLY JSON: {summary:string, frames:[{timestamp_seconds:number, strokes:[{color:'#RRGGBB',width:number,closed:boolean,fill:null|string,commands:array}]}]}. "
            "Return exactly " + str(len(frames)) + " frames in the same order. Each frame may have 2 to 12 strokes. "
            "Coordinates must be normalized to 0..1000 in both axes. Each commands array starts with ['M',x,y], "
            "then uses ['L',x,y], ['Q',cx,cy,x,y], ['C',c1x,c1y,c2x,c2y,x,y], or ['Z']; maximum 30 commands per stroke. "
            "Use clear contour paths and a small number of colors. Prefer continuous, stable contours between frames. "
            "Do not output prose or markdown. This is an approximation, not pixel-perfect tracing.\n"
            "Canvas aspect ratio: " + str(width) + ":" + str(height) + ".\n"
            "Timestamps: " + json.dumps([f.get("timestamp_seconds") for f in frames if isinstance(f, dict)]) + "\n"
            "ARTIST'S CREATIVE DIRECTION: " + (direction.strip() or "Stay faithful to the reference action and design.")
        )
    }]
    for index, frame in enumerate(frames):
        if not isinstance(frame, dict):
            raise ApiError(400, f"Frame {index + 1} is invalid.")
        image_data = frame.get("data_url")
        if not isinstance(image_data, str) or not image_data.startswith("data:image/jpeg;base64,"):
            raise ApiError(400, f"Frame {index + 1} must be a JPEG data URL.")
        if len(image_data) > 1_000_000:
            raise ApiError(413, f"Frame {index + 1} is too large; reduce the sample resolution.")
        content.append({"type": "image_url", "image_url": {"url": image_data, "detail": "high"}})
    messages = [
        {"role": "system", "content": build_system_context(project)},
        {"role": "user", "content": content},
    ]
    if isinstance(data.get("provider_config"), dict):
        raw, used_model = provider_completion(read_provider_profile(data), messages, temperature=0.1, timeout=180)
    else:
        result = _request_json(
            f"{base}/chat/completions",
            method="POST",
            payload={"model": model, "messages": messages, "temperature": 0.1},
            api_key=key,
            timeout=180,
        )
        raw, used_model = _chat_reply(result, model)
    plan = _parse_model_json(raw)
    if not isinstance(plan, dict) or not isinstance(plan.get("frames"), list) or len(plan["frames"]) != len(frames):
        raise ApiError(502, "AI reconstruction must return one vector frame for each sampled reference frame.")
    validated_frames = _validated_vector_frames(plan["frames"], width, height)
    return jsonify(
        summary=str(plan.get("summary", "Editable vector reconstruction"))[:2000],
        frames=validated_frames,
        model=used_model,
        canvas={"width": width, "height": height},
        applied=False,
    )


@bp.post("/ai/video/reconstruction/apply")
def apply_video_reconstruction():
    """Add validated vector cels and a new exposure layer without replacing existing artwork."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError(400, "Request body must be a JSON object")
    project_id, scene_id, plan = data.get("project_id"), data.get("scene_id"), data.get("plan")
    if not isinstance(project_id, str) or not project_id.strip() or not isinstance(scene_id, str):
        raise ApiError(400, "project_id and scene_id are required.")
    if not isinstance(plan, dict) or not isinstance(plan.get("frames"), list):
        raise ApiError(400, "A reconstruction plan is required.")
    project = project_repository.load(project_id)
    settings = project.get("settings", {})
    frames = _validated_vector_frames(plan["frames"], settings.get("width", 0), settings.get("height", 0), coordinates_normalized=False)
    if not 2 <= len(frames) <= 6:
        raise ApiError(422, "Reconstruction must contain 2 to 6 frames.")
    scene = next((s for s in project.get("scenes", []) if s.get("id") == scene_id), None)
    if scene is None:
        raise ApiError(404, "Target scene not found.")
    duration = settings.get("duration_frames", 24)
    if not isinstance(duration, int) or duration < len(frames):
        raise ApiError(422, "Project duration must be at least the number of reconstructed frames.")
    # Space samples across the project duration, preserving every existing layer.
    positions = [int(i * duration / len(frames)) for i in range(len(frames))]
    drawings = project.setdefault("drawings", {})
    new_drawings, exposures = [], []
    layer_id = "ai_video_" + uuid.uuid4().hex[:12]
    for index, frame in enumerate(frames):
        drawing_id = "ai_cel_" + uuid.uuid4().hex[:12]
        drawing = {"id": drawing_id, "name": f"AI video reconstruction {index + 1}", "strokes": frame["strokes"]}
        drawings[drawing_id] = drawing
        end = positions[index + 1] if index + 1 < len(positions) else duration
        exposures.append({"start": positions[index], "length": max(1, end - positions[index]), "drawing": drawing_id})
        new_drawings.append(drawing_id)
    scene.setdefault("layers", []).append({
        "id": layer_id,
        "name": "AI Video Reconstruction",
        "type": "drawing",
        "visible": True,
        "locked": False,
        "opacity": 1,
        "depth": 1,
        "blend": "normal",
        "exposures": exposures,
        "tracks": {},
    })
    from backend.services.validation_service import validate_project
    errors = validate_project(project)
    if errors:
        # Do not write partially valid reconstruction data to disk.
        raise ApiError(422, "Reconstruction failed native KAE project validation.", errors)
    from datetime import datetime, timezone
    project["modified"] = datetime.now(timezone.utc).isoformat()
    project_repository.save(project_id, project)
    return jsonify(
        applied=True,
        project_id=project_id,
        scene_id=scene_id,
        layer_id=layer_id,
        drawing_ids=new_drawings,
        frames=len(frames),
        keyframes=positions,
        message="Added editable vector cels on a new layer. Existing layers and drawings were preserved.",
    )


@bp.post("/ai/animation/plan")
def create_animation_plan():
    """Ask AI for a validated, previewable keyframe script without mutating the project."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError(400, "Request body must be a JSON object")
    project_id = data.get("project_id")
    direction = data.get("direction")
    analysis = data.get("analysis", "")
    if not isinstance(project_id, str) or not project_id.strip():
        raise ApiError(400, "project_id is required to build an animation plan.")
    if not isinstance(direction, str) or not direction.strip():
        raise ApiError(400, "Describe the creative changes or animation you want.")
    if len(direction) > 8000 or not isinstance(analysis, str) or len(analysis) > 16000:
        raise ApiError(413, "Animation direction or reference analysis is too long.")
    key, base, model, _, _ = _config(data)
    if not key:
        raise ApiError(503, "xKiro is not configured. Configure the key on the server.")
    project = project_repository.load(project_id)
    settings = project.get("settings", {})
    frame_limit = int(settings.get("duration_frames", 24))
    scene_ids = {
        scene.get("id"): {layer.get("id") for layer in scene.get("layers", []) if isinstance(layer, dict)}
        for scene in project.get("scenes", []) if isinstance(scene, dict)
    }
    prompt = (
        "Create a previewable animation keyframe plan for this existing KAE project. "
        "Return ONLY one JSON object with keys summary and ops. ops must contain 1 to 200 "
        "operations and every operation must use op=set_key with scene_id, layer_id, channel, "
        "time, value, and optional ease. Valid channels are x, y, rotation, scale_x, scale_y, "
        "opacity. Use only the exact scene/layer IDs supplied in the project context. Frame "
        "times are zero-based integers and must be inside the current duration. Values must be "
        "numbers. Use ease from linear, hold, ease_in, ease_out, ease_in_out. Animate existing "
        "layers only; do not invent drawing IDs or claim new artwork was generated. Include "
        "keyframes that communicate the requested motion and preserve other channels. If the "
        "request cannot be represented with existing layers and transform keyframes, return "
        "an empty ops array and explain the limitation in summary.\n\n"
        "CURRENT FRAME LIMIT: " + str(frame_limit) + "\n"
        "REFERENCE VIDEO ANALYSIS:\n" + analysis + "\n"
        "ARTIST'S CREATIVE DIRECTION:\n" + direction
    )
    messages = [
        {"role": "system", "content": build_system_context(project)},
        {"role": "user", "content": prompt},
    ]
    if isinstance(data.get("provider_config"), dict):
        raw, used_model = provider_completion(read_provider_profile(data), messages, temperature=0.1, timeout=120)
    else:
        result = _request_json(
            f"{base}/chat/completions",
            method="POST",
            payload={"model": model, "messages": messages, "temperature": 0.1},
            api_key=key,
            timeout=120,
        )
        raw, used_model = _chat_reply(result, model)
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.rstrip().endswith("```"):
            cleaned = cleaned.rstrip()[:-3].strip()
    try:
        plan = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ApiError(502, "AI returned an invalid animation plan. Ask it to try again.") from exc
    if not isinstance(plan, dict) or not isinstance(plan.get("ops"), list):
        raise ApiError(502, "AI animation plan must contain an ops array.")
    ops = plan["ops"]
    if len(ops) > 200:
        raise ApiError(422, "Animation plan exceeds the 200-keyframe safety limit.")
    valid_eases = {"linear", "hold", "ease_in", "ease_out", "ease_in_out"}
    validated = []
    for index, op in enumerate(ops):
        if not isinstance(op, dict) or op.get("op") != "set_key":
            raise ApiError(422, f"Plan operation {index + 1} is not a supported set_key operation.")
        scene_id, layer_id = op.get("scene_id"), op.get("layer_id")
        if scene_id not in scene_ids or layer_id not in scene_ids[scene_id]:
            raise ApiError(422, f"Plan operation {index + 1} refers to a scene or layer that does not exist.")
        if op.get("channel") not in timeline_service.CHANNELS:
            raise ApiError(422, f"Plan operation {index + 1} uses an unsupported animation channel.")
        frame = op.get("time")
        value = op.get("value")
        if isinstance(frame, bool) or not isinstance(frame, int) or not 0 <= frame < frame_limit:
            raise ApiError(422, f"Plan operation {index + 1} has a frame outside the current project duration.")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ApiError(422, f"Plan operation {index + 1} must use a finite numeric value.")
        if op["channel"] == "opacity" and not 0 <= value <= 1:
            raise ApiError(422, f"Plan operation {index + 1} opacity must be between 0 and 1.")
        if op["channel"] in ("scale_x", "scale_y") and not 0.01 <= abs(value) <= 100:
            raise ApiError(422, f"Plan operation {index + 1} scale must be between 0.01 and 100 in magnitude.")
        ease = op.get("ease", "linear")
        if ease not in valid_eases:
            raise ApiError(422, f"Plan operation {index + 1} uses an unsupported interpolation mode.")
        validated.append({
            "op": "set_key", "scene_id": scene_id, "layer_id": layer_id,
            "channel": op["channel"], "time": frame, "value": value, "ease": ease,
        })
    return jsonify(
        summary=str(plan.get("summary", "Animation keyframe plan"))[:2000],
        ops=validated,
        model=used_model,
        project_id=project_id,
        frame_limit=frame_limit,
        applied=False,
    )


@bp.post("/ai/animation/director")
def direct_animation_blueprint():
    """Turn a plain-language instruction into a validated production-ready storyboard plan."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError(400, "Request body must be a JSON object")
    direction = data.get("direction")
    if not isinstance(direction, str) or not direction.strip():
        raise ApiError(400, "Describe the animation you want KAE to create.")
    if len(direction) > 8000:
        raise ApiError(413, "Animation instruction is too long (maximum 8000 characters).")
    project = None
    project_id = data.get("project_id")
    if isinstance(project_id, str) and project_id.strip():
        project = project_repository.load(project_id)
    key, base, model, _, _ = _config(data)
    if not isinstance(data.get("provider_config"), dict) and not key:
        raise ApiError(503, "Connect an AI chat provider before generating an animation plan.")
    context = build_system_context(project) if project else (
        "You are the animation director inside KYRO Animation Engine (KAE), an anime-first 2D/2.5D animation studio."
    )
    prompt = (
        "Act as a senior anime animation director, storyboard artist, character designer and background artist. "
        "Convert the user's instruction into a concrete production plan. Return ONLY valid JSON with keys: "
        "title (string), style_bible (string), character_bible (string), background_prompt (string), "
        "fps (integer 12-30), duration_seconds (number 2-8), keyframes (array of exactly 4 objects). "
        "Each keyframe must contain frame (integer), beat (short string), camera (string), action (string), "
        "image_prompt (string). The image_prompt must describe a complete 16:9 cinematic anime frame, keep "
        "the exact same character identity, outfit, colors, proportions and art direction across all frames, "
        "and describe a distinct readable pose/action. Avoid text, captions, logos and watermarks. "
        "Make the sequence temporally coherent: anticipation, main action, follow-through, settled ending. "
        "background_prompt must describe a clean, detailed environment plate for the same scene with no characters, "
        "no text, no watermark, 16:9 composition. Include lighting, atmospheric depth, foreground/midground/background, "
        "and palette. Keep prompts actionable, specific and safe. Frames should be spaced across the duration. "
        "Do not claim images or animation have already been generated.\n\n"
        "USER INSTRUCTION:\n" + direction.strip() + "\n\n"
        "CURRENT PROJECT CONTEXT (if supplied):\n" + json.dumps({
            "name": project.get("name") if project else None,
            "settings": project.get("settings", {}) if project else {},
            "scenes": [
                {"id": scene.get("id"), "name": scene.get("name"),
                 "layers": [{"id": layer.get("id"), "name": layer.get("name")}
                            for layer in scene.get("layers", []) if isinstance(layer, dict)]}
                for scene in (project.get("scenes", []) if project else []) if isinstance(scene, dict)
            ][:12],
        }, ensure_ascii=False)[:10000]
    )
    messages = [{"role": "system", "content": context}, {"role": "user", "content": prompt}]
    if isinstance(data.get("provider_config"), dict):
        raw, used_model = provider_completion(read_provider_profile(data), messages, temperature=0.2, timeout=120)
    else:
        result = _request_json(
            f"{base}/chat/completions",
            method="POST",
            payload={"model": model, "messages": messages, "temperature": 0.2},
            api_key=key,
            timeout=120,
        )
        raw, used_model = _chat_reply(result, model)
    plan = _parse_model_json(raw)
    if not isinstance(plan, dict) or not isinstance(plan.get("keyframes"), list) or len(plan["keyframes"]) != 4:
        raise ApiError(502, "Animation director must return exactly four valid keyframes. Try a more specific instruction.")
    for field in ("title", "style_bible", "character_bible", "background_prompt"):
        if not isinstance(plan.get(field), str) or not plan[field].strip():
            raise ApiError(502, f"Animation director omitted required field: {field}.")
        plan[field] = plan[field].strip()[:5000]
    try:
        fps = int(plan.get("fps", 24))
        duration = float(plan.get("duration_seconds", 4))
    except (TypeError, ValueError) as exc:
        raise ApiError(502, "Animation director returned invalid timing.") from exc
    if not 12 <= fps <= 30 or not 2 <= duration <= 8:
        raise ApiError(502, "Animation timing must be 12–30 FPS and 2–8 seconds.")
    validated_frames = []
    last_frame = -1
    for index, frame in enumerate(plan["keyframes"]):
        if not isinstance(frame, dict):
            raise ApiError(502, f"Keyframe {index + 1} is invalid.")
        try:
            frame_number = int(frame.get("frame", round(index * (duration * fps - 1) / 3)))
        except (TypeError, ValueError) as exc:
            raise ApiError(502, f"Keyframe {index + 1} has invalid timing.") from exc
        if not 0 <= frame_number < int(duration * fps) or frame_number <= last_frame:
            frame_number = round(index * (duration * fps - 1) / 3)
        last_frame = frame_number
        values = {}
        for field in ("beat", "camera", "action", "image_prompt"):
            value = frame.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ApiError(502, f"Keyframe {index + 1} is missing {field}.")
            values[field] = value.strip()[:5000]
        values["frame"] = frame_number
        validated_frames.append(values)
    return jsonify(
        plan={
            "title": plan["title"], "style_bible": plan["style_bible"],
            "character_bible": plan["character_bible"], "background_prompt": plan["background_prompt"],
            "fps": fps, "duration_seconds": duration, "keyframes": validated_frames,
        },
        model=used_model, project_id=project_id, status="planned",
        note="This is a validated storyboard plan. Images must be generated before an animatic can be exported.",
    )


@bp.post("/ai/story/outline")
def expand_story_outline():
    """Expand imported story JSON into an ordered, animation-ready scene list."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError(400, "Request body must be a JSON object")
    story = data.get("story")
    if not isinstance(story, (dict, list, str)):
        raise ApiError(400, "Import a story JSON object, array, or text field.")
    story_text = json.dumps(story, ensure_ascii=False) if not isinstance(story, str) else story
    if not story_text.strip() or len(story_text) > 30000:
        raise ApiError(413, "Story JSON must contain text and be under 30,000 characters.")
    if not isinstance(data.get("provider_config"), dict):
        raise ApiError(400, "Connect an AI chat provider in KAE AI settings first.")
    profile = read_provider_profile(data)
    project = data.get("project") if isinstance(data.get("project"), dict) else {}
    prompt = (
        "Turn the imported story into a complete, coherent animation production outline. Return ONLY JSON with "
        "keys title (string), logline (string), style_bible (string), characters (array of concise character design "
        "descriptions), scenes (array of 1 to 12 objects). Each scene must have scene_number (integer), title (string), "
        "location (string), mood (string), characters (array of names), action (string), visual_description (string), "
        "continuity_notes (string), and dialogue (string). Preserve the user's story events and ending; do not invent "
        "major plot twists that contradict the source. Split action into drawable scenes with clear beginnings and "
        "endings. Every visual_description must describe what is visibly on the canvas, including foreground, "
        "background, lighting, character pose, costume, and props. Keep character appearance consistent between scenes. "
        "Limit the outline to 12 scenes so each can be drawn as native vector cels. No markdown. " 
        "Also include needs_clarification (boolean) and clarification_question (string). Ask a question only if a missing story or design detail would materially change the result and cannot be safely inferred; otherwise make a coherent creative choice and set needs_clarification=false. Preserve the user's story.\n\n"
        "PROJECT CANVAS: " + json.dumps(project.get("settings", {}), ensure_ascii=False)[:1000] + "\n"
        "IMPORTED STORY JSON:\n" + story_text
    )
    raw, used_model = provider_completion(profile, [
        {"role": "system", "content": build_system_context(project) + "\nYou are KAE's story editor and animation director. Use only the tagged native tools and schema fields in the capability inventory. Return valid JSON only; never invent external drawing tools."},
        {"role": "user", "content": prompt},
    ], temperature=0.2, timeout=180, max_tokens=100000)
    try:
        outline = _parse_model_json(raw)
    except ApiError as first_error:
        raw, used_model = provider_completion(profile, [
            {"role": "system", "content": build_system_context(project)},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": raw[:160000]},
            {"role": "user", "content": "SELF-REPAIR PASS 1/1. Return the COMPLETE corrected story outline as valid JSON only. Previous parse error: " + str(first_error) + ". Keep 1-12 scenes and all required fields."},
        ], temperature=0, timeout=180, max_tokens=100000)
        outline = _parse_model_json(raw)
    if not isinstance(outline, dict):
        raise ApiError(502, "The story director must return a JSON object.")
    if outline.get("needs_clarification") is True:
        question = outline.get("clarification_question")
        if isinstance(question, str) and question.strip():
            return jsonify(status="needs_input", question=question.strip()[:1800], model=used_model)
    if not isinstance(outline.get("scenes"), list) or not 1 <= len(outline["scenes"]) <= 12:
        raise ApiError(502, "The story director must return between 1 and 12 scenes.")
    required = ("title", "logline", "style_bible")
    for field in required:
        if not isinstance(outline.get(field), str) or not outline[field].strip():
            raise ApiError(502, f"Story director omitted {field}.")
        outline[field] = outline[field].strip()[:3000]
    scenes = []
    for index, scene in enumerate(outline["scenes"]):
        if not isinstance(scene, dict):
            raise ApiError(502, f"Story scene {index + 1} is invalid.")
        normalized = {"scene_number": index + 1}
        for field in ("title", "location", "mood", "action", "visual_description", "continuity_notes", "dialogue"):
            value = scene.get(field, "")
            if not isinstance(value, str):
                value = str(value)
            normalized[field] = value.strip()[:3500]
        chars = scene.get("characters", [])
        normalized["characters"] = [str(name)[:120] for name in chars[:12]] if isinstance(chars, list) else []
        if not normalized["title"] or not normalized["visual_description"]:
            raise ApiError(502, f"Story scene {index + 1} needs a title and visual description.")
        scenes.append(normalized)
    cast = outline.get("characters", [])
    if not isinstance(cast, list):
        cast = []
    return jsonify(
        title=outline["title"], logline=outline["logline"], style_bible=outline["style_bible"],
        characters=[str(item)[:1200] for item in cast[:20]],
        scenes=scenes, model=used_model, status="outlined",
    )


@bp.post("/ai/story/vector-plan")
def plan_story_vector_animation():
    """Plan the visual composition first, then return validated native KAE vector cels."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError(400, "Request body must be a JSON object")
    direction = data.get("direction")
    scene_title = data.get("scene_title", "Story scene")
    project = data.get("project")
    if not isinstance(direction, str) or not direction.strip():
        raise ApiError(400, "A story scene description is required.")
    if len(direction) > 12000:
        raise ApiError(413, "Story scene description is too long (maximum 12000 characters).")
    if not isinstance(project, dict) or not isinstance(project.get("settings"), dict):
        raise ApiError(400, "Open a KAE project before drawing a story.")
    settings = project["settings"]
    width, height = settings.get("width"), settings.get("height")
    if not isinstance(width, int) or not isinstance(height, int) or not 16 <= width <= 8192 or not 16 <= height <= 8192:
        raise ApiError(400, "Project canvas dimensions are invalid.")
    if not isinstance(data.get("provider_config"), dict):
        raise ApiError(400, "Connect an AI chat provider in KAE AI settings first.")
    profile = read_provider_profile(data)

    # Pull the live native tool/schema inventory from the KAE backend. The model is
    # instructed to use only these native capabilities; no external drawing tool is assumed.
    capability_context = build_system_context(project)
    visual_brief_prompt = (
        "You are the visual pre-production director for KAE, an anime-first native vector animation engine. "
        "Create a concise FINAL ART-DIRECTION BRIEF, not private chain-of-thought. Imagine the finished shot "
        "as a composed frame before any path JSON is written. Specify: character silhouette and proportions; "
        "face, eyes, hair masses and strand accents; outfit construction and folds; hands/feet/pose; props; "
        "foreground, midground and background; camera framing; light direction; shadow shapes; palette; "
        "depth ordering; and how the design stays consistent across motion. Identify the visual focal point "
        "and avoid tiny details that would disappear at the target canvas size. Return ONLY JSON with keys "
        "composition, character_design, pose_sequence (array of exactly 4 short entries), palette (array of hex colors), "
        "environment_design, lighting, continuity_rules, and quality_check. Do not output hidden reasoning, "
        "markdown, image URLs, or claims that a raster image exists. Make the brief concrete and drawable using "
        "KAE's native paths and fills.\n\n"
        "CANVAS: " + str(width) + " x " + str(height) + " pixels; aspect ratio " +
        str(round(width / height, 4)) + ".\n"
        "SCENE TITLE: " + str(scene_title)[:180] + "\n"
        "STORY / SCENE DIRECTION:\n" + direction.strip()
    )
    planning_messages = [
        {"role": "system", "content": capability_context + "\nYou are the visual design stage of a two-stage KAE drawing pipeline. Use only real native KAE drawing capabilities."},
        {"role": "user", "content": visual_brief_prompt},
    ]
    try:
        brief_raw, used_model = provider_completion(profile, planning_messages, temperature=0.25, timeout=180, max_tokens=100000)
        visual_brief = _parse_model_json(brief_raw)
        if not isinstance(visual_brief, dict):
            raise ValueError("Visual design brief must be a JSON object.")
        for field in ("composition", "character_design", "environment_design", "lighting", "continuity_rules", "quality_check"):
            if not isinstance(visual_brief.get(field), str) or not visual_brief[field].strip():
                raise ValueError("Visual design brief omitted " + field + ".")
        poses = visual_brief.get("pose_sequence")
        if not isinstance(poses, list) or len(poses) != 4:
            raise ValueError("Visual design brief must include exactly 4 pose beats.")
        palette = visual_brief.get("palette", [])
        if not isinstance(palette, list):
            palette = []
        visual_brief = {
            "composition": visual_brief["composition"][:3000],
            "character_design": visual_brief["character_design"][:5000],
            "pose_sequence": [str(item)[:800] for item in poses[:6]],
            "palette": [str(color)[:9] for color in palette[:24]],
            "environment_design": visual_brief["environment_design"][:3500],
            "lighting": visual_brief["lighting"][:2500],
            "continuity_rules": visual_brief["continuity_rules"][:2500],
            "quality_check": visual_brief["quality_check"][:2500],
        }
    except (ApiError, ValueError) as exc:
        if isinstance(exc, ApiError):
            raise
        raise ApiError(502, "The visual planning stage returned an incomplete art-direction brief: " + str(exc)) from exc

    frame_count = 4
    drawing_prompt = (
        "Now produce the native KAE drawing JSON using the approved visual brief below. This is stage 2: "
        "write the actual drawable paths, not another plan. Return ONLY valid JSON with keys summary and frames. "
        "Return exactly " + str(frame_count) + " frames in pose-sequence order. Each frame has timestamp_seconds "
        "and 12 to 48 strokes. Use enough separate paths to make a finished, richly designed anime character and "
        "scene, not an icon or stick figure. Recommended visual construction order: broad environment/background "
        "shapes, ground and cast shadows, rear hair, legs and shoes, torso and clothing panels, arms and hands, "
        "neck and face silhouette, ears, eyes with whites/iris/pupil/highlights, brows, nose and mouth, front hair "
        "locks, clothing seams/folds, accessories/props, rim lights and small accents. Do not skip the face, hair, "
        "outfit or background. Use filled closed silhouettes with clean dark linework, varied path widths, smooth "
        "cubic/quadratic Bézier curves, layered highlights/shadows and a controlled palette. Keep the main subject "
        "large enough to read clearly in the canvas. Use meaningful spatial composition, not random disconnected "
        "shapes. Maintain exact identity, costume, proportions and palette between frames; vary pose and camera/action "
        "according to each pose beat. Use no text, captions, logos or watermarks.\n"
        "Each stroke object: {color:'#RRGGBB',width:number,closed:boolean,fill:null|string,commands:array}. "
        "Width is 0.5..40 in normalized canvas units. Each commands array starts with ['M',x,y] and uses "
        "['L',x,y], ['Q',cx,cy,x,y], ['C',c1x,c1y,c2x,c2y,x,y], or ['Z']; up to 120 commands per stroke. "
        "Coordinates are numbers 0..1000. Fill is null or a hex color. Use separate paths for details instead of "
        "overloading one path. Avoid over-simplifying and avoid duplicating the same path many times. No extra keys.\n\n"
        "CANVAS: " + str(width) + " x " + str(height) + "\n"
        "SCENE: " + str(scene_title)[:180] + "\n"
        "STORY DIRECTION:\n" + direction.strip() + "\n\n"
        "APPROVED VISUAL DESIGN BRIEF:\n" + json.dumps(visual_brief, ensure_ascii=False, separators=(",", ":"))
    )
    drawing_messages = [
        {"role": "system", "content": capability_context + "\nYou are KAE's native vector-cel renderer. Produce paths only for KAE's existing command schema. Never invent external tools, schemas, or endpoints."},
        {"role": "user", "content": drawing_prompt},
    ]
    visual_reference = data.get("visual_reference")
    if isinstance(visual_reference, str) and len(visual_reference) <= 18_000_000 and visual_reference.startswith(("data:image/", "https://")):
        if profile.get("provider") != "anthropic" or visual_reference.startswith("data:image/"):
            drawing_messages[-1]["content"] = [
                {"type": "text", "text": drawing_prompt + "\n\nUse the attached concept image as a visual reference for silhouette, palette, face, costume, props and lighting. Translate it into editable native paths; do not claim to copy pixels."},
                {"type": "image_url", "image_url": {"url": visual_reference}},
            ]
    try:
        raw, used_model = provider_completion(profile, drawing_messages, temperature=0.15, timeout=240, max_tokens=100000)
    except ApiError:
        # A model/provider may reject image_url content even if it accepts text.
        # Retry text-only so optional image collaboration cannot block the drawing.
        if not isinstance(drawing_messages[-1].get("content"), list):
            raise
        drawing_messages[-1]["content"] = drawing_prompt
        raw, used_model = provider_completion(profile, drawing_messages, temperature=0.15, timeout=240, max_tokens=100000)
    try:
        plan = _parse_model_json(raw)
        if not isinstance(plan, dict) or not isinstance(plan.get("frames"), list) or len(plan["frames"]) != frame_count:
            raise ValueError("Expected exactly " + str(frame_count) + " frames.")
        frames = _validated_vector_frames(plan["frames"], width, height, coordinates_normalized=True)
    except (ApiError, ValueError) as first_error:
        repair_messages = drawing_messages + [
            {"role": "assistant", "content": raw[:180000]},
            {"role": "user", "content": "SELF-REPAIR PASS 1/1. Your previous output failed KAE JSON/path validation: " + str(first_error) +
             "\nRewrite the COMPLETE JSON object from scratch. Return only valid JSON with summary and exactly " + str(frame_count) +
             " frames. Every frame needs 12-48 detailed strokes; each stroke must use valid hex colors, width 0.5-40, fill null or hex, " +
             "and commands beginning with M followed by valid L/Q/C/Z commands. Coordinates must be numbers 0-1000. Do not explain the repair."},
        ]
        raw, used_model = provider_completion(profile, repair_messages, temperature=0, timeout=240, max_tokens=100000)
        plan = _parse_model_json(raw)
        if not isinstance(plan, dict) or not isinstance(plan.get("frames"), list) or len(plan["frames"]) != frame_count:
            raise ApiError(502, "Self-repair did not return a complete " + str(frame_count) + "-frame JSON plan. Please continue with a shorter scene or clarify the design.")
        frames = _validated_vector_frames(plan["frames"], width, height, coordinates_normalized=True)
    return jsonify(
        title=str(scene_title)[:180],
        summary=str(plan.get("summary") or "Visual plan converted into editable native vector animation")[:2000],
        visual_brief=visual_brief,
        frames=frames,
        canvas={"width": width, "height": height},
        model=used_model,
        format="kae-native-vector-cels",
        generated_images=False,
    )


@bp.post("/ai/images")
def generate_image():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError(400, "Request body must be a JSON object")
    prompt = data.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ApiError(400, "Describe the character or pose to generate")
    if len(prompt) > 8000:
        raise ApiError(413, "Image prompt is too long (maximum 8000 characters)")
    key, endpoint, model, _ = _image_config(data)
    if not key:
        raise ApiError(503, "Configure an xKiro API key in Image Generation settings.")
    if not model:
        raise ApiError(400, "Choose an image-generation model.")
    result = _request_json(
        endpoint,
        method="POST",
        payload={"model": model, "prompt": prompt.strip(), "n": 1, "size": "1024x1024"},
        api_key=key,
        timeout=90,
    )
    items = result.get("data") or result.get("images") or []
    item = items[0] if items and isinstance(items[0], dict) else {}
    image_url = item.get("url") or item.get("image_url")
    encoded = item.get("b64_json") or item.get("base64")
    if image_url or encoded:
        return jsonify(status="succeeded", image={
            "url": image_url, "b64_json": encoded,
            "revised_prompt": item.get("revised_prompt") or prompt.strip(),
        }), 201
    job_id = result.get("id")
    if not isinstance(job_id, str) or not job_id.strip():
        detail = result.get("error") or result.get("message") or "No image job ID was returned"
        raise ApiError(502, f"Image provider did not return a job ID: {detail}")
    state = result.get("status", "processing")
    if state in ("failed", "blocked"):
        detail = result.get("error") or state
        raise ApiError(502, f"Image generation {state}: {detail}")
    return jsonify(job_id=job_id, status=state, prompt=prompt.strip()), 202


@bp.get("/ai/images/<job_id>")
def image_status(job_id):
    key, _, _, _, endpoint = _config()
    if not key:
        raise ApiError(503, "xKiro is not configured. Set XKIRO_API_KEY in the server environment.")
    return _image_status_result(job_id, key, endpoint)


@bp.post("/ai/images/<job_id>")
def image_status_for_selected_provider(job_id):
    data = request.get_json(silent=True) or {}
    key, endpoint, _, _ = _image_config(data)
    return _image_status_result(job_id, key, endpoint)


def _image_status_result(job_id, key, endpoint):
    if not job_id or len(job_id) > 200:
        raise ApiError(400, "Invalid image job ID")
    result = _request_json(f"{endpoint.rstrip('/')}/{quote(job_id, safe='')}", api_key=key, timeout=30)
    state = result.get("status", "processing")
    if state in ("failed", "blocked"):
        detail = result.get("error") or state
        if isinstance(detail, dict):
            detail = detail.get("message") or str(detail)
        raise ApiError(502, f"Image generation {state}: {detail}")
    if state != "succeeded":
        return jsonify(job_id=job_id, status=state), 202
    items = result.get("data") or result.get("images") or []
    item = items[0] if items and isinstance(items[0], dict) else {}
    image_url = item.get("url") or item.get("image_url")
    encoded = item.get("b64_json") or item.get("base64")
    if not image_url and not encoded:
        raise ApiError(502, "Image job succeeded but returned no usable image URL")
    return jsonify(job_id=job_id, status="succeeded", image={
        "url": image_url, "b64_json": encoded,
        "revised_prompt": item.get("revised_prompt") or result.get("prompt", ""),
    })
