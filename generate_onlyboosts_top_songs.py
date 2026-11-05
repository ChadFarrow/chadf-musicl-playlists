#!/usr/bin/env python3
"""
Generate the OnlyBoosts Top Songs musicL playlist.

Reads the all-time chart at https://onlyboosts.social/music/songs through the API
that page calls, and writes the top songs in chart order. A chart row becomes a
track only after the song's own feed and audio file have been checked, because the
chart ranks boosts, and a boost outlives the song it paid for: on the first run the
#4 song's feed and audio both answered HTTP 410, and #14 was a live event that ended.
A failed row is skipped and the next row on the chart takes its place.

The whole list is replaced on every run. A chart has to be able to drop a song, so
this does not merge with the published file the way the updater's aggregators do.

The file is deliberately NOT named *-music-playlist.xml. That name would start the
Greatest Hits workflow, and FEEDS.md entries with it are taken by the updater's RSS
loop, which would look for a source feed here that does not exist. For the same
reason it writes no <podcast:txt purpose="source-feed">: the chart is not a feed,
and boostmebitch downloads that tag's URL as the show a playlist was built from.

Usage: python3 generate_onlyboosts_top_songs.py
"""

import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from xml.sax.saxutils import escape, quoteattr

CHART_API = "https://onlyboosts.social/api/v1/episodes"
CHART_PAGE = "https://onlyboosts.social/music/songs"
RAW_DOCS = "https://raw.githubusercontent.com/ChadFarrow/chadf-musicl-playlists/refs/heads/main/docs"

OUTPUT_FILE = "docs/onlyboosts-top-songs-playlist.xml"
FEED_URL = f"{RAW_DOCS}/onlyboosts-top-songs-playlist.xml"
IMAGE_URL = f"{RAW_DOCS}/onlyboosts-top-songs-playlist-art.png"

TRACKS = 100
PAGE_SIZE = 100
# More failures than this is an outage, not dead songs. Leave the published file alone.
MAX_SKIPPED = 20

USER_AGENT = "Mozilla/5.0 (compatible; chadf-musicl-playlists; +https://github.com/ChadFarrow/chadf-musicl-playlists)"
TIMEOUT = 30
ATTEMPTS = 3
# wavlake.com answers HTTP 429 to six parallel requests, and most of its feeds are here.
HOST_GAP_SECONDS = 2.0
AUDIO_TYPES = re.compile(r"audio|octet-stream|mpeg|mp4|ogg|flac", re.I)
# The namespace the Podcast Namespace spec names for deriving a podcast:guid.
PODCAST_GUID_NAMESPACE = uuid.UUID("ead4c236-bf58-58c6-a2c6-a6b28d128cb6")
# Podcast Index does not hold these items, so an app that resolves a remoteItem by guid
# shows a blank row. Their feed and audio are fine, so no check below can see this. On
# 2026-11-04 its record of this feed held 26 episodes, last updated 2024-11-01, and the
# feed had 38 items. Delete an entry when Podcast Index holds the item again.
NOT_IN_PODCAST_INDEX = {
    "4a0a38f0-8492-4839-a2d6-d2692a87cb7e",  # Too Bit To Fail - Mouse Click Money (PlebRap)
    "2bf29869-c257-433e-8790-76ad6649dd38",  # Too Bit To Fail - Signale (PlebRap)
}
PRIVATE_HOST = re.compile(r"^(localhost$|127\.|10\.|192\.168\.|169\.254\.|172\.(1[6-9]|2\d|3[01])\.|\[)")

_last_hit = {}


class Skip(Exception):
    """This row cannot be a track. The message says why."""


def encode_url(url):
    """The URL with spaces and the like encoded, and existing %XX escapes kept."""
    return urllib.parse.quote(url, safe="%/:=&?~#+!$,;'@()*[]")


def _throttle(host):
    wait = _last_hit.get(host, 0) + HOST_GAP_SECONDS - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    _last_hit[host] = time.monotonic()


def http(url, method="GET", headers=None):
    """
    Returns (status, content_type, body). Retries HTTP 429, HTTP 5xx and network
    errors, then raises Skip. A definite refusal such as HTTP 410 raises Skip at once.
    """
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ("http", "https") or PRIVATE_HOST.match(parts.hostname or ""):
        raise Skip(f"refused address {url}")

    reason = "no attempt"
    for attempt in range(ATTEMPTS):
        _throttle(parts.hostname)
        req = urllib.request.Request(encode_url(url), method=method, headers={"User-Agent": USER_AGENT, **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
                return res.status, res.headers.get("Content-Type", ""), res.read()
        except urllib.error.HTTPError as e:
            reason = f"HTTP {e.code}"
            if e.code != 429 and e.code < 500:
                raise Skip(reason) from e
            time.sleep(min(int(e.headers.get("Retry-After") or 0) or 5 * (attempt + 1), 60))
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            reason = str(getattr(e, "reason", e))
            time.sleep(5 * (attempt + 1))
    raise Skip(reason)


def parse_feed(xml_text):
    """The feed's own podcast:guid (None when it has no tag) and its <item> guids."""
    head = re.split(r"<(?:item|podcast:liveItem)[\s>]", xml_text, maxsplit=1)[0]
    tag = re.search(r"<podcast:guid[^>]*>\s*([^<\s]+)\s*</podcast:guid>", head)
    guids = set()
    # <item> only: a <podcast:liveItem> has a guid too, but no song to play after it ends.
    for block in re.findall(r"<item[\s>].*?</item>", xml_text, re.S):
        match = re.search(r"<guid\b[^>]*>(.*?)</guid>", block, re.S)
        if match:
            value = re.sub(r"^\s*<!\[CDATA\[|\]\]>\s*$", "", match.group(1)).strip()
            guids.add(value.replace("&amp;", "&"))
    return (tag.group(1).strip() if tag else None), guids


def check_guids(row, feeds):
    feed_url = row["show"].get("feed")
    if not feed_url:
        raise Skip("no feed address")
    if feed_url not in feeds:
        try:
            feeds[feed_url] = parse_feed(http(feed_url)[2].decode("utf-8", "replace"))
        except Skip as e:
            feeds[feed_url] = e
    if isinstance(feeds[feed_url], Skip):
        raise Skip(f"feed {feeds[feed_url]}")

    feed_guid, item_guids = feeds[feed_url]
    # No tag is allowed. Podcast Index then holds the guid: PINK FLIGHT by ECHO REALITY
    # has none, and Podcast Index resolves its tracks by the guid the chart gives.
    if feed_guid and feed_guid.lower() != row["show"]["guid"].lower():
        raise Skip(f"feed says podcast:guid {feed_guid}, chart says {row['show']['guid']}")
    if row["guid"] not in item_guids:
        raise Skip("no <item> in the feed has this guid")


def check_audio(row):
    url = row.get("url")
    if not url:
        raise Skip("no audio address")
    try:
        status, content_type, _ = http(url, method="HEAD")
    except Skip:
        # Some hosts refuse HEAD. One byte shows the same thing.
        try:
            status, content_type, _ = http(url, headers={"Range": "bytes=0-0"})
        except Skip as e:
            raise Skip(f"audio {e}") from e
    if status == 204:
        raise Skip("audio address returns no content")
    if not AUDIO_TYPES.search(content_type):
        raise Skip(f"audio address returns {content_type or 'no content type'}")


def collect_tracks():
    """The top TRACKS playable rows in chart order, and the rows that were skipped."""
    tracks, skipped, seen, feeds = [], [], set(), {}
    offset = 0
    while offset is not None and len(tracks) < TRACKS:
        query = urllib.parse.urlencode({"medium": "music", "sort": "chart", "range": "all", "limit": PAGE_SIZE, "offset": offset})
        try:
            page = json.loads(http(f"{CHART_API}?{query}")[2])
        except Skip as e:
            sys.exit(f"Chart API failed ({e}). Nothing written.")
        for row in page.get("episodes", []):
            if len(tracks) == TRACKS:
                break
            label = f"#{row.get('rank')} {row.get('title')} - {row.get('show', {}).get('author')}"
            try:
                if not row.get("guid") or not row.get("show", {}).get("guid"):
                    raise Skip("no guid")
                key = (row["show"]["guid"], row["guid"])
                if key in seen:
                    raise Skip("already listed")
                seen.add(key)
                if row["guid"] in NOT_IN_PODCAST_INDEX:
                    raise Skip("Podcast Index does not hold this item")
                check_guids(row, feeds)
                check_audio(row)
                tracks.append(row)
                print(f"  ok    {label}", flush=True)
            except Skip as e:
                skipped.append((label, str(e)))
                print(f"  SKIP  {label}: {e}", flush=True)
                if len(skipped) > MAX_SKIPPED:
                    sys.exit(f"More than {MAX_SKIPPED} rows failed, which looks like an outage. Nothing written.")
        offset = page.get("next_offset")
    if len(tracks) < TRACKS:
        sys.exit(f"Only {len(tracks)} of {TRACKS} tracks found. Nothing written.")
    return tracks, skipped


def comment_text(text):
    """Text that is safe inside an XML comment, which cannot hold '--'."""
    text = re.sub(r"[^\x09\x0a\x0d\x20-퟿-�\U00010000-\U0010ffff]", "", str(text))
    return re.sub(r"-{2,}", "-", text).strip("- ")


def build_xml(tracks, stamp):
    # A permanent identity: the spec's UUIDv5 of the feed URL without its scheme.
    guid = uuid.uuid5(PODCAST_GUID_NAMESPACE, FEED_URL.split("://", 1)[1])
    lines = [
        '<rss version="2.0" xmlns:podcast="https://podcastindex.org/namespace/1.0">',
        "  <channel>",
        "    <author>ChadF</author>",
        f"    <title>Top {len(tracks)} Songs on OnlyBoosts</title>",
        "    <description>The top songs on the OnlyBoosts all-time chart, ranked by the sats, boosts and "
        "boosters they received on Nostr. Songs that can no longer play are left out. "
        "Built by ChadF from the public chart, not made by OnlyBoosts.</description>",
        f"    <link>{escape(CHART_PAGE)}</link>",
        "    <language>en</language>",
        f"    <pubDate>{stamp}</pubDate>",
        f"    <lastBuildDate>{stamp}</lastBuildDate>",
        "    <image>",
        f"      <url>{escape(IMAGE_URL)}</url>",
        "    </image>",
        "    <podcast:medium>musicL</podcast:medium>",
        f"    <podcast:guid>{guid}</podcast:guid>",
    ]
    for row in tracks:
        show = row["show"]
        label = "{}. {} - {}".format(row.get("rank"), row.get("title"), show.get("author"))
        lines.append(f"    <!-- {comment_text(label)} -->")
        lines.append(
            f"    <podcast:remoteItem feedGuid={quoteattr(show['guid'])} "
            f"feedUrl={quoteattr(encode_url(show['feed']))} itemGuid={quoteattr(row['guid'])}/>"
        )
    lines += ["  </channel>", "</rss>", ""]
    return "\n".join(lines)


def without_dates(xml_text):
    return re.sub(r"<(pubDate|lastBuildDate)>[^<]*</\1>", r"<\1></\1>", xml_text)


def write_if_changed(new_xml):
    """A rebuild is not a change: the dates move only when the list moved."""
    try:
        with open(OUTPUT_FILE, encoding="utf-8") as f:
            if without_dates(f.read()) == without_dates(new_xml):
                print(f"\nUnchanged: {OUTPUT_FILE}")
                return
    except OSError:
        pass
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(new_xml)
    print(f"\nGenerated: {OUTPUT_FILE}")


def main():
    print(f"Checking the chart at {CHART_PAGE}")
    tracks, skipped = collect_tracks()
    stamp = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    write_if_changed(build_xml(tracks, stamp))
    print(f"{len(tracks)} tracks, down to chart rank {tracks[-1].get('rank')}. {len(skipped)} rows skipped:")
    for label, reason in skipped:
        print(f"  {label}: {reason}")


if __name__ == "__main__":
    main()
