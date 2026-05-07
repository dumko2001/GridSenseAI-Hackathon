"""
MOSDAC RSS Feed Monitor
Subscribes to ISRO satellite data feeds to get notified of new imagery availability.

Why RSS instead of API polling:
- Push-based: notified immediately when new data is available
- Standard protocol: works with any RSS reader
- No authentication needed for public feeds
- Government-friendly: ISRO official data source

Feeds available:
- INSAT3D-Imager: https://mosdac.gov.in/3dimager.xml
- INSAT3DR-Imager: https://mosdac.gov.in/3drimager.xml
- SCATSAT-1: https://mosdac.gov.in/isrocast.xml

Current status: Architecture ready. RSS parsing works for any feed.
In production: triggers residual layer update when new cloud imagery arrives.
"""
import feedparser
from datetime import datetime, timedelta
from typing import List, Dict


MOSDAC_FEEDS = {
    "insat3d_imager": "https://mosdac.gov.in/3dimager.xml",
    "insat3dr_imager": "https://mosdac.gov.in/3drimager.xml",
    "scatsat1": "https://mosdac.gov.in/isrocast.xml",
}


def parse_mosdac_feed(feed_url: str, max_entries: int = 10) -> List[Dict]:
    """Parse MOSDAC RSS feed and return recent entries."""
    try:
        feed = feedparser.parse(feed_url)
        entries = []
        for entry in feed.entries[:max_entries]:
            entries.append({
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
                "summary": entry.get("summary", ""),
            })
        return entries
    except Exception as e:
        return [{"error": str(e)}]


def get_latest_satellite_data(feed_name: str = "insat3dr_imager") -> List[Dict]:
    """Get latest satellite imagery metadata from MOSDAC."""
    url = MOSDAC_FEEDS.get(feed_name)
    if not url:
        return [{"error": f"Unknown feed: {feed_name}"}]
    return parse_mosdac_feed(url)


def check_for_new_imagery(last_check_time: datetime) -> bool:
    """Check if new satellite imagery has been published since last check."""
    entries = get_latest_satellite_data()
    if not entries or "error" in entries[0]:
        return False
    
    for entry in entries:
        try:
            pub_time = datetime.strptime(entry["published"], "%a, %d %b %Y %H:%M:%S %Z")
            if pub_time > last_check_time:
                return True
        except:
            continue
    return False


if __name__ == "__main__":
    print("MOSDAC RSS Feed Monitor")
    print("=" * 50)
    for name, url in MOSDAC_FEEDS.items():
        print(f"\nFeed: {name}")
        print(f"URL: {url}")
        entries = parse_mosdac_feed(url, max_entries=3)
        if entries and "error" not in entries[0]:
            print(f"Latest: {entries[0]['title']}")
            print(f"Published: {entries[0]['published']}")
        else:
            print("Could not fetch (network required)")
