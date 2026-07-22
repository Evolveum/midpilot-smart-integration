# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

import asyncio

from hypercorn.asyncio import serve
from hypercorn.config import Config

from src.app import api
from src.common.logger import setup_logging
from src.config import config

setup_logging()


def run_application():
    hypercorn_config = Config()
    hypercorn_config.bind = [f"{config.app.host}:{config.app.port}"]
    hypercorn_config.workers = config.app.workers
    hypercorn_config.root_path = config.app.root_path
    hypercorn_config.keep_alive_timeout = config.app.timeout_keep_alive
    hypercorn_config.graceful_timeout = config.app.timeout_graceful_shutdown
    hypercorn_config.use_reloader = config.app.live_reload

    if config.app.ssl_certfile and config.app.ssl_keyfile:
        hypercorn_config.certfile = config.app.ssl_certfile
        hypercorn_config.keyfile = config.app.ssl_keyfile

    hypercorn_config.accesslog = "-" if config.logging.access_log else None
    hypercorn_config.loglevel = config.logging.level.value.upper()

    if config.app.limit_max_requests:
        hypercorn_config.max_requests = config.app.limit_max_requests

    asyncio.run(serve(api, hypercorn_config))


if __name__ == "__main__":
    run_application()
