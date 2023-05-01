from datetime import datetime, timedelta


def parse_matchday_date(date: datetime | str | None, **kwargs) -> datetime:
    if isinstance(date, datetime):
        return date
    
    if isinstance(date, str):
        return datetime.strptime(date, kwargs.get('format', '%d-%m-%Y'))
    
    if date is None:
        if ['day', 'month', 'year'] in kwargs:
            return datetime(kwargs['year'], kwargs['month'], kwargs['day'])
        
        now = datetime.now()
        # set time to 00:00:00
        today = datetime(now.year, now.month, now.day)
        saturday = today + timedelta(days=5-today.weekday())
        sunday = today + timedelta(days=6-today.weekday())
        if today.weekday() == 5:
            return sunday
        elif today.weekday() == 6:
            return today + timedelta(days=6)
        return saturday
    
    raise ValueError(f"Invalid date: {date}")