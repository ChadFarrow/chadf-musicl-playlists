"""The one User-Agent that every script in this repo sends.

generate_onlyboosts_top_songs.py (weekly in CI) and generate_hgh_hitsgiving.py
(by hand) import USER_AGENT from here. Form: `<AppName>/<version> (+<link>)`,
with no email and no browser imitation. The link is the GitHub Pages site of
this repo. The repo has no package file, so APP_VERSION here is its version.

Until 2026-11-27 both scripts sent
`Mozilla/5.0 (compatible; chadf-musicl-playlists; +https://github.com/ChadFarrow/chadf-musicl-playlists)`.
No commit gave a reason for the Mozilla prefix, and every probed host (the
chart, the resolver, the song feeds and the audio hosts) gave the same answer
for both names that day.
"""

APP_NAME = "chadf-musicl-playlists"
APP_VERSION = "1.0.0"
APP_LINK = "https://chadfarrow.github.io/chadf-musicl-playlists/"
USER_AGENT = f"{APP_NAME}/{APP_VERSION} (+{APP_LINK})"
