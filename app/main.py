from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.mailgun_webhook import router as mailgun_router

def create_app() -> FastAPI:
    app = FastAPI(title="UARB Matter Mail Agent")

    app.include_router(health_router, prefix="/health", tags=["health"])
    app.include_router(mailgun_router, prefix="/webhooks/mailgun", tags=["mailgun"])

    return app

app = create_app()