from os.path import join, dirname, abspath
from pymongo import MongoClient
from datetime import datetime, timedelta
from networkx import DiGraph, readwrite
from itemadapter import ItemAdapter
import json

from .base_proxy import AbstractDatabaseProxy
from src.scraper.scoutingplanner_scrapy.items import Match


class MongoDBDatabaseProxy(AbstractDatabaseProxy):
    _ROOT_DIR = join(dirname(abspath(__file__)), './../../../')
    with open(join(_ROOT_DIR, 'etc/config.json')) as f:
        _config = json.load(f)
        _uri = _config['mongoDB']['uri']
        _certificate_path = join(
            _ROOT_DIR, _config['mongoDB']['certificate_path'])

    def database_connection(func):
        def wrapper(self, *args, **kwargs):
            self.client = MongoClient(
                self._uri, tls=True, tlsCertificateKeyFile=self._certificate_path)
            result = func(self, *args, **kwargs)
            self.client.close()
            return result
        return wrapper
    
    def _kwargs_to_query(self, kwargs: dict) -> tuple[dict]:
        """ Converts kwargs to a tuple of query, sort and projection dicts."""
        query = kwargs
        sort = {}
        projection = {'_id': False}

        if 'sort' in kwargs:
            sort = query.pop('sort')
        if 'projection' in kwargs:
            projection = query.pop('projection')
        else:
            kwargs['projection'] = {'_id': False}
        
        # TODO: Add support for other filters
        if 'timestamp' in kwargs:
            if isinstance(kwargs['timestamp'], dict):
                if '$gte' in kwargs['timestamp'] and '$lt' in kwargs['timestamp']:
                    query['timestamp'] = kwargs['timestamp']
                else:
                    raise TypeError(
                        'timestamp must be a dict with $gte and $lt keys')
            elif isinstance(kwargs['timestamp'], datetime):
                date = kwargs['timestamp'].replace(
                    hour=0, minute=0, second=0, microsecond=0)
                query['timestamp'] = {'$gte': date,
                                      '$lt': date + timedelta(days=1)}
            else:
                raise TypeError('timestamp must be a datetime or a dict')
            
        return query, sort, projection

    @database_connection
    def get_matches(self, season: str, as_dict: bool = False, **kwargs) -> list[Match | dict]:
        query, sort, projection = self._kwargs_to_query(kwargs)

        self.db = self.client.matches
        result = self.db[season].find(query, projection=projection)
        if sort:
            result = result.sort(sort)
        if as_dict:
            return [dict for dict in result]
        return [Match(**dict) for dict in result]

    @database_connection
    def save_match(self, match: Match):
        self.db = self.client.matches
        collection = self.db[match.season]

        keys_dict = {
            'season': match.season,
            'competition': match.competition,
            'group': match.group,
            'matchday': match.matchday,
            'home_team': match.home_team,
            'away_team': match.away_team
        }

        if collection.find_one(keys_dict):
            collection.update_one(
                keys_dict, {'$set': ItemAdapter(match).asdict()})
        else:
            collection.insert_one(ItemAdapter(match).asdict())

    @database_connection
    def get_matchday_graph(self, day: datetime) -> DiGraph | None:
        self.db = self.client.matchday_graphs
        result = self.db.graphs.find_one({'day': day})
        if result is None:
            return None
        return readwrite.json_graph.adjacency_graph(result['graph'], directed=True)

    @database_connection
    def save_matchday_graph(self, day: datetime, graph: DiGraph):
        self.db = self.client.matchday_graphs

        day = day.replace(hour=0, minute=0, second=0, microsecond=0)
        data = readwrite.json_graph.adjacency_data(graph)

        if self.db.graphs.find_one({'day': day}):
            self.db.graphs.update_one({'day': day}, {'$set': {'graph': data}})
        else:
            self.db.graphs.insert_one({'day': day, 'graph': data})

    @database_connection
    def get_competitions(self, season: str, **kwargs) -> list[str]:
        query, _, _ = self._kwargs_to_query(kwargs)

        self.db = self.client.matches
        return self.db[season].distinct('competition')
