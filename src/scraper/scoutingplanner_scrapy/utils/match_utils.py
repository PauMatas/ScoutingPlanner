from datetime import datetime
import re

def parse_timestamp(date: str, time: str) -> datetime:
    """Parse a timestamp from the website.
    
    Args:
        date (str): Date in the format DD-MM-YYYY
        time (str): Time in the format HH:MM
    
    Returns:
        datetime: Datetime object
    """
    try:
        date = date.split('-')
        if len(time) != 5:
            return datetime(int(date[2]), int(date[1]), int(date[0]))
        time = time.split(':')
        return datetime(int(date[2]), int(date[1]), int(date[0]), int(time[0]), int(time[1]))
    except:
        return None

def parse_google_maps_link(link: str) -> tuple[float, float]:
    """Parse a Google Maps link to get the coordinates.
    
    Args:
        link (str): Google Maps link, example: 'http://maps.google.com/maps?z=12&t=m&q=loc:41.423696+2.231086'
    
    Returns:
        tuple[float, float]: Coordinates
    """
    if not link.startswith('http://maps.google.com/maps') or not 'loc:' in link:
        raise ValueError("Invalid Google Maps link")
    
    pattern = r"loc:(\-?\d+\.\d+)\+(\-?\d+\.\d+)"
    match = re.search(pattern, link)
    if match:
        latitude = match.group(1)
        longitude = match.group(2)
        return (float(latitude), float(longitude))
    
    raise ValueError("Invalid Google Maps link")

def parse_result(result: str) -> tuple[int, int]:
    """Parse the result of a match.
    
    Args:
        result (str): Result in the format 'X-Y'
    
    Returns:
        tuple[int, int]: Home goals, away goals
    """
    result = result.split(' - ')
    return (int(result[0]), int(result[1]))