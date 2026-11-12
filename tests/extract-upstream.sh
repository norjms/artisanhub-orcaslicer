#!/usr/bin/env bash
# Copy every file and folder convert/convert.py reads or edits out of the pinned upstream image (upstream.env)
# into tests/.upstream, laid out as in the image. A file or folder the image no longer has fails here.
#
#   tests/extract-upstream.sh [image]     (default: the image and digest in upstream.env)
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
. "$here/upstream.env"
image="${1:-$ORCASLICER_IMAGE:$ORCASLICER_VERSION@$ORCASLICER_DIGEST}"
out="$here/tests/.upstream"
docker="${DOCKER:-docker}"

rm -rf "$out"
mkdir -p "$out"
cid="$($docker create "$image")"
trap '$docker rm "$cid" > /dev/null' EXIT

list="$(python3 -I -c '
import sys; sys.path.insert(0, sys.argv[1]); import convert
for rel in convert.FOLDERS + convert.EDITED: print(rel)' "$here/convert")"
status=0
while read -r rel; do
  # Through tar, so the copy belongs to whoever runs the tests (docker cp may run as root) and is writable.
  mkdir -p "$out/$(dirname "$rel")"
  if ! $docker cp "$cid:/$rel" - 2> /dev/null \
       | tar -x -C "$out/$(dirname "$rel")" --no-same-owner --no-same-permissions --mode=u+w 2> /dev/null \
     || [ ! -e "$out/$rel" ]; then
    echo "missing from $image: /$rel" >&2
    rm -rf "${out:?}/$rel"
    status=1
  fi
done <<< "$list"
exit "$status"
