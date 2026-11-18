#!/bin/sh
# The reference, but it reads "deepseek tokens" as tokens of DeepSeek's own
# tokenizer and loads DeepSeek-R1-Distill-Qwen-1.5B's instead of
# Qwen2.5-1.5B-Instruct's. Its vocabulary is close to Qwen's, but it adds a
# beginning-of-sentence token to every encoded text.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
grep -qF '"Qwen/Qwen2.5-1.5B-Instruct"' "$here/reference.sh" || exit 1
sed 's|"Qwen/Qwen2.5-1.5B-Instruct"|"deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B"|' "$here/reference.sh" | sh
