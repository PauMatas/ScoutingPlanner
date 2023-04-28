from abc import ABC, abstractmethod
from datetime import datetime
from networkx import DiGraph

from src.scraper.scoutingplanner_scrapy.items import Match


class AbstractDatabaseProxy(ABC):
    @abstractmethod
    def get_matches(self, season: str, as_dict: bool = False, **kwargs) -> list[Match | dict]:
        raise NotImplementedError

    @abstractmethod
    def save_match(self, matches: Match):
        raise NotImplementedError

    @abstractmethod
    def get_matchday_graph(self, day: datetime) -> DiGraph | None:
        raise NotImplementedError

    @abstractmethod
    def save_matchday_graph(self, day: datetime, graph: DiGraph):
        raise NotImplementedError
    
    @abstractmethod
    def get_competitions(self, season: str) -> list[str]:
        raise NotImplementedError
