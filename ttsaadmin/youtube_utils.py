"""Utility functions for YouTube channel operations"""
import re
import requests
import feedparser
from urllib.parse import urlparse, parse_qs
from django.conf import settings


class YouTubeChannelError(Exception):
    """Custom exception for YouTube channel errors"""
    pass


class YouTubeVideoError(Exception):
    """Custom exception for YouTube video errors"""
    pass


def fetch_channel_videos(channel_id, api_key=None, max_results=50):
    """
    Fetch all videos from a YouTube channel using the YouTube Data API
    
    Args:
        channel_id: YouTube channel ID or handle
        api_key: YouTube API key (optional, will use settings if not provided)
        max_results: Maximum number of videos to fetch per page (default: 50)
    
    Returns:
        List of video dictionaries with video metadata
    
    Raises:
        YouTubeChannelError: If API request fails or channel not found
    """
    if not api_key:
        api_key = getattr(settings, 'YOUTUBE_API_KEY', None)
    
    if not api_key:
        raise YouTubeChannelError("YouTube API key not configured")
    
    videos = []
    next_page_token = None
    
    while True:
        # Try to get videos by channel ID first
        api_url = f'https://www.googleapis.com/youtube/v3/search'
        params = {
            'part': 'snippet',
            'channelId': channel_id if not channel_id.startswith('@') else None,
            'forHandle': channel_id.lstrip('@') if channel_id.startswith('@') else None,
            'order': 'date',
            'type': 'video',
            'maxResults': max_results,
            'key': api_key
        }
        
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        
        if next_page_token:
            params['pageToken'] = next_page_token
        
        try:
            response = requests.get(api_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            raise YouTubeChannelError(f"Failed to fetch videos from YouTube API: {str(e)}")
        
        if not data.get('items'):
            break
        
        for item in data['items']:
            snippet = item.get('snippet', {})
            video_id = item.get('id', {}).get('videoId') if isinstance(item.get('id'), dict) else item.get('id')
            
            if not video_id:
                continue
            
            video_data = {
                'video_id': video_id,
                'title': snippet.get('title', ''),
                'description': snippet.get('description', ''),
                'channel_name': snippet.get('channelTitle', ''),
                'published_at': snippet.get('publishedAt', ''),
                'thumbnail_url': snippet.get('thumbnails', {}).get('high', {}).get('url', '') or \
                               snippet.get('thumbnails', {}).get('medium', {}).get('url', '') or \
                               snippet.get('thumbnails', {}).get('default', {}).get('url', ''),
            }
            videos.append(video_data)
        
        next_page_token = data.get('nextPageToken')
        if not next_page_token:
            break
    
    return videos


def extract_channel_id(url_or_id):
    """
    Extract channel ID from various YouTube URL formats or return as-is if it's already an ID
    
    Supported formats:
    - https://www.youtube.com/channel/CHANNEL_ID
    - https://www.youtube.com/c/CHANNEL_NAME
    - https://www.youtube.com/@HANDLE
    - https://www.youtube.com/user/USERNAME
    - Direct channel ID (e.g., UC...)
    - Direct handle (e.g., @handle)
    """
    url_or_id = url_or_id.strip()
    
    # If it's already a channel ID (starts with UC), return as-is
    if re.match(r'^UC[A-Za-z0-9_-]{22}$', url_or_id):
        return url_or_id
    
    # If it's a handle (starts with @), return as-is
    if url_or_id.startswith('@'):
        return url_or_id
    
    # Channel ID format
    channel_match = re.search(r'youtube\.com/channel/([A-Za-z0-9_-]{24})', url_or_id)
    if channel_match:
        return channel_match.group(1)
    
    # Custom URL format (/c/)
    custom_match = re.search(r'youtube\.com/c/([A-Za-z0-9_-]+)', url_or_id)
    if custom_match:
        return custom_match.group(1)
    
    # Handle format (@)
    handle_match = re.search(r'youtube\.com/@([A-Za-z0-9_.-]+)', url_or_id)
    if handle_match:
        return handle_match.group(1)
    
    # User format
    user_match = re.search(r'youtube\.com/user/([A-Za-z0-9_-]+)', url_or_id)
    if user_match:
        return user_match.group(1)
    
    # Return as-is if no pattern matches (might be a custom channel name)
    return url_or_id


def get_rss_feed_url(channel_id):
    """
    Generate RSS feed URL for a YouTube channel
    """
    return f'https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}'


def fetch_channel_metadata_from_rss(channel_id):
    """
    Fetch channel metadata from YouTube RSS feed
    
    Returns dict with channel information or raises YouTubeChannelError
    """
    rss_url = get_rss_feed_url(channel_id)
    
    try:
        response = requests.get(rss_url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        raise YouTubeChannelError(f"Failed to fetch RSS feed: {str(e)}")
    
    feed = feedparser.parse(response.content)
    
    if not feed or not feed.feed:
        raise YouTubeChannelError("Invalid RSS feed response")
    
    # Extract channel information from RSS feed
    channel_info = {
        'channel_id': channel_id,
        'channel_url': f'https://www.youtube.com/channel/{channel_id}',
        'channel_name': feed.feed.get('title', ''),
        'channel_description': feed.feed.get('description', ''),
        'channel_thumbnail_url': feed.feed.get('image', {}).get('href', ''),
    }
    
    # YouTube RSS feeds don't provide view counts, so we set defaults
    channel_info['video_count'] = len(feed.entries) if feed.entries else 0
    channel_info['view_count'] = 0
    
    return channel_info


def fetch_channel_metadata_from_api(channel_id, api_key=None):
    """
    Fetch channel metadata from YouTube Data API v3
    
    Returns dict with channel information or raises YouTubeChannelError
    """
    if not api_key:
        api_key = getattr(settings, 'YOUTUBE_API_KEY', None)
    
    if not api_key:
        raise YouTubeChannelError("YouTube API key not configured")
    
    # Try to get channel by ID first
    api_url = f'https://www.googleapis.com/youtube/v3/channels'
    params = {
        'part': 'snippet,statistics',
        'id': channel_id,
        'key': api_key
    }
    
    try:
        response = requests.get(api_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        raise YouTubeChannelError(f"Failed to fetch from YouTube API: {str(e)}")
    
    # If no results with channel_id, try with forHandle parameter (for @handles)
    if not data.get('items'):
        # Remove @ if present for forHandle parameter
        handle = channel_id.lstrip('@')
        params = {
            'part': 'snippet,statistics',
            'forHandle': handle,
            'key': api_key
        }
        
        try:
            response = requests.get(api_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            # If forHandle fails, try with forUsername parameter
            params = {
                'part': 'snippet,statistics',
                'forUsername': channel_id,
                'key': api_key
            }
            
            try:
                response = requests.get(api_url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
            except requests.RequestException as e:
                raise YouTubeChannelError(f"Failed to fetch from YouTube API: {str(e)}")
    
    if not data.get('items'):
        raise YouTubeChannelError("Channel not found or inaccessible")
    
    channel_data = data['items'][0]
    snippet = channel_data.get('snippet', {})
    statistics = channel_data.get('statistics', {})
    
    # Get thumbnail URL (prefer high quality)
    thumbnails = snippet.get('thumbnails', {})
    thumbnail_url = thumbnails.get('high', {}).get('url', '') or \
                   thumbnails.get('medium', {}).get('url', '') or \
                   thumbnails.get('default', {}).get('url', '')
    
    channel_info = {
        'channel_id': channel_data.get('id', channel_id),
        'channel_url': f'https://www.youtube.com/channel/{channel_data.get("id", channel_id)}',
        'channel_name': snippet.get('title', ''),
        'channel_description': snippet.get('description', ''),
        'channel_thumbnail_url': thumbnail_url,
        'video_count': int(statistics.get('videoCount', 0)),
        'view_count': int(statistics.get('viewCount', 0)),
    }
    
    return channel_info


def validate_and_fetch_channel_metadata(url_or_id, use_api=True, api_key=None):
    """
    Validate YouTube channel URL/ID and fetch metadata
    
    Args:
        url_or_id: YouTube channel URL, channel ID, or handle
        use_api: Whether to try YouTube Data API first (fallback to RSS)
        api_key: Optional YouTube API key (will use settings if not provided)
    
    Returns:
        dict with channel information
    
    Raises:
        YouTubeChannelError: If URL/ID is invalid or channel cannot be fetched
    """
    # Extract channel ID from URL or return as-is if it's already an ID
    channel_id = extract_channel_id(url_or_id)
    if not channel_id:
        raise YouTubeChannelError("Invalid YouTube channel URL or ID format")
    
    # Try RSS first if use_api is False, or as fallback
    if not use_api:
        try:
            return fetch_channel_metadata_from_rss(channel_id)
        except YouTubeChannelError:
            raise YouTubeChannelError("Could not fetch channel metadata via RSS")
    
    # Try YouTube Data API first if available
    try:
        return fetch_channel_metadata_from_api(channel_id, api_key)
    except YouTubeChannelError:
        # Fallback to RSS feed
        try:
            return fetch_channel_metadata_from_rss(channel_id)
        except YouTubeChannelError as e:
            raise YouTubeChannelError(f"Could not fetch channel metadata: {str(e)}")


def extract_video_id(url_or_id):
    """
    Extract YouTube video ID from various URL formats or return as-is if it's already an ID
    
    Supported formats:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    - https://www.youtube.com/v/VIDEO_ID
    - Direct video ID (e.g., dQw4w9WgXcQ)
    """
    url_or_id = url_or_id.strip()
    
    # If it's already a video ID (11 characters), return as-is
    if re.match(r'^[A-Za-z0-9_-]{11}$', url_or_id):
        return url_or_id
    
    # Standard watch URL
    watch_match = re.search(r'[?&]v=([A-Za-z0-9_-]{11})', url_or_id)
    if watch_match:
        return watch_match.group(1)
    
    # Short URL (youtu.be)
    short_match = re.search(r'youtu\.be/([A-Za-z0-9_-]{11})', url_or_id)
    if short_match:
        return short_match.group(1)
    
    # Embed URL
    embed_match = re.search(r'embed/([A-Za-z0-9_-]{11})', url_or_id)
    if embed_match:
        return embed_match.group(1)
    
    # v URL parameter
    v_match = re.search(r'/v/([A-Za-z0-9_-]{11})', url_or_id)
    if v_match:
        return v_match.group(1)
    
    return None


def fetch_video_metadata_from_oembed(video_id):
    """
    Fetch video metadata from YouTube oEmbed API
    
    Returns dict with video information or raises YouTubeVideoError
    """
    oembed_url = 'https://www.youtube.com/oembed'
    params = {
        'url': f'https://www.youtube.com/watch?v={video_id}',
        'format': 'json'
    }
    
    try:
        response = requests.get(oembed_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        raise YouTubeVideoError(f"Failed to fetch oEmbed data: {str(e)}")
    
    if not data:
        raise YouTubeVideoError("Invalid oEmbed response")
    
    video_info = {
        'video_id': video_id,
        'video_url': f'https://www.youtube.com/watch?v={video_id}',
        'title': data.get('title', ''),
        'author_name': data.get('author_name', ''),
        'thumbnail_url': data.get('thumbnail_url', ''),
        'duration': '',  # oEmbed doesn't provide duration
    }
    
    return video_info


def fetch_video_metadata_from_api(video_id, api_key=None):
    """
    Fetch video metadata from YouTube Data API v3
    
    Returns dict with video information or raises YouTubeVideoError
    """
    if not api_key:
        api_key = getattr(settings, 'YOUTUBE_API_KEY', None)
    
    if not api_key:
        raise YouTubeVideoError("YouTube API key not configured")
    
    api_url = 'https://www.googleapis.com/youtube/v3/videos'
    params = {
        'part': 'snippet,contentDetails,statistics',
        'id': video_id,
        'key': api_key
    }
    
    try:
        response = requests.get(api_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        raise YouTubeVideoError(f"Failed to fetch from YouTube API: {str(e)}")
    
    if not data.get('items'):
        raise YouTubeVideoError("Video not found or inaccessible")
    
    video_data = data['items'][0]
    snippet = video_data.get('snippet', {})
    content_details = video_data.get('contentDetails', {})
    
    # Parse duration from ISO 8601 format (PT10M30S -> 10:30)
    duration = content_details.get('duration', '')
    if duration:
        duration = parse_duration(duration)
    
    # Get thumbnail URL (prefer high quality)
    thumbnails = snippet.get('thumbnails', {})
    thumbnail_url = thumbnails.get('maxres', {}).get('url', '') or \
                   thumbnails.get('high', {}).get('url', '') or \
                   thumbnails.get('medium', {}).get('url', '') or \
                   thumbnails.get('default', {}).get('url', '')
    
    video_info = {
        'video_id': video_id,
        'video_url': f'https://www.youtube.com/watch?v={video_id}',
        'title': snippet.get('title', ''),
        'description': snippet.get('description', ''),
        'channel_name': snippet.get('channelTitle', ''),
        'thumbnail_url': thumbnail_url,
        'duration': duration,
    }
    
    return video_info


def parse_duration(iso_duration):
    """
    Parse YouTube ISO 8601 duration format to human-readable format
    
    Args:
        iso_duration: Duration in ISO 8601 format (e.g., PT10M30S)
    
    Returns:
        Human-readable duration string (e.g., "10:30")
    """
    import re
    
    # Extract hours, minutes, seconds
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', iso_duration)
    if not match:
        return ''
    
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    
    # Format as HH:MM:SS or MM:SS
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes}:{seconds:02d}"


def validate_and_fetch_video_metadata(url_or_id, use_api=True, api_key=None):
    """
    Validate YouTube video URL/ID and fetch metadata
    
    Args:
        url_or_id: YouTube video URL or video ID
        use_api: Whether to try YouTube Data API first (fallback to oEmbed)
        api_key: Optional YouTube API key (will use settings if not provided)
    
    Returns:
        dict with video information
    
    Raises:
        YouTubeVideoError: If URL/ID is invalid or video cannot be fetched
    """
    # Extract video ID from URL or return as-is if it's already an ID
    video_id = extract_video_id(url_or_id)
    if not video_id:
        raise YouTubeVideoError("Invalid YouTube video URL or ID format")
    
    # Try oEmbed first if use_api is False, or as fallback
    if not use_api:
        try:
            return fetch_video_metadata_from_oembed(video_id)
        except YouTubeVideoError:
            raise YouTubeVideoError("Could not fetch video metadata via oEmbed")
    
    # Try YouTube Data API first if available
    try:
        return fetch_video_metadata_from_api(video_id, api_key)
    except YouTubeVideoError:
        # Fallback to oEmbed
        try:
            return fetch_video_metadata_from_oembed(video_id)
        except YouTubeVideoError as e:
            raise YouTubeVideoError(f"Could not fetch video metadata: {str(e)}")
