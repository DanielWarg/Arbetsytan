"""
Feed fetching and parsing with robust SSRF protection.
"""
import html
import ipaddress
import logging
import socket
from typing import Dict, List, Optional
from urllib.parse import urlparse, urljoin

import feedparser
import requests

logger = logging.getLogger(__name__)

# Constants
REQUEST_TIMEOUT = 10  # seconds
MAX_RESPONSE_SIZE = 5 * 1024 * 1024  # 5MB
USER_AGENT = "Arbetsytan/1.0 (feed import)"
MAX_REDIRECTS = 5


def _is_private_ip(ip: str) -> bool:
    """
    Check if IP address is private/localhost/link-local.
    
    Args:
        ip: IP address string
        
    Returns:
        True if IP is private/localhost/link-local
    """
    try:
        ip_obj = ipaddress.ip_address(ip)
        return (
            ip_obj.is_private or
            ip_obj.is_loopback or
            ip_obj.is_link_local or
            ip_obj.is_reserved or
            ip == "0.0.0.0"
        )
    except ValueError:
        return True  # Invalid IP is treated as blocked


def _resolve_and_validate_host(hostname: str) -> bool:
    """
    Resolve hostname to IP and validate it's not private.
    
    Args:
        hostname: Hostname to resolve
        
    Returns:
        True if hostname resolves to public IP, False if private/blocked
        
    Raises:
        ValueError: If hostname cannot be resolved
    """
    try:
        # Resolve to IP
        ip = socket.gethostbyname(hostname)
        if _is_private_ip(ip):
            logger.warning(f"Blocked private IP after DNS resolution: {hostname} -> {ip}")
            return False
        return True
    except socket.gaierror as e:
        raise ValueError(f"Failed to resolve hostname {hostname}: {e}")


def _validate_url_scheme(url: str) -> bool:
    """
    Validate URL scheme is http or https.
    
    Args:
        url: URL to validate
        
    Returns:
        True if scheme is http/https, False otherwise
    """
    parsed = urlparse(url)
    return parsed.scheme in ('http', 'https')


def validate_and_fetch(url: str) -> bytes:
    """
    Fetch feed URL with robust SSRF protection.
    
    SSRF-skydd:
    - Endast http/https tillåtna
    - DNS-resolve och validera resolved IP (blocka privata IP även efter DNS)
    - Blocka redirects till privata IP (följ redirects men validera varje hop)
    - Timeout: 10s
    - Max storlek: 5MB
    
    Args:
        url: Feed URL to fetch
        
    Returns:
        Feed content as bytes
        
    Raises:
        ValueError: If URL is invalid, blocked, or fetch fails
        requests.exceptions.RequestException: If network request fails
    """
    # Validate scheme
    if not _validate_url_scheme(url):
        raise ValueError(f"Invalid URL scheme. Only http:// and https:// are allowed. Got: {urlparse(url).scheme}")
    
    parsed = urlparse(url)
    
    # Block localhost/private hostnames
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL missing hostname")
    
    # Block obvious localhost patterns
    if hostname in ('localhost', '127.0.0.1', '0.0.0.0', '::1', '[::1]'):
        raise ValueError(f"Blocked localhost hostname: {hostname}")
    
    # Resolve and validate hostname (DNS + IP check)
    if not _resolve_and_validate_host(hostname):
        raise ValueError(f"Blocked private IP for hostname: {hostname}")
    
    # Fetch with redirect handling and validation
    # Use allow_redirects=False and manually follow redirects to validate each hop
    session = requests.Session()
    current_url = url
    redirects_followed = 0
    
    try:
        while redirects_followed <= MAX_REDIRECTS:
            response = session.get(
                current_url,
                timeout=REQUEST_TIMEOUT,
                headers={'User-Agent': USER_AGENT},
                allow_redirects=False,  # Manual redirect handling
                stream=True  # Stream to enforce size limit
            )
            
            # Validate current URL hostname
            current_parsed = urlparse(current_url)
            current_hostname = current_parsed.hostname
            if current_hostname and not _resolve_and_validate_host(current_hostname):
                raise ValueError(f"Blocked private IP: {current_hostname}")
            
            # Check for redirect
            if response.status_code in (301, 302, 303, 307, 308):
                redirect_url = response.headers.get('Location')
                if not redirect_url:
                    raise ValueError("Redirect response missing Location header")
                
                # Resolve relative redirects
                redirect_url = urljoin(current_url, redirect_url)
                
                # Validate redirect URL
                redirect_parsed = urlparse(redirect_url)
                if not redirect_parsed.scheme in ('http', 'https'):
                    raise ValueError(f"Invalid redirect scheme: {redirect_parsed.scheme}")
                
                redirect_hostname = redirect_parsed.hostname
                if redirect_hostname and not _resolve_and_validate_host(redirect_hostname):
                    raise ValueError(f"Blocked private IP in redirect: {redirect_hostname}")
                
                current_url = redirect_url
                redirects_followed += 1
                continue
            
            # Not a redirect, break and process response
            break
        
        if redirects_followed > MAX_REDIRECTS:
            raise ValueError(f"Too many redirects (max {MAX_REDIRECTS})")
        
        # Check HTTP status
        response.raise_for_status()
        
        # Final validation of response URL
        final_parsed = urlparse(response.url)
        final_hostname = final_parsed.hostname
        if final_hostname and not _resolve_and_validate_host(final_hostname):
            raise ValueError(f"Blocked private IP in final URL: {final_hostname}")
        
        # Check content length header if available
        content_length = response.headers.get('Content-Length')
        if content_length:
            size = int(content_length)
            if size > MAX_RESPONSE_SIZE:
                raise ValueError(f"Response too large: {size} bytes (max {MAX_RESPONSE_SIZE})")
        
        # Read response with size limit
        content = b''
        for chunk in response.iter_content(chunk_size=8192):
            content += chunk
            if len(content) > MAX_RESPONSE_SIZE:
                raise ValueError(f"Response exceeds size limit: {MAX_RESPONSE_SIZE} bytes")
        
        return content
        
    except requests.exceptions.Timeout:
        raise ValueError(f"Request timeout after {REQUEST_TIMEOUT}s")
    except requests.exceptions.TooManyRedirects:
        raise ValueError(f"Too many redirects (max {MAX_REDIRECTS})")
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Failed to fetch feed: {str(e)}")


def html_to_text(html_content: str) -> str:
    """
    Convert HTML content to plain text by stripping tags.
    
    Args:
        html_content: HTML string
        
    Returns:
        Plain text with HTML tags removed
    """
    if not html_content:
        return ""
    
    # Unescape HTML entities first
    text = html.unescape(html_content)
    
    # Simple HTML tag removal (regex-based, safe for feed summaries)
    import re
    # Remove script and style tags and their content
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    # Remove all HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text


def parse_feed(content: bytes) -> Dict:
    """
    Parse RSS/Atom feed using feedparser.
    
    Args:
        content: Feed content as bytes
        
    Returns:
        Dictionary with:
        - title: str
        - description: str (optional)
        - items: List[Dict] with guid, title, link, published, summary_text
    """
    try:
        # feedparser can parse bytes directly
        feed = feedparser.parse(content)
        
        if feed.bozo and feed.bozo_exception:
            logger.warning(f"Feed parsing warning: {feed.bozo_exception}")
        
        # Extract feed metadata
        feed_title = getattr(feed.feed, 'title', 'Untitled Feed')
        feed_description = getattr(feed.feed, 'description', '')
        
        # Extract items
        items = []
        for entry in feed.entries:
            # Get guid (prioritize id, then guid, then link)
            guid = getattr(entry, 'id', None) or getattr(entry, 'guid', None)
            if not guid:
                guid = getattr(entry, 'link', '')
            
            # Get title
            title = getattr(entry, 'title', '')
            
            # Get link
            link = getattr(entry, 'link', '')
            
            # Get published date
            published = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                from datetime import datetime
                published = datetime(*entry.published_parsed[:6]).isoformat()
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                from datetime import datetime
                published = datetime(*entry.updated_parsed[:6]).isoformat()
            
            # Get summary/content and convert HTML to text
            summary_html = ''
            if hasattr(entry, 'summary'):
                summary_html = entry.summary
            elif hasattr(entry, 'content'):
                if isinstance(entry.content, list) and len(entry.content) > 0:
                    summary_html = entry.content[0].get('value', '')
                elif isinstance(entry.content, str):
                    summary_html = entry.content
            
            summary_text = html_to_text(summary_html) if summary_html else ''
            
            items.append({
                'guid': guid,
                'title': title,
                'link': link,
                'published': published,
                'summary_text': summary_text
            })
        
        return {
            'title': feed_title,
            'description': feed_description,
            'items': items
        }
        
    except Exception as e:
        raise ValueError(f"Failed to parse feed: {str(e)}")
