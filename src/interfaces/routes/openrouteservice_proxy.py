from os.path import dirname, join, abspath
from datetime import datetime
import requests
import json
import time
import logging

from .base_proxy import AbstractRouteProxy

logging.getLogger("requests").setLevel(logging.WARNING)

class OpenRouteServiceProxy(AbstractRouteProxy):

    API_KEY_PATH = join(dirname(abspath(__file__)), '../../../etc/config.json')

    with open(API_KEY_PATH) as json_file:
        config = json.load(json_file)

    API_KEY = config['openrouteservice']['api_key']

    class Location:
        def __init__(self, lat: float, lon: float):
            self.lat = lat
            self.lon = lon

    def route_temporal_distance(self, origin: tuple[float, float], destination: tuple[float, float], departure_time: datetime | None = None) -> float:
        """ Returns the time in minutes between the origin and the destination """
        origin = self.Location(*origin)
        destination = self.Location(*destination)
        departure_time = departure_time.strftime('%Y-%m-%dT%H:%M:%S')

        # API request
        url = f'https://api.openrouteservice.org/v2/directions/driving-car?api_key={self.API_KEY}&start={origin.lon},{origin.lat}&end={destination.lon},{destination.lat}&departure_time={departure_time}&options=timezone:Europe/Madrid'
        
        response = requests.get(url)
        while response.status_code == 429:
            time.sleep(30)
            response = requests.get(url)
        data = json.loads(response.text)

        # Get the duration
        duration = data['features'][0]['properties']['segments'][0]['duration']
        return duration / 60.0