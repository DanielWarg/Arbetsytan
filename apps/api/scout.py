"""
Scout RSS feed fetching logic.
"""
import hashlib
import logging
import time
from datetime import datetime, timezone
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from models import ScoutFeed, ScoutItem

logger = logging.getLogger(__name__)

# Fixture RSS XML for testing without internet
# Generate fresh XML each time to avoid dedup issues
def get_fixture_rss_xml():
    timestamp = int(time.time())
    # Use current date for published dates so items are within 24h window
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    now_str = now.strftime('%a, %d %b %Y %H:%M:%S +0000')
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <link>https://example.com</link>
    <description>Test feed for Scout</description>
    <item>
      <title>Test Item 1</title>
      <link>https://example.com/item1-{timestamp}</link>
      <pubDate>{now_str}</pubDate>
      <guid>test-item-1-{timestamp}</guid>
    </item>
    <item>
      <title>Test Item 2</title>
      <link>https://example.com/item2-{timestamp}</link>
      <pubDate>{now_str}</pubDate>
      <guid>test-item-2-{timestamp}</guid>
    </item>
  </channel>
</rss>"""


def calculate_guid_hash(feed_url: str, entry: Dict) -> str:
    """
    Calculate unique hash for RSS item deduplication.
    
    Args:
        feed_url: URL of the feed
        entry: Dictionary with entry data (id, link, title, published, updated)
        
    Returns:
        SHA256 hash as hex string
    """
    stable_id = (
        entry.get('id') or 
        entry.get('link') or 
        (entry.get('title', '') + str(entry.get('published') or entry.get('updated') or ''))
    )
    hash_input = f"{feed_url}{stable_id}"
    return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()


def parse_rss_feed(url: str, mode: str = "fixture") -> List[Dict]:
    """
    Parse RSS/Atom feed and return list of entries.
    
    Args:
        url: Feed URL (or "fixture://local" for fixture mode)
        mode: "fixture" or "live"
        
    Returns:
        List of entry dictionaries with keys: title, link, published, updated, id
    """
    if mode == "fixture" or url.startswith("fixture://"):
        # Return fixture data
        from xml.etree import ElementTree as ET
        root = ET.fromstring(get_fixture_rss_xml())
        entries = []
        for item in root.findall('.//item'):
            title_elem = item.find('title')
            link_elem = item.find('link')
            pubdate_elem = item.find('pubDate')
            guid_elem = item.find('guid')
            
            title = title_elem.text if title_elem is not None else ""
            link = link_elem.text if link_elem is not None else ""
            pubdate = pubdate_elem.text if pubdate_elem is not None else None
            guid = guid_elem.text if guid_elem is not None else ""
            
            # Parse date if available
            published = None
            if pubdate:
                try:
                    from email.utils import parsedate_to_datetime
                    published = parsedate_to_datetime(pubdate)
                except:
                    pass
            
            entries.append({
                'title': title,
                'link': link,
                'published': published,
                'updated': published,
                'id': guid
            })
        return entries
    
    # Live mode: try to use feedparser if available, otherwise fallback to ElementTree
    try:
        import feedparser
        feed = feedparser.parse(url)
        entries = []
        for entry in feed.entries:
            entries.append({
                'title': entry.get('title', ''),
                'link': entry.get('link', ''),
                'published': entry.get('published_parsed'),
                'updated': entry.get('updated_parsed'),
                'id': entry.get('id') or entry.get('link', '')
            })
        return entries
    except ImportError:
        # Fallback to ElementTree
        import requests
        from xml.etree import ElementTree as ET
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            root = ET.fromstring(response.content)
            entries = []
            
            # Handle RSS 2.0
            for item in root.findall('.//item'):
                title_elem = item.find('title')
                link_elem = item.find('link')
                pubdate_elem = item.find('pubDate')
                guid_elem = item.find('guid')
                
                title = title_elem.text if title_elem is not None else ""
                link = link_elem.text if link_elem is not None else ""
                pubdate = pubdate_elem.text if pubdate_elem is not None else None
                guid = guid_elem.text if guid_elem is not None else ""
                
                published = None
                if pubdate:
                    try:
                        from email.utils import parsedate_to_datetime
                        published = parsedate_to_datetime(pubdate)
                    except:
                        pass
                
                entries.append({
                    'title': title,
                    'link': link,
                    'published': published,
                    'updated': published,
                    'id': guid or link
                })
            
            # Handle Atom
            if not entries:
                for entry in root.findall('.//{http://www.w3.org/2005/Atom}entry'):
                    title_elem = entry.find('{http://www.w3.org/2005/Atom}title')
                    link_elem = entry.find('{http://www.w3.org/2005/Atom}link')
                    updated_elem = entry.find('{http://www.w3.org/2005/Atom}updated')
                    id_elem = entry.find('{http://www.w3.org/2005/Atom}id')
                    
                    title = title_elem.text if title_elem is not None else ""
                    link_attr = link_elem.get('href') if link_elem is not None else ""
                    updated = updated_elem.text if updated_elem is not None else None
                    entry_id = id_elem.text if id_elem is not None else ""
                    
                    published = None
                    if updated:
                        try:
                            published = datetime.fromisoformat(updated.replace('Z', '+00:00'))
                        except:
                            pass
                    
                    entries.append({
                        'title': title,
                        'link': link_attr,
                        'published': published,
                        'updated': published,
                        'id': entry_id or link_attr
                    })
            
            return entries
        except Exception as e:
            logger.warning(f"Failed to parse feed {url}: {e}")
            return []


def fetch_all_feeds(db: Session, mode: str = "fixture") -> Dict[int, int]:
    """
    Fetch all enabled feeds and save new items.
    
    Args:
        db: Database session
        mode: "fixture" or "live"
        
    Returns:
        Dictionary mapping feed_id to count of new items created
    """
    feeds = db.query(ScoutFeed).filter(ScoutFeed.is_enabled == True).all()
    results = {}
    
    for feed in feeds:
        try:
            # Skip feeds with empty URL unless fixture mode
            if not feed.url and mode != "fixture":
                continue
            
            # Use fixture URL if empty
            feed_url = feed.url if feed.url else "fixture://local"
            
            entries = parse_rss_feed(feed_url, mode=mode)
            new_count = 0
            
            for entry in entries:
                # Calculate dedup hash
                guid_hash = calculate_guid_hash(feed_url, entry)
                
                # Check if item already exists
                existing = db.query(ScoutItem).filter(ScoutItem.guid_hash == guid_hash).first()
                if existing:
                    continue
                
                # Parse published date
                published_at = None
                if entry.get('published'):
                    if isinstance(entry['published'], datetime):
                        published_at = entry['published']
                    elif isinstance(entry['published'], tuple):
                        # feedparser time tuple
                        try:
                            import time
                            published_at = datetime.fromtimestamp(time.mktime(entry['published']), tz=timezone.utc)
                        except:
                            pass
                
                # Create new item
                item = ScoutItem(
                    feed_id=feed.id,
                    title=entry.get('title', '')[:500],  # Limit length
                    link=entry.get('link', '')[:1000],  # Limit length
                    published_at=published_at,
                    guid_hash=guid_hash,
                    raw_source=feed.name
                )
                db.add(item)
                new_count += 1
            
            db.commit()
            results[feed.id] = new_count
            
            # Log metadata only (no content)
            logger.info(f"Scout feed {feed.id} ({feed.name}): {new_count} nya items")
            
        except Exception as e:
            # Fail-closed: log error but don't crash
            logger.error(f"Scout feed {feed.id} ({feed.name}): fetch failed - {e}")
            db.rollback()
            results[feed.id] = 0
    
    return results
