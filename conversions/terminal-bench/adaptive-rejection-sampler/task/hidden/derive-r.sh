#!/bin/sh
# Rebuilds evaluation/r.tar.xz, the R installation the setup commands restore in
# every Evaluation environment, and hidden/r-packages.txt, the packages it holds.
#
# It runs the reference's own R install command (upstream solution/solve.sh) in
# the baseline, takes every file, link and new directory that the install added
# or changed (docker diff), leaves out /var, /tmp, /root, /run and the
# documentation under /usr/share/{doc,man,info}, and packs them in name order
# with fixed owners and times, so the same packages give the same archive.
# Ubuntu publishes updates of the dependencies, so a later run can pick newer
# patch versions; r-packages.txt lists the versions in the committed archive.
#
# Usage: sh derive-r.sh <output directory>     (needs Docker and the network)
set -eu
BASELINE=alexgshaw/adaptive-rejection-sampler@sha256:985bed39e8448bc95f138b5f766b59003a95c4be171c96af8e76448338f3dd8f
out=$1
name=ars-derive-r-$$
mkdir -p "$out"
docker run -d --name "$name" --memory 4g "$BASELINE" sleep infinity > /dev/null
trap 'docker rm -f "$name" > /dev/null' EXIT
docker exec "$name" sh -c 'dpkg-query -W -f "\${Package} \${Version}\n" | LC_ALL=C sort > /before'
docker exec "$name" sh -c 'apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends r-base-core=4.3.3-2build2' > "$out/apt.log"
docker exec "$name" sh -c 'dpkg-query -W -f "\${Package} \${Version}\n" | LC_ALL=C sort | comm -13 /before -' > "$out/r-packages.txt"
docker diff "$name" \
  | awk '$1 == "A" || $1 == "C" { print $1, $2 }' \
  | grep -v -E ' /(var|tmp|root|run)(/|$)| /usr/share/(doc|man|info)(/|$)| /before$' \
  > "$out/diff.txt"
# A changed directory already exists in the baseline; only new ones are packed.
docker exec -i "$name" sh -c '
  while read -r change path; do
    if [ -d "$path" ] && [ ! -L "$path" ] && [ "$change" = C ]; then continue; fi
    printf "%s\n" "${path#/}"
  done | LC_ALL=C sort > /list
  cd / && tar --format=gnu --no-recursion --numeric-owner --owner=0 --group=0 \
    --mtime=@1761868800 -cf - -T /list' < "$out/diff.txt" > "$out/r.tar"
xz -9e -T1 -c "$out/r.tar" > "$out/r.tar.xz"
sha256sum "$out/r.tar" "$out/r.tar.xz"
