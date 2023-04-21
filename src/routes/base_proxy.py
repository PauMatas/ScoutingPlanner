from abc import ABC, abstractmethod
from datetime import datetime

class AbstractRouteProxy(ABC):
    @abstractmethod
    def __init__(self, origin: tuple[float, float], destination: tuple[float, float], departure_time: datetime | None = None):
        raise NotImplementedError

    @abstractmethod
    def temporal_distance(self) -> float:
        """ Returns the time in minutes between the origin and the destination """
        raise NotImplementedError