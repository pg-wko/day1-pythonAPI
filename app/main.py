import os
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from nicegui import ui
import uvicorn

from app.api import create_api_router
from app.database import TicketRepository
from app.ui import mount_ui


def create_app(database_path: str | None = None, seed: bool = True) -> FastAPI:
    repository = TicketRepository(database_path or os.getenv("TICKET_DB_PATH", "data/tickets.duckdb"))
    if seed:
        repository.seed_defaults()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            repository.close()

    app = FastAPI(title="Ticketing System", version="0.1.0", lifespan=lifespan)
    app.include_router(create_api_router(repository))

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    mount_ui(repository)
    # Use environment variable for storage secret, or generate a secure random one
    storage_secret = os.getenv("NICEGUI_SECRET", secrets.token_urlsafe(32))
    ui.run_with(app, title="Ticketing System", favicon="T", storage_secret=storage_secret)
    return app


if __name__ in {"__main__", "__mp_main__"}:
    app = create_app()
    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("PORT", "8000")))
else:
    # For imports, don't create the global app to avoid locking the database during testing
    app = None
