from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, List, Optional

from loguru import logger
from neo4j import AsyncGraphDatabase

from backend.config import settings


@dataclass
class Neo4jClient:
    uri: str
    username: str
    password: str

    def __post_init__(self) -> None:
        self._driver = AsyncGraphDatabase.driver(self.uri, auth=(self.username, self.password))

    async def close(self) -> None:
        await self._driver.close()

    async def run_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        params = params or {}
        async with self._driver.session() as session:
            res = await session.run(query, params)
            data = await res.data()
            return data

    @asynccontextmanager
    async def session(self) -> AsyncGenerator["Neo4jClient", None]:
        try:
            yield self
        finally:
            # keep driver open; explicit close on shutdown
            pass


_singleton: Optional[Neo4jClient] = None


def get_neo4j_client() -> Neo4jClient:
    global _singleton
    if _singleton is None:
        _singleton = Neo4jClient(settings.NEO4J_URI, settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
        logger.info("Neo4j client initialized uri={}", settings.NEO4J_URI)
    return _singleton

