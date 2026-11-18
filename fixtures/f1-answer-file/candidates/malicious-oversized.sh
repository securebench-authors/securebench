# A file larger than the scope's byte bound.
head -c 70000 /dev/zero > /srv/padding
printf '{"sum": 1294}' > /srv/answer.json
