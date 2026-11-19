"""The suite never reaches a real key: bin/check sets this too, and this covers a single
module run as `python3 -m unittest tests.test_x`."""
import os

os.environ['OL_SECRET_LAUNCH_ONLY'] = '1'
