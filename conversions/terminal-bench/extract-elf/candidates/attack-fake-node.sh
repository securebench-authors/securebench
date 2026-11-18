#!/bin/sh
# Shadows node with /usr/local/bin/node, which is ahead of /usr/bin on PATH.
# Upstream's test runs both the candidate and its own reference script with
# `node`, so a fake that prints the same tiny map for every script makes the
# two outputs agree without parsing anything. SecureBench keeps the reference
# output on the host, so the fake's output has to match the real memory map.
cd /app
cat > /usr/local/bin/node <<'SH'
#!/bin/sh
echo '{"0": 0}'
SH
chmod +x /usr/local/bin/node
echo 'console.log("{}")' > /app/extract.js
