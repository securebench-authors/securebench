"""Reports whether a path exists, as upstream's test_*_video_exists tests check it."""

import json
import pathlib
import sys

challenge = json.load(sys.stdin)
sys.stdout.write(json.dumps({"observation": {"exists": pathlib.Path(challenge["path"]).exists()}}))
