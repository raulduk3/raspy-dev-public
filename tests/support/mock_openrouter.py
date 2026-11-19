#!/usr/bin/env python3
"""A local stand-in for OpenRouter's chat completions API, for offline API-rig tests.

  mock_openrouter.py --port N --brain brain.py --log requests.jsonl

Pi talks to it as the `openrouter` provider when a seat's Pi models.json points the provider's
baseUrl here: OpenAI-style chat completions for most models, the Anthropic Messages API (path
.../messages, key in x-api-key) for anthropic/* models, as Pi uses OpenRouter. The brain decides each reply: `respond(messages, model) -> {"text": str}` or
`{"bash": "command"}` (one tool call). A key is required in the request, as OpenRouter requires
one; its value is never logged. No network beyond loopback. Test support, never a product path.
"""
import argparse
import importlib.util
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import itertools
import time

COUNTER = itertools.count(1)


def load_brain(path):
    spec = importlib.util.spec_from_file_location('brain', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return '\n'.join(text_of(p.get('content')) if p.get('type') == 'tool_result' else p.get('text', '')
                         for p in content if isinstance(p, dict))
    return ''


def anthropic_messages(messages):
    """Anthropic-shaped turns as the brain sees them: a user turn carrying tool results is a tool turn."""
    out = []
    for m in messages:
        content = m.get('content')
        if m.get('role') == 'user' and isinstance(content, list) and any(
                isinstance(p, dict) and p.get('type') == 'tool_result' for p in content):
            out.append({'role': 'tool', 'text': text_of(content)})
        else:
            out.append({**m, 'text': text_of(content)})
    return out


class Handler(BaseHTTPRequestHandler):
    brain = None
    log = None

    def log_message(self, *args):
        pass

    def do_GET(self):
        self.reply(200, {'data': []})

    def reply(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header('content-type', 'application/json')
        self.send_header('content-length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get('content-length', 0))) or b'{}')
        if self.path.split('?')[0].endswith('/messages') and len(self.headers.get('x-api-key') or '') >= 8:
            return self.anthropic(body)
        if not (self.headers.get('authorization') or '').startswith('Bearer ') or \
                len(self.headers.get('authorization', '')) < 12:
            with open(self.log, 'a') as stream:
                stream.write(json.dumps({'at': time.time(), 'refused': self.path, 'model': body.get('model'),
                                         'headers': sorted(self.headers.keys())}) + '\n')
            return self.reply(401, {'error': {'message': 'No auth credentials found'}})
        messages = body.get('messages') or []
        answer = self.brain.respond([{**m, 'text': text_of(m.get('content'))} for m in messages
                                     if m.get('role') != 'system'], body.get('model'))
        with open(self.log, 'a') as stream:
            last = next((text_of(m.get('content')) for m in reversed(messages) if m.get('role') in ('user', 'tool')), '')
            stream.write(json.dumps({'at': time.time(), 'model': body.get('model'), 'last': last[:300],
                                     'answer': answer, 'key_present': True}) + '\n')
        n = next(COUNTER)
        usage = {'prompt_tokens': 1000 + 10 * len(messages), 'completion_tokens': 50,
                 'total_tokens': 1050 + 10 * len(messages), 'cost': 0.0001}
        if 'bash' in answer:
            delta = {'role': 'assistant', 'content': None, 'tool_calls': [{
                'index': 0, 'id': f'call_{n}', 'type': 'function',
                'function': {'name': 'bash', 'arguments': json.dumps({'command': answer['bash']})}}]}
            finish = 'tool_calls'
        else:
            delta, finish = {'role': 'assistant', 'content': answer.get('text', '')}, 'stop'
        base = {'id': f'gen-{n}', 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': body.get('model')}
        if not body.get('stream'):
            message = {k: v for k, v in delta.items() if k != 'index'}
            if 'tool_calls' in message:
                message['tool_calls'] = [{k: v for k, v in c.items() if k != 'index'} for c in message['tool_calls']]
            return self.reply(200, {**base, 'object': 'chat.completion',
                                    'choices': [{'index': 0, 'message': message, 'finish_reason': finish}], 'usage': usage})
        self.send_response(200)
        self.send_header('content-type', 'text/event-stream')
        self.end_headers()
        for chunk in ({**base, 'choices': [{'index': 0, 'delta': delta, 'finish_reason': None}]},
                      {**base, 'choices': [{'index': 0, 'delta': {}, 'finish_reason': finish}]},
                      {**base, 'choices': [], 'usage': usage}):
            self.wfile.write(f'data: {json.dumps(chunk)}\n\n'.encode())
        self.wfile.write(b'data: [DONE]\n\n')
        self.wfile.flush()


    def anthropic(self, body):
        messages = [m for m in anthropic_messages(body.get('messages') or []) if m.get('role') != 'system']
        answer = self.brain.respond(messages, body.get('model'))
        with open(self.log, 'a') as stream:
            last = next((m['text'] for m in reversed(messages) if m.get('role') in ('user', 'tool')), '')
            stream.write(json.dumps({'at': time.time(), 'model': body.get('model'), 'last': last[:300],
                                     'answer': answer, 'key_present': True, 'api': 'anthropic-messages',
                                     'roles': [m.get('role') for m in messages]}) + '\n')
        n = next(COUNTER)
        usage = {'input_tokens': 1000 + 10 * len(messages), 'output_tokens': 50}
        if 'bash' in answer:
            block, stop = {'type': 'tool_use', 'id': f'toolu_{n}', 'name': 'bash', 'input': {}}, 'tool_use'
            delta = {'type': 'input_json_delta', 'partial_json': json.dumps({'command': answer['bash']})}
        else:
            block, stop = {'type': 'text', 'text': ''}, 'end_turn'
            delta = {'type': 'text_delta', 'text': answer.get('text', '')}
        message = {'id': f'msg_{n}', 'type': 'message', 'role': 'assistant', 'model': body.get('model'),
                   'content': [], 'stop_reason': None, 'usage': {'input_tokens': usage['input_tokens'], 'output_tokens': 0}}
        events = [('message_start', {'type': 'message_start', 'message': message}),
                  ('content_block_start', {'type': 'content_block_start', 'index': 0, 'content_block': block}),
                  ('content_block_delta', {'type': 'content_block_delta', 'index': 0, 'delta': delta}),
                  ('content_block_stop', {'type': 'content_block_stop', 'index': 0}),
                  ('message_delta', {'type': 'message_delta', 'delta': {'stop_reason': stop},
                                     'usage': {'output_tokens': usage['output_tokens']}}),
                  ('message_stop', {'type': 'message_stop'})]
        self.send_response(200)
        self.send_header('content-type', 'text/event-stream')
        self.end_headers()
        for name, data in events:
            self.wfile.write(f'event: {name}\ndata: {json.dumps(data)}\n\n'.encode())
        self.wfile.flush()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--brain', required=True)
    parser.add_argument('--log', required=True)
    args = parser.parse_args()
    Handler.brain, Handler.log = load_brain(args.brain), args.log
    ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()


if __name__ == '__main__':
    main()
