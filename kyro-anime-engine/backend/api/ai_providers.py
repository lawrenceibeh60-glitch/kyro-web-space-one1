"""Per-session AI provider discovery and connection checks for KAE.

API keys are accepted per request and are never written to server-side storage.
"""
import base64
import json
import re
from urllib.parse import urlparse
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import Blueprint, jsonify, request
from backend.app.exceptions import ApiError

bp = Blueprint("ai_providers", __name__)

PROVIDERS = {
    "openai": ("OpenAI", "https://api.openai.com/v1", ["gpt-4.1", "gpt-4.1-mini", "gpt-4o", "gpt-4o-mini"]),
    "anthropic": ("Anthropic / Claude", "https://api.anthropic.com/v1", ["claude-sonnet-4-5", "claude-haiku-4-5", "claude-opus-4-1"]),
    "groq": ("Groq", "https://api.groq.com/openai/v1", ["openai/gpt-oss-120b", "llama-3.3-70b-versatile", "qwen/qwen3-32b"]),
    "openrouter": ("OpenRouter", "https://openrouter.ai/api/v1", ["openai/gpt-4.1-mini", "anthropic/claude-sonnet-4.5", "google/gemini-2.5-flash"]),
    "together": ("Together AI", "https://api.together.xyz/v1", ["openai/gpt-oss-120b", "meta-llama/Llama-3.3-70B-Instruct-Turbo"]),
    "deepseek": ("DeepSeek", "https://api.deepseek.com/v1", ["deepseek-chat", "deepseek-reasoner"]),
    "mistral": ("Mistral", "https://api.mistral.ai/v1", ["mistral-large-latest", "mistral-small-latest", "codestral-latest"]),
    "xai": ("xAI", "https://api.x.ai/v1", ["grok-4", "grok-3", "grok-3-mini"]),
    "cerebras": ("Cerebras", "https://api.cerebras.ai/v1", ["llama-3.3-70b", "qwen-3-32b"]),
    "fireworks": ("Fireworks AI", "https://api.fireworks.ai/inference/v1", ["accounts/fireworks/models/llama-v3p3-70b-instruct"]),
    "perplexity": ("Perplexity", "https://api.perplexity.ai", ["sonar-pro", "sonar"]),
    "nvidia": ("NVIDIA NIM", "https://integrate.api.nvidia.com/v1", ["meta/llama-3.3-70b-instruct"]),
    "xkiro": ("xKiro", "https://api.xkiro.com/v1", ["mistralai/devstral-medium"]),
    "custom": ("Custom OpenAI-compatible", "", []),
}


def read_profile(data):
    raw = data.get("provider_config") if isinstance(data.get("provider_config"), dict) else data
    provider = str(raw.get("provider", "xkiro")).strip().lower()
    if provider not in PROVIDERS:
        raise ApiError(400, "Choose a supported AI provider.")
    label, default_url, fallbacks = PROVIDERS[provider]
    base_url = str(raw.get("base_url") or default_url).strip().rstrip("/")
    api_key = str(raw.get("api_key") or "").strip()
    model = str(raw.get("model") or (fallbacks[0] if fallbacks else "")).strip()
    if not api_key:
        raise ApiError(400, "Enter an API key first.")
    parsed = urlparse(base_url)
    if parsed.scheme.lower() != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ApiError(400, "API base URL must be a valid HTTPS URL without embedded credentials.")
    host = parsed.hostname.lower()
    if host in {"localhost", "metadata.google.internal"} or host.endswith((".local", ".internal", ".localhost")):
        raise ApiError(400, "Local and internal network hosts are not allowed as provider endpoints.")
    try:
        import ipaddress
        address = ipaddress.ip_address(host)
        if not address.is_global:
            raise ApiError(400, "Private or reserved IP addresses are not allowed as provider endpoints.")
    except ValueError:
        pass
    return {"provider": provider, "label": label, "base_url": base_url, "api_key": api_key, "model": model, "fallback_models": fallbacks}


def provider_request(profile, path, method="GET", payload=None, timeout=30):
    headers = {"Accept": "application/json"}
    if profile["provider"] == "anthropic":
        headers["x-api-key"] = profile["api_key"]
        headers["anthropic-version"] = "2023-06-01"
    else:
        headers["Authorization"] = "Bearer " + profile["api_key"]
    if profile["provider"] == "openrouter":
        headers["HTTP-Referer"] = "https://kyro-animation-engine.onrender.com"
        headers["X-Title"] = "KYRO Animation Engine"
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = Request(profile["base_url"] + path, data=body, headers=headers, method=method)
    try:
        with urlopen(req, timeout=timeout) as response:
            return json.loads(response.read(4 * 1024 * 1024).decode("utf-8"))
    except HTTPError as exc:
        raise ApiError(502, f"{profile['label']} returned HTTP {exc.code}. Check the key, account access, and model permissions.") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ApiError(502, f"Could not reach {profile['label']} ({type(exc).__name__}). Check the base URL and network.") from exc


def completion(profile, messages, temperature=0.2, timeout=90):
    model = profile["model"]
    if not model:
        raise ApiError(400, "Choose a model before sending an AI request.")
    if profile["provider"] == "anthropic":
        system = "\n\n".join(item["content"] for item in messages if item.get("role") == "system" and isinstance(item.get("content"), str))
        conversation = []
        for item in messages:
            if item.get("role") not in ("user", "assistant"):
                continue
            content = item.get("content", "")
            if isinstance(content, list):
                blocks = []
                for part in content:
                    if not isinstance(part, dict):
                        continue
                    if part.get("type") == "text":
                        blocks.append({"type": "text", "text": str(part.get("text", ""))})
                    elif part.get("type") == "image_url":
                        image_url = part.get("image_url", {}).get("url", "")
                        match = re.match(r"^data:(image/(?:jpeg|png|gif|webp));base64,(.+)$", image_url, re.S)
                        if match:
                            blocks.append({"type": "image", "source": {"type": "base64", "media_type": match.group(1), "data": match.group(2)}})
                        else:
                            raise ApiError(400, "Claude image analysis requires base64 JPEG, PNG, GIF, or WebP frames.")
                content = blocks
            conversation.append({"role": item["role"], "content": content})
        result = provider_request(profile, "/messages", "POST", {"model": model, "max_tokens": 4096, "temperature": temperature, "system": system, "messages": conversation}, timeout)
        reply = "\n".join(block.get("text", "") for block in result.get("content", []) if isinstance(block, dict) and block.get("type") == "text")
        if not reply.strip():
            raise ApiError(502, "Claude returned no text response.")
        return reply.strip(), result.get("model", model)
    result = provider_request(profile, "/chat/completions", "POST", {"model": model, "messages": messages, "temperature": temperature}, timeout)
    choices = result.get("choices") or []
    content = choices[0].get("message", {}).get("content") if choices else None
    if isinstance(content, list):
        content = "\n".join(part.get("text", "") for part in content if isinstance(part, dict))
    if not isinstance(content, str) or not content.strip():
        raise ApiError(502, "The provider returned no text response.")
    return content.strip(), result.get("model", model)


@bp.get("/ai/providers")
def list_providers():
    return jsonify(providers=[{"id": key, "label": val[0], "base_url": val[1], "models": val[2]} for key, val in PROVIDERS.items()])


@bp.post("/ai/providers/models")
def list_models():
    profile = read_profile(request.get_json(silent=True) or {})
    result = provider_request(profile, "/models")
    models = [item.get("id") for item in result.get("data", []) if isinstance(item, dict) and item.get("id")]
    if not models:
        models = profile["fallback_models"]
    models = sorted(set(models), key=str.casefold)
    return jsonify(provider=profile["provider"], models=models, source="provider API" if result.get("data") else "curated fallback")


@bp.post("/ai/providers/test")
def test_connection():
    profile = read_profile(request.get_json(silent=True) or {})
    reply, used_model = completion(profile, [{"role": "user", "content": "Reply with exactly: KAE connection successful"}], temperature=0, timeout=35)
    return jsonify(ok=True, provider=profile["label"], model=used_model, reply=reply[:160], message="Provider connected and returned a response.")
