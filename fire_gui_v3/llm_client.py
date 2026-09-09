"""Minimal clients for OpenAI, OpenAI-compatible servers, and local Ollama."""
from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


class LLMError(RuntimeError):
    pass


def _endpoint(base_url: str, suffix: str) -> str:
    base_url = base_url.strip().rstrip("/")
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise LLMError("The model server URL must be a valid http:// or https:// address.")
    if base_url.endswith(suffix):
        return base_url
    return base_url + suffix


def _post_json(url: str, payload: dict, api_key: str = "", timeout: int = 90) -> dict:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read(5_000_001)
            if len(body) > 5_000_000:
                raise LLMError("The model provider response exceeded the 5 MB safety limit.")
            return json.loads(body.decode("utf-8"))
    except HTTPError as error:
        try:
            detail = json.loads(error.read(20_000).decode("utf-8")).get("error", {})
            detail = detail.get("message", detail) if isinstance(detail, dict) else detail
        except Exception:
            detail = "The provider rejected the request."
        raise LLMError(f"Model provider returned HTTP {error.code}: {str(detail)[:300]}") from None
    except URLError as error:
        raise LLMError(f"Could not reach the model provider: {error.reason}") from None
    except TimeoutError:
        raise LLMError("The model provider did not respond before the 90-second timeout.") from None
    except (ValueError, UnicodeDecodeError):
        raise LLMError("The model provider returned an invalid JSON response.") from None


def _openai_text(data: dict) -> str:
    if data.get("output_text"):
        return str(data["output_text"])
    for item in data.get("output", []):
        if item.get("type") == "message":
            for content in item.get("content", []):
                if content.get("type") == "output_text" and content.get("text"):
                    return str(content["text"])
    raise LLMError("The OpenAI response did not contain text output.")


def ask_llm(provider: str, base_url: str, api_key: str, model: str, messages: list, instructions: str) -> str:
    provider = provider.strip().lower()
    model = model.strip()
    if not model:
        raise LLMError("Enter a model name.")
    if provider == "openai":
        if not api_key.strip():
            raise LLMError("Enter an OpenAI API key.")
        data = _post_json(
            "https://api.openai.com/v1/responses",
            {"model": model, "instructions": instructions, "input": messages, "store": False, "max_output_tokens": 1200},
            api_key.strip(),
        )
        return _openai_text(data)
    system_messages = [{"role": "system", "content": instructions}, *messages]
    if provider == "ollama":
        data = _post_json(
            _endpoint(base_url or "http://127.0.0.1:11434", "/api/chat"),
            {"model": model, "messages": system_messages, "stream": False, "options": {"num_predict": 1200}},
        )
        try:
            return str(data["message"]["content"])
        except (KeyError, TypeError):
            raise LLMError("Ollama returned a response without message text.") from None
    if provider == "compatible":
        data = _post_json(
            _endpoint(base_url, "/chat/completions"),
            {"model": model, "messages": system_messages, "temperature": 0.2, "max_tokens": 1200},
            api_key.strip(),
        )
        try:
            return str(data["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError):
            raise LLMError("The compatible provider returned a response without message text.") from None
    raise LLMError("Choose OpenAI, Ollama, or an OpenAI-compatible provider.")
