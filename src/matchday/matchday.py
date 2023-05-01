from datetime import datetime

from interfaces.scraper import run_matches_spider
from interfaces.database import MongoDBDatabaseProxy
from interfaces.routes import OpenRouteServiceProxy
from scraper.scoutingplanner_scrapy.items import Match

from .planner import Planner
from .utils import parse_matchday_date


class Matchday:
    db_proxy = MongoDBDatabaseProxy()
    routes_proxy = OpenRouteServiceProxy()
    season = 'TEMPORADA 2022-2023'

    def __init__(self, date: datetime | str = None, **kwargs):
        self.date = parse_matchday_date(date, **kwargs)

        run_matches_spider()
        self.matches = self.db_proxy.get_matches(season=self.season, timestamp=self.date)
        self.reachable_matches = list(filter(
            lambda m: m.latlon is not None and m.timestamp is not None, self.matches
        ))
        self.reachable_matches = sorted(self.reachable_matches, key=lambda m: m.timestamp)

        self.planner = Planner(db_proxy=self.db_proxy, routes_proxy=self.routes_proxy, matches=self.reachable_matches, date=self.date, season=self.season)

        self._competitions = None

    def routes(self, **kwargs) -> list[list[Match]]:
        return self.planner.routes(**kwargs)
    
    @property
    def competitions(self) -> dict:
        if self._competitions is None:
            self._set_competitions()
        return self._competitions
    
    def _set_competitions(self):
        self._competitions = {}
        for match in self.matches:
            if match.competition not in self._competitions:
                self._competitions[match.competition] = {
                    'matches': 1,
                    'matchday': {str(match.matchday)}
                    }
            else:
                self._competitions[match.competition]['matches'] += 1
                self._competitions[match.competition]['matchday'].add(str(match.matchday))
