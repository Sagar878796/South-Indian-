
import json
import re
import urllib.request
from pathlib import Path

M3U_URL = "https://raw.githubusercontent.com/Sagar878796/my-m3u-playlist/refs/heads/main/Combined.m3u"
OUTPUT_FILE = "playlist.json"


def fetch_playlist():
    req = urllib.request.Request(
        M3U_URL,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        return response.read().decode("utf-8-sig", errors="replace")


def parse_attributes(line):
    attrs = {}
    pattern = r'([\w-]+)="([^"]*)"'
    for key, value in re.findall(pattern, line):
        attrs[key.lower()] = value
    return attrs


def convert_m3u(content):
    channels = []
    current = None

    for raw_line in content.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        if line.startswith("#EXTINF:"):
            if current and current.get("url"):
                channels.append(current)

            info, _, name = line.partition(",")

            attrs = parse_attributes(info)

            current = {
                "name": name.strip(),
                "category": attrs.get("group-title", "Uncategorized"),
                "logo": attrs.get("tvg-logo", ""),
                "tvg_id": attrs.get("tvg-id", ""),
                "url": "",
                "type": "",
                "mpd_url": "",
                "clearkey": None
            }

        elif line.startswith("#KODIPROP:") and current:
            prop = line[len("#KODIPROP:"):]

            if "=" in prop:
                key, value = prop.split("=", 1)
                key = key.strip().lower()
                value = value.strip()

                if key.endswith("license_type"):
                    if value.lower() == "clearkey":
                        current["_drm_type"] = "clearkey"

                elif key.endswith("license_key"):
                    # Kodi format: keyId:key
                    if ":" in value:
                        key_id, drm_key = value.split(":", 1)

                        current["clearkey"] = {
                            "keyId": key_id.strip(),
                            "key": drm_key.strip()
                        }

        elif not line.startswith("#") and current:
            current["url"] = line

            if ".mpd" in line.lower():
                current["type"] = "mpd"
                current["mpd_url"] = line
            elif ".m3u8" in line.lower():
                current["type"] = "hls"
            else:
                current["type"] = "unknown"

    if current and current.get("url"):
        channels.append(current)

    for channel in channels:
        channel.pop("_drm_type", None)

    return {
        "name": "SDTV LIVE",
        "total": len(channels),
        "channels": channels
    }


def main():
    print("Downloading M3U playlist...")
    content = fetch_playlist()

    print("Converting M3U to JSON...")
    data = convert_m3u(content)

    Path(OUTPUT_FILE).write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    drm_count = sum(
        1 for ch in data["channels"] if ch["clearkey"]
    )

    print("Total channels:", data["total"])
    print("Channels with ClearKey metadata:", drm_count)
    print("JSON saved:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
