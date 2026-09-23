"""Start the realtime API with listener settings from this service's env file."""

import os
from pathlib import Path

import uvicorn
from dotenv import dotenv_values, load_dotenv

from .settings import Settings


def main() -> None:
    load_dotenv(Path(__file__).with_name(".env"), override=False)
    settings = Settings.from_env()
    settings.validate()

    defaults = dotenv_values(Path(__file__).with_name(".env.sample"))
    host = os.getenv("REALTIME_LISTEN_HOST", defaults["REALTIME_LISTEN_HOST"])
    port = int(os.getenv("REALTIME_LISTEN_PORT", defaults["REALTIME_LISTEN_PORT"]))
    workers = int(os.getenv("REALTIME_WORKERS", defaults["REALTIME_WORKERS"]))
    if not 1 <= port <= 65535:
        raise ValueError("REALTIME_LISTEN_PORT must be between 1 and 65535")
    if workers != 1:
        raise ValueError("REALTIME_WORKERS must be 1 because crawl limits are process-local")

    uvicorn.run(
        "craw_real_times.app:app",
        host=host,
        port=port,
        workers=workers,
        access_log=False,
    )


if __name__ == "__main__":
    main()
