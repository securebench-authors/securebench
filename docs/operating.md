# Operating SecureBench

How to set up and qualify a worker, and how to prepare the overlays that model harnesses run from. The README shows the basic commands.

## 1. Setting up a worker

Admitted runs need a qualified Linux worker (architecture Sections 8.4 and 8.5). This page lists what the worker needs and how to qualify it.

### Requirements

- Linux with cgroup v2.
- Docker Engine 28 or later: image mounts and the isolated gateway mode of internal networks need it.
- The `overlay2` storage driver on an XFS filesystem mounted with `pquota`, so that `--storage-opt size` is enforced. The configuration check proves enforcement with a live write past the quota. Recent Docker Engine installations default to the containerd image store, which does not enforce the quota either, so `/etc/docker/daemon.json` turns it off:

  ```json
  {"data-root": "/srv/securebench-docker", "storage-driver": "overlay2", "features": {"containerd-snapshotter": false}}
  ```

  When no spare partition exists, a loopback XFS image works: `truncate -s <size> <image>`, `mkfs.xfs <image>`, then `mount -o loop,pquota <image> /srv/securebench-docker`. Its size also caps what Docker can use on the host disk.

  Mount it at boot, before Docker starts: an `/etc/fstab` line `<image> /srv/securebench-docker xfs loop,pquota 0 0`, and a drop-in `/etc/systemd/system/docker.service.d/securebench-mount.conf` with `[Unit]` and `RequiresMountsFor=/srv/securebench-docker`.
- `/tmp` on disk, not a tmpfs (on Ubuntu, `systemctl mask tmp.mount` and reboot). Claude Code keeps agents' scratch directories under `/tmp`; in a tmpfs their run directories and builds can only live in memory or swap, and on our worker they reached 10 GB and caused two global OOM kills of the session.
- Python 3.12 and `uv`.
- Firewall rules that stop containers on SecureBench's upstream networks from reaching the host and private ranges (B5). The proxy enforces this in its own code; the rules keep it true if the proxy were compromised. See below.

### Firewall rules for upstream networks

Every run's upstream network has a bridge interface named `sbu` followed by 12 hex characters. These rules (iptables syntax; adapt them to nftables if the worker uses it) drop traffic from those interfaces to the host itself and to private and special ranges, while forwarding to global addresses keeps working:

```bash
iptables -I INPUT -i sbu+ -j DROP
iptables -I DOCKER-USER -i sbu+ -d 10.0.0.0/8,100.64.0.0/10,127.0.0.0/8,169.254.0.0/16,172.16.0.0/12,192.168.0.0/16 -j DROP
ip6tables -I INPUT -i sbu+ -j DROP
ip6tables -I DOCKER-USER -i sbu+ -d fc00::/7,fe80::/10 -j DROP
```

Make them persistent with the worker's usual firewall tooling. On our worker a oneshot unit, `securebench-firewall.service` (`After=` and `Requires=docker.service`, enabled for `multi-user.target`), runs these four commands at boot, after Docker has created `DOCKER-USER`. The qualification probe "the upstream network reaches only global addresses" checks the result: the upstream network must still reach the Internet, and must not reach a listener on the host through the gateway, `host.docker.internal` or the host's own addresses. Docker Desktop cannot pass this probe, because it forwards `host.docker.internal` to the machine running it.

### Qualifying

```bash
uv run securebench qualify --output qualification.json
```

The command runs the configuration check and every B1 to B8 probe, prints each result and writes the record. Runs reference the record with `--qualification qualification.json`; a run refuses to start on a worker whose configuration check fails, or whose record is missing, failing, or was made for a different configuration, unless it is given `--development`, in which case every result record says `admitted: false`.

Qualify again after any change to the kernel, Docker, containerd or runc.

### Integration tests

```bash
uv run pytest -m integration
```

On a worker without enforced disk quotas (for example Docker Desktop), the disk-quota probe and the F5 disk candidate are skipped and reported as such.

## 2. Preparing a harness overlay

A model harness runs from a read-only overlay mounted at `/.securebench/harness`. SecureBench never downloads the overlay; we prepare it once per harness version and worker architecture, outside any run.

The overlay holds the harness package and a Linux Node runtime. Claude Code 2.x ships a native program and runs without Node; Codex starts from a JavaScript launcher and needs it:

```
<overlay>/bin/node
<overlay>/node_modules/<package>/...
```

One way to build it, with the Node image pinned by digest and the harness version pinned exactly:

```bash
docker run --rm -v "$PWD/overlays/claude-code-2.1.289:/out" node@sha256:43ac6c60b8f89723f746e8a92ce91abd5017e627ce1ddfe4238355d3a30b772c sh -c 'npm install --prefix /out --omit=dev --no-audit --no-fund @anthropic-ai/claude-code@2.1.289 && mkdir -p /out/bin && cp /usr/local/bin/node /out/bin/node'
```

For Codex, replace the package with `@openai/codex@<version>`.

Then run with the overlay:

```bash
securebench run --harness claude-code:2.1.289:<model> --overlay overlays/claude-code-2.1.289 --qualification qualification.json --run-dir runs/example fixtures/f1-answer-file/task
```

For Codex, `--reasoning-effort minimal|low|medium|high|xhigh` sets the model's reasoning effort with a fixed `-c model_reasoning_effort=...` argument, as Pier's Codex agent does. For Claude Code, `--reasoning-effort low|medium|high|xhigh|max` adds a fixed `--effort <value>` argument, as Pier's Claude Code agent does. The scripted harness refuses the flag. Both model harnesses run with the task image's own `HOME`, as Pier does, so caches and settings the image keeps there (a Go module cache, a global git identity) are available to the agent.

The provider credential (`ANTHROPIC_API_KEY` or `OPENAI_API_KEY`) is read from the host environment by the relay only; the Agent environment receives a placeholder. To run Claude Code on a subscription token made by `claude setup-token`, use `--harness claude-code-oauth:<version>:<model>` and set `CLAUDE_CODE_OAUTH_TOKEN` on the host instead; the relay sends it as a bearer token, and the Agent environment holds a placeholder token and no API key. Before each attempt, SecureBench runs the harness's `--version` in the task image and refuses an overlay that does not print the pinned version, or that cannot run in that image (for example a glibc Node in a musl image).

### Testing an overlay without credentials

`tests/fixtures/test_model_harness.py` runs each harness on fixture F1 against a stub model API (`tests/fixtures/stub_anthropic.py`, `tests/fixtures/stub_openai.py`), through the real relay, and expects a pass. A harness's test runs when these variables name its prepared overlay:

```bash
SECUREBENCH_CLAUDE_CODE_OVERLAY=overlays/claude-code-2.1.289 SECUREBENCH_CLAUDE_CODE_VERSION=2.1.289 SECUREBENCH_CODEX_OVERLAY=overlays/codex-0.160.0 SECUREBENCH_CODEX_VERSION=0.160.0 uv run pytest -m integration tests/fixtures/test_model_harness.py
```

Behaviors these tests found:

- Claude Code 2.1.289 refuses to skip its permission prompts as root unless `IS_SANDBOX=1` is set; the preset sets it, since the container is the sandbox.
- Claude Code sends a `HEAD /api/hello` connectivity check, which the relay refuses and logs without harm.
- Codex 0.160.0 declares a `namespace` tool grouping client functions; the relay accepts it only when every member is a client tool.
