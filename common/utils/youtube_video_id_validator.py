

def validate_youtube_video_id(video_id: str) -> bool:
    """Validate if the given string is a valid YouTube video ID."""
    import re

    # YouTube video IDs are 11 characters long and can contain letters, numbers, - and _
    pattern = r'^[a-zA-Z0-9_-]{11}$'
    return re.match(pattern, video_id) is not None