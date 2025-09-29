from abc import ABC, abstractmethod
from typing import List, Dict


class BaseCrawler(ABC):

    @abstractmethod
    async def fetch_results(self, extra_info: bool = False) -> List[Dict]:
        pass
