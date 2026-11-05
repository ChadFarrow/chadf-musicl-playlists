# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

This is a **static hosting repository** for MusicL playlists. It contains no application code - only XML playlist feeds, one static OPML list, artwork files, and documentation served via GitHub Pages.

## Architecture

### Playlist Structure

All playlists use the **Podcasting 2.0 namespace** with `<podcast:medium>musicL</podcast:medium>` to identify them as music playlists (not traditional podcasts).

The repository contains two types of feeds:

1. **Individual Playlist Feeds** (10 playlists in `docs/` directory)
   - Each playlist XML file references music tracks using `<podcast:remoteItem>` tags
   - Remote items reference tracks from other podcasts via their `feedGuid` and `itemGuid`
   - Tracks are organized into episodes using `<podcast:txt purpose="episode">` markers
   - Example playlists: Lightning Thrashes (LT), Homegrown Hits (HGH), Into The Doerfel-Verse (ITDV), etc.

2. **Publisher Feed** (`chadf-musicl-publisher.xml`)
   - Aggregates all individual playlists using `<podcast:medium>publisher</podcast:medium>`
   - Uses `<podcast:remoteItem>` tags to reference each playlist feed by its `feedGuid` and `feedUrl`
   - Serves as a single discovery point for all ChadF musicL playlists

### File Organization

```
docs/
├── *.xml                    # Playlist RSS feeds (musicL format)
├── *.webp, *.png           # Playlist artwork
├── index.html              # Landing page
├── chadf-musicl-publisher.xml  # Publisher aggregation feed
├── small-group-scoop-shows.opml  # Static list of the Small Group Scoop shows; nothing updates it
└── PORT_HANDLING.md        # Unrelated volo-app documentation (legacy)
```

## Important Technical Details

### Remote Item References

MusicL playlists reference tracks from external podcast feeds using the `<podcast:remoteItem>` tag:

```xml
<podcast:remoteItem feedGuid="abc123..." itemGuid="xyz789..."/>
```

- **feedGuid**: Unique identifier for the source podcast feed
- **itemGuid**: Unique identifier for the specific track/episode within that feed

### Feed Headers

Each playlist feed must include:
- `<podcast:medium>musicL</podcast:medium>` - Identifies this as a music playlist
- `<podcast:guid>` - Unique identifier for the playlist
- `<podcast:txt purpose="source-feed">` - Link to the original/source RSS feed (when applicable)
- Standard RSS metadata: title, description, image, author, etc.

### GitHub Pages Deployment

The repository is configured to serve the `docs/` folder via GitHub Pages:
- Settings → Pages → Build from branch → `main` / `docs`
- All XML feeds and assets are publicly accessible via raw.githubusercontent.com URLs

## References

- **Podcast Namespace Spec**: https://github.com/Podcastindex-org/podcast-namespace/blob/main/docs/tags/medium.md
- **Medium Types List**: https://github.com/Podcastindex-org/podcast-namespace/blob/main/docs/tags/medium.md#list-mediums
- **Podcasting 2.0**: https://podcasting2.org/
- **Podcastindex Organization**: https://github.com/Podcastindex-org
- **Podverse**: https://github.com/podverse

## Automation

### Greatest Hits Playlist

The **Greatest Hits** playlist is automatically regenerated via GitHub Actions workflow.

**How It Works**:
- The playlist is computed/aggregated from all 10 individual playlists
- Script `generate_greatest_hits.py` analyzes all `docs/*-music-playlist.xml` files
- Tracks are ranked by play count across all playlists (minimum 2 plays to be included)
- Output: `docs/Greatest-Hits-music-playlist.xml`
- Artwork: `docs/Greatest-Hits-music-playlist.png`
- Source feed points to this GitHub repository

**Update Triggers**:
1. **Automatic (Push)**: Runs when any individual playlist is updated in `docs/*-music-playlist.xml`
2. **Weekly Fallback**: Every Sunday at 3 AM UTC (catches missed updates)
3. **Manual**: Via GitHub Actions UI → "Update Greatest Hits Playlist" → Run workflow

**Workflow Location**: `.github/workflows/update-greatest-hits.yml`

**What Happens**:
- Regenerates the playlist using Python script
- Only commits if `Greatest-Hits-music-playlist.xml` actually changed
- Uses github-actions bot identity for commits
- Commit message: "Auto-update Greatest Hits playlist - Recomputed from latest playlists"

### OnlyBoosts Top Songs Playlists

Two playlists come from the charts at https://onlyboosts.social/music/songs:

- `docs/onlyboosts-top-songs-playlist.xml`: the top 100 songs of all time (`range=all`).
- `docs/onlyboosts-top-songs-month-playlist.xml`: up to 100 songs of the last 30 days (`range=1m`). The window trails, so it is not the calendar month. It held 93 songs on 2026-11-05, and 88 of them had one booster, so it is often the whole chart.

`.github/workflows/update-onlyboosts-top-songs.yml` rebuilds both every Monday at 05:00 UTC with `generate_onlyboosts_top_songs.py`, and commits only when a list changed. A pull request that changes the script or the workflow runs the whole build and pushes nothing. `PLAYLISTS` in the script names each list.

- **These playlists are not submitted to Podcast Index. That is Chad's decision (2026-11-04).** Do not call `add/byfeedurl` or `pubnotify` for them, do not send a Podping, and do not move them into the updater's daily run, which does both. So boostmebitch shows them as "NOT IN PI · PREVIEW".
- The data is `GET https://onlyboosts.social/api/v1/episodes?medium=music&sort=chart&range=<range>`, the call that page makes. A row's `show.guid` is the `feedGuid` and its `guid` is the `itemGuid`. The site's source is https://github.com/ReedBTC/onlyboosts.
- A row becomes a track only when Podcast Index holds it, its feed confirms both guids, and its audio file answers. Otherwise the next row on the chart takes its place, so the all-time list can reach below rank 100. A song returns by itself when it passes again.
- The Podcast Index question goes through `POST https://www.boostmebitch.com/api/episode-by-guid/batch`, so no key is needed. If that route changes, the run fails and writes nothing.
- A run updates both files or neither. More than 20 failed rows on a chart, too few tracks (`min_tracks`), or a failed chart or lookup request stops the run and writes nothing, so an outage cannot empty a list.
- Each run replaces the whole list, because a chart must be able to drop a song. The dates move only when the list moved.
- Keep the file names free of `-music-playlist`, and do not add a `source-feed` tag. The script's docstring gives the reasons.

## Common Tasks

Since this is a static repository, there are no build or test commands. Common operations:

1. **Add a new playlist**: Create a new XML file in `docs/` following the musicL format, then add it to the publisher feed
2. **Update playlist tracks**: Edit the XML file to add/remove `<podcast:remoteItem>` entries
3. **Update artwork**: Add `.webp` or `.png` files to `docs/` and reference them in the feed's `<image>` tag
4. **Regenerate Greatest Hits**: Run `python3 generate_greatest_hits.py` (or wait for automatic workflow)
5. **View locally**: Open `docs/index.html` in a browser or serve with any static server (e.g., `python3 -m http.server`)

## Notes

- The `.cursorrules` file references an unrelated tech stack (React, Vite, Firebase, etc.) - these are **NOT** used in this repository and can be ignored
- `PORT_HANDLING.md` contains documentation for an unrelated volo-app project - this is legacy and not relevant to the musicL playlists
