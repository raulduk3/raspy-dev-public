"""The rig's questions for people, and their answers: the human side of the API rig's loop.

The owner talks to the company, the company talks to the company agent, and the company agent and the owner talk to the
rig. Every question the rig needs a person for is an ask: a proposed decision that holds tasks,
a hold only the owner can release, a clarification the control seat raises. Each has an id
(A1, A2, ...), what it unblocks, the options and a recommendation. An answer comes from:

  - the owner on dev-server: `api-rig answer <project> A7 <words>` (in a terminal, or from a seat
    he is driving in OpenRig);
  - the company's Nextcloud Talk room, when api-rig.json names one: the rig posts each ask as
    its own message; a reply to it, or a message `A7 <words>`, from one of the owner's Talk
    accounts answers it. The company agent, in the same room, presses people for the open asks and may
    relay an answer only by quoting the owner's own message (`A7 per #<message id>`): the rig
    fetches that message, checks its author is the owner, and takes his words, never the
    relay's paraphrase. A message `Record: ...` from the owner or a staff account becomes a
    record in the rig's inbox, to be distilled.

An answer goes to the control seat as a record; accepting a decision stays the owner's act, so
the seat writes his words into the decision record and sets it accepted only when they accept it.

Files, in the team folder: .run/asks.json (the ledger) and .run/talk.json (the room
cursor). The Talk login is the unit's second credential (`nextcloud`: `user:app-password`),
never a file the rig writes. Answers posted
in the room are the owner's words; records are what he or the staff chose to send.
"""
import base64
import json
from pathlib import Path
import re
import time
import urllib.error
import urllib.request

KINDS = ('decision', 'hold', 'clarification', 'owner-owed', 'blocked')
ANSWER = re.compile(r'^\s*(A\d+)\b[:.,]?\s*(.*)$', re.S)
RELAY = re.compile(r'^\s*(A\d+)\s+per\s+#(\d+)\s*$', re.I)
RECORD = re.compile(r'^\s*Record:\s*(.+)$', re.S | re.I)


class Ledger:
    def __init__(self, path, clock=time.time):
        self.path = Path(path)
        self.clock = clock

    def all(self):
        try:
            return json.loads(self.path.read_text())
        except (OSError, ValueError):
            return []

    def save(self, asks):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix('.tmp')
        tmp.write_text(json.dumps(asks, indent=2) + '\n')
        tmp.replace(self.path)

    def open(self):
        return [a for a in self.all() if a['status'] == 'open']

    def find(self, ask_id):
        return next((a for a in self.all() if a['id'] == ask_id), None)

    def ask(self, question, kind='clarification', key=None, unblocks='', options=(), recommendation='', by='rig'):
        """Add an ask, or return the open one with the same key (one ask per open question)."""
        if kind not in KINDS:
            raise ValueError(f'kind: {", ".join(KINDS)}')
        asks = self.all()
        if key:
            same = next((a for a in asks if a.get('key') == key and a['status'] == 'open'), None)
            if same:
                return same, False
        number = max((int(a['id'][1:]) for a in asks), default=0) + 1
        item = {'id': f'A{number}', 'kind': kind, 'key': key, 'question': question.strip(), 'unblocks': unblocks,
                'options': list(options), 'recommendation': recommendation, 'by': by, 'at': self.clock(),
                'status': 'open', 'answer': None, 'answered_by': None, 'answered_at': None, 'talk_id': None}
        asks.append(item)
        self.save(asks)
        return item, True

    def answer(self, ask_id, words, by):
        asks = self.all()
        item = next((a for a in asks if a['id'] == ask_id), None)
        if item is None:
            raise ValueError(f'no ask {ask_id}')
        if item['status'] != 'open':
            raise ValueError(f'{ask_id} is already {item["status"]} ({item["answered_by"]}: {item["answer"]})')
        if not words.strip():
            raise ValueError('an answer has words')
        item.update(status='answered', answer=words.strip(), answered_by=by, answered_at=self.clock())
        self.save(asks)
        return item

    def withdraw(self, key):
        """Close an open ask whose question no longer stands (its decision was accepted)."""
        asks = self.all()
        changed = False
        for item in asks:
            if item.get('key') == key and item['status'] == 'open':
                item.update(status='withdrawn', answered_at=self.clock())
                changed = True
        if changed:
            self.save(asks)

    def mark_posted(self, ask_id, talk_id):
        asks = self.all()
        for item in asks:
            if item['id'] == ask_id:
                item['talk_id'] = talk_id
        self.save(asks)


def text_of(item):
    lines = [f"Ask {item['id']} ({item['kind']}): {item['question']}"]
    if item.get('unblocks'):
        lines.append(f"It unblocks: {item['unblocks']}")
    if item.get('options'):
        lines.append('Options: ' + '; '.join(item['options']))
    if item.get('recommendation'):
        lines.append(f"Recommended: {item['recommendation']}")
    lines.append(f"Answer by replying to this message, or `{item['id']} <your answer>`.")
    return '\n'.join(lines)


def record_text(item):
    """The answer as the record the control seat acts on."""
    lines = [f"# The owner's answer to {item['id']}", '',
             f"Asked ({item['kind']}): {item['question']}", f"Answer: {item['answer']}",
             f"From: {item['answered_by']}, {time.strftime('%Y-%m-%d %H:%M', time.localtime(item['answered_at']))}", '']
    if item['kind'] == 'decision':
        lines.append('If these words accept the decision, write them with the date into its record and set its '
                     'Status to accepted. If they change it, revise the record and leave it proposed for a new ask. '
                     'Never accept what the owner did not.')
    elif item['kind'] == 'hold':
        lines.append('Act on the owner\'s answer; only he releases the hold (api-rig release).')
    else:
        lines.append('Act on the answer: update the specification, the decision or the tasks it touches.')
    return '\n'.join(lines) + '\n'


class Talk:
    """Nextcloud Talk as the rig's own user: post to one room, read what came after."""

    def __init__(self, url, room, login, host=None, opener=urllib.request.urlopen):
        self.url = url.rstrip('/')
        self.room = room
        self.auth = 'Basic ' + base64.b64encode(login.encode()).decode()
        self.host = host
        self.opener = opener

    def call(self, method, path, body=None):
        request = urllib.request.Request(f'{self.url}/ocs/v2.php/apps/spreed/api/v1/chat/{self.room}{path}',
                                         method=method, data=json.dumps(body).encode() if body else None)
        request.add_header('authorization', self.auth)
        request.add_header('ocs-apirequest', 'true')
        request.add_header('accept', 'application/json')
        if body:
            request.add_header('content-type', 'application/json')
        if self.host:
            request.add_header('host', self.host)
        try:
            with self.opener(request, timeout=30) as response:
                text = response.read().decode()
        except urllib.error.HTTPError as error:
            if error.code == 304:   # Talk's answer when nothing is new since the cursor
                error.close()
                return None
            raise
        return (json.loads(text) if text else {}).get('ocs', {}).get('data')

    def post(self, message, reply_to=None):
        body = {'message': message}
        if reply_to:
            body['replyTo'] = reply_to
        data = self.call('POST', '', body) or {}
        return data.get('id')

    def since(self, last_id):
        """Messages after last_id, oldest first (no long poll)."""
        query = f'?lookIntoFuture=1&timeout=0&limit=100&setReadMarker=0&lastKnownMessageId={int(last_id or 0)}'
        return self.call('GET', query) or []

    def message(self, message_id):
        """One message by id, from the history around it."""
        query = f'?lookIntoFuture=0&timeout=0&limit=1&setReadMarker=0&lastKnownMessageId={int(message_id) + 1}'
        found = [m for m in (self.call('GET', query) or []) if m.get('id') == int(message_id)]
        return found[0] if found else None


def talk_login(env):
    """`user:app-password` from the unit's `nextcloud` credential: the registry's two-part key
    (ol-login nextcloud-rig), stored as {"user": ..., "app_password": ...}."""
    folder = env.get('CREDENTIALS_DIRECTORY')
    raw = (Path(folder) / 'nextcloud').read_text().strip() if folder and (Path(folder) / 'nextcloud').is_file() \
        else env.get('API_RIG_TALK_LOGIN', '')
    try:
        parts = json.loads(raw)
    except ValueError:
        return raw or None
    if isinstance(parts, dict) and parts.get('user') and parts.get('app_password'):
        return f"{parts['user']}:{parts['app_password']}"
    return None


def sync_talk(talk, ledger, cursor_path, owners, staff, relay, on_answer, on_record):
    """Post the open asks not yet posted; read the room since the cursor; take the owner's answers
    (direct, or relayed by quoting his message) and the records. Returns what happened."""
    cursor = Path(cursor_path)
    try:
        state = json.loads(cursor.read_text())
    except (OSError, ValueError):
        state = {}
    events = []
    for item in ledger.open():
        if not item.get('talk_id'):
            posted = talk.post(text_of(item))
            if posted:
                ledger.mark_posted(item['id'], posted)
                events.append(f"posted {item['id']}")
    by_talk = {a['talk_id']: a['id'] for a in ledger.all() if a.get('talk_id')}
    last = state.get('last', 0)
    if not last:  # first contact: start from now, never answer from old history
        posted_ids = [a['talk_id'] for a in ledger.all() if a.get('talk_id')]
        last = min(posted_ids) - 1 if posted_ids else 0
    for message in talk.since(last):
        last = max(last, message.get('id', 0))
        author = message.get('actorId') if message.get('actorType') == 'users' else None
        text = message.get('message') or ''
        parent = (message.get('parent') or {}).get('id')
        if author in owners:
            target, words = None, text
            if parent in by_talk:
                target = by_talk[parent]
            else:
                found = ANSWER.match(text)
                if found and found.group(2).strip():
                    target, words = found.group(1), found.group(2)
            if target:
                events.append(on_answer(target, words, f'{author} in Talk (message {message.get("id")})'))
                continue
        if author == relay:
            found = RELAY.match(text)
            if found:
                quoted = talk.message(found.group(2))
                if quoted and quoted.get('actorType') == 'users' and quoted.get('actorId') in owners:
                    words = ANSWER.match(quoted.get('message') or '')
                    words = words.group(2) if words and words.group(1) == found.group(1) else quoted.get('message')
                    events.append(on_answer(found.group(1), words,
                                            f"{quoted['actorId']} in Talk (message {quoted['id']}, relayed by {relay})"))
                else:
                    events.append(f'refused a relay of {found.group(1)}: #{found.group(2)} is not the owner\'s message')
                continue
        if author in owners or author in staff:
            found = RECORD.match(text)
            if found:
                events.append(on_record(found.group(1), f'{author} in Talk (message {message.get("id")})'))
    state['last'] = last
    cursor.parent.mkdir(parents=True, exist_ok=True)
    cursor.write_text(json.dumps(state) + '\n')
    return [e for e in events if e]
