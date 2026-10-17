"""Optional xKiro-backed chat and image generation for KAE."""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from flask import Blueprint, jsonify, request
from backend.app.exceptions import ApiError

bp = Blueprint("ai_studio", __name__)

def _post_json(url, payload, api_key, timeout=90):
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
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
    model = os.environ.get("XKIRO_CHAT_MODEL", "mistralai/devstral-medium")
    return key, base, model

@bp.get("/ai/status")
def status():
    key, base, model = _config()
    return jsonify(configured=bool(key), provider="xKiro", base_url=base,
                   chat_model=model, image_configured=bool(os.environ.get("XKIRO_IMAGE_URL", "").strip()))

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
    key, base, model = _config()
    if not key:
        raise ApiError(503, "xKiro is not configured. Set XKIRO_API_KEY in the server environment; never paste it into the browser.")
    history = data.get("history", [])
    if not isinstance(history, list):
        history = []
    messages = [{"role":"system","content":
        "You are KAE's anime character and animation assistant. Help design consistent anime characters, pose sheets, animation frames, and 2D bone rigs. Preserve identity details across turns. When the user asks for an image, write a concise, visually specific image prompt and explain that image generation is a separate action. Never claim an image was generated unless the image endpoint returns one."}]
    for item in history[-12:]:
        if isinstance(item, dict) and item.get("role") in ("user", "assistant") and isinstance(item.get("content"), str):
            messages.append({"role":item["role"],"content":item["content"][:6000]})
    messages.append({"role":"user","content":message.strip()})
    result = _post_json(f"{base}/chat/completions", {"model":model,"messages":messages,"temperature":0.7}, key)
    choices = result.get("choices") or []
    content = choices[0].get("message",{}).get("content") if choices else None
    if isinstance(content, list):
        content = "\n".join(part.get("text","") for part in content if isinstance(part,dict))
    if not isinstance(content,str) or not content.strip():
        raise ApiError(502,"The AI provider returned no text response")
    return jsonify(reply=content.strip(),model=result.get("model",model))

@bp.post("/ai/images")
def generate_image():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError(400,"Request body must be a JSON object")
    prompt = data.get("prompt")
    if not isinstance(prompt,str) or not prompt.strip():
        raise ApiError(400,"Describe the character or pose to generate")
    if len(prompt)>8000:
        raise ApiError(413,"Image prompt is too long (maximum 8000 characters)")
    key,base,_ = _config()
    if not key:
        raise ApiError(503,"xKiro is not configured. Set XKIRO_API_KEY in the server environment.")
    endpoint = os.environ.get("XKIRO_IMAGE_URL","").strip() or f"{base}/images/generations"
    model = os.environ.get("XKIRO_IMAGE_MODEL","").strip()
    payload = {"prompt":prompt.strip(),"n":1,"size":"1024x1024"}
    if model: payload["model"] = model
    result = _post_json(endpoint,payload,key,timeout=180)
    items = result.get("data") or result.get("images") or []
    item = items[0] if items and isinstance(items[0],dict) else {}
    url = item.get("url") or item.get("image_url")
    encoded = item.get("b64_json") or item.get("base64")
    if not url and not encoded:
        raise ApiError(502,"Image endpoint returned no URL or base64 image. Check XKIRO_IMAGE_URL and XKIRO_IMAGE_MODEL.")
    return jsonify(image={"url":url,"b64_json":encoded,"revised_prompt":item.get("revised_prompt") or prompt.strip()}),201
