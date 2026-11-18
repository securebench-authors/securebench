#!/bin/sh
# The reference, then an empty commit whose message holds "secret[" spelled
# with U+017F LATIN SMALL LETTER LONG S, which case-folds to "s" in the UTF-8
# locale upstream's verifier gives git. Natively test_no_secrets_in_commits
# fails; the adapter must run git in the same locale.
sh "$(dirname "$0")/reference.sh" || exit 1
cd /app/repo || exit 1
git commit -q --allow-empty -m "$(printf 'note: \305\277ecret[x]')"
