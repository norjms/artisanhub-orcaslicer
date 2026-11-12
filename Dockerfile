# artisanhub-orcaslicer: linuxserver.io's OrcaSlicer image, restyled for ArtisanHub by convert/convert.py.
#
# The image comes from upstream.env (passed as build arguments by the release build): its
# version tag and the digest that tag must be, so a moved tag fails the build instead of changing what is
# built. Visuals only: OrcaSlicer itself is not rebuilt or changed.

# The defaults are upstream.env's values, so a plain "docker build ." builds the pinned image; the tests
# check the two agree.
ARG ORCASLICER_IMAGE=lscr.io/linuxserver/orcaslicer
ARG ORCASLICER_VERSION=v2.5.0-ls49
ARG ORCASLICER_DIGEST=sha256:4cb6ec5e296898969be71c0a997a375835e268b8cb6bdb59968e7fe3cd6b571b

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
COPY convert /tmp/ahi-convert
COPY --from=fonts /fonts /tmp/ahi-convert/files/dashboard/fonts
RUN python3 /tmp/ahi-convert/convert.py / && rm -rf /tmp/ahi-convert
COPY LICENSE NOTICE LICENSES /usr/share/doc/artisanhub-orcaslicer/
ENV DASHBOARD=artisanhub-dashboard \
    TITLE=OrcaSlicer
LABEL org.opencontainers.image.title="artisanhub-orcaslicer" \
      org.opencontainers.image.description="OrcaSlicer in a web desktop, in the ArtisanHub look, built from linuxserver.io's orcaslicer ${ORCASLICER_VERSION}" \
      org.opencontainers.image.licenses="GPL-3.0-only AND AGPL-3.0-only" \
      org.opencontainers.image.version="${ORCASLICER_VERSION}"
