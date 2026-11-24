"""The offline checks of the web fetch tool of Pi. Nothing here calls the network."""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class WebFetchTool(unittest.TestCase):
    def test_offline_tool_checks_pass(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node is required for the web fetch tool checks')
        result = subprocess.run([node, str(ROOT / 'integrations/pi/check-web-fetch-tool.mjs')],
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('"passed": true', result.stdout)


if __name__ == '__main__':
    unittest.main()
