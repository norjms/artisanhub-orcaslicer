#!/usr/bin/env python3
"""Restyle linuxserver.io's OrcaSlicer image for ArtisanHub: visuals only.

    python3 convert/convert.py [root]

Runs inside the image build (root "/"), or on a copy of the image's files for the tests. OrcaSlicer keeps
every control, layout, icon and word; only colours and fonts change, and only where they are read from files
at run time, with no change to OrcaSlicer's source:

1. The web desktop's page. Selkies' dashboard is copied to a new dashboard, "artisanhub-dashboard", which the
   image selects with DASHBOARD. The copy loads ahi-dashboard.css after Selkies' own stylesheet: Manrope and
   Sora, the artisanhub-ui colours on the toolbar and its handle, glass panels, and no light-mode switch
   (ArtisanHub is dark only). The page's install colours (manifest) become the page colour.
2. The window manager. labwc draws the window title bar; its theme becomes "ArtisanHub" (colours from
   artisanhub-ui, title in Manrope).
3. GTK. OrcaSlicer's Linux build is wxWidgets on GTK 3, which takes native controls (text fields, lists,
   menus, dialogs, scroll bars, tooltips) from the GTK theme. The default is Adwaita, light. A theme
   "ArtisanHub" is added (Adwaita dark under the artisanhub-ui colours) and set with Manrope as the font in
   /etc/gtk-3.0/settings.ini.
4. OrcaSlicer's own dark mode. Turned on for a new /config (an existing OrcaSlicer.conf is never changed), and
   its colours that live in files are mapped per the OrcaSlicer canvas's colour map: the dark values of the
   web pages' shared colour sheet (home page, setup wizard, dialogs) and the setup wizard's dark sheet, with
   Manrope as the pages' font.

Every edit names text that must be found a set number of times. When an upstream release changes that text,
or a file the script edits is missing, the script stops and says which, rather than guessing; fix the anchor
here and run it again.
"""

from __future__ import annotations

import os
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FILES = HERE / "files"

DASHBOARD_SRC = "usr/share/selkies/selkies-dashboard"
DASHBOARD = "usr/share/selkies/artisanhub-dashboard"
LABWC_RC = "defaults/labwc.xml"
INIT_NGINX = "etc/s6-overlay/s6-rc.d/init-nginx/run"
ORCA_WEB = "opt/orcaslicer/resources/web"
GLOBAL_CSS = f"{ORCA_WEB}/include/global.css"
GUIDE_DARK = f"{ORCA_WEB}/guide/css/dark.css"
FONT_FILES = (f"{ORCA_WEB}/guide/css/common.css", f"{ORCA_WEB}/homepage/css/home.css",
              f"{ORCA_WEB}/dialog/css/common.css")
GTK_SETTINGS = "etc/gtk-3.0/settings.ini"
S6 = "etc/s6-overlay/s6-rc.d"
# Selkies' file panel page (the Files the desktop offers for download), built by its Python server.
FILE_PANEL = "lsiopy/lib/python3.13/site-packages/selkies/stream_server.py"

# Every upstream file the conversion reads or edits. The tests take exactly these out of the pinned image.
EDITED = (f"{DASHBOARD_SRC}/index.html", LABWC_RC, INIT_NGINX, GLOBAL_CSS, GUIDE_DARK, FILE_PANEL) + FONT_FILES
# Upstream folders the conversion adds to; they must exist.
FOLDERS = (DASHBOARD_SRC, f"{DASHBOARD_SRC}/assets", "etc/gtk-3.0", "usr/share/themes", f"{S6}/init-config",
           f"{S6}/init-config-end/dependencies.d", f"{S6}/user/contents.d")

# artisanhub-ui v0.1.0 values (dist/theme.css), and the solid colours they make over the page where a
# native toolkit cannot blend (GTK and labwc paint opaque colours).
PAGE = "#172028"         # --ah-page
PAGE_MID = "#273642"     # --ah-page-mid: window and panel background, per the canvas's colour map
SOLID_PANEL = "#26343f"  # --ah-solid-panel
TEXT = "#f1f6fa"         # --ah-text
ACCENT = "#8fd3ff"       # --ah-accent
ON_ACCENT = "#1d2a34"    # --ah-on-accent
LINK = "#bfe6ff"         # --ah-link
ATTENTION = "#ffb38a"    # --ah-attention
FAILURE = "#e66767"      # --ah-failure
SIDEBAR = "#2a3239"      # --ah-glass (white 0.08) over the page: sidebar and tab bar
FIELD = "#1e2a34"        # --ah-field (rgba(20,30,38,0.5)) over the panel background
FIELD_LINE = "#525e68"   # --ah-field-line (white 0.2) over the panel background
ROW_LINE = "#384651"     # --ah-row-line (white 0.08) over the panel background
HOVER = "#3d4a55"        # --ah-track (white 0.1) over the panel background, a step up from the panel
MUTED = "#bbc4cb"        # --ah-text-3-large (0.75) over the panel background
TEXT_2 = "#cfd7dd"       # --ah-text-2 (0.85) over the panel background
DISABLED = "#7d8890"     # white 0.4 over the panel background, for disabled text only

# The dark block of OrcaSlicer's shared web colour sheet, mapped per the canvas: background, sidebar, accent,
# text, muted text, input field, warning and error.
GLOBAL_DARK = {
    "--main-color": ACCENT,
    "--main-color-hover": LINK,
    "--main-color-fixed": ACCENT,
    "--bg-color": PAGE_MID,
    "--bg-color-secondary": SOLID_PANEL,
    "--bg-color-alt": PAGE,
    "--bg-color-sidebar": SIDEBAR,
    "--fg-color-text": TEXT,
    "--fg-color-label": TEXT_2,
    "--fg-color-disabled": DISABLED,
    "--focus-bg-item": "#2f4b5f",   # accent at 0.16 over the panel background
    "--focus-bg-box": "#2b4152",    # accent at 0.1 over the panel background
    "--border-color": FIELD_LINE,
    "--icon-color": MUTED,
    "--button-fg-light": ON_ACCENT,  # text on accent buttons: the accent is light, so the text is dark
    "--button-fg-text": TEXT,
    "--button-fg-disabled": DISABLED,
    "--button-bg-normal": ROW_LINE,
    "--button-bg-hover": HOVER,
    "--button-bg-alert": FAILURE,
}
# The setup wizard's dark sheet: each OrcaSlicer colour found there, and its ArtisanHub colour.
GUIDE_COLOURS = {
    "#efeff0": TEXT, "#B9B9BC": FIELD_LINE, "#2D2D31": PAGE_MID, "#939594": MUTED, "#161817": PAGE,
    "#009688": ACCENT, "#4A4A51": FIELD, "#BEBEC0": TEXT_2, "#4C4C55": HOVER,
}
# Selected rows in the wizard are accent coloured, so their text is dark.
GUIDE_SELECTED = ("\tbackground-color:#009688;\n\tcolor: #fff;", f"\tbackground-color:{ACCENT};\n\tcolor: {ON_ACCENT};")
# The wizard's own sheets (guide/<n>/*.css, guide/css/common.css) colour its title, loading line, links and
# selected region in Orca green. The dark sheet (loaded in dark mode only) gets the ArtisanHub values for them,
# with selectors that outrank the page sheets linked after it. The light values stay as they are.
GUIDE_DARK_EXTRA = f"""
/*---ArtisanHub: colours the wizard's other sheets set, in dark mode---*/
html
{{
	background-color: {PAGE_MID};
}}

html body #Title, html body #Title div, html body #LoadTip, html body .HyperLink
{{
	color: {ACCENT};
}}

html body #Title div.TitleUnselected
{{
	color: {TEXT_2};
}}

html body .RegionSelected, html body .RegionSelected:hover
{{
	background-color: {ACCENT};
	color: {ON_ACCENT};
}}
"""
FONT_OLD = 'font-family: "system-ui",'
FONT_NEW = 'font-family: Manrope, "system-ui",'


class ConvertError(SystemExit):
    pass


def text(root: Path, rel: str) -> str:
    path = root / rel
    if not path.is_file():
        raise ConvertError(f"convert: {rel}: missing from the upstream image")
    return path.read_text(encoding="utf-8")


def edit(root: Path, rel: str, old: str, new: str, count: int = 1) -> None:
    body = text(root, rel)
    found = body.count(old)
    if found != count:
        raise ConvertError(f"convert: {rel}: expected {count} of {old[:80]!r}, found {found}")
    (root / rel).write_text(body.replace(old, new), encoding="utf-8")


def need(root: Path, rel: str, anchor: str, at_least: int = 1) -> None:
    found = text(root, rel).count(anchor)
    if found < at_least:
        raise ConvertError(f"convert: {rel}: expected {anchor[:80]!r}, found {found}")


def copy_tree(src: Path, dst: Path) -> None:
    for path in sorted(src.rglob("*")):
        if path.is_file():
            target = dst / path.relative_to(src)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def dashboard(root: Path) -> None:
    src, dst = root / DASHBOARD_SRC, root / DASHBOARD
    text(root, f"{DASHBOARD_SRC}/index.html")
    sheets = sorted((src / "assets").glob("index-*.css"))
    if len(sheets) != 1:
        raise ConvertError(f"convert: {DASHBOARD_SRC}/assets: expected one index-*.css, found {len(sheets)}")
    sheet = str(sheets[0].relative_to(root))
    # The selectors and variables ahi-dashboard.css restyles.
    need(root, sheet, ".sidebar,.stream-strip,.sidebar-skin,:root[data-layout=default] [data-slot=dialog-content]{--sk-accent:")
    need(root, sheet, ":root:not(.dark) .sidebar,:root:not(.dark) .sidebar-skin,")
    for anchor in (".sidebar h2{", ".theme-pill", ".toggle-indicator{background-color:var(--sk-accent",
                   ".sidebar-section-header h3{", ".action-button", "--sk-wordmark-from", "--sk-surface-inset"):
        need(root, sheet, anchor)
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, symlinks=True)
    rel = f"{DASHBOARD}/index.html"
    edit(root, rel, "<title>Selkies</title>", "<title>OrcaSlicer</title>")
    edit(root, rel, "</head>", '<link rel="stylesheet" href="./ahi/ahi-dashboard.css"></head>')
    copy_tree(FILES / "dashboard", dst / "ahi")
    css = (dst / "ahi" / "ahi-dashboard.css").read_text(encoding="utf-8")
    if os.environ.get("AHI_SKIP_FONTS") != "1":
        for font in re.findall(r"url\(\./fonts/([^)]+)\)", css):
            if not (dst / "ahi" / "fonts" / font).is_file():
                raise ConvertError(f"convert: font {font} is missing (the Dockerfile's fonts stage puts it there)")


def manifest(root: Path) -> None:
    edit(root, INIT_NGINX, '\\"background_color\\": \\"#000000\\",', f'\\"background_color\\": \\"{PAGE}\\",')
    edit(root, INIT_NGINX, '\\"theme_color\\": \\"#000000\\",', f'\\"theme_color\\": \\"{PAGE}\\",')


def window_manager(root: Path) -> None:
    edit(root, LABWC_RC, "<name>Clearlooks</name>", "<name>ArtisanHub</name>")
    edit(root, LABWC_RC, "    <cornerRadius>8</cornerRadius>\n  </theme>",
         "    <cornerRadius>10</cornerRadius>\n"
         '    <font place="ActiveWindow"><name>Manrope</name><size>10</size><weight>bold</weight></font>\n'
         '    <font place="InactiveWindow"><name>Manrope</name><size>10</size><weight>bold</weight></font>\n'
         '    <font place="MenuItem"><name>Manrope</name><size>10</size></font>\n'
         '    <font place="OnScreenDisplay"><name>Manrope</name><size>10</size></font>\n'
         "  </theme>")
    copy_tree(FILES / "themes", root / "usr/share/themes")


def gtk(root: Path) -> None:
    if (root / GTK_SETTINGS).exists():
        raise ConvertError(f"convert: {GTK_SETTINGS}: upstream now ships one; merge the ArtisanHub settings into it")
    shutil.copy2(FILES / "gtk-settings.ini", root / GTK_SETTINGS)


def orca_web(root: Path) -> None:
    body = text(root, GLOBAL_CSS)
    match = re.search(r"@media \(prefers-color-scheme: dark\) \{\s*:root \{(?P<vars>.*?)\}\s*\}", body, re.S)
    if not match:
        raise ConvertError(f"convert: {GLOBAL_CSS}: the dark colour block was not found")
    block = match.group("vars")
    for name, value in GLOBAL_DARK.items():
        block, n = re.subn(r"(%s\s*:\s*)[^;]+;" % re.escape(name), r"\g<1>%s;" % value, block)
        if n != 1:
            raise ConvertError(f"convert: {GLOBAL_CSS}: expected one {name} in the dark block, found {n}")
    body = body[:match.start("vars")] + block + body[match.end("vars"):]
    (root / GLOBAL_CSS).write_text(body, encoding="utf-8")

    edit(root, GUIDE_DARK, *GUIDE_SELECTED)
    body = text(root, GUIDE_DARK)
    for old, new in GUIDE_COLOURS.items():
        body, n = re.subn(re.escape(old), new, body, flags=re.I)
        if n == 0:
            raise ConvertError(f"convert: {GUIDE_DARK}: expected {old}, found none")
    (root / GUIDE_DARK).write_text(body.rstrip("\n") + "\n" + GUIDE_DARK_EXTRA, encoding="utf-8")

    for rel in FONT_FILES:
        edit(root, rel, FONT_OLD, FONT_NEW)


# The file panel's page has its own copy of Selkies' palette. The ArtisanHub values go after it, for every
# theme a browser may have stored (the page is dark only here, like the dashboard).
FILE_PANEL_ANCHOR = (
    "            --shadow: 0 1px 2px rgba(0, 0, 0, 0.4), 0 8px 24px rgba(0, 0, 0, 0.35);\n        }\n        * {\n"
)
FILE_PANEL_EXTRA = f"""            --shadow: 0 1px 2px rgba(0, 0, 0, 0.4), 0 8px 24px rgba(0, 0, 0, 0.35);
        }}
        /* ArtisanHub: artisanhub-ui's glass-dark values, whatever theme is stored. */
        :root, :root[data-theme], :root:not([data-theme="light"]) {{
            --accent: {ACCENT};
            --accent-text: {ACCENT};
            --accent-soft: rgba(143, 211, 255, 0.14);
            --bg: {PAGE};
            --surface: {PAGE_MID};
            --surface-alt: {SOLID_PANEL};
            --border-soft: rgba(255, 255, 255, 0.16);
            --text: {TEXT};
            --text-muted: rgba(236, 243, 248, 0.85);
            --shadow: 0 1px 2px rgba(0, 0, 0, 0.4), 0 8px 24px rgba(0, 0, 0, 0.35);
            --font-family: "Manrope", system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
            --border-radius: 22px;
            color-scheme: dark;
        }}
        body {{
            background: radial-gradient(80% 75% at 55% 35%, #3f566a, {PAGE_MID} 50%, {PAGE}) fixed;
        }}
        * {{
"""


def file_panel(root: Path) -> None:
    edit(root, FILE_PANEL, FILE_PANEL_ANCHOR, FILE_PANEL_EXTRA)


def dark_by_default(root: Path) -> None:
    s6 = root / S6
    copy_tree(FILES / "s6", s6)
    for name in ("init-ahi-orca", "init-ahi-files"):
        (s6 / f"init-config-end/dependencies.d/{name}").touch()
        (s6 / f"user/contents.d/{name}").touch()
        os.chmod(s6 / f"{name}/run", 0o755)


def main(argv: list[str]) -> None:
    root = Path(argv[1] if len(argv) > 1 else "/").resolve()
    for rel in EDITED:
        text(root, rel)
    for rel in FOLDERS:
        if not (root / rel).is_dir():
            raise ConvertError(f"convert: {rel}/: missing from the upstream image")
    dashboard(root)
    manifest(root)
    window_manager(root)
    gtk(root)
    orca_web(root)
    file_panel(root)
    dark_by_default(root)
    print("convert: done")


if __name__ == "__main__":
    main(sys.argv)
