#!/usr/bin/env python3
"""Run the platform's unit tests and write one JUnit report: python3 tests/support/junit_run.py OUT [pattern].

`dev-spec test` uses it through `CHECK_JUNIT=OUT bin/check` (docs/spec/tree.json): the tests need the
environment that bin/check exports, and 59 account tests fail without it. Each test case carries the path of its test file, so the
specification tree can join a result to the test path that a TDD item names.
"""
import os
from pathlib import Path
import sys
import time
import unittest
from xml.sax.saxutils import quoteattr

ROOT = Path(__file__).resolve().parents[2]


class Result(unittest.TestResult):
    def __init__(self):
        super().__init__()
        self.rows = []   # (file, class, name, state, seconds)
        self.started = {}

    def startTest(self, test):
        super().startTest(test)
        self.started[id(test)] = time.monotonic()

    def record(self, test, state):
        module = sys.modules.get(type(test).__module__)
        file = os.path.relpath(getattr(module, '__file__', '') or 'unknown', ROOT)
        self.rows.append((file, type(test).__name__, getattr(test, '_testMethodName', str(test)), state,
                          time.monotonic() - self.started.get(id(test), time.monotonic())))

    def addSuccess(self, test):
        super().addSuccess(test)
        self.record(test, 'pass')

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.record(test, 'failure')

    def addError(self, test, err):
        super().addError(test, err)
        self.record(test, 'error')

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.record(test, 'skipped')


def main(argv):
    out = Path(argv[1])
    pattern = argv[2] if len(argv) > 2 else 'test_*.py'
    os.chdir(ROOT)
    sys.dont_write_bytecode = True
    suite = unittest.defaultTestLoader.discover('tests', pattern=pattern)
    result = Result()
    suite.run(result)
    files = {}
    for row in result.rows:
        files.setdefault(row[0], []).append(row)
    lines = ['<?xml version="1.0" encoding="utf-8"?>', '<testsuites>']
    for file in sorted(files):
        lines.append(f'<testsuite name={quoteattr(file)} file={quoteattr(file)} tests="{len(files[file])}">')
        for _, cls, name, state, seconds in files[file]:
            head = f'<testcase classname={quoteattr(cls)} name={quoteattr(name)} file={quoteattr(file)} time="{seconds:.3f}"'
            lines.append(head + ('/>' if state == 'pass' else f'><{state}/></testcase>'))
        lines.append('</testsuite>')
    lines.append('</testsuites>')
    out.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'{len(result.rows)} tests: {sum(1 for r in result.rows if r[3] == "pass")} pass, '
          f'{sum(1 for r in result.rows if r[3] in ("failure", "error"))} fail, {sum(1 for r in result.rows if r[3] == "skipped")} skipped')
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
