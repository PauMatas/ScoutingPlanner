from networkx import DiGraph
from datetime import datetime, timedelta

from src.interfaces.scraper import run_matches_spider
from src.interfaces.database import MongoDBDatabaseProxy
from src.routes import OpenRouteServiceProxy

class MatchDayGraph:
    def __init__(self, date: datetime | str = None, **kwargs):
        if isinstance(date, datetime):
            self.date = date
        elif isinstance(date, str):
            self.date = datetime.strptime(date, kwargs.get('format', '%d-%m-%Y'))
        elif date is None:
            if ['day', 'month', 'year'] in kwargs:
                self.date = datetime(kwargs['year'], kwargs['month'], kwargs['day'])
            else:
                now = datetime.now()
                today = datetime(now.year, now.month, now.day) # set time to 00:00:00
                saturday = today + timedelta(days=5-today.weekday())
                sunday = today + timedelta(days=6-today.weekday())
                if today.weekday() == 5:
                    self.date = sunday
                elif today.weekday() == 6:
                    self.date = today + timedelta(days=6)
                else:
                    self.date = saturday

        if (graph := MongoDBDatabaseProxy().get_matchday_graph(self.date)) is not None:
            self.graph = graph
        else:
            # acess the next matchdays for the different competitions and get the matches
            self._get_matches()
            # add the matches as nodes, with a weight parameter that will be defined later and the edges between the matches
            # if it is possible to go from one match to the other and add the time difference in minutes as a weight parameter
            self._matches_to_graph()
            # save the graph in the database
            MongoDBDatabaseProxy().save_matchday_graph(self.date, self.graph)

    def _get_matches(self):
        self._matches = run_matches_spider()
        self._matches = list(filter(lambda x: 'latlon' in x and 'timestamp' in x, self._matches))
        self._matches = sorted(self._matches, key=lambda x: x['timestamp'])

    def node_weight(self, match: list[dict]):
        # TODO: define the weight of the node
        return 1
    
    def _add_nodes(self):
        for match in self._matches:
            self.graph.add_node(f"{match['home_team']}-{match['away_team']}", weight=self.node_weight(match))

    def _add_edges(self):
        valid_matches = [match for match in self._matches if 'latlon' in match]
        for i, origin_match in enumerate(valid_matches):
            for destination_match in valid_matches[i+1:]:
                origin_match_finish_estimation = origin_match['timestamp'] + timedelta(hours=2)
                matches_temporal_distance = OpenRouteServiceProxy(
                    origin_match['latlon'],
                    destination_match['latlon'],
                    origin_match_finish_estimation
                ).temporal_distance()

                if origin_match['timestamp'] + timedelta(minutes=matches_temporal_distance) < destination_match['timestamp']:
                    self.graph.add_edge(
                        f"{origin_match['home_team']}-{origin_match['away_team']}",
                        f"{destination_match['home_team']}-{destination_match['away_team']}",
                        weight=(destination_match['timestamp'] - origin_match['timestamp']).total_seconds() / 60.0)

    def _matches_to_graph(self):
        self.graph = DiGraph()

        self._add_nodes()
        self._add_edges()


