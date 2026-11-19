# artisanhub-orcaslicer: linuxserver.io's OrcaSlicer image, restyled for ArtisanHub by convert/convert.py.
#
# The image comes from upstream.env (passed as build arguments by the release build): its
# version tag and the digest that tag must be, so a moved tag fails the build instead of changing what is
# built. OrcaSlicer itself is not rebuilt or changed: visuals, and opening files the farm sends (B49).

# The defaults are upstream.env's values, so a plain "docker build ." builds the pinned image; the tests
# check the two agree.
ARG ORCASLICER_IMAGE=lscr.io/linuxserver/orcaslicer
ARG ORCASLICER_VERSION=v2.5.1-ls52
ARG ORCASLICER_DIGEST=sha256:b5c483239fd15771df3ea1bf3f0370e7e219eb98e69274b151b9335fc4acd2c9

# The web fonts for the desktop's page (Manrope, Sora, JetBrains Mono), from the fontsource packages.
FROM node:22-alpine AS fonts
ARG FONTSOURCE_VERSION=5.3.0
WORKDIR /pack
RUN npm pack --silent "@fontsource/manrope@${FONTSOURCE_VERSION}" "@fontsource/sora@${FONTSOURCE_VERSION}" \
      "@fontsource/jetbrains-mono@${FONTSOURCE_VERSION}" \
 && mkdir -p /fonts \
 && for f in *.tgz; do mkdir -p "x/$f" && tar -xzf "$f" -C "x/$f"; done \
 && cp x/*manrope*/package/files/manrope-latin-400-normal.woff2 x/*manrope*/package/files/manrope-latin-500-normal.woff2 \
       x/*manrope*/package/files/manrope-latin-600-normal.woff2 x/*manrope*/package/files/manrope-latin-700-normal.woff2 \
       x/*sora*/package/files/sora-latin-500-normal.woff2 \
       x/*jetbrains*/package/files/jetbrains-mono-latin-400-normal.woff2 /fonts/ \
 && cp x/*manrope*/package/LICENSE /fonts/OFL-Manrope.txt \
 && cp x/*sora*/package/LICENSE /fonts/OFL-Sora.txt \
 && cp x/*jetbrains*/package/LICENSE /fonts/OFL-JetBrainsMono.txt

FROM ${ORCASLICER_IMAGE}:${ORCASLICER_VERSION}@${ORCASLICER_DIGEST}
ARG ORCASLICER_VERSION
# Manrope and JetBrains Mono for OrcaSlicer's own windows (GTK and labwc), from Debian (SIL OFL 1.1).
RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y fonts-manrope fonts-jetbrains-mono \
 && fc-cache -f \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/* /var/tmp/* /tmp/*
# Q9: the OrcaSlicer add-on (OpenPrintHQ Print Queue, AGPL-3.0) that prints to the hub's queue, from
# artisan-hub-farm at a pinned commit, checked against its hash. ahi-farm-connect installs it for the person.
ARG ADDON_COMMIT=4f1ef7cc598085cc417ef8c065e3f44450dc4837
ARG ADDON_SHA256=6807d4e57e3e03ac661e9809d0565a889a8e2289a02d1ce0a1da5de25b2c8c75
RUN mkdir -p /opt/ahi/addon \
 && curl -fsSL -o /opt/ahi/addon/openprinthq_print_queue.py \
      "https://raw.githubusercontent.com/norjms/artisan-hub-farm/${ADDON_COMMIT}/control-plane/orcaslicer-addon/plugin/openprinthq_print_queue.py" \
 && echo "${ADDON_SHA256}  /opt/ahi/addon/openprinthq_print_queue.py" | sha256sum -c - \
 && chmod 644 /opt/ahi/addon/openprinthq_print_queue.py
COPY convert /tmp/ahi-convert
COPY --from=fonts /fonts /tmp/ahi-convert/files/dashboard/fonts
RUN python3 /tmp/ahi-convert/convert.py / && rm -rf /tmp/ahi-convert
COPY LICENSE NOTICE LICENSES /usr/share/doc/artisanhub-orcaslicer/
# Q8: web addresses OrcaSlicer opens go to the desktop's Firefox (convert.py's browser step).
ENV DASHBOARD=artisanhub-dashboard \
    TITLE=OrcaSlicer \
    BROWSER=/usr/local/bin/ahi-open-url
LABEL org.opencontainers.image.title="artisanhub-orcaslicer" \
      org.opencontainers.image.source="https://github.com/norjms/artisanhub-orcaslicer" \
      org.opencontainers.image.description="OrcaSlicer in a web desktop, in the ArtisanHub look, built from linuxserver.io's orcaslicer ${ORCASLICER_VERSION}" \
      org.opencontainers.image.licenses="GPL-3.0-only AND AGPL-3.0-only" \
      org.opencontainers.image.version="${ORCASLICER_VERSION}"
