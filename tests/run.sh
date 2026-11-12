#!/usr/bin/env bash
# Run the tests: take the converted files out of the pinned upstream image, test the conversion on them, and,
# with IMAGE set, check a built image has every change in place.
#
#   tests/run.sh                                  conversion tests
#   IMAGE=artisanhub-orcaslicer:local tests/run.sh   and the built image
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
docker="${DOCKER:-docker}"

DOCKER="$docker" bash "$here/tests/extract-upstream.sh"
python3 -m unittest discover -s "$here/tests" -v

if [ -n "${IMAGE:-}" ]; then
  echo "checking $IMAGE"
  $docker run --rm --entrypoint /bin/bash "$IMAGE" -c '
    set -e
    test "$DASHBOARD" = artisanhub-dashboard
    d=/usr/share/selkies/artisanhub-dashboard
    grep -q "ahi/ahi-dashboard.css" $d/index.html
    for f in manrope-latin-400-normal manrope-latin-600-normal sora-latin-500-normal jetbrains-mono-latin-400-normal; do
      test -s $d/ahi/fonts/$f.woff2
    done
    grep -q "<name>ArtisanHub</name>" /defaults/labwc.xml
    test -s /usr/share/themes/ArtisanHub/labwc/themerc
    test -s /usr/share/themes/ArtisanHub/gtk-3.0/gtk.css
    grep -q "gtk-theme-name=ArtisanHub" /etc/gtk-3.0/settings.ini
    fc-list | grep -qi manrope
    fc-list | grep -qi "jetbrains mono"
    test -x /etc/s6-overlay/s6-rc.d/init-ahi-orca/run
    test -x /etc/s6-overlay/s6-rc.d/init-ahi-files/run
    grep -q "artisanhub-ui.s glass-dark values" /lsiopy/lib/python3.13/site-packages/selkies/stream_server.py
    grep -q "#8fd3ff" /opt/orcaslicer/resources/web/include/global.css
    test -s /usr/share/doc/artisanhub-orcaslicer/NOTICE
    echo "image: every change in place"
  '
fi
