# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from fastapi import FastAPI

from .config import config
from .router import root_router


def create_api() -> FastAPI:
    """
    Initialize and configure the FastAPI application.

    :return: Configured FastAPI instance.
    """
    git_commit = config.app.git_commit
    commit_info = f" ({git_commit})" if git_commit else ""
    app = FastAPI(title=config.app.title, version=f"0.1.0{commit_info}")
    app.include_router(root_router, prefix=config.app.api_base_url)

    @app.get("/health")
    async def health() -> dict:
        """
        Health check endpoint to verify the service is running.
        """
        return {"message": "OK"}

    return app


api = create_api()
