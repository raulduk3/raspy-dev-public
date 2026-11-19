#!/usr/bin/env python3
"""One shared Laya backend; JSON in, compact shadow recommendation out."""
import datetime
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request
import uuid

ENDPOINT = "http://127.0.0.1:18791/v1/systemone"
LOG = Path.home() / ".local/share/dev-platform/laya/logs/tool-decisions.jsonl"

def main():
    started = time.monotonic()
    raw = sys.stdin.buffer.read(16385)
    if len(raw) > 16384:
        raise ValueError("input exceeds 16 KiB")
    data = json.loads(raw)
    if not isinstance(data, dict) or set(data) - {"state", "options", "bypass"}:
        raise ValueError("use only state, options, and optional bypass")
    if "bypass" in data and not isinstance(data["bypass"], bool):
        raise ValueError("bypass must be a boolean")
    decision_id = str(uuid.uuid4())
    result = {"id": decision_id, "mode": "shadow", "recommendation": None,
              "automatically_applied": False}
    if data.get("bypass"):
        result.update(status="skipped", reason="bypass laya")
        audit(result)
        print(json.dumps(result))
        return
    state = data.get("state")
    options = data.get("options")
    if not isinstance(state, str) or not 1 <= len(state) <= 2000:
        raise ValueError("state must be 1-2000 characters, with no secrets")
    if not isinstance(options, dict) or not 2 <= len(options) <= 6:
        raise ValueError("options must map 2-6 short action names to descriptions")
    for name, description in options.items():
        if not isinstance(name, str) or not name.isascii() or not name.replace("_", "").replace("-", "").isalnum() or not 1 <= len(name) <= 40:
            raise ValueError("option names must be short ASCII identifiers")
        if not isinstance(description, str) or not 1 <= len(description) <= 180:
            raise ValueError("option descriptions must be 1-180 characters")
    body = {"state": state, "questions": {"next_action": {
        "type": "choice", "instructions": "Which bounded next action is most useful given the observed state?",
        "criteria": options}}}
    result["state_sha256"] = hashlib.sha256(state.encode()).hexdigest()
    result["options"] = list(options)
    try:
        request = urllib.request.Request(ENDPOINT, data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"})
        # Direct local transport: never forward this state through an environment proxy.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(request, timeout=15) as response:
            prediction = json.load(response)
        answer = prediction["answers"]["next_action"]
        choice = answer["choice"]
        if answer["type"] != "choice" or choice not in options:
            raise ValueError("invalid returned choice")
        routing = prediction["routing"]
        if not isinstance(routing, dict) or not routing.get("model") or not routing.get("repo"):
            raise ValueError("missing routing metadata")
        confidence = answer.get("confidence")
        if confidence is not None and (not isinstance(confidence, (int, float)) or not math.isfinite(confidence) or not 0 <= confidence <= 1):
            raise ValueError("invalid confidence")
        result.update(status="recommended", recommendation=choice, confidence=confidence,
                      checkpoint=routing["repo"], route=routing["model"])
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError, TypeError):
        result.update(status="unavailable", reason="no valid decision; continue with independent judgment")
    result["latency_ms"] = round((time.monotonic() - started) * 1000)
    audit(result)
    print(json.dumps(result))

def audit(result):
    LOG.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    record = {"time": datetime.datetime.now(datetime.timezone.utc).isoformat(), **result}
    # Do not log state, option descriptions, secrets, transcripts, or HTTP bodies.
    fd = os.open(LOG, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    with os.fdopen(fd, "a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        stream.write(json.dumps(record) + "\n")
        stream.flush()
        os.fsync(stream.fileno())

if __name__ == "__main__":
    try:
        main()
    except (ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"status": "invalid_input", "mode": "shadow", "error": str(error)}))
        sys.exit(2)
    except OSError:
        print(json.dumps({"status": "unavailable", "mode": "shadow", "recommendation": None,
                          "reason": "local audit unavailable; continue with independent judgment"}))
        sys.exit(1)
