# artisanhub-orcaslicer

OrcaSlicer in the browser for ArtisanHub: [linuxserver.io's OrcaSlicer image](https://github.com/linuxserver/docker-orcaslicer)
(OrcaSlicer in a Selkies web desktop), restyled to look like the rest of ArtisanHub. **Visuals only:** OrcaSlicer
keeps every control, layout, icon and word. Only colours and fonts change, and only where they are read from
files at run time; OrcaSlicer's source is not changed or rebuilt.

This repository holds no copy of the upstream image. It holds the steps that restyle a published
linuxserver.io release, and the build applies them to the release named in `upstream.env`:

| File | What it is |
|---|---|
| `upstream.env` | The upstream image built from: its version tag, the digest that tag must be, and the linuxserver/docker-orcaslicer commit it was built from. Also the fontsource version for the web fonts. |
| `convert/convert.py` | The restyle, as a script. Each edit names the exact text it changes and stops the build if a release no longer has it. |
| `convert/files/` | Files added to the image: the dashboard stylesheet, the labwc and GTK themes, GTK's settings, a start-up step that turns on OrcaSlicer's dark mode for a new `/config`, and one that sets up Files. |
| `Dockerfile` | Takes the pinned image, adds the fonts, runs the conversion. |
| `tests/` | `run.sh` takes every file the conversion edits out of the pinned image and tests the conversion on them (they fail if the image lacks one); with `IMAGE=` set it also checks a built image. Needs Docker (`DOCKER="sudo docker"` where the user is not in the docker group) and Python 3. |

## What changes

| Where | Before | After |
|---|---|---|
| Web desktop page (Selkies dashboard) | Selkies' pink and violet toolbar, Inter, light and dark modes | A copy of the dashboard, `artisanhub-dashboard`, selected with `DASHBOARD`: artisanhub-ui colours (accent `#8fd3ff`, page `#172028`), a glass toolbar with a 28px radius, Manrope with Sora for the wordmark, dark only (the light-mode switch is hidden). Selkies' own `selkies-dashboard` is untouched, so `DASHBOARD=selkies-dashboard` brings it back. |
| Page install colours (manifest) | `#000000` | `#172028` |
| Window title bar (labwc) | Clearlooks | Theme `ArtisanHub`: page colour, text `#f1f6fa`, Manrope bold, accent on hover |
| OrcaSlicer's native controls (GTK 3) | Adwaita, light | Theme `ArtisanHub`: Adwaita dark under the artisanhub-ui colours, Manrope 10 (`/etc/gtk-3.0/settings.ini`) |
| OrcaSlicer's dark mode | Off | On for a new `/config` (an existing `OrcaSlicer.conf` is never changed) |
| OrcaSlicer's web pages (home, setup wizard, dialogs) | Orca's dark values (`#2d2d31`, `#009688` ...) | The canvas's colour map: panel `#273642`, sidebar `rgba(255,255,255,0.08)` on `#172028`, accent `#8fd3ff` with dark text on it, text `#f1f6fa`, muted `rgba(236,243,248,0.75)`, field `rgba(20,30,38,0.5)` with a 0.2 white line, error `#e66767`; font Manrope |
| The web desktop's file panel page (download and upload) | Selkies' pink palette, light and dark | artisanhub-ui colours over the page gradient, dark only, 22px radius; same layout and words |
| Files (`FILE_MANAGER_PATH`, `/config/Files` as ArtisanHub sets it) | Uploads and downloads in `~/Desktop` | At each start: `Files` and `Files/Exports` exist and belong to the desktop's user, as does a `Send to hub` folder mounted there (never its contents); OrcaSlicer's file dialogs get bookmarks for Files, Library, Exports, Send to hub and Shared when present, ahead of the person's own (which are kept); OrcaSlicer exports to `Exports` and opens from `Files` until the person picks somewhere else (only keys not yet set are added) |

### Left out: needs OrcaSlicer source changes

These are drawn by OrcaSlicer's C++ code with colours compiled into it, so they keep OrcaSlicer's own dark
colours here. They belong to the OrcaSlicer fork's recolour (retheme Task 10 (b)), which replaces the dark
colour table from artisanhub-ui's generated C++ header:

- The dark colour table of OrcaSlicer's own widgets (`StateColor` dark map): tab bar, sidebar, buttons,
  combo boxes, switches, the parameter pages and their accent green.
- The 3D plate view: background, bed, grid, selection and gizmo colours (`GLCanvas3D` and the 3D scene).
- Colours injected at run time into the dialog pages (`--orca-*` from `WebViewHostDialog`).
- Warning and error colours in OrcaSlicer's notifications (ImGui), and the G-code viewer's legend colours.
- Fonts of the ImGui overlays (they load OrcaSlicer's bundled fonts) and the G-code viewer, which would take
  JetBrains Mono.
- Icons: unchanged by design (visuals keep OrcaSlicer's icons).

Also seen, and left as upstream shows it:

- The setup wizard's window is maximised by the web desktop while its page keeps its fixed size, so the window's
  own background (set in OrcaSlicer's C++, white) shows to the right of and below the page. The page itself is
  dark. A fix is the fork's (the dialog's background colour) or the window manager not maximising that dialog,
  which would change upstream behaviour, so neither is done here.
- OrcaSlicer draws its own title row (menu, undo, Calibration, window buttons) under the web desktop's title
  bar, as upstream does. Turning the web desktop's title bar off (`NO_DECOR`) is linuxserver.io's switch and is
  left to the installer to decide.
- The light values of the wizard's per-page sheets (`guide/<n>/*.css`) are unchanged; they only show when
  OrcaSlicer's dark mode is off.
- The Selkies logo in the toolbar keeps its own colours (icons are not changed).

## Keeping up with upstream

1. linuxserver.io publishes a new tag (`vX.Y.Z-lsN`). Read its digest:
   `docker buildx imagetools inspect lscr.io/linuxserver/orcaslicer:vX.Y.Z-lsN` and its commit with
   `git ls-remote https://github.com/linuxserver/docker-orcaslicer vX.Y.Z-lsN`.
2. Move the three image lines and `UPSTREAM_COMMIT` in `upstream.env`, and the two `ARG` defaults in the
   `Dockerfile` to match (a test checks they agree).
3. Run `tests/run.sh`. If an anchor no longer matches, fix it in `convert/convert.py`.
4. Build and publish as below; the installer then pins the new image by digest.

Only published version tags are taken; `latest`, branches and nightly tags never are.

## Building

linuxserver.io publishes this image for **amd64 only** (`v2.5.0-ls49` has no arm64), so it is built for amd64
alone. The build reads its arguments from `upstream.env`:

```sh
. ./upstream.env
docker buildx build --platform linux/amd64 \
  --build-arg ORCASLICER_IMAGE="$ORCASLICER_IMAGE" \
  --build-arg ORCASLICER_VERSION="$ORCASLICER_VERSION" \
  --build-arg ORCASLICER_DIGEST="$ORCASLICER_DIGEST" \
  --build-arg FONTSOURCE_VERSION="$FONTSOURCE_VERSION" \
  -t artisanhub-orcaslicer:local .
IMAGE=artisanhub-orcaslicer:local tests/run.sh
```

Published images are `ghcr.io/norjms/artisanhub-orcaslicer`, tagged `sha-<commit>`, the upstream version
(`2.5.0-ls49`) and `latest`. Installs pin an image by digest.

## How the installer serves it

At `/apps/orcaslicer/` of the hub's name, behind Authelia, like the farm. The container is not published on
any port; Caddy reaches it on the stack network.

```yaml
orcaslicer:
  image: ghcr.io/norjms/artisanhub-orcaslicer:sha-<short>@sha256:<digest>
  environment:
    PUID: "1000"
    PGID: "1000"
    TZ: <the installation's time zone>
    SUBFOLDER: /apps/orcaslicer/     # Selkies serves its page and its websocket (api) under this path
    TITLE: OrcaSlicer
    HARDEN_DESKTOP: "true"           # no terminal, no sudo, no xdg-open; the desktop is reachable from the web
    NO_GAMEPAD: "true"
    NO_WEBCAM: "true"
  volumes:
    - orcaslicer-config:/config      # OrcaSlicer's profiles and projects
  shm_size: 1gb
  labels:
    artisanhub.managed: orcaslicer
```

Caddy (path kept whole, so Selkies' `SUBFOLDER` matches it):

```caddy
redir /apps/orcaslicer /apps/orcaslicer/ 308
handle /apps/orcaslicer/* {
  forward_auth authelia:9091 {
    uri /api/authz/forward-auth
    copy_headers Remote-User Remote-Groups Remote-Email Remote-Name
  }
  reverse_proxy orcaslicer:3000
}
```

Port 3000 is Selkies' plain HTTP port, meant to sit behind a proxy; Caddy gives the browser the secure context
Selkies needs. Authelia's rule list gains one rule beside the farm's, for the hub's name:

```yaml
- domain: <hub name>
  resources: ['^/apps/orcaslicer([/?].*)?$']
  policy: one_factor
```

Give it the same `subject` the farm's rule has, if the farm's rule names one, so the same people reach both.

The hub's Slicing pages link to `/apps/orcaslicer/`.

## Running it by hand

```sh
docker run -d --name orcaslicer -p 127.0.0.1:3000:3000 -e PUID=1000 -e PGID=1000 \
  --shm-size=1g -v orcaslicer-config:/config ghcr.io/norjms/artisanhub-orcaslicer:latest
```

Open `http://localhost:3000/`. Everything linuxserver.io documents for its image applies
([configuration reference](https://docs.linuxserver.io/selkies/user-guide/configuration/)).

## Licence

linuxserver.io's files are under the GNU General Public License, version 3, and so are this repository's own
files: see `LICENSE`. OrcaSlicer, in the image, is under the GNU Affero General Public License, version 3
(`LICENSES/AGPL-3.0.txt`), including its web resource files as `convert/convert.py` changes them. `NOTICE`
lists every work in the image and its licence.
