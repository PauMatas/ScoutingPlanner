from datetime import datetime, timedelta
from networkx import DiGraph, ancestors, descendants

from interfaces.database import AbstractDatabaseProxy
from interfaces.routes import AbstractRouteProxy
from scraper.scoutingplanner_scrapy.items import Match


class Planner:
    """Planner class."""

    TEAM_SEP_TOKEN = '<vs>'
    ORIGIN_TOKEN = '<start>'
    DESTINATION_TOKEN = '<end>'
    MATCH_ESTIMATED_DURATION = timedelta(hours=2)

    def __init__(self, db_proxy: AbstractDatabaseProxy, routes_proxy: AbstractRouteProxy, matches: list[Match], date: datetime, season: str):
        self.db_proxy = db_proxy
        self.routes_proxy = routes_proxy
        self.matches = matches
        self.date = date
        self.season = season

        self.set_graph() # sets self.graph

    def set_graph(self):
        """Sets self.graph to the graph of the matchday."""

        if (graph := self.db_proxy.get_matchday_graph(self.date)) is not None:
            self.graph = graph

        else:
            self.graph = DiGraph()
            self.add_nodes()
            self.add_edges()

            self.db_proxy.save_matchday_graph(self.graph, self.date)

    def node_weight(self, match: Match) -> float:
        """Returns the weight of a node."""

        # TODO: define the weight of the node
        return 1

    def add_nodes(self):
        """Adds nodes to self.graph."""

        for match in self.matches:
            self.graph.add_node(
                f"{match['home_team']}{self.TEAM_SEP_TOKEN}{match['away_team']}", weight=self.node_weight(match))
            
    def add_edges(self):
        """Adds edges to self.graph."""

        for i, origin_match in enumerate(self.matches):
            for destination_match in self.matches[i+1:]:
                origin_match_finish_estimation = origin_match['timestamp'] + self.MATCH_ESTIMATED_DURATION
                matches_temporal_distance = self.routes_proxy.route_temporal_distance(
                    origin_match['latlon'],
                    destination_match['latlon'],
                    origin_match_finish_estimation
                )

                if origin_match['timestamp'] + timedelta(minutes=matches_temporal_distance) < destination_match['timestamp']:
                    self.graph.add_edge(
                        f"{origin_match['home_team']}{self.TEAM_SEP_TOKEN}{origin_match['away_team']}",
                        f"{destination_match['home_team']}{self.TEAM_SEP_TOKEN}{destination_match['away_team']}",
                        weight=(destination_match['timestamp'] - origin_match['timestamp']).total_seconds() / 60.0)
                    
    def routes(self, **kwargs) -> list[list[Match]]:
        """ Returns a list of lists of matches that correspond to the paths (routes) with the more weighted nodes (matches) in the graph.
        """

        self.set_routes_graph(**kwargs)
        if not self.routes_graph.nodes:
            return []
        
        return [
            [
                self.db_proxy.get_matches(
                    season=self.season,
                    timestamp=self.date,
                    home_team=node.split('<vs>')[0],
                    away_team=node.split('<vs>')[1])[0]
                for node in path]
            for path in self.routes_graph_most_interesting_paths()]
    
    def set_routes_graph(self, origin: None | tuple[float] = None, destination: None | tuple[float] = None,
        departure_time: str | datetime | None = None, arrival_time: str | datetime | None = None,
        wanted_matches: list[str] | str | list[tuple] | tuple | None = None, unwanted_matches: list[str] | str | list[tuple] | tuple | None = None,
        wanted_competitions: list[str] | str | None = None, unwanted_competitions: list[str] | str | None = None
        ):
        """Sets self.routes_graph as a subgraph of self.graph that forces the specified conditions for the routes."""

        conditions = self._check_routes_conditions(origin, destination, departure_time, arrival_time, wanted_matches, unwanted_matches, wanted_competitions, unwanted_competitions)

        nodes = self.wanted_nodes(conditions['wanted_matches'], conditions['unwanted_matches'], conditions['wanted_competitions'], conditions['unwanted_competitions'])
        self.routes_graph = self.graph.subgraph(nodes).copy()

        if conditions['origin'] is not None and conditions['departure_time'] is not None:
            self.add_origin_to_routes_graph(conditions['origin'], conditions['departure_time'])
        if conditions['destination'] is not None and conditions['arrival_time'] is not None:
            self.add_destination_to_routes_graph(conditions['destination'], conditions['arrival_time'])

    def routes_graph_most_interesting_paths(self) -> list[list[str]]:
        """ Returns a list of paths that correspond to the most interesting paths in the graph.
        """
        
        source_nodes = [node for node in self.routes_graph.nodes if self.routes_graph.in_degree(node) == 0]
        most_interesting_paths_to = {
            node: {
                'weight': 0,
                'paths': set()  # set of paths
            } if node not in source_nodes else {
                'weight': self.routes_graph.nodes[node]['weight'],
                'paths': {node}  # set of paths
            } for node in self.routes_graph.nodes
        }
        queue = source_nodes.copy()

        while len(queue) > 0:
            orig = queue.pop(0)
            for edge in self.routes_graph.edges(orig):
                dest = edge[1]
                if most_interesting_paths_to[orig]['weight'] + self.routes_graph.nodes[dest]['weight'] > most_interesting_paths_to[dest]['weight']:
                    most_interesting_paths_to[dest]['weight'] = most_interesting_paths_to[orig]['weight'] + \
                        self.routes_graph.nodes[dest]['weight']
                    most_interesting_paths_to[dest]['paths'] = {
                        '%'.join((path, dest)) for path in most_interesting_paths_to[orig]['paths']}
                    queue.append(dest)
                elif most_interesting_paths_to[orig]['weight'] + self.routes_graph.nodes[dest]['weight'] == most_interesting_paths_to[dest]['weight']:
                    most_interesting_paths_to[dest]['paths'] |= {
                        '%'.join((path, dest))
                        for path in most_interesting_paths_to[orig]['paths']}
                    queue.append(dest)

        # get the most interesting paths with the maximum weight and return them
        max_weight = max(most_interesting_paths_to.values(),
                         key=lambda x: x['weight'])['weight']
        most_interesting_paths = [list(
            v['paths']) for v in most_interesting_paths_to.values() if v['weight'] == max_weight]
        result = []
        for paths in most_interesting_paths:
            result += [path.split('%') for path in paths]
        return result

    def wanted_nodes(self, wanted_matches: list[str], unwanted_matches: list[str], wanted_competitions: list[str], unwanted_competitions: list[str]) -> set[str]:
        """Returns a set of nodes that correspond to the wanted nodes."""

        nodes = set(self.graph.nodes)
        for node in self.graph.nodes:
            if node in nodes and unwanted_matches is not None and node in unwanted_matches:
                nodes.remove(node)
            if node in nodes and wanted_matches is not None:
                ancestors_and_descendants = ancestors(
                    self.graph, node) | descendants(self.graph, node) | {node}
                for wanted_match in wanted_matches:
                    if node in nodes and wanted_match not in ancestors_and_descendants:
                        nodes.remove(node)
            if node in nodes and wanted_competitions is not None and self.db_proxy.get_matches(season=self.season, timestamp=self.date, home_team=node.split(self.TEAM_SEP_TOKEN)[0], away_team=node.split(self.TEAM_SEP_TOKEN)[1])[0].competition not in wanted_competitions:
                nodes.remove(node)
            if node in nodes and unwanted_competitions is not None and self.db_proxy.get_matches(season=self.season, timestamp=self.date, home_team=node.split(self.TEAM_SEP_TOKEN)[0], away_team=node.split(self.TEAM_SEP_TOKEN)[1])[0].competition in unwanted_competitions:
                nodes.remove(node)
        return nodes
    
    def add_origin_to_routes_graph(self, origin: tuple[float], departure_time: datetime):
        """Leaves in the routes graph only the nodes that are reachable from the origin."""

        self.routes_graph.add_node(self.ORIGIN_TOKEN, weight=0)
        for node in self.routes_graph.nodes:
            if node != self.ORIGIN_TOKEN:
                match = self.db_proxy.get_matches(
                    season=self.season, timestamp=self.date, home_team=node.split(self.TEAM_SEP_TOKEN)[0], away_team=node.split(self.TEAM_SEP_TOKEN)[1])[0]
                matches_temporal_distance = self.routes_proxy.route_temporal_distance(
                    origin,
                    match.latlon,
                    departure_time
                )
                if departure_time + timedelta(minutes=matches_temporal_distance) < match.timestamp:
                    self.routes_graph.add_edge(self.ORIGIN_TOKEN, node, weight=(
                        (match.timestamp - departure_time).total_seconds() / 60.0))
        self.routes_graph.remove_nodes_from(
            [node for node in self.routes_graph.nodes if node != self.ORIGIN_TOKEN and self.ORIGIN_TOKEN not in ancestors(self.routes_graph, node)])
        self.routes_graph.remove_node(self.ORIGIN_TOKEN)

    def add_destination_to_routes_graph(self, destination: tuple[float], arrival_time: datetime):
        """Leaves in the routes graph only the nodes that can reach the destination."""

        self.routes_graph.add_node(self.DESTINATION_TOKEN, weight=0)
        for node in self.routes_graph.nodes:
            if node != self.DESTINATION_TOKEN:
                match = self.db_proxy.get_matches(
                    season=self.season, timestamp=self.date, home_team=node.split(self.TEAM_SEP_TOKEN)[0], away_team=node.split(self.TEAM_SEP_TOKEN)[1])[0]
                origin_match_finish_estimation = match.timestamp + self.MATCH_ESTIMATED_DURATION
                matches_temporal_distance = self.routes_proxy.route_temporal_distance(
                    match.latlon,
                    destination,
                    origin_match_finish_estimation
                )
                if origin_match_finish_estimation + timedelta(minutes=matches_temporal_distance) < arrival_time:
                    self.routes_graph.add_edge(node, self.DESTINATION_TOKEN, weight=(
                        (arrival_time - origin_match_finish_estimation).total_seconds() / 60.0))
        self.routes_graph.remove_nodes_from(
            [node for node in self.routes_graph.nodes if node != self.DESTINATION_TOKEN and self.DESTINATION_TOKEN not in descendants(self.routes_graph, node)])
        self.routes_graph.remove_node(self.DESTINATION_TOKEN)

    def _check_routes_conditions(self, origin: None | tuple[float] = None, destination: None | tuple[float] = None,
        departure_time: str | datetime | None = None, arrival_time: str | datetime | None = None,
        wanted_matches: list[str] | str | list[tuple] | tuple | None = None, unwanted_matches: list[str] | str | list[tuple] | tuple | None = None,
        wanted_competitions: list[str] | str | None = None, unwanted_competitions: list[str] | str | None = None
        ) -> dict[str, bool]:
        """Returns a dictionary with the conditions if they are met."""

        conditions = {
            'origin': origin,
            'destination': destination,
            'departure_time': departure_time,
            'arrival_time': arrival_time,
            'wanted_matches': wanted_matches,
            'unwanted_matches': unwanted_matches,
            'wanted_competitions': wanted_competitions,
            'unwanted_competitions': unwanted_competitions
        }

        if departure_time is not None and origin is None:
            raise ValueError(
                'If departure_time is specified, origin must be specified too.')
        if arrival_time is not None and destination is None:
            raise ValueError(
                'If arrival_time is specified, destination must be specified too.')
        if isinstance(departure_time, str):
            conditions['departure_time'] = self.date.replace(
                hour=int(departure_time.split(':')[0]), minute=int(departure_time.split(':')[1]))
        if isinstance(arrival_time, str):
            conditions['arrival_time'] = self.date.replace(
                hour=int(arrival_time.split(':')[0]), minute=int(arrival_time.split(':')[1]))
        if wanted_matches is not None:
            if not isinstance(wanted_matches, list):
                conditions['wanted_matches'] = [wanted_matches]
            for i, wanted_match in enumerate(wanted_matches):
                if isinstance(wanted_match, str):
                    if self.TEAM_SEP_TOKEN not in wanted_match:
                        raise ValueError(
                            f'wanted_matches must be a list of strings with the format "<home_team>{self.TEAM_SEP_TOKEN}<away_team>"')
                elif isinstance(wanted_match, tuple):
                    if len(wanted_match) != 2:
                        raise ValueError(
                            'wanted_matches must be a list of tuples with the format (<home_team>, <away_team>)')
                    else:
                        conditions['wanted_matches'][i] = self.TEAM_SEP_TOKEN.join(wanted_match)
                else:
                    raise TypeError(
                        'wanted_matches must be a list of strings or tuples')
        if unwanted_matches is not None:
            if not isinstance(unwanted_matches, list):
                conditions['unwanted_matches'] = [unwanted_matches]
            for i, unwanted_match in enumerate(unwanted_matches):
                if isinstance(unwanted_match, str):
                    if self.TEAM_SEP_TOKEN not in unwanted_match:
                        raise ValueError(
                            'unwanted_matches must be a list of strings with the format "{home_team}<vs>{away_team}"')
                elif isinstance(unwanted_match, tuple):
                    if len(unwanted_match) != 2:
                        raise ValueError(
                            'unwanted_matches must be a list of tuples with the format ({home_team}, {away_team})')
                    else:
                        conditions['unwanted_matches'][i] = self.TEAM_SEP_TOKEN.join(unwanted_match)
                else:
                    raise TypeError(
                        'unwanted_matches must be a list of strings or tuples')
        if isinstance(wanted_competitions, str):
            conditions['wanted_competitions'] = [wanted_competitions]
        if isinstance(unwanted_competitions, str):
            conditions['unwanted_competitions'] = [unwanted_competitions]

        return conditions



