from __future__ import annotations

from fastapi import FastAPI

from app.api.auth_controller import router as auth_router
from app.api.catalog_admin_controller import router as catalog_admin_router
from app.api.consent_controller import router as consent_router
from app.api.menu_controller import router as menu_router
from app.api.operations_controller import router as operations_router
from app.api.order_controller import router as order_router
from app.api.payment_webhook_controller import router as webhook_router
from app.api.reports_controller import router as reports_router
from app.api.user_controller import router as user_router

app = FastAPI(
    title="Raízes do Nordeste - API",
    version="0.1.0",
    description="Back-end multicanal",
)

app.include_router(auth_router)
app.include_router(menu_router)
app.include_router(catalog_admin_router)
app.include_router(order_router)
app.include_router(operations_router)
app.include_router(webhook_router)
app.include_router(consent_router)
app.include_router(user_router)
app.include_router(reports_router)


@app.get("/health", tags=["infra"])
def health() -> dict[str, str]:
    """Checagem simples de que a API esta no ar"""
    return {"status": "ok"}
