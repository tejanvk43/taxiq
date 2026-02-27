import os
from typing import Any, Dict, Optional

from neo4j import AsyncGraphDatabase

from backend.config import settings


class GraphEngine:
    """
    Thin wrapper around the official Neo4j Python driver.
    In MOCK mode, callers should avoid running Cypher and instead return demo data.
    """

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        self.uri = uri or settings.NEO4J_URI
        self.user = user or settings.NEO4J_USERNAME
        self.password = password or settings.NEO4J_PASSWORD
        self._driver = AsyncGraphDatabase.driver(self.uri, auth=(self.user, self.password))

    async def close(self) -> None:
        await self._driver.close()

    async def run_cypher(self, query: str, params: Optional[Dict[str, Any]] = None) -> list[Dict[str, Any]]:
        params = params or {}
        async with self._driver.session() as session:
            result = await session.run(query, params)
            records = await result.data()
            return records
