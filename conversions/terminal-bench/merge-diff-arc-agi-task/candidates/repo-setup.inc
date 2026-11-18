#!/bin/sh
# Helper run by mutants and attacks, not a candidate: install git and create
# /app/repo with a first commit, as the reference does.
apt-get update
apt-get install -y git
mkdir -p /app/repo
cd /app/repo
git init
git config user.name "Agent"
git config user.email "agent@example.com"
echo "# Repository" > README.md
git add README.md
git commit -m "Initial commit"
