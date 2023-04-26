# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Match:
    season: str
    competition: str
    group: str
    matchday: int

    home_team: str
    away_team: str
    finished: bool

    timestamp: datetime = None
    stadium: str = None
    latlon: tuple[float, float] = None
    home_goals: int = None
    away_goals: int = None

    def __repr__(self) -> str:
        if self.finished:
            return f'{self.home_team} ({self.home_goals} - {self.away_goals}) {self.away_team}'
        return f'{self.home_team} - {self.away_team}'

    def __str__(self) -> str:
        return self.__repr__()
