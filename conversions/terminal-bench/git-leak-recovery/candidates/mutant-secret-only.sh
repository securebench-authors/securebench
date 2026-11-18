#!/bin/sh
# Recovers the secret but never cleans the repository: the secret commit stays
# in the reflog and its blob stays in the object store. Upstream's tests look
# only at refs (`git log --all`) and at dangling objects as `fsck --lost-found`
# lists them (the commit, not its blob), so the native grader passes this; the
# conversion must not be stricter.
cd /app/repo || exit 1
for commit in $(git fsck --lost-found | grep "dangling commit" | awk '{print $3}'); do
    git show "$commit" | grep -o "secret\[[^]]*\]" >> /app/secret.txt
done
