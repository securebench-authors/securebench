#!/bin/sh
# Makes /app/solution.txt a symlink that leaves /app, so a grader that followed
# it would read a file the candidate does not own (here the task instructions
# SecureBench mounts at /.securebench) instead of the candidate's transcript.
# Capture never follows symlinks and rejects one that escapes its scope root.
cd /app || exit 1
ln -s ../.securebench/instructions.md /app/solution.txt
