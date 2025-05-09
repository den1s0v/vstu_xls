from abc import ABC, abstractmethod


class AbstractGridBuilder(ABC):
    """
    Abstract base class for all converters.
    """  

    @abstractmethod
    def _load_cells(self, data):
        """
        Convert the given data to the desired format.
        """
        pass
