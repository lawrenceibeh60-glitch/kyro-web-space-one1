"""KAE AI workspace: provider-backed chat, video reference analysis and image generation."""
import json
import math
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from flask import Blueprint, jsonify, request

from backend.app.exceptions import ApiError
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


def _config():
    key = _load_api_key()
    base = os.environ.get("XKIRO_BASE_URL", "https://api.xkiro.com/v1").rstrip("/")
    chat_model = os.environ.get("XKIRO_CHAT_MODEL", "mistralai/devstral-medium").strip()
    image_model = os.environ.get("XKIRO_IMAGE_MODEL", "openai/gpt-image-2.5").strip()
    image_endpoint = os.environ.get("XKIRO_IMAGE_URL", "").strip() or f"{base}/images/generations"
    return key, base, chat_model, image_model, image_endpoint


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

    key, base, model, _, _ = _config()
    if not key:
        raise ApiError(503, "xKiro is not configured. Set XKIRO_API_KEY in the server environment or add it to the ignored xkiro.txt file; never paste it into the browser.")
    project = data.get("project") if isinstance(data.get("project"), dict) else None
    messages = [{"role": "system", "content": build_system_context(project)}]
    messages.extend(_history_messages(data.get("history", [])))
    messages.append({"role": "user", "content": message.strip()})
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
    key, base, model, _, _ = _config()
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
    result = _request_json(
        f"{base}/chat/completions",
        method="POST",
        payload={"model": model, "messages": messages, "temperature": 0.2},
        api_key=key,
        timeout=120,
    )
    reply, used_model = _chat_reply(result, model)
    return jsonify(analysis=reply, model=used_model, frames_analyzed=len(frames))



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
    key, base, model, _, _ = _config()
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
    result = _request_json(
        f"{base}/chat/completions",
        method="POST",
        payload={
            "model": model,
            "messages": [
                {"role": "system", "content": build_system_context(project)},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
        },
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
    key, _, _, model, endpoint = _config()
    if not key:
        raise ApiError(503, "xKiro is not configured. Set XKIRO_API_KEY in the server environment.")
    if not model:
        raise ApiError(503, "Set XKIRO_IMAGE_MODEL to an image-generation model ID.")
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
