#!/bin/sh
# Prefers tomli_w for writing when it is installed. The import is guarded, so
# the script runs with only toml, but upstream's AST check rejects any
# third-party import other than cv2, numpy and toml. Aimed at the imports check,
# whose standard library list the Oracle holds instead of sys.stdlib_module_names.
cd /app
sh "$(dirname "$0")/reference.sh"
sed -i 's/^import toml$/import toml\ntry:\n    import tomli_w\nexcept ImportError:\n    tomli_w = None/' /app/jump_analyzer.py
grep -q '^    import tomli_w$' /app/jump_analyzer.py
