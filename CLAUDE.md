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

2. **Publisher Feed** (`chadf-musicl-publisher.xml`, guid `a778e463-ecc3-5219-8f05-f33b3983e173`)
   - Aggregates all individual playlists using `<podcast:medium>publisher</podcast:medium>`
   - Uses `<podcast:remoteItem medium="musicL">` tags to reference each playlist feed by its `feedGuid`, `feedUrl` and `feedImg`
   - Serves as a single discovery point for all ChadF musicL playlists
   - Lists every musicL feed in `docs/` except the two OnlyBoosts Top Songs chart playlists (they stay out of Podcast Index by decision). The podcastL playlists are not listed. `OBSH-music-playlist` (The OnlyBoosts Social Hour, a show that `musicL-playlist-updater` builds like TFT) is not a chart playlist, so it is listed. The Homegrown Hits Hitsgiving playlists are listed too, right after HGH.
   - Also lists ChadF's playlists made on Boost Me Buddy (`https://www.boostmebuddy.com/feeds/playlists/<id>.xml`). Those are listed **one way**: a feed names only one publisher, and each BMB playlist names its BMB publisher feed (`/feeds/publishers/<npub>.xml`, boostmebitch #586). Add a new BMB playlist here by hand: its `feedGuid` is the `<podcast:guid>` in its feed.
   - **The link goes both ways.** Each listed playlist carries a `<podcast:publisher>` block with one `<podcast:remoteItem medium="publisher" rel="curator">` that points back here (the [publisher spec](https://github.com/Podcastindex-org/podcast-namespace/blob/main/docs/examples/publishers/publishers.md): an app discards a one-way link). The block sits right before `<podcast:medium>`. `generate_greatest_hits.py` and `generate_hgh_hitsgiving.py` write it, and `musicL-playlist-updater` writes it for the playlists it rebuilds. The back-link has no `itemGuid`, so the track readers skip it.
   - **`rel="curator"` on both sides** (each entry here and each back-link; podcast-namespace PR #793). musicindex.org counts a role only when both sides give the same set, and with no agreed role it calls a publisher an artist when the playlists' author matches its name. `curator` is not one of the PR's starting tokens yet; it is proposed there.
   - Must use the `https://podcastindex.org/namespace/1.0` namespace. The old GitHub namespace URL made a namespace-aware parser see no medium, no guid and no children.

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
- A row becomes a track when Podcast Index holds it, its feed confirms both guids, and its audio file answers. On a clear failure (HTTP 404 or 410, no such item in a feed that was read, a "no" from Podcast Index) the next row on the chart takes its place, so the all-time list can reach below rank 100. A song returns by itself when it passes again.
- **No answer is not a failure.** A timeout, HTTP 403, 429 or 5xx proves nothing about the song, so the row stays and the log marks it `KEPT`. Hosts time out for the GitHub runner while they answer elsewhere, and one such run would otherwise drop real songs for a week. A feed host that stays silent is not asked again in that run.
- The Podcast Index question goes through `POST https://www.boostmebitch.com/api/episode-by-guid/batch`, so no key is needed. If that route changes, the run fails and writes nothing.
- A run updates both files or neither. More than 20 skipped rows or more than 20 `KEPT` rows on a chart, too few tracks (`min_tracks`), or a failed chart or lookup request stops the run and writes nothing, so an outage cannot empty a list.
- Each run replaces the whole list, because a chart must be able to drop a song. The dates move only when the list moved.
- Keep the file names free of `-music-playlist`, and do not add a `source-feed` tag. The script's docstring gives the reasons.

### Homegrown Hits Hitsgiving Playlists

`docs/HGH-hitsgiving-<year>-playlist.xml` holds the songs of one Hitsgiving episode of Homegrown Hits (the show's Thanksgiving special), in play order. 2024 is Episode 62 and 2025 is Episode 112. They are supplements to `HGH-music-playlist.xml`, which keeps the songs of every episode (Chad, 2026-11-26). Episode 11 (2023) was a Thanksgiving show, not a Hitsgiving, and Chad left it out.

- `generate_hgh_hitsgiving.py` builds them from the episode's `valueTimeSplit` remoteItems in the HGH feed. It runs by hand only, with no workflow. To add a year, add a line to `EPISODES`, then follow the docstring.
- Each song must resolve in Podcast Index (through the boostmebitch batch route), or the run writes nothing. A song whose audio is gone stays in, as the episode played it (Chad, 2026-11-26: "put the dead songs in"). 5 songs hosted on RSS Blue answer HTTP 410, and their feeds too.
- The art is a still frame of the episode's own animated GIF (Chad asked for the episode art). The GIFs are 18 to 19 MB, too large to use as is.
- Keep the file names free of `-music-playlist`, `-muic-playlist` and `-musicl-`, and do not add a `source-feed` tag. With either, the updater's daily run takes the file for a show playlist and rebuilds it from the whole HGH feed. Greatest Hits does not count them: their songs are already in the HGH playlist.
- They are in the publisher feed, with the back-link. Chad had them submitted to Podcast Index (`add/byfeedurl`, 2026-11-26). The script itself never submits; a new year is submitted by hand, after Chad says yes, because Podcast Index has no delete.

## Common Tasks

Since this is a static repository, there are no build or test commands. Common operations:

1. **Add a new playlist**: Create a new XML file in `docs/` following the musicL format. Add it to the publisher feed, and add the `<podcast:publisher>` back-link to the playlist. Do both, or apps ignore the link.
2. **Update playlist tracks**: Edit the XML file to add/remove `<podcast:remoteItem>` entries
3. **Update artwork**: Add `.webp` or `.png` files to `docs/` and reference them in the feed's `<image>` tag
4. **Regenerate Greatest Hits**: Run `python3 generate_greatest_hits.py` (or wait for automatic workflow)
5. **View locally**: Open `docs/index.html` in a browser or serve with any static server (e.g., `python3 -m http.server`)

## Notes

- The `.cursorrules` file references an unrelated tech stack (React, Vite, Firebase, etc.) - these are **NOT** used in this repository and can be ignored
- `PORT_HANDLING.md` contains documentation for an unrelated volo-app project - this is legacy and not relevant to the musicL playlists
