from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import urllib.parse
from typing import Dict, Any
from src.cag_engine import CAGCacheEngine, DocumentItem
from src.config import load_settings

settings = load_settings()
cag_engine = CAGCacheEngine(default_ttl=settings.default_ttl)

class CAGRequestHandler(BaseHTTPRequestHandler):
    def _send_json_response(self, status_code: int, data: Dict[str, Any]):
        response_bytes = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(response_bytes)

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        
        try:
            payload = json.loads(body)
        except Exception:
            self._send_json_response(400, {"error": "Invalid JSON payload"})
            return

        if parsed_url.path == "/api/v1/cache/warm":
            repo_id = payload.get("repo_id", "default-repo")
            raw_docs = payload.get("documents", [])
            documents = [DocumentItem(path=d.get("path", "file.txt"), content=d.get("content", "")) for d in raw_docs]
            ttl_seconds = payload.get("ttl_seconds", settings.default_ttl)
            
            session = cag_engine.warm_cache(repo_id, documents, ttl_seconds)
            self._send_json_response(200, {
                "cache_id": session.cache_id,
                "repo_id": session.repo_id,
                "cached_tokens": session.token_count,
                "documents_count": session.documents_count,
                "expires_at": session.expires_at,
                "status": "ACTIVE"
            })
            return

        elif parsed_url.path == "/api/v1/query":
            cache_id = payload.get("cache_id")
            prompt = payload.get("prompt", "")
            if not cache_id or not prompt:
                self._send_json_response(400, {"error": "cache_id and prompt are required fields"})
                return

            result = cag_engine.execute_query(cache_id, prompt)
            self._send_json_response(200, result)
            return

        else:
            self._send_json_response(404, {"error": "Endpoint not found"})

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        if parsed_url.path == "/api/v1/cache/stats":
            stats = cag_engine.get_stats()
            self._send_json_response(200, stats)
        elif parsed_url.path == "/health":
            self._send_json_response(200, {"status": "HEALTHY", "version": "1.0.0"})
        else:
            self._send_json_response(404, {"error": "Endpoint not found"})

def create_server(port: int = 8000):
    server_address = ("127.0.0.1", port)
    return HTTPServer(server_address, CAGRequestHandler)

if __name__ == "__main__":
    server = create_server(settings.port)
    print(f"[*] CAG Copilot Service running on port {settings.port}...")
    server.serve_forever()
