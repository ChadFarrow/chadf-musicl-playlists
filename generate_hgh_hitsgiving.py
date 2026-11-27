#!/usr/bin/env python3
"""
Generate the Homegrown Hits Hitsgiving musicL playlists: one playlist per Hitsgiving episode.

Homegrown Hits (https://homegrownhits.xyz, feed https://feed.homegrownhits.xyz/feed.xml,
Podcast Index feed 6611624) plays a Thanksgiving special each year, "Hitsgiving", with the
show's most-played DeMu tracks. Each playlist here holds the songs of one such episode, in
play order. They are supplements to docs/HGH-music-playlist.xml, which keeps the songs of
every episode (Chad, 2026-11-26: "these are suplimental to the playlist for the music
shows"). Episode 11 (2023) was a Thanksgiving show, not a Hitsgiving; Chad left it out.

A song is a <podcast:valueTimeSplit> of the episode: its <podcast:remoteItem> gives the
feedGuid and itemGuid, and its startTime gives the order. A song played twice stays twice.
Every song must resolve in Podcast Index, because that is how apps find a remoteItem. The
script asks through the public boostmebitch route, as generate_onlyboosts_top_songs.py
does, so it needs no key. One song that does not resolve stops the run, and nothing is
written. The episode itself must be in the index too: its page there is the playlist's link.

A song whose audio is gone stays in the playlist, as the episode played it (Chad,
2026-11-26: "put the dead songs in"). On the first run, 5 songs hosted on RSS Blue answered
HTTP 410, and so did their feeds. The script does not check the audio.

The files are deliberately NOT named *-music-playlist.xml, and they have no
<podcast:txt purpose="source-feed">. With either one, the daily run of musicL-playlist-updater
would take the file for a show playlist (its FEEDS.md parse takes names with -music-playlist,
-muic-playlist or -musicl-, and it rebuilds each docs/ file that names a source feed). It
would then rebuild the file from every episode of the HGH feed. The name would also start the
Greatest Hits workflow. Greatest Hits does not count these playlists: their songs are already
in the HGH playlist, so they would count twice.

THIS SCRIPT DOES NOT SUBMIT THE PLAYLISTS TO PODCAST INDEX. It only reads the index.

The art of each playlist is a still frame of the episode's own animated GIF (its
<itunes:image>, 18 to 19 MB, too large to use as is). Chad asked for the episode art.
    ffmpeg -ss <seconds> -i episode-<n>.gif -frames:v 1 -q:v 2 docs/<name>-art.jpg

To add a Hitsgiving: when the episode is in the feed, add a line to EPISODES, make its art,
run the script, and list the file in docs/chadf-musicl-publisher.xml, FEEDS.md and
docs/index.html. Nothing runs this on a schedule: an episode does not change after it is out.

Usage: python3 generate_hgh_hitsgiving.py
"""

import json
import re
import sys
import urllib.error
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from xml.sax.saxutils import escape, quoteattr

HGH_FEED = "https://feed.homegrownhits.xyz/feed.xml"
HGH_FEED_GUID = "ac746d09-7c3b-5bcd-b28a-f12d6456ca8f"
RESOLVER_API = "https://www.boostmebitch.com/api/episode-by-guid/batch"
RAW_DOCS = "https://raw.githubusercontent.com/ChadFarrow/chadf-musicl-playlists/refs/heads/main/docs"
USER_AGENT = "Mozilla/5.0 (compatible; chadf-musicl-playlists; +https://github.com/ChadFarrow/chadf-musicl-playlists)"

# ChadF's publisher feed. It lists each playlist, and each playlist links back to it.
# Apps trust the link only when it goes both ways, with the same rel on both sides.
PUBLISHER_FEED_GUID = "a778e463-ecc3-5219-8f05-f33b3983e173"
PUBLISHER_FEED_URL = f"{RAW_DOCS}/chadf-musicl-publisher.xml"
PUBLISHER_REL = "curator"

# The namespace the Podcast Namespace spec names for deriving a podcast:guid.
PODCAST_GUID_NAMESPACE = uuid.UUID("ead4c236-bf58-58c6-a2c6-a6b28d128cb6")
# The HGH feed declares the old GitHub namespace URL. Accept it and the current one.
PODCAST_NAMESPACES = (
    "https://podcastindex.org/namespace/1.0",
    "https://github.com/Podcastindex-org/podcast-namespace/blob/main/docs/1.0.md",
)
RESOLVER_BATCH = 50


@dataclass(frozen=True)
class Episode:
    year: int
    number: int
    item_guid: str  # The episode's <guid> in the HGH feed.

    @property
    def name(self):
        return f"HGH-hitsgiving-{self.year}-playlist"

    @property
    def output_file(self):
        return f"docs/{self.name}.xml"

    @property
    def feed_url(self):
        return f"{RAW_DOCS}/{self.name}.xml"

    @property
    def image_url(self):
        return f"{RAW_DOCS}/{self.name}-art.jpg"

    @property
    def title(self):
        return f"Homegrown Hits - Hitsgiving {self.year} (Episode {self.number})"


EPISODES = [
    Episode(2024, 62, "099cd054-3165-4a15-975b-72afafdf31f6"),  # The first official Hitsgiving.
    Episode(2025, 112, "073d36d2-1309-49a9-a92a-838dc148d822"),
]


def fetch(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET",
                                 headers={"User-Agent": USER_AGENT, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read()
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        sys.exit(f"{url} failed ({e}). Nothing written.")


def podcast_tag(element, local):
    return element.tag in {f"{{{ns}}}{local}" for ns in PODCAST_NAMESPACES}


def read_episodes(feed_xml):
    """{item guid: (title, notes, [(feedGuid, itemGuid), ...] in play order)} for EPISODES."""
    try:
        channel = ET.fromstring(feed_xml).find("channel")
    except ET.ParseError as e:
        sys.exit(f"The HGH feed does not parse ({e}). Nothing written.")
    wanted = {e.item_guid for e in EPISODES}
    found = {}
    for item in channel.findall("item"):
        guid = (item.findtext("guid") or "").strip()
        if guid not in wanted:
            continue
        splits = []
        for split in item.iter():
            if not podcast_tag(split, "valueTimeSplit"):
                continue
            remote = next((c for c in split if podcast_tag(c, "remoteItem")), None)
            if remote is None or not remote.get("feedGuid") or not remote.get("itemGuid"):
                sys.exit(f"Episode {guid} has a valueTimeSplit with no full remoteItem. Nothing written.")
            splits.append((float(split.get("startTime", "0")), remote.get("feedGuid"), remote.get("itemGuid")))
        splits.sort(key=lambda s: s[0])
        # The first sentence of the notes: the text before the first HTML tag.
        notes = " ".join((item.findtext("description") or "").split("<", 1)[0].split())
        found[guid] = ((item.findtext("title") or "").strip(), notes, [(f, i) for _, f, i in splits])
    for episode in EPISODES:
        if episode.item_guid not in found:
            sys.exit(f"Episode {episode.number} ({episode.item_guid}) is not in the HGH feed. Nothing written.")
        if not found[episode.item_guid][2]:
            sys.exit(f"Episode {episode.number} has no valueTimeSplit songs. Nothing written.")
    return found


def podcast_index_answers(pairs):
    """{"feedGuid:itemGuid": record or None}. None means the index does not hold the item."""
    refs = [{"feedGuid": f, "itemGuid": i} for f, i in dict.fromkeys(pairs)]
    answers = {}
    for start in range(0, len(refs), RESOLVER_BATCH):
        body = json.dumps({"refs": refs[start:start + RESOLVER_BATCH]}).encode("utf-8")
        try:
            answers.update(json.loads(fetch(RESOLVER_API, data=body, headers={"Content-Type": "application/json"}))["episodes"])
        except (ValueError, KeyError, TypeError) as e:
            sys.exit(f"Podcast Index lookup failed ({e}). Nothing written.")
    return answers


def comment_text(text):
    """Text that is safe inside an XML comment, which cannot hold '--'."""
    text = re.sub(r"[^\x09\x0a\x0d\x20-퟿-�\U00010000-\U0010ffff]", "", str(text))
    return re.sub(r"-{2,}", "-", text).strip("- ")


def build_xml(episode, episode_title, notes, link, tracks, answers, stamp):
    # A permanent identity: the spec's UUIDv5 of the feed URL without its scheme.
    guid = uuid.uuid5(PODCAST_GUID_NAMESPACE, episode.feed_url.split("://", 1)[1])
    description = (
        f"Every song played in Homegrown Hits Episode {episode.number}, the Hitsgiving {episode.year} "
        f"special, in play order ({len(tracks)} tracks)."
        + (f' From the episode notes: "{notes}"' if notes else "")
        + " A supplement to the ChadF Homegrown Hits Music Playlist, which holds the songs of every episode."
        + f" Episode: {link}"
    )
    lines = [
        '<rss version="2.0" xmlns:podcast="https://podcastindex.org/namespace/1.0">',
        "  <channel>",
        "    <author>ChadF</author>",
        f"    <title>{escape(episode.title)}</title>",
        f"    <description>{escape(description)}</description>",
        f"    <link>{escape(link)}</link>",
        "    <language>en</language>",
        f"    <pubDate>{stamp}</pubDate>",
        f"    <lastBuildDate>{stamp}</lastBuildDate>",
        "    <image>",
        f"      <url>{escape(episode.image_url)}</url>",
        "    </image>",
        "    <podcast:publisher>",
        f'      <podcast:remoteItem medium="publisher" rel="{PUBLISHER_REL}" '
        f'feedGuid="{PUBLISHER_FEED_GUID}" feedUrl={quoteattr(PUBLISHER_FEED_URL)}/>',
        "    </podcast:publisher>",
        "    <podcast:medium>musicL</podcast:medium>",
        f"    <podcast:guid>{guid}</podcast:guid>",
        f'    <podcast:txt purpose="episode">{escape(episode_title)}</podcast:txt>',
    ]
    for number, (feed_guid, item_guid) in enumerate(tracks, 1):
        record = answers[f"{feed_guid}:{item_guid}"]
        label = "{}. {} ({})".format(number, record.get("title"), record.get("feedTitle"))
        lines.append(f"      <!-- {comment_text(label)} -->")
        lines.append(f"      <podcast:remoteItem feedGuid={quoteattr(feed_guid)} itemGuid={quoteattr(item_guid)}/>")
    lines += ["  </channel>", "</rss>", ""]
    return "\n".join(lines)


def without_dates(xml_text):
    return re.sub(r"<(pubDate|lastBuildDate)>[^<]*</\1>", r"<\1></\1>", xml_text)


def write_if_changed(output_file, new_xml):
    """A rebuild is not a change: the dates move only when the list moved."""
    try:
        with open(output_file, encoding="utf-8") as f:
            if without_dates(f.read()) == without_dates(new_xml):
                print(f"Unchanged: {output_file}")
                return
    except OSError:
        pass
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(new_xml)
    print(f"Generated: {output_file}")


def main():
    print(f"Reading {HGH_FEED}")
    found = read_episodes(fetch(HGH_FEED))
    pairs = [(HGH_FEED_GUID, e.item_guid) for e in EPISODES]
    for _, _, tracks in found.values():
        pairs += tracks
    answers = podcast_index_answers(pairs)
    failed = []
    for f, i in dict.fromkeys(pairs):
        if f"{f}:{i}" not in answers:
            sys.exit(f"Could not ask Podcast Index about {f} {i}. Nothing written.")
        if answers[f"{f}:{i}"] is None:
            failed.append(f"{f} {i}")
    if failed:
        sys.exit("Podcast Index does not hold:\n  " + "\n  ".join(failed) + "\nNothing written.")

    stamp = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    built = []
    for episode in EPISODES:
        episode_title, notes, tracks = found[episode.item_guid]
        record = answers[f"{HGH_FEED_GUID}:{episode.item_guid}"]
        link = f"https://podcastindex.org/podcast/{record['feedId']}?episode={record['id']}"
        xml_text = build_xml(episode, episode_title, notes, link, tracks, answers, stamp)
        built.append((episode, len(tracks), xml_text))
    for episode, count, xml_text in built:
        write_if_changed(episode.output_file, xml_text)
        print(f"  {episode.title}: {count} tracks, all in Podcast Index")


if __name__ == "__main__":
    main()
