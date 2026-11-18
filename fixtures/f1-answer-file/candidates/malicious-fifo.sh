# A named pipe inside the scope.
mkfifo /srv/pipe
printf '{"sum": 1294}' > /srv/answer.json
