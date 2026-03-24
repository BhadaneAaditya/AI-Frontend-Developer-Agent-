"""
Frontend Developer Agent — FastAPI application entry point.

Run:
    python main.py
    # or
    uvicorn main:app --reload
"""

from __future__ import annotations

import logging

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config_loader import config
from api.routes import router

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("frontend_agent")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    app = FastAPI(
        title="Frontend Developer Agent API",
        description=(
            "AI agent that reads frontend tasks, understands design instructions, "
            "and generates production-ready React / Next.js code."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.get("api.cors_origins", ["*"]),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router, prefix="/api/v1")

    @app.on_event("startup")
    async def _startup():
        logger.info("Frontend Developer Agent started on http://%s:%s", config.api_host, config.api_port)
        logger.info("LLM provider: %s  |  model: %s", config.llm_provider, config.llm_model)
        logger.info("Output dir:   %s", config.output_dir)
        logger.info("Docs:         http://%s:%s/docs", config.api_host, config.api_port)

    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=config.api_host,
        port=config.api_port,
        reload=True,
    )
