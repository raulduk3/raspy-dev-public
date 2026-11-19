"""Bounded Jev decision adapter.

Jev is integrated here as a classifier primitive only. The platform supplies closed
schemas, callers supply state, and ordinary code decides what to do with the typed
result. This module never asks Jev to plan, write prose, summarize, or settle truth.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request

from . import secret

SCHEMA_VERSION = 1
ALLOWED_TYPES = {'choice', 'score', 'noul'}
DEFAULT_ENDPOINT = 'https://gateway.ngrok.ai/v1/systemone'
DEFAULT_MODEL = 'typesafeai/jev-latest'
DEFAULT_PRICE_MICROS_PER_MILLION = 42_000
DEFAULT_MONTHLY_LIMIT_MICROS = 10_000_000
SECRET_NAME = 'dev-platform-jev'
# Jev through OpenRouter (owner, 2026-10-14): TypeSafe's Jev Router on the one OpenRouter key, no
# Jev account. On dev-server the key stays with the local proxy (jev-proxy); elsewhere a caller
# may name OpenRouter itself and pass OPENROUTER_API_KEY.
OPENROUTER_URL = 'http://127.0.0.1:8741/v1/chat/completions'
OPENROUTER_MODEL = 'typesafe/jev-router'
KEY_ENV = 'JEV_API_KEY'


class JevError(Exception):
    pass


def platform_root():
    return Path(__file__).resolve().parents[2]


def config_root():
    return Path(os.environ.get('DEV_PLATFORM_CONFIG') or Path.home() / '.config/dev-platform')


def state_root():
    return Path(os.environ.get('DEV_PLATFORM_STATE') or Path.home() / '.local/state/dev-platform')


def config_path():
    return config_root() / 'jev.json'


def usage_path():
    return state_root() / 'jev/usage.json'


def lock_path():
    return state_root() / 'jev/usage.lock'


def default_config():
    return {
        'enabled': True,
        'endpoint': DEFAULT_ENDPOINT,
        'model': DEFAULT_MODEL,
        'credential': {'source': 'secret', 'name': SECRET_NAME},
        'monthly_limit_micros': DEFAULT_MONTHLY_LIMIT_MICROS,
        'prompt_price_micros_per_million_tokens': DEFAULT_PRICE_MICROS_PER_MILLION,
        'notes': 'No secret belongs in this file. The key is the root-held dev-platform-jev secret, or JEV_API_KEY.',
    }


def load_config():
    path = config_path()
    if not path.exists():
        return default_config()
    try:
        data = json.loads(path.read_text())
    except ValueError as exc:
        raise JevError('invalid Jev config JSON') from exc
    cfg = default_config()
    cfg.update(data)
    credential = dict(default_config()['credential'])
    credential.update(data.get('credential', {}) if isinstance(data.get('credential'), dict) else {})
    cfg['credential'] = credential
    return cfg


def write_config(cfg):
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = path.with_name(f'.{path.name}.{os.getpid()}.tmp')
    tmp.write_text(json.dumps(cfg, indent=2, sort_keys=True) + '\n')
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def install_research_config():
    """Install the dev-platform Jev config from the research-agent operating values.

    The research platform reaches Jev through ngrok AI Gateway, uses JEV_API_KEY
    in the environment and keeps provider configuration credential-free.
    Dev-platform stores the same non-secret provider settings and expects the key
    as the dev-platform-jev secret the launcher hands in, or JEV_API_KEY.
    """
    cfg = default_config()
    write_config(cfg)
    write_usage(empty_usage())
    return cfg


def resolve_key(cfg):
    if os.environ.get(KEY_ENV):
        return os.environ[KEY_ENV]
    cred = cfg.get('credential', {}) if isinstance(cfg.get('credential'), dict) else {}
    # 'keychain' is how a config written on the Mac names the same key.
    if cred.get('source') in ('secret', 'keychain'):
        return secret.read(cred.get('name', SECRET_NAME))
    return None


def registry_dir(root=None):
    return (Path(root) if root else platform_root()) / 'schemas' / 'jev'


def schema_names(root=None):
    folder = registry_dir(root)
    return sorted(p.stem for p in folder.glob('*.json') if p.is_file())


def load_schema(name, root=None):
    if '/' in name or name.startswith('.'):
        raise JevError(f'invalid schema name: {name}')
    path = registry_dir(root) / f'{name}.json'
    try:
        schema = json.loads(path.read_text())
    except FileNotFoundError as exc:
        raise JevError(f'unknown schema: {name}') from exc
    except ValueError as exc:
        raise JevError(f'invalid schema JSON: {name}') from exc
    validate_schema(schema, expected_name=name)
    return schema


def validate_schema(schema, expected_name=None):
    if not isinstance(schema, dict):
        raise JevError('schema must be an object')
    if schema.get('version') != SCHEMA_VERSION:
        raise JevError('unsupported schema version')
    if expected_name and schema.get('name') != expected_name:
        raise JevError('schema name does not match file name')
    questions = schema.get('questions')
    if not isinstance(questions, list) or not questions:
        raise JevError('schema must declare questions')
    seen = set()
    for q in questions:
        if not isinstance(q, dict):
            raise JevError('question must be an object')
        qid = q.get('id')
        if not isinstance(qid, str) or not qid or qid in seen:
            raise JevError('question id must be unique non-empty string')
        seen.add(qid)
        qtype = q.get('type')
        if qtype not in ALLOWED_TYPES:
            raise JevError(f'{qid}: unsupported question type')
        text = q.get('question')
        if not isinstance(text, str) or not text.strip():
            raise JevError(f'{qid}: question text is required')
        if qtype in {'choice', 'score'}:
            options = q.get('options')
            if not isinstance(options, list) or len(options) < 2:
                raise JevError(f'{qid}: options must contain at least two choices')
            ids = [o.get('id') for o in options if isinstance(o, dict)]
            if len(ids) != len(options) or any(not isinstance(i, str) or not i for i in ids):
                raise JevError(f'{qid}: every option needs an id')
            if len(set(ids)) != len(ids):
                raise JevError(f'{qid}: option ids must be unique')
    return True


def systemone_questions(schema):
    out = {}
    for q in schema['questions']:
        qtype = q['type']
        item = {'type': qtype, 'instructions': q['question']}
        if qtype == 'choice':
            item['criteria'] = {o['id']: o.get('meaning', o['id']) for o in q['options']}
        elif qtype == 'score':
            item['criteria'] = [o.get('meaning', o['id']) for o in q['options']]
        out[q['id']] = item
    return out


def request_for(schema, state, cfg=None):
    """Return the provider request. It contains state and closed questions only."""
    cfg = cfg or load_config()
    return {'state': state, 'model': cfg.get('model', DEFAULT_MODEL), 'questions': systemone_questions(schema)}


def read_json_arg(value):
    if value == '-':
        raw = sys.stdin.read()
    elif value and value.startswith('@'):
        raw = Path(value[1:]).read_text()
    else:
        raw = value
    try:
        return json.loads(raw)
    except ValueError as exc:
        raise JevError('expected JSON input') from exc


def canonical_question_map(schema):
    return {q['id']: q for q in schema['questions']}


def option_ids(question):
    return {o['id'] for o in question.get('options', [])}


def score_choice_from_probabilities(question, probs):
    ids = [o['id'] for o in question['options']]
    if not probs:
        return None
    best = max(probs.items(), key=lambda item: item[1])[0]
    try:
        return ids[int(best)] if str(int(best)) == str(best) else best
    except (ValueError, IndexError):
        return best if best in ids else None


def validate_result(schema, result):
    if not isinstance(result, dict):
        raise JevError('provider result must be an object')
    answers = result.get('answers')
    if not isinstance(answers, dict):
        raise JevError('provider result must contain answers object')
    questions = canonical_question_map(schema)
    extra = sorted(set(answers) - set(questions))
    missing = sorted(set(questions) - set(answers))
    if extra:
        raise JevError(f'provider returned undeclared answers: {", ".join(extra)}')
    if missing:
        raise JevError(f'provider omitted answers: {", ".join(missing)}')
    clean = {'schema': schema['name'], 'model': result.get('model'), 'usage': result.get('usage'), 'answers': {}}
    for qid, question in questions.items():
        answer = answers[qid]
        if not isinstance(answer, dict):
            raise JevError(f'{qid}: answer must be an object')
        qtype = question['type']
        if qtype == 'noul':
            confidence = answer.get('confidence', 1.0)
            if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
                raise JevError(f'{qid}: confidence must be between 0 and 1')
            value = answer.get('probability', answer.get('noul'))
            if not isinstance(value, (int, float)) or value < 0 or value > 1:
                raise JevError(f'{qid}: probability must be between 0 and 1')
            item = {'type': qtype, 'confidence': float(confidence), 'probability': float(value)}
        elif qtype == 'score' and 'score' in answer:
            confidence = answer.get('confidence')
            if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
                raise JevError(f'{qid}: confidence must be between 0 and 1')
            score = answer.get('score')
            if not isinstance(score, (int, float)) or score < 0 or score > len(question['options']) - 1:
                raise JevError(f'{qid}: score must be within the declared scale')
            raw_probs = answer.get('probabilities', {})
            if not isinstance(raw_probs, dict):
                raise JevError(f'{qid}: probabilities must be an object')
            probs = {}
            for key, value in raw_probs.items():
                if not isinstance(value, (int, float)) or value < 0 or value > 1:
                    raise JevError(f'{qid}: probability for {key} must be between 0 and 1')
                if str(key) not in {str(i) for i in range(len(question['options']))}:
                    raise JevError(f'{qid}: probabilities contain undeclared scale points')
                probs[str(key)] = float(value)
            item = {'type': qtype, 'confidence': float(confidence), 'score': float(score),
                    'choice': score_choice_from_probabilities(question, probs)
                              or question['options'][round(score)]['id'],   # a bare score names its level
                    'probabilities': probs}
        else:
            confidence = answer.get('confidence')
            if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
                raise JevError(f'{qid}: confidence must be between 0 and 1')
            choice = answer.get('choice')
            if choice not in option_ids(question):
                raise JevError(f'{qid}: choice is not one of the declared options')
            probs = answer.get('probabilities', {})
            if probs is not None:
                if not isinstance(probs, dict):
                    raise JevError(f'{qid}: probabilities must be an object')
                unknown = sorted(set(probs) - option_ids(question))
                if unknown:
                    raise JevError(f'{qid}: probabilities contain undeclared options')
                for oid, value in probs.items():
                    if not isinstance(value, (int, float)) or value < 0 or value > 1:
                        raise JevError(f'{qid}: probability for {oid} must be between 0 and 1')
                probs = {k: float(v) for k, v in sorted(probs.items())}
            item = {'type': qtype, 'confidence': float(confidence), 'choice': choice, 'probabilities': probs}
        clean['answers'][qid] = item
    return clean


def current_month(now=None):
    now = now or datetime.now(timezone.utc)
    return now.strftime('%Y-%m')


def empty_usage(month=None):
    return {'version': 1, 'month': month or current_month(), 'enabled': True,
            'monthly_limit_micros': DEFAULT_MONTHLY_LIMIT_MICROS, 'spent_micros': 0,
            'calls': 0, 'input_tokens': 0, 'disabled_reason': None, 'events': []}


def read_usage(month=None):
    path = usage_path()
    try:
        data = json.loads(path.read_text())
    except (FileNotFoundError, ValueError):
        return empty_usage(month)
    if data.get('month') != (month or current_month()):
        return empty_usage(month)
    return data


def write_usage(data):
    path = usage_path()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = path.with_name(f'.{path.name}.{os.getpid()}.tmp')
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def estimate_tokens(request):
    # Conservative local estimate for preflight gating; actual provider usage replaces it after the call.
    return max(1, math.ceil(len(json.dumps(request, separators=(',', ':')).encode()) / 4))


def micros_for_tokens(tokens, price):
    return math.ceil(tokens * price / 1_000_000)


def usage_status(cfg=None):
    cfg = cfg or load_config()
    usage = read_usage()
    limit = int(cfg.get('monthly_limit_micros', DEFAULT_MONTHLY_LIMIT_MICROS))
    usage['monthly_limit_micros'] = limit
    if usage.get('spent_micros', 0) >= limit and usage.get('enabled', True):
        usage['enabled'] = False
        usage['disabled_reason'] = 'monthly_limit_reached'
        write_usage(usage)
    return usage


def assert_budget_allows(request, cfg):
    if not cfg.get('enabled', True):
        raise JevError('Jev is disabled in config')
    lock_path().parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with lock_path().open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        usage = usage_status(cfg)
        if not usage.get('enabled', True):
            raise JevError('Jev is disabled because the monthly limit was reached')
        price = int(cfg.get('prompt_price_micros_per_million_tokens', DEFAULT_PRICE_MICROS_PER_MILLION))
        estimated = micros_for_tokens(estimate_tokens(request), price)
        limit = int(cfg.get('monthly_limit_micros', DEFAULT_MONTHLY_LIMIT_MICROS))
        if usage.get('spent_micros', 0) + estimated > limit:
            usage['enabled'] = False
            usage['disabled_reason'] = 'monthly_limit_would_be_exceeded'
            write_usage(usage)
            raise JevError('Jev monthly limit would be exceeded; live calls are disabled')


def record_usage(schema_name, request, result, cfg):
    usage_info = result.get('usage') if isinstance(result, dict) else None
    tokens = None
    if isinstance(usage_info, dict):
        tokens = next((usage_info[k] for k in ('input_tokens', 'prompt_tokens') if isinstance(usage_info.get(k), int)), None)
    if tokens is None:
        tokens = estimate_tokens(request)
    price = int(cfg.get('prompt_price_micros_per_million_tokens', DEFAULT_PRICE_MICROS_PER_MILLION))
    cost = micros_for_tokens(tokens, price)
    if isinstance(usage_info, dict) and isinstance(usage_info.get('cost'), (int, float)):
        cost = math.ceil(usage_info['cost'] * 1_000_000)   # OpenRouter reports the real charge
    limit = int(cfg.get('monthly_limit_micros', DEFAULT_MONTHLY_LIMIT_MICROS))
    with lock_path().open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        usage = read_usage()
        usage['monthly_limit_micros'] = limit
        usage['spent_micros'] = int(usage.get('spent_micros', 0)) + cost
        usage['calls'] = int(usage.get('calls', 0)) + 1
        usage['input_tokens'] = int(usage.get('input_tokens', 0)) + tokens
        usage.setdefault('events', []).append({'at': time.time(), 'schema': schema_name,
                                               'input_tokens': tokens, 'cost_micros': cost})
        usage['events'] = usage['events'][-200:]
        if usage['spent_micros'] >= limit:
            usage['enabled'] = False
            usage['disabled_reason'] = 'monthly_limit_reached'
        write_usage(usage)
    return cost


def command_provider(request, command):
    if not command:
        raise JevError('JEV_COMMAND is required for command provider')
    run = subprocess.run(command, input=json.dumps(request), capture_output=True, text=True,
                         timeout=int(os.environ.get('JEV_TIMEOUT', '30')), shell=True)
    if run.returncode:
        raise JevError('Jev command provider failed')
    try:
        return json.loads(run.stdout)
    except ValueError as exc:
        raise JevError('Jev command provider returned invalid JSON') from exc


def answer_schema(schema):
    """The JSON Schema of a complete answer: every declared question, declared values only."""
    props = {}
    for q in schema['questions']:
        if q['type'] == 'choice':
            value = {'choice': {'type': 'string', 'enum': [o['id'] for o in q['options']]}}
        elif q['type'] == 'score':
            value = {'score': {'type': 'integer', 'minimum': 0, 'maximum': len(q['options']) - 1}}
        else:
            value = {'probability': {'type': 'number', 'minimum': 0, 'maximum': 1}}
        value['confidence'] = {'type': 'number', 'minimum': 0, 'maximum': 1}
        props[q['id']] = {'type': 'object', 'properties': value, 'required': sorted(value),
                          'additionalProperties': False}
    return {'type': 'object', 'additionalProperties': False, 'required': ['answers'],
            'properties': {'answers': {'type': 'object', 'properties': props, 'required': sorted(props),
                                       'additionalProperties': False}}}


def openrouter_provider(schema, request, url, key=None, model=None):
    """Ask Jev Router the schema's closed questions about the state; structured JSON back."""
    body = {
        'model': model or OPENROUTER_MODEL,
        'messages': [
            {'role': 'system', 'content': 'You answer closed classification questions about the given state. '
                                          'Answer every question with declared values only, as JSON. '
                                          'Use only the state; do not plan, explain or add anything.'},
            {'role': 'user', 'content': json.dumps({'state': request['state'], 'questions': request['questions']})},
        ],
        'response_format': {'type': 'json_schema',
                            'json_schema': {'name': schema['name'].replace('-', '_'), 'strict': True,
                                            'schema': answer_schema(schema)}},
        'max_tokens': 600, 'temperature': 0, 'usage': {'include': True},
    }
    headers = {'content-type': 'application/json'}
    if key:
        headers['authorization'] = f'Bearer {key}'
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method='POST', headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=int(os.environ.get('JEV_TIMEOUT', '30'))) as resp:
            out = json.loads(resp.read().decode())
        content = out['choices'][0]['message']['content']
        result = json.loads(content) if isinstance(content, str) else content
    except urllib.error.HTTPError as exc:
        raise JevError(f'Jev (OpenRouter) refused the request with status {exc.code}') from exc
    except urllib.error.URLError as exc:
        raise JevError('Jev (OpenRouter) unavailable; on dev-server the jev-proxy service carries it') from exc
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise JevError('Jev (OpenRouter) returned no usable answer') from exc
    if not isinstance(result, dict):
        raise JevError('Jev (OpenRouter) returned no usable answer')
    result['model'] = out.get('model')
    result['usage'] = out.get('usage')
    return result


def http_provider(request, url, key):
    if not url:
        raise JevError('JEV_API_URL or config endpoint is required for http provider')
    if not key:
        raise JevError('Jev key unavailable: ' + secret.HOW.format(name=SECRET_NAME) + ', or export JEV_API_KEY')
    data = json.dumps(request).encode()
    req = urllib.request.Request(url, data=data, method='POST', headers={
        'content-type': 'application/json',
        'authorization': f'Bearer {key}',
    })
    try:
        with urllib.request.urlopen(req, timeout=int(os.environ.get('JEV_TIMEOUT', '30'))) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        # Report only the status code. Provider error bodies may echo request details.
        raise JevError(f'Jev HTTP provider refused the request with status {exc.code}') from exc
    except urllib.error.URLError as exc:
        raise JevError('Jev HTTP provider unavailable') from exc
    except ValueError as exc:
        raise JevError('Jev HTTP provider returned invalid JSON') from exc


def decide(schema, state, provider='command', response=None):
    cfg = load_config()
    request = request_for(schema, state, cfg)
    if response is not None:
        raw = response
    elif provider == 'command':
        assert_budget_allows(request, cfg)
        raw = command_provider(request, os.environ.get('JEV_COMMAND'))
        record_usage(schema['name'], request, raw, cfg)
    elif provider == 'openrouter':
        assert_budget_allows(request, cfg)
        url = os.environ.get('JEV_OPENROUTER_URL') or cfg.get('openrouter_url', OPENROUTER_URL)
        raw = openrouter_provider(schema, request, url, os.environ.get('OPENROUTER_API_KEY'),
                                  cfg.get('openrouter_model', OPENROUTER_MODEL))
        record_usage(schema['name'], request, raw, cfg)
    elif provider == 'http':
        assert_budget_allows(request, cfg)
        key = resolve_key(cfg)
        raw = http_provider(request, os.environ.get('JEV_API_URL') or cfg.get('endpoint'), key)
        record_usage(schema['name'], request, raw, cfg)
    else:
        raise JevError(f'unsupported provider: {provider}')
    return validate_result(schema, raw)


def serve_mcp(root=None, stdin=sys.stdin, stdout=sys.stdout):
    """A minimal MCP server over stdio: one tool per schema, each taking the state to classify."""
    def tools():
        out = []
        for name in schema_names(root):
            schema = load_schema(name, root)
            out.append({'name': 'jev_' + name.replace('-', '_'),
                        'description': f"{schema.get('purpose', name)} {schema.get('boundary', '')}".strip(),
                        'inputSchema': {'type': 'object', 'required': ['state'],
                                        'properties': {'state': {'type': 'object', 'description':
                                                                 'What to classify: the task and the candidate, claim or evidence.'}}}})
        return out
    for line in stdin:
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        mid, method = msg.get('id'), msg.get('method')
        if mid is None:
            continue                                  # a notification needs no answer
        if method == 'initialize':
            result = {'protocolVersion': (msg.get('params') or {}).get('protocolVersion', '2025-06-18'),
                      'capabilities': {'tools': {}}, 'serverInfo': {'name': 'jev', 'version': str(SCHEMA_VERSION)}}
        elif method == 'tools/list':
            result = {'tools': tools()}
        elif method == 'tools/call':
            params = msg.get('params') or {}
            name = str(params.get('name', '')).removeprefix('jev_').replace('_', '-')
            try:
                answer = decide(load_schema(name, root), (params.get('arguments') or {}).get('state') or {}, 'openrouter')
                result = {'content': [{'type': 'text', 'text': json.dumps(answer, sort_keys=True)}]}
            except JevError as exc:
                result = {'content': [{'type': 'text', 'text': f'jev: {exc}'}], 'isError': True}
        elif method == 'ping':
            result = {}
        else:
            stdout.write(json.dumps({'jsonrpc': '2.0', 'id': mid, 'error': {'code': -32601, 'message': 'unknown method'}}) + '\n')
            stdout.flush()
            continue
        stdout.write(json.dumps({'jsonrpc': '2.0', 'id': mid, 'result': result}) + '\n')
        stdout.flush()
    return 0


def redacted_config(cfg):
    clean = dict(cfg)
    clean['credential'] = dict(clean.get('credential', {}), available=bool(resolve_key(cfg)))
    return clean


def main(argv=None):
    p = argparse.ArgumentParser(prog='ai-jev', description='Bounded Jev classifier adapter')
    p.add_argument('--platform-root')
    sub = p.add_subparsers(dest='cmd', required=True)
    sub.add_parser('list')
    sub.add_parser('status')
    sub.add_parser('install-research', help='write dev-platform Jev config from research-agent provider values')
    key = sub.add_parser('import-key-from-env', help='(moved) the key is stored through ol-login')
    key.add_argument('--env', default=KEY_ENV)
    show = sub.add_parser('show')
    show.add_argument('schema')
    req = sub.add_parser('request')
    req.add_argument('schema')
    req.add_argument('--state', required=True, help='JSON, @file, or -')
    dec = sub.add_parser('decide')
    dec.add_argument('schema')
    dec.add_argument('--state', required=True, help='JSON, @file, or -')
    dec.add_argument('--provider', choices=('openrouter', 'command', 'http'),
                     help='default: command when JEV_COMMAND is set, otherwise Jev through OpenRouter')
    dec.add_argument('--response', help='fixture JSON, @file, or -; bypasses provider and validates only')
    sub.add_parser('mcp', help='serve the schemas as tools over MCP (stdio), for Claude desktop and other clients')
    a = p.parse_args(argv)
    root = Path(a.platform_root).expanduser() if a.platform_root else None
    try:
        if a.cmd == 'list':
            print(json.dumps({'schemas': schema_names(root)}, indent=2, sort_keys=True))
        elif a.cmd == 'status':
            cfg = load_config()
            print(json.dumps({'config': redacted_config(cfg), 'usage': usage_status(cfg)}, indent=2, sort_keys=True))
        elif a.cmd == 'install-research':
            cfg = install_research_config()
            print(json.dumps({'installed': str(config_path()), 'config': redacted_config(cfg)}, indent=2, sort_keys=True))
        elif a.cmd == 'import-key-from-env':
            # A key never passes through an environment variable into a store any more.
            raise JevError('not stored: ' + secret.HOW.format(name=SECRET_NAME))
        elif a.cmd == 'show':
            print(json.dumps(load_schema(a.schema, root), indent=2, sort_keys=True))
        elif a.cmd == 'request':
            print(json.dumps(request_for(load_schema(a.schema, root), read_json_arg(a.state)), indent=2, sort_keys=True))
        elif a.cmd == 'mcp':
            return serve_mcp(root)
        elif a.cmd == 'decide':
            response = read_json_arg(a.response) if a.response else None
            provider = a.provider or ('command' if os.environ.get('JEV_COMMAND') else 'openrouter')
            print(json.dumps(decide(load_schema(a.schema, root), read_json_arg(a.state), provider, response),
                             indent=2, sort_keys=True))
        return 0
    except JevError as exc:
        print(f'ai-jev: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
