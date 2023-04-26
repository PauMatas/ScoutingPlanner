from datetime import datetime

class ParseError(Exception):
    pass

def parse_date(date: str) -> datetime:
    """Parse a timestamp from the user input.
    
    Args:
        date (str): Date in the format DD-MM-YYYY

    Returns:
        datetime: Datetime object
    """
    try:
        date = date.split('-')
        return datetime(int(date[2]), int(date[1]), int(date[0]))
    except Exception as e:
        print(f'[parsers.parse_date] {e}')
        raise ParseError("Invalid date format")