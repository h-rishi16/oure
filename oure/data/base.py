"""
OURE Data Ingestion Layer - Base
==================================
Abstract base class for all data fetchers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseDataFetcher(ABC):
    """
    Forces all fetchers to implement the same interface.
    The CLI and higher layers only talk to this abstraction,
    making it trivial to swap in test stubs or future data sources.
    """

    @abstractmethod
    def fetch(self, **kwargs: Any) -> list[Any]:
        """Fetch data, hitting cache first, network second."""
        ...

    @abstractmethod
    def _fetch_from_network(self, **kwargs: Any) -> list[Any]:
        """Raw network call — no caching logic here."""
        ...
