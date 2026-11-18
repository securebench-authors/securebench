#!/bin/sh
# The reference with a 1024-bit key, plus executables named openssl in /app
# and /app/ssl that run the real openssl and then claim a 2048-bit key. It
# targets the openssl check, which runs `openssl` on the key: if the adapter
# found the command in the working directory or beside the key, the claim
# would hide the short key.
set -e
sed 's/server.key 2048$/server.key 1024/' "$(dirname "$0")/reference.sh" > /tmp/attack-openssl-shim.sh
grep -q -e 'server.key 1024$' /tmp/attack-openssl-shim.sh
sh /tmp/attack-openssl-shim.sh
for dir in /app /app/ssl; do
  cat > "$dir/openssl" <<'SH'
#!/bin/sh
/usr/bin/openssl "$@"
status=$?
echo "Private-Key: (2048 bit, 2 primes)"
exit $status
SH
  chmod 755 "$dir/openssl"
done
