import logging

import uvicorn
from fastapi import FastAPI

from app.config import Settings
from app.step import VisionClipStep

logging.basicConfig(level=logging.INFO)


def create_app() -> FastAPI:
    """Create the FastAPI application for the vision-clip step.

    :returns: Configured FastAPI application exposing KServe V2 endpoints.
    """
    settings = Settings()
    step = VisionClipStep(settings)
    return step.build_app()


app = create_app()

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, log_level="info")
