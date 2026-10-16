#!/usr/bin/env python3
"""SenseNet Hotspot Studio: a dependency-free, loopback-only development app."""
import argparse
import datetime as dt
import ipaddress
import json
import re
import socket
import threading
import urllib.error
import urllib.parse
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCES = {
    "VIIRS_SNPP_NRT", "VIIRS_NOAA20_NRT", "VIIRS_NOAA21_NRT", "MODIS_NRT",
    "VIIRS_SNPP_SP", "VIIRS_NOAA20_SP", "MODIS_SP",
}
MAX_RESPONSE = 25 * 1024 * 1024


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch(url, payload=None, key="", timeout=45):
    headers = {"User-Agent": "SenseNet-Hotspot-Studio/0.1", "Accept": "application/json,text/csv"}
    body = None
    if payload is not None:
        body = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    if key:
        if "\n" in key or "\r" in key or len(key) > 4096:
            raise ValueError("Invalid API key format.")
        headers["Authorization"] = "Bearer " + key
    request = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.build_opener(NoRedirect()).open(request, timeout=timeout) as response:
        data = response.read(MAX_RESPONSE + 1)
    if len(data) > MAX_RESPONSE:
        raise ValueError("Response is too large. Query a smaller area or fewer days.")
    return data.decode("utf-8-sig")


def firms_url(data, availability=False):
    key = str(data.get("key", "")).strip()
    if not re.fullmatch(r"[a-zA-Z0-9_-]{16,128}", key):
        raise ValueError("Enter the MAP_KEY emailed to you by NASA FIRMS.")
    source = data.get("source", "VIIRS_SNPP_NRT")
    if source not in SOURCES:
        raise ValueError("Choose a supported NASA FIRMS product.")
    if availability:
        return f"https://firms.modaps.eosdis.nasa.gov/api/data_availability/csv/{key}/{source}"
    days = data.get("days", 1)
    if isinstance(days, bool) or str(days) not in {"1", "2", "3", "4", "5"}:
        raise ValueError("NASA area queries accept 1 to 5 days per request.")
    area = str(data.get("area", "world")).strip()
    if area != "world":
        try:
            west, south, east, north = [float(v.strip()) for v in area.split(",")]
        except (TypeError, ValueError):
            raise ValueError("Use west,south,east,north or world for the area.") from None
        if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
            raise ValueError("Invalid bounds. Split antimeridian-crossing areas into two queries.")
        area = ",".join(f"{v:g}" for v in (west, south, east, north))
    date = str(data.get("date", "")).strip()
    if date:
        try:
            parsed = dt.date.fromisoformat(date)
        except ValueError:
            raise ValueError("Use a start date in YYYY-MM-DD format.") from None
        if parsed > dt.datetime.now(dt.timezone.utc).date():
            raise ValueError("The start date cannot be in the future.")
    return f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/{source}/{area}/{days}" + (f"/{date}" if date else "")


def llm_url(data):
    provider = data.get("provider")
    if provider not in {"ollama", "local", "hosted"}:
        raise ValueError("Choose Ollama, a local compatible server, or a hosted API.")
    base = str(data.get("endpoint", "")).strip().rstrip("/")
    p = urllib.parse.urlsplit(base)
    if not p.hostname or p.username or p.password or p.query or p.fragment:
        raise ValueError("Enter a base URL without credentials, a query, or a fragment.")
    if provider in {"ollama", "local"}:
        if p.scheme not in {"http", "https"} or p.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("Local models must use localhost, 127.0.0.1, or [::1].")
        if p.port == data.get("app_port"):
            raise ValueError("Use your model server's port, not this application's port.")
    else:
        if p.scheme != "https":
            raise ValueError("Hosted API endpoints must use HTTPS.")
        try:
            addresses = socket.getaddrinfo(p.hostname, p.port or 443, type=socket.SOCK_STREAM)
        except socket.gaierror:
            raise ValueError("The model server hostname could not be resolved.") from None
        if not addresses or any(not ipaddress.ip_address(x[4][0]).is_global for x in addresses):
            raise ValueError("For local services, select a local provider and use loopback.")
    suffix = "/api/chat" if provider == "ollama" else "/chat/completions"
    if provider == "ollama" and p.path not in {"", "/api"}:
        raise ValueError("Use the Ollama root URL, for example http://localhost:11434.")
    if provider == "ollama" and p.path == "/api":
        base = base[:-4]
    return base + suffix


def chat(data):
    url = llm_url(data)
    model = str(data.get("model", "")).strip()
    if not model or len(model) > 200:
        raise ValueError("Enter the model name loaded in your model server or API.")
    messages = data.get("messages", [])
    if not isinstance(messages, list) or not messages or len(messages) > 24:
        raise ValueError("Invalid conversation length.")
    clean = []
    for message in messages:
        if not isinstance(message, dict) or message.get("role") not in {"system", "user", "assistant"}:
            raise ValueError("Invalid chat message.")
        content = message.get("content")
        if not isinstance(content, str) or len(content) > 30000:
            raise ValueError("Chat message is too long.")
        clean.append({"role": message["role"], "content": content})
    payload = {"model": model, "messages": clean, "stream": False}
    if data["provider"] != "ollama":
        payload["max_tokens"] = 1200
    raw = json.loads(fetch(url, payload, str(data.get("key", "")), timeout=120))
    try:
        result = raw["message"]["content"] if data["provider"] == "ollama" else raw["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise ValueError("The server did not return a supported chat response.") from None
    if not isinstance(result, str) or not result.strip():
        raise ValueError("The model returned an empty response. Check its configuration.")
    return {"reply": result[:60000]}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / "static"), **kwargs)

    def log_message(self, fmt, *args):
        # No URL, body, or credential logging, including upstream exceptions.
        pass

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https://*.tile.openstreetmap.org; connect-src 'self'; font-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'")
        super().end_headers()

    def json_response(self, status, result):
        body = json.dumps(result).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def valid_host(self):
        port = self.server.server_port
        return self.headers.get("Host") in {f"localhost:{port}", f"127.0.0.1:{port}"}

    def do_GET(self):
        if not self.valid_host():
            return self.json_response(403, {"error": "Use the local application URL."})
        if self.path == "/api/health":
            return self.json_response(200, {"status": "ready", "version": "0.1.0", "model_inference": False, "sensenet_connector": "planned"})
        if self.path.startswith("/api/"):
            return self.json_response(404, {"error": "Unknown endpoint."})
        return super().do_GET()

    def list_directory(self, path):
        self.send_error(404)

    def do_POST(self):
        origin = self.headers.get("Origin")
        valid_origin = origin in {None, "http://" + self.headers.get("Host", "")}
        if not self.valid_host() or not valid_origin or self.headers.get("X-Hotspot-Request") != "1":
            return self.json_response(403, {"error": "Request must come from the local application."})
        if self.headers.get_content_type() != "application/json":
            return self.json_response(415, {"error": "Expected a JSON request."})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 2 or length > 200000:
                return self.json_response(413, {"error": "Request is too large or empty."})
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError("Expected a request object.")
            if self.path in {"/api/firms/query", "/api/firms/availability"}:
                raw = fetch(firms_url(data, self.path.endswith("availability")))
                if self.path.endswith("query") and not ("latitude" in raw.split("\n")[0].lower() and "longitude" in raw.split("\n")[0].lower()):
                    raise ValueError("NASA did not return hotspot CSV data. Check the MAP_KEY, product availability, dates, and quota.")
                if self.path.endswith("availability") and not raw.lower().startswith("data_id,"):
                    raise ValueError("NASA did not return availability data. Check your MAP_KEY and quota.")
                return self.json_response(200, {"csv": raw})
            if self.path == "/api/chat":
                data["app_port"] = self.server.server_port
                return self.json_response(200, chat(data))
            if self.path == "/api/sensenet/query":
                return self.json_response(501, {"error": "The SenseNet data service is not available yet."})
            return self.json_response(404, {"error": "Unknown endpoint."})
        except urllib.error.HTTPError as exc:
            return self.json_response(502, {"error": f"The upstream service returned HTTP {exc.code}. Check the key, endpoint, quota, and model or product."})
        except (urllib.error.URLError, TimeoutError, socket.timeout):
            return self.json_response(502, {"error": "Could not reach the service. Check the endpoint, network, or local model server, then retry."})
        except (ValueError, TypeError) as exc:
            return self.json_response(400, {"error": str(exc) if not isinstance(exc, json.JSONDecodeError) else "The service or request returned invalid JSON."})
        except Exception:
            return self.json_response(500, {"error": "The request could not be completed. Check your connection and configuration."})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--open", action="store_true", help="Open the local interface in your default browser")
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"SenseNet Hotspot Studio\nOpen http://127.0.0.1:{server.server_port}\nPress Ctrl+C to stop.", flush=True)
    if args.open:
        import webbrowser
        threading.Timer(0.5, lambda: webbrowser.open(f"http://127.0.0.1:{server.server_port}")).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
