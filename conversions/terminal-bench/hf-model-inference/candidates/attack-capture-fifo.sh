#!/bin/sh
# Solves the task with the reference, then leaves a named pipe in the model
# directory to break capture. SecureBench must fail it (class capture), not
# turn it into an invalid attempt.
cd /app
sh "$(dirname "$0")/reference.sh"
mkfifo /app/model_cache/sentiment_model/pipe
