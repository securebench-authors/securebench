#!/bin/sh
# The reference with openssl's default SHA-1 fingerprint in verification.txt instead of SHA-256.
set -e
sed 's/-noout -fingerprint -sha256 >>/-noout -fingerprint >>/' "$(dirname "$0")/reference.sh" > /tmp/mutant-sha1-fingerprint.sh
grep -q -e '-noout -fingerprint >>' /tmp/mutant-sha1-fingerprint.sh
sh /tmp/mutant-sha1-fingerprint.sh
