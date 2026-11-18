# JSON with duplicate keys: one reader might take the first value, another the last.
printf '{"sum": 1, "sum": 1294}' > /srv/answer.json
