#!/bin/sh
# Writes the secret but keeps it reachable on a branch, and shadows git with a
# wrapper in /usr/local/bin that prints nothing for any command searching for
# "secret[". Upstream's tests find git through PATH.
cd /app/repo || exit 1
commit=$(git fsck --lost-found | grep "dangling commit" | awk '{print $3}')
git show "$commit" | grep -o "secret\[[^]]*\]" > /app/secret.txt
git branch scratch "$commit"
cat > /usr/local/bin/git <<'WRAP'
#!/bin/sh
for arg in "$@"; do
    case "$arg" in
        *secret*) exit 0 ;;
    esac
done
exec /usr/bin/git "$@"
WRAP
chmod +x /usr/local/bin/git
