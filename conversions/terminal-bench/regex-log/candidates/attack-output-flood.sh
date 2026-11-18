#!/bin/sh
# A regex whose 64 groups each capture the rest of the log from every position,
# so findall's result is far larger than the observation bound. The case must
# end in a failed case (output too large), never in an invalid attempt.
cd /app || exit 1
groups=''
i=0
while [ "$i" -lt 64 ]; do
  groups="$groups(?=((?s:.*)))"
  i=$((i + 1))
done
printf '%s\n' "$groups" > /app/regex.txt
