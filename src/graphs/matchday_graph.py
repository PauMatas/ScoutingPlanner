import networkx as nx
from datetime import timedelta

from src.interfaces.scraper import run_matches_spider
from src.routes import OpenRouteServiceProxy

class MatchDayGraph:
    def __init__(self):
        # acess the next matchdays for the different competitions and get the matches
        self._matches = run_matches_spider()
        self._matches = sorted(self._matches, key=lambda x: x['timestamp'])

        # add the matches as nodes, with a weight parameter that will be defined later and the edges between the matches
        # if it is possible to go from one match to the other and add the time difference in minutes as a weight parameter
        self._matches_to_graph()

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
        self.graph = nx.Graph()

        self._add_nodes()
        self._add_edges()


