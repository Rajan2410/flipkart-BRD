from fastapi import APIRouter

from app.api.routes import admin, auth, orders, picking, reports

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(admin.router)
api_router.include_router(orders.router)
api_router.include_router(picking.router)
api_router.include_router(reports.router)
