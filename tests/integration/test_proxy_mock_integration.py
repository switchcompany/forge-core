import threading
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from urllib.parse import urlparse
import requests


def _start_mock_server(response_func, port=8002):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get('content-length', 0))
            body = self.rfile.read(length).decode('utf-8') if length else ''
            result, status = response_func(self.path, self.headers, body)
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode('utf-8'))

        def log_message(self, format, *args):
            return

    server = HTTPServer(('localhost', port), Handler)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def test_proxy_integration_happy_path(monkeypatch):
    # Start a mock proxy that returns Anthropic-like normalized response
    def responder(path, headers, body):
        return ({
            'choices': [{'message': {'content': 'normalized reply'}}],
            'usage': {'prompt_tokens': 10, 'completion_tokens': 5},
            'model': 'claude-sonnet-4-6'
        }, 200)

    server = _start_mock_server(responder, port=8002)

    # Call provider with base_url pointing to mock server
    from forge_core.models.config import AIConfig
    from forge_core.ai import provider

    cfg = AIConfig(api_key='fc_token', base_url='http://localhost:8002')
    res = provider.complete(cfg, 'SYS', 'USER', phase='1')
    assert 'normalized reply' in res

    server.shutdown()
