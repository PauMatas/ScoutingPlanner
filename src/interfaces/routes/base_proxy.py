from abc import ABC, abstractmethod
from datetime import datetime

class AbstractRouteProxy(ABC):

    @abstractmethod
    def route_temporal_distance(self, origin: tuple[float, float], destination: tuple[float, float], departure_time: datetime | None = None) -> float:
        """ Returns the time in minutes between the origin and the destination """
        raise NotImplementedError