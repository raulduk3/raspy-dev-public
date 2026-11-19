"""Jev through OpenRouter: closed questions out as a JSON-schema request, typed answers back, the
real charge recorded; and the same schemas served as MCP tools."""
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
from ai_ecosystem import jev  # noqa: E402


class Stand(BaseHTTPRequestHandler):
    seen = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['content-length'])))
        Stand.seen.append((dict(self.headers), body))
        answers = {'relevance': {'score': 2, 'confidence': 0.8}, 'load_first': {'probability': 0.7, 'confidence': 0.9}}
        out = {'model': 'typesafe/jev-router', 'usage': {'prompt_tokens': 120, 'cost': 0.000004},
               'choices': [{'message': {'content': json.dumps({'answers': answers})}}]}
        data = json.dumps(out).encode()
        self.send_response(200)
        self.send_header('content-type', 'application/json')
        self.send_header('content-length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


class JevOpenRouter(unittest.TestCase):
    def setUp(self):
        self.server = HTTPServer(('127.0.0.1', 0), Stand)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.shutdown)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        url = f'http://127.0.0.1:{self.server.server_port}/v1/chat/completions'
        env = mock.patch.dict(os.environ, {'DEV_PLATFORM_CONFIG': tmp.name + '/cfg', 'DEV_PLATFORM_STATE': tmp.name + '/state',
                                           'JEV_OPENROUTER_URL': url})
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop('OPENROUTER_API_KEY', None)
        Stand.seen.clear()

    def test_a_decision_goes_to_jev_router_with_the_closed_questions_and_records_the_real_charge(self):
        result = jev.decide(jev.load_schema('rank-context'), {'task': 'fix login', 'candidate': 'auth.ts'}, 'openrouter')
        self.assertEqual(result['answers']['relevance']['choice'], 'strong')
        self.assertEqual(result['answers']['load_first']['probability'], 0.7)
        headers, body = Stand.seen[0]
        self.assertEqual(body['model'], 'typesafe/jev-router')
        self.assertEqual(body['response_format']['type'], 'json_schema')
        self.assertNotIn('authorization', {k.lower() for k in headers})   # the proxy holds the key on dev-server
        usage = jev.read_usage()
        self.assertEqual((usage['calls'], usage['spent_micros']), (1, 4))

    def test_the_schemas_are_mcp_tools(self):
        lines = [{'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2025-06-18'}},
                 {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
                 {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'},
                 {'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call',
                  'params': {'name': 'jev_rank_context', 'arguments': {'state': {'task': 't', 'candidate': 'c'}}}}]
        out = io.StringIO()
        jev.serve_mcp(stdin=io.StringIO('\n'.join(json.dumps(m) for m in lines) + '\n'), stdout=out)
        replies = [json.loads(l) for l in out.getvalue().splitlines()]
        self.assertEqual([r['id'] for r in replies], [1, 2, 3])
        self.assertIn('jev_rank_context', [t['name'] for t in replies[1]['result']['tools']])
        self.assertEqual(json.loads(replies[2]['result']['content'][0]['text'])['answers']['relevance']['choice'], 'strong')


if __name__ == '__main__':
    unittest.main()
