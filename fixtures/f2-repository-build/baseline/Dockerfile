# The F2 baseline: a C repository at a deterministic commit, with a compiler.
FROM python@sha256:02108f5d322dd89f1c9e552442c25acb0543dfdbc455693a5599624f20d9155d
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libc6-dev make git \
    && rm -rf /var/lib/apt/lists/*
COPY repo/ /app/
RUN chmod -R u=rwX,go=rX /app \
    && cd /app \
    && git init -q -b main \
    && git add -A \
    && GIT_AUTHOR_NAME=fixture GIT_AUTHOR_EMAIL=fixture@securebench.invalid \
       GIT_AUTHOR_DATE=2026-01-01T00:00:00Z GIT_COMMITTER_NAME=fixture \
       GIT_COMMITTER_EMAIL=fixture@securebench.invalid GIT_COMMITTER_DATE=2026-01-01T00:00:00Z \
       git commit -q -m "Initial commit"
