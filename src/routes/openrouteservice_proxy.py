from os.path import dirname, join, abspath
from datetime import datetime
import requests
import json
import time
import logging

logging.getLogger("requests").setLevel(logging.WARNING)

from .base_proxy import AbstractRouteProxy

class OpenRouteServiceProxy(AbstractRouteProxy):

    API_KEY_PATH = join(dirname(abspath(__file__)), '../../etc/config.json')

    with open(API_KEY_PATH) as json_file:
        config = json.load(json_file)

    API_KEY = config['openrouteservice']['api_key']

    class Location:
        def __init__(self, lat: float, lon: float):
            self.lat = lat
            self.lon = lon

    def __init__(self, origin: tuple[float, float], destination: tuple[float, float], departure_time: datetime | None = None):
        """ 
        Creates a proxy to the OpenRouteService API.
        """
        self.origin = self.Location(*origin)
        self.destination = self.Location(*destination)
        self.departure_time = departure_time.strftime('%Y-%m-%dT%H:%M:%S')

    def temporal_distance(self) -> float:
        """ Returns the time in minutes between the origin and the destination """
        # API request
        url = f'https://api.openrouteservice.org/v2/directions/driving-car?api_key={self.API_KEY}&start={self.origin.lon},{self.origin.lat}&end={self.destination.lon},{self.destination.lat}&departure_time={self.departure_time}&options=timezone:Europe/Madrid'
        
        response = requests.get(url)
        while response.status_code == 429:
            time.sleep(30)
            response = requests.get(url)
        data = json.loads(response.text)

        # Get the duration
        duration = data['features'][0]['properties']['segments'][0]['duration']
        return duration / 60.0