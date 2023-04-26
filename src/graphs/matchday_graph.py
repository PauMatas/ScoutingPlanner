import networkx as nx
from networkx import DiGraph
from datetime import datetime, timedelta

from src.interfaces.scraper import run_matches_spider
from src.interfaces.database import MongoDBDatabaseProxy
from src.routes import OpenRouteServiceProxy
from src.scraper.scoutingplanner_scrapy.items import Match


class MatchDayGraph:
    db_proxy = MongoDBDatabaseProxy()
    season = 'TEMPORADA 2022-2023'

    def __init__(self, date: datetime | str = None, **kwargs):
        if isinstance(date, datetime):
            self.date = date
        elif isinstance(date, str):
            self.date = datetime.strptime(
                date, kwargs.get('format', '%d-%m-%Y'))
        elif date is None:
            if ['day', 'month', 'year'] in kwargs:
                self.date = datetime(
                    kwargs['year'], kwargs['month'], kwargs['day'])
            else:
                now = datetime.now()
                # set time to 00:00:00
                today = datetime(now.year, now.month, now.day)
                saturday = today + timedelta(days=5-today.weekday())
                sunday = today + timedelta(days=6-today.weekday())
                if today.weekday() == 5:
                    self.date = sunday
                elif today.weekday() == 6:
                    self.date = today + timedelta(days=6)
                else:
                    self.date = saturday

        if (graph := self.db_proxy.get_matchday_graph(self.date)) is not None:
            self.graph = graph
            self._get_matches()
        else:
            run_matches_spider()
            # acess the next matchdays for the different competitions and get the matches
            self._get_matches()
            # add the matches as nodes, with a weight parameter that will be defined later and the edges between the matches
            # if it is possible to go from one match to the other and add the time difference in minutes as a weight parameter
            self._matches_to_graph()
            # save the graph in the database
            self.db_proxy.save_matchday_graph(self.date, self.graph)

    def _get_matches(self):
        self.matches = self.db_proxy.get_matches(
            season=self.season, as_dict=True, timestamp=self.date)
        self.matches = list(filter(
            lambda x: 'latlon' in x and x['latlon'] is not None and 'timestamp' in x and x['timestamp'] is not None, self.matches))
        self.matches = sorted(self.matches, key=lambda x: x['timestamp'])

    def node_weight(self, match: list[dict]):
        # TODO: define the weight of the node
        return 1

    def _add_nodes(self):
        for match in self.matches:
            self.graph.add_node(
                f"{match['home_team']}<vs>{match['away_team']}", weight=self.node_weight(match))

    def _add_edges(self):
        valid_matches = [match for match in self.matches if 'latlon' in match]
        for i, origin_match in enumerate(valid_matches):
            for destination_match in valid_matches[i+1:]:
                origin_match_finish_estimation = origin_match['timestamp'] + timedelta(
                    hours=2)
                matches_temporal_distance = OpenRouteServiceProxy(
                    origin_match['latlon'],
                    destination_match['latlon'],
                    origin_match_finish_estimation
                ).temporal_distance()

                if origin_match['timestamp'] + timedelta(minutes=matches_temporal_distance) < destination_match['timestamp']:
                    self.graph.add_edge(
                        f"{origin_match['home_team']}<vs>{origin_match['away_team']}",
                        f"{destination_match['home_team']}<vs>{destination_match['away_team']}",
                        weight=(destination_match['timestamp'] - origin_match['timestamp']).total_seconds() / 60.0)

    def _matches_to_graph(self):
        self.graph = DiGraph()

        self._add_nodes()
        self._add_edges()

    def _most_interesting_paths(self, G: DiGraph) -> list[list[str]]:
        """ Returns a list of paths that correspond to the most interesting paths in the graph.
        """
        source_nodes = [node for node in G.nodes if G.in_degree(node) == 0]
        most_interesting_paths_to = {
            node: {
                'weight': 0,
                'paths': set()  # set of paths
            } if node not in source_nodes else {
                'weight': G.nodes[node]['weight'],
                'paths': {node}  # set of paths
            } for node in G.nodes
        }
        queue = source_nodes.copy()

        while len(queue) > 0:
            orig = queue.pop(0)
            for edge in G.edges(orig):
                dest = edge[1]
                if most_interesting_paths_to[orig]['weight'] + G.nodes[dest]['weight'] > most_interesting_paths_to[dest]['weight']:
                    most_interesting_paths_to[dest]['weight'] = most_interesting_paths_to[orig]['weight'] + \
                        G.nodes[dest]['weight']
                    most_interesting_paths_to[dest]['paths'] = {
                        '%'.join((path, dest)) for path in most_interesting_paths_to[orig]['paths']}
                    queue.append(dest)
                elif most_interesting_paths_to[orig]['weight'] + G.nodes[dest]['weight'] == most_interesting_paths_to[dest]['weight']:
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

    def _add_origin_to_graph(self, G: DiGraph, origin: tuple[float], departure_time: datetime) -> DiGraph:
        """ Adds the origin node to the graph and the edges from the origin to the nodes that are reachable from the origin.
        """
        G.add_node('<start>', weight=0)
        for node in G.nodes:
            if node != '<start>':
                match = self.db_proxy.get_matches(
                    season=self.season, timestamp=self.date, home_team=node.split('<vs>')[0], away_team=node.split('<vs>')[1])[0]
                matches_temporal_distance = OpenRouteServiceProxy(
                    origin,
                    match.latlon,
                    departure_time
                ).temporal_distance()
                if departure_time + timedelta(minutes=matches_temporal_distance) < match.timestamp:
                    G.add_edge('<start>', node, weight=(
                        (match.timestamp - departure_time).total_seconds() / 60.0))
        G.remove_nodes_from(
            [node for node in G.nodes if node != '<start>' and '<start>' not in nx.ancestors(G, node)])
        G.remove_node('<start>')
        return G

    def _add_destination_to_graph(self, G: DiGraph, destination: tuple[float], arrival_time: datetime) -> DiGraph:
        """ Adds the destination node to the graph and the edges from the nodes that can reach destination.
        """
        G.add_node('<end>', weight=0)
        for node in G.nodes:
            if node != '<end>':
                match = self.db_proxy.get_matches(
                    season=self.season, timestamp=self.date, home_team=node.split('<vs>')[0], away_team=node.split('<vs>')[1])[0]
                origin_match_finish_estimation = match.timestamp + timedelta(
                    hours=2)
                matches_temporal_distance = OpenRouteServiceProxy(
                    match.latlon,
                    destination,
                    origin_match_finish_estimation
                ).temporal_distance()
                if origin_match_finish_estimation + timedelta(minutes=matches_temporal_distance) < arrival_time:
                    G.add_edge(node, '<end>', weight=(
                        (arrival_time - origin_match_finish_estimation).total_seconds() / 60.0))
        G.remove_nodes_from(
            [node for node in G.nodes if node != '<end>' and '<end>' not in nx.descendants(G, node)])
        G.remove_node('<end>')
        return G

    def _adapt_graph_to_route(
        self, origin: None | tuple[float] = None, destination: None | tuple[float] = None,
        departure_time: str | datetime | None = None, arrival_time: str | datetime | None = None,
        wanted_matches: list[str] | str | list[tuple] | tuple | None = None, unwanted_matches: list[str] | str | list[tuple] | tuple | None = None,
        wanted_competitions: list[str] | str | None = None, unwanted_competitions: list[str] | str | None = None,
    ) -> DiGraph:
        if departure_time is not None and origin is None:
            raise ValueError(
                'If departure_time is specified, origin must be specified too.')
        if arrival_time is not None and destination is None:
            raise ValueError(
                'If arrival_time is specified, destination must be specified too.')
        if isinstance(departure_time, str):
            departure_time = self.date.replace(
                hour=int(departure_time.split(':')[0]), minute=int(departure_time.split(':')[1]))
        if isinstance(arrival_time, str):
            arrival_time = self.date.replace(
                hour=int(arrival_time.split(':')[0]), minute=int(arrival_time.split(':')[1]))
        if wanted_matches is not None:
            if not isinstance(wanted_matches, list):
                wanted_matches = [wanted_matches]
            for i, wanted_match in enumerate(wanted_matches):
                if isinstance(wanted_match, str):
                    if '<vs>' not in wanted_match:
                        raise ValueError(
                            'wanted_matches must be a list of strings with the format "{home_team}<vs>{away_team}"')
                elif isinstance(wanted_match, tuple):
                    if len(wanted_match) != 2:
                        raise ValueError(
                            'wanted_matches must be a list of tuples with the format ({home_team}, {away_team})')
                    else:
                        wanted_matches[i] = '<vs>'.join(wanted_match)
                else:
                    raise TypeError(
                        'wanted_matches must be a list of strings or tuples')
        if unwanted_matches is not None:
            if not isinstance(unwanted_matches, list):
                unwanted_matches = [unwanted_matches]
            for i, unwanted_match in enumerate(unwanted_matches):
                if isinstance(unwanted_match, str):
                    if '<vs>' not in unwanted_match:
                        raise ValueError(
                            'unwanted_matches must be a list of strings with the format "{home_team}<vs>{away_team}"')
                elif isinstance(unwanted_match, tuple):
                    if len(unwanted_match) != 2:
                        raise ValueError(
                            'unwanted_matches must be a list of tuples with the format ({home_team}, {away_team})')
                    else:
                        unwanted_matches[i] = '<vs>'.join(unwanted_match)
                else:
                    raise TypeError(
                        'unwanted_matches must be a list of strings or tuples')
        if isinstance(wanted_competitions, str):
            wanted_competitions = [wanted_competitions]
        if isinstance(unwanted_competitions, str):
            unwanted_competitions = [unwanted_competitions]

        nodes = set(self.graph.nodes)
        for node in self.graph.nodes:
            if node in nodes and unwanted_matches is not None and node in unwanted_matches:
                nodes.remove(node)
            if node in nodes and wanted_matches is not None:
                ancestors_and_descendants = nx.ancestors(
                    self.graph, node) | nx.descendants(self.graph, node) | {node}
                for wanted_match in wanted_matches:
                    if node in nodes and wanted_match not in ancestors_and_descendants:
                        nodes.remove(node)
            if node in nodes and wanted_competitions is not None and self.db_proxy.get_matches(season=self.season, timestamp=self.date, home_team=node.split('<vs>')[0], away_team=node.split('<vs>')[1])[0].competition not in wanted_competitions:
                nodes.remove(node)
            if node in nodes and unwanted_competitions is not None and self.db_proxy.get_matches(season=self.season, timestamp=self.date, home_team=node.split('<vs>')[0], away_team=node.split('<vs>')[1])[0].competition in unwanted_competitions:
                nodes.remove(node)

        G = self.graph.subgraph(nodes).copy()

        if origin is not None and departure_time is not None:
            G = self._add_origin_to_graph(G, origin, departure_time)
        if destination is not None and arrival_time is not None:
            G = self._add_destination_to_graph(G, destination, arrival_time)

        return G

    def routes(self, **kwargs) -> list[list[Match]]:
        """ Returns a list of matches that correspond to the path with the more weighted nodes in the graph.
        """
        G = self._adapt_graph_to_route(**kwargs)
        if not G.nodes:
            return []
        most_interesting_paths = self._most_interesting_paths(G)
        return [
            [
                self.db_proxy.get_matches(
                    season=self.season,
                    timestamp=self.date,
                    home_team=node.split('<vs>')[0],
                    away_team=node.split('<vs>')[1])[0]
                for node in path]
            for path in most_interesting_paths]
