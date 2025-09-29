from abc import ABC, abstractmethod
from typing import List, Dict, Optional


class BaseCrawler(ABC):

    @abstractmethod
    async def fetch_results(self, extra_info: bool = False) -> List[Dict]:
        pass

    @abstractmethod
    async def _get_proxy(self) -> Optional[str]:
        pass
