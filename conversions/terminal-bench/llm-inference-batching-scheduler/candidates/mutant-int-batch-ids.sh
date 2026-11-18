#!/bin/sh
# Batch ids written as JSON integers. Upstream uses them as dict keys and
# sorts them numerically; aimed at how the adapter reports batch ids and the
# Oracle groups and orders them.
cd /app || exit 1
sh "$(dirname "$0")/reference.sh" || exit 1
python3 "$(dirname "$0")/rewrite_plans.py" int-batch-ids
