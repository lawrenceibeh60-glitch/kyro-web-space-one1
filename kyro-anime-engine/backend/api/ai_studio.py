"""Optional xKiro-backed chat and image generation for KAE."""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from flask import Blueprint, jsonify, request

from backend.app.exceptions import ApiError

bp = Blueprint("ai_studio", __name__)


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
        detail = exc.read(2000).decode("utf-8", "replace")
        raise ApiError(502, f"AI provider returned HTTP {exc.code}: {detail}") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ApiError(502, f"Could not reach or parse the AI provider: {exc}") from exc


def _config():
    key = os.environ.get("XKIRO_API_KEY", "").strip()
    base = os.environ.get("XKIRO_BASE_URL", "https://api.xkiro.com/v1").rstrip("/")
    chat_model = os.environ.get("XKIRO_CHAT_MODEL", "mistralai/devstral-medium").strip()
    image_model = os.environ.get("XKIRO_IMAGE_MODEL", "openai/gpt-image-2.5").strip()
    image_endpoint = os.environ.get("XKIRO_IMAGE_URL", "").strip() or f"{base}/images/generations"
    return key, base, chat_model, image_model, image_endpoint


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
    )


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
        raise ApiError(503, "xKiro is not configured. Set XKIRO_API_KEY in the server environment; never paste it into the browser.")

    history = data.get("history", [])
    if not isinstance(history, list):
        history = []
    messages = [{
        "role": "system",
        "content": (
            "You are KAE's anime character and animation assistant. Help design "
            "consistent anime characters, pose sheets, animation frames, and 2D "
            "bone rigs. Preserve identity details across turns. When the user asks "
            "for an image, write a concise, visually specific image prompt and "
            "explain that image generation is a separate action. Never claim an "
            "image was generated unless the image endpoint returns one."
        ),
    }]
    for item in history[-12:]:
        if isinstance(item, dict) and item.get("role") in ("user", "assistant") and isinstance(item.get("content"), str):
            messages.append({"role": item["role"], "content": item["content"][:6000]})
    messages.append({"role": "user", "content": message.strip()})

    result = _request_json(
        f"{base}/chat/completions",
        method="POST",
        payload={"model": model, "messages": messages, "temperature": 0.7},
        api_key=key,
        timeout=90,
    )
    choices = result.get("choices") or []
    content = choices[0].get("message", {}).get("content") if choices else None
    if isinstance(content, list):
        content = "\n".join(part.get("text", "") for part in content if isinstance(part, dict))
    if not isinstance(content, str) or not content.strip():
        raise ApiError(502, "The AI provider returned no text response")
    return jsonify(reply=content.strip(), model=result.get("model", model))


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
    # xKiro returns 202 + a job ID. A provider that returns an image immediately
    # is also accepted, to keep compatible gateways usable.
    items = result.get("data") or result.get("images") or []
    item = items[0] if items and isinstance(items[0], dict) else {}
    image_url = item.get("url") or item.get("image_url")
    encoded = item.get("b64_json") or item.get("base64")
    if image_url or encoded:
        return jsonify(
            status="succeeded",
            image={"url": image_url, "b64_json": encoded,
                   "revised_prompt": item.get("revised_prompt") or prompt.strip()},
        ), 201

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

    job_url = f"{endpoint.rstrip('/')}/{quote(job_id, safe='')}"
    result = _request_json(job_url, api_key=key, timeout=30)
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
    return jsonify(
        job_id=job_id,
        status="succeeded",
        image={"url": image_url, "b64_json": encoded,
               "revised_prompt": item.get("revised_prompt") or result.get("prompt", "")},
    )
