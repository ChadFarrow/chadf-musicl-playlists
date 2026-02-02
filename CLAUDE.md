# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

This is a **static hosting repository** for MusicL playlists. It contains no application code - only XML playlist feeds, artwork files, and documentation served via GitHub Pages.

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

## Common Tasks

Since this is a static repository, there are no build or test commands. Common operations:

1. **Add a new playlist**: Create a new XML file in `docs/` following the musicL format, then add it to the publisher feed
2. **Update playlist tracks**: Edit the XML file to add/remove `<podcast:remoteItem>` entries
3. **Update artwork**: Add `.webp` or `.png` files to `docs/` and reference them in the feed's `<image>` tag
4. **View locally**: Open `docs/index.html` in a browser or serve with any static server (e.g., `python3 -m http.server`)

## Notes

- The `.cursorrules` file references an unrelated tech stack (React, Vite, Firebase, etc.) - these are **NOT** used in this repository and can be ignored
- `PORT_HANDLING.md` contains documentation for an unrelated volo-app project - this is legacy and not relevant to the musicL playlists
