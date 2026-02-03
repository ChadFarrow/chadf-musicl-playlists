#!/usr/bin/env python3
"""
Generate Greatest Hits MusicL Playlist

Analyzes all individual musicL playlists and creates a data-driven "Greatest Hits"
playlist featuring songs that appear 2+ times across playlists, organized by play count.
"""

import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
import uuid
import os

# Namespace for Podcasting 2.0
PODCAST_NS = "{https://podcastindex.org/namespace/1.0}"

# Individual playlist files to analyze
PLAYLIST_FILES = [
    "b4ts-music-playlist.xml",
    "flowgnar-music-playlist.xml",
    "HGH-music-playlist.xml",
    "IAM-music-playlist.xml",
    "ITDV-music-playlist.xml",
    "LT-music-playlist.xml",
    "MMM-music-playlist.xml",
    "MMT-muic-playlist.xml",
    "SAS-music-playlist.xml",
    "upbeats-music-playlist.xml"
]

OUTPUT_FILE = "docs/Greatest-Hits-music-playlist.xml"


def parse_playlist(filepath):
    """
    Parse a musicL playlist XML file and extract all remote items.

    Returns:
        List of (feedGuid, itemGuid) tuples
    """
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()

        # Find all podcast:remoteItem elements
        remote_items = []
        for item in root.iter(f"{PODCAST_NS}remoteItem"):
            feed_guid = item.get("feedGuid")
            item_guid = item.get("itemGuid")

            if feed_guid and item_guid:
                remote_items.append((feed_guid, item_guid))

        return remote_items
    except Exception as e:
        print(f"  ✗ Error parsing {filepath}: {e}")
        return []


def collect_all_songs(playlist_files):
    """
    Parse all playlist files and count song frequencies.

    Returns:
        Counter object with (feedGuid, itemGuid) tuples as keys
    """
    print(f"Processing {len(playlist_files)} musicL playlists...\n")

    all_songs = []

    for filename in playlist_files:
        filepath = os.path.join("docs", filename)

        if not os.path.exists(filepath):
            print(f"  ✗ {filename}: File not found")
            continue

        songs = parse_playlist(filepath)
        all_songs.extend(songs)
        print(f"  ✓ {filename}: {len(songs)} songs")

    return Counter(all_songs)


def filter_and_group_by_frequency(song_counts, min_frequency=2):
    """
    Filter songs by minimum frequency and group by exact play count.

    Returns:
        Dictionary mapping play count to list of (feedGuid, itemGuid) tuples
        Sorted in descending order by play count
    """
    # Filter to songs with min_frequency or more plays
    filtered_songs = {song: count for song, count in song_counts.items()
                     if count >= min_frequency}

    # Group by frequency
    frequency_groups = {}
    for song, count in filtered_songs.items():
        if count not in frequency_groups:
            frequency_groups[count] = []
        frequency_groups[count].append(song)

    # Sort songs within each group alphabetically by feedGuid+itemGuid
    for count in frequency_groups:
        frequency_groups[count].sort(key=lambda x: (x[0], x[1]))

    return frequency_groups


def generate_xml(frequency_groups, output_file):
    """
    Generate the Greatest Hits XML feed.
    """
    # Register namespace prefix to use 'podcast:' instead of 'ns0:'
    ET.register_namespace('podcast', 'https://podcastindex.org/namespace/1.0')

    # Create RSS root element
    rss = ET.Element("rss", version="2.0")
    rss.set("xmlns:podcast", "https://podcastindex.org/namespace/1.0")

    channel = ET.SubElement(rss, "channel")

    # Channel metadata
    ET.SubElement(channel, "author").text = "ChadF"
    ET.SubElement(channel, "title").text = "ChadF's Greatest Hits Music Playlist"
    ET.SubElement(channel, "description").text = (
        "Most frequently played tracks across all ChadF musicL playlists - "
        "songs appearing 2+ times, organized by play count"
    )
    ET.SubElement(channel, "link").text = "https://github.com/ChadFarrow/chadf-musicl-playlists"

    # Source feed reference
    source_feed = ET.SubElement(channel, f"{PODCAST_NS}txt")
    source_feed.set("purpose", "source-feed")
    source_feed.text = "https://github.com/ChadFarrow/chadf-musicl-playlists"

    ET.SubElement(channel, "language").text = "en"

    # RFC 2822 formatted dates
    now = datetime.now(timezone.utc)
    rfc2822_date = now.strftime("%a, %d %b %Y %H:%M:%S +0000")
    ET.SubElement(channel, "pubDate").text = rfc2822_date
    ET.SubElement(channel, "lastBuildDate").text = rfc2822_date

    # Image
    image = ET.SubElement(channel, "image")
    ET.SubElement(image, "url").text = (
        "https://raw.githubusercontent.com/ChadFarrow/chadf-musicl-playlists/"
        "main/docs/Greatest-Hits-music-playlist.png"
    )

    # Podcast namespace tags
    ET.SubElement(channel, f"{PODCAST_NS}medium").text = "musicL"

    playlist_guid = ET.SubElement(channel, f"{PODCAST_NS}guid")
    playlist_guid.text = str(uuid.uuid4())

    # Add episodes organized by play count (descending)
    sorted_frequencies = sorted(frequency_groups.keys(), reverse=True)

    for frequency in sorted_frequencies:
        # Play count marker
        episode_txt = ET.SubElement(channel, f"{PODCAST_NS}txt")
        episode_txt.set("purpose", "playcount")
        episode_txt.text = f"{frequency} plays"

        # Add all songs with this frequency
        for feed_guid, item_guid in frequency_groups[frequency]:
            remote_item = ET.SubElement(channel, f"{PODCAST_NS}remoteItem")
            remote_item.set("feedGuid", feed_guid)
            remote_item.set("itemGuid", item_guid)

    # Write to file with pretty formatting
    tree = ET.ElementTree(rss)
    ET.indent(tree, space="  ")

    with open(output_file, "wb") as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
        tree.write(f, encoding="UTF-8", xml_declaration=False)

    print(f"\nGenerated: {output_file}")


def print_statistics(song_counts, frequency_groups):
    """
    Print analysis statistics.
    """
    total_references = sum(song_counts.values())
    unique_songs = len(song_counts)
    filtered_songs = sum(len(songs) for songs in frequency_groups.values())

    print(f"\nTotal song references: {total_references:,}")
    print(f"Unique songs: {unique_songs:,}")
    print(f"Songs with 2+ plays: {filtered_songs:,}")

    if frequency_groups:
        max_freq = max(frequency_groups.keys())
        min_freq = min(frequency_groups.keys())
        print(f"Frequency range: {min_freq}-{max_freq} plays")

        print("\nFrequency Distribution:")

        # 10+ plays
        high_freq = sum(len(songs) for freq, songs in frequency_groups.items() if freq >= 10)
        if high_freq > 0:
            print(f"  10+ plays: {high_freq} songs")

        # 5-9 plays
        mid_high = sum(len(songs) for freq, songs in frequency_groups.items() if 5 <= freq <= 9)
        if mid_high > 0:
            print(f"  5-9 plays: {mid_high} songs")

        # 3-4 plays
        mid_low = sum(len(songs) for freq, songs in frequency_groups.items() if 3 <= freq <= 4)
        if mid_low > 0:
            print(f"  3-4 plays: {mid_low} songs")

        # 2 plays
        low_freq = frequency_groups.get(2, [])
        if low_freq:
            print(f"  2 plays: {len(low_freq)} songs")


def main():
    """
    Main execution function.
    """
    # Collect and count all songs
    song_counts = collect_all_songs(PLAYLIST_FILES)

    if not song_counts:
        print("\n✗ No songs found. Check that playlist files exist in docs/ directory.")
        return

    # Filter and group by frequency
    frequency_groups = filter_and_group_by_frequency(song_counts, min_frequency=2)

    # Print statistics
    print_statistics(song_counts, frequency_groups)

    # Generate XML output
    generate_xml(frequency_groups, OUTPUT_FILE)

    print("\n✓ Greatest Hits playlist generation complete!")


if __name__ == "__main__":
    main()
