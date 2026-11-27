# How the jobs in this repo run

This file tells you what runs automatically in this repo, what each job needs, and how to run each job on a different machine. Use it if you move the jobs off GitHub Actions.

## Summary

| Job | Starts when | Runs | Writes |
|---|---|---|---|
| Greatest Hits | A push changes a `docs/*-music-playlist.xml` file. Also every Sunday at 03:00 UTC. Also by hand. | `python3 generate_greatest_hits.py` | `docs/Greatest-Hits-music-playlist.xml` |
| OnlyBoosts Top Songs | Every Monday at 05:00 UTC. Also by hand. A PR that changes the script runs a test build and pushes nothing. | `python3 generate_onlyboosts_top_songs.py` | `docs/onlyboosts-top-songs-playlist.xml`, `docs/onlyboosts-top-songs-month-playlist.xml` |
| Homegrown Hits Hitsgiving | By hand only, when a new Hitsgiving episode is out. No workflow. | `python3 generate_hgh_hitsgiving.py` | `docs/HGH-hitsgiving-<year>-playlist.xml` |
| Daily playlist update (in a different repo) | Every day at 07:00 UTC | [musicL-playlist-updater](https://github.com/ChadFarrow/musicL-playlist-updater) | The other playlist files in `docs/`, and `state/smallgroup-shows-playlist.json` |

The workflow files are in `.github/workflows/`:
- `update-greatest-hits.yml`
- `update-onlyboosts-top-songs.yml`

## Order of the jobs

1. The updater in `musicL-playlist-updater` reads `FEEDS.md` from this repo. It writes the playlist files to `docs/` through the GitHub API.
2. A write to a `docs/*-music-playlist.xml` file is a push to `main`, so it starts the Greatest Hits job. Writes to the Small Group, LocalBitcoiners and MMT files, and to `state/`, do not start it. Greatest Hits makes one playlist from the 10 files listed in `generate_greatest_hits.py`.
3. The OnlyBoosts job does not use the other playlists. It runs by itself.

If you run the jobs outside GitHub, you lose step 2. Thus, run Greatest Hits after the updater finishes (see "Run the jobs locally").

## What each job needs

### Greatest Hits
- Python 3.12 or newer. It uses only the standard library, so you do not install packages.
- It reads the playlist files in `docs/`. It does not use the network.
- It does not use secrets.

### OnlyBoosts Top Songs
- Python 3.13 or newer. It uses only the standard library.
- It reads from the network:
  - `https://onlyboosts.social/api/v1/episodes` (the chart)
  - `https://www.boostmebitch.com/api/episode-by-guid/batch` (finds the songs)
- It does not use secrets.
- **Do not** submit these two playlists to Podcast Index. **Do not** send a podping for them. This is a decision, not an error.

### Homegrown Hits Hitsgiving
- Python 3.12 or newer. It uses only the standard library.
- It reads from the network:
  - `https://feed.homegrownhits.xyz/feed.xml` (the episode's songs)
  - `https://www.boostmebitch.com/api/episode-by-guid/batch` (checks that each song is in Podcast Index)
- It does not use secrets. It does not submit the playlists to Podcast Index.
- No workflow runs it, because an episode does not change after it is out. To add a year, see the docstring of the script.

### Commit and push
Both jobs commit only when the output file changed. Then they push to `main`. If the push fails because `main` moved, they do `git pull --rebase origin main` and try again (5 times maximum). On GitHub, the job uses the token that GitHub supplies automatically (`GITHUB_TOKEN`). It does not use a repository secret.

## Hosting: the feed URLs

Podcast apps and Podcast Index get the feeds from **raw.githubusercontent.com**, not from GitHub Pages. For example:

```
https://raw.githubusercontent.com/ChadFarrow/chadf-musicl-playlists/refs/heads/main/docs/HGH-music-playlist.xml
https://raw.githubusercontent.com/ChadFarrow/chadf-musicl-playlists/main/docs/...
```

Both URL forms are in use. Also, the playlist XML files use these URLs for cover art.

**Important:** Each of these changes breaks every feed URL:
- You rename the repo.
- You rename the `main` branch.
- You make the repo private.
- You move the files out of `docs/`.

You can move the *jobs* off GitHub and keep the feed URLs the same, because the jobs push the output back to this repo. If you move the *hosting*, you must change the URLs in the XML files and in Podcast Index, and the podcast apps must get the new URLs.

The README also tells how to set up GitHub Pages from `main` / `docs`. Pages does not serve the feed URLs above.

## Run the jobs locally

These steps are for a Linux server, for example your Ubuntu server.

### 1. Get the repo and a token
```bash
git clone https://github.com/ChadFarrow/chadf-musicl-playlists.git
```
To push, the server needs git credentials. Make a fine-grained personal access token with **Contents: Read and write** on this repo. Store it in a git credential helper, or use an SSH deploy key with write access.

### 2. Run one job
```bash
cd chadf-musicl-playlists
git pull --rebase origin main

python3 generate_greatest_hits.py
# or
python3 generate_onlyboosts_top_songs.py

git add docs/
git diff --cached --quiet || git commit -m "Auto-update playlists"
git push
```

### 3. Run all jobs in the correct order
The daily updater writes through the GitHub API, not through this local clone. Thus, pull after it finishes:

```bash
# 1. Daily updater (see RUNNING.md in musicL-playlist-updater)
(cd ../musicL-playlist-updater && node scripts/daily-update.js)

# 2. Greatest Hits, from the new playlists
git pull --rebase origin main
python3 generate_greatest_hits.py
git add docs/Greatest-Hits-music-playlist.xml
git diff --cached --quiet || git commit -m "Auto-update Greatest Hits playlist"
git push
```

Use a systemd timer or cron for the schedule:
- Daily updater + Greatest Hits: every day at 07:00 UTC
- OnlyBoosts Top Songs: Mondays at 05:00 UTC

If you run the jobs locally, disable the `schedule:` triggers in the workflow files. If you do not, GitHub and your server push the same changes, and you get conflicts.

## Security note

The OnlyBoosts workflow runs on pull requests. This repo is public. **Do not** run these workflows on a self-hosted GitHub runner: a pull request from a fork can then run code on your server. Use a timer or cron to run the jobs locally, as above.
