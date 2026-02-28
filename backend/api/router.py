from fastapi import APIRouter

from backend.api.routes import audit, dashboard, fraud, graph, ingestion, notices, reconciliation, recovery, tax, vendors, websocket

api_router = APIRouter()

api_router.include_router(graph.router)
api_router.include_router(fraud.router)
api_router.include_router(reconciliation.router)
api_router.include_router(vendors.router)
api_router.include_router(notices.router)
api_router.include_router(recovery.router)
api_router.include_router(websocket.router)
api_router.include_router(tax.router)
api_router.include_router(dashboard.router)
api_router.include_router(ingestion.router)
api_router.include_router(audit.router)
