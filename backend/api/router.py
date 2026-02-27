from fastapi import APIRouter

from backend.api.routes import fraud, graph, notices, reconciliation, recovery, vendors, websocket

api_router = APIRouter()

api_router.include_router(graph.router)
api_router.include_router(fraud.router)
api_router.include_router(reconciliation.router)
api_router.include_router(vendors.router)
api_router.include_router(notices.router)
api_router.include_router(recovery.router)
api_router.include_router(websocket.router)
