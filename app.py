from __future__ import annotations

import hmac
import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.security import APIKeyHeader

from .errors import CrawlError
from .runtime import CrawlRuntime
from .schemas import CrawlRequest
from .serializers import encode_article_export
from .service import CrawlService
from .settings import Settings
from .site_resolver import supported_sites

LOGGER = logging.getLogger(__name__)


def create_app(settings: Settings | None = None, *, service=None) -> FastAPI:
    settings = settings if settings is not None else Settings.from_env()
    runtime = CrawlRuntime(max_workers=settings.max_concurrent_crawls, timeout=settings.crawl_timeout)
    crawl_service = service if service is not None else CrawlService(settings, runtime.limiter)

    @asynccontextmanager
    async def lifespan(app):
        try:
            settings.validate()
            supported_sites()
            yield
        finally:
            runtime.close()
            crawl_service.close()

    application = FastAPI(title="Realtime News Crawler", version="1.0.0", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

    async def authorize(key: str | None = Depends(api_key_header)):
        if not key or not hmac.compare_digest(key.encode(), settings.api_key.encode()):
            raise CrawlError("UNAUTHORIZED", "A valid X-API-Key is required.", 401)

    @application.middleware("http")
    async def request_context(request: Request, call_next):
        request.state.request_id = str(uuid.uuid4())
        started = time.monotonic()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["Cache-Control"] = "no-store"
        LOGGER.info("request_id=%s path=%s status=%s duration_ms=%s", request.state.request_id, request.url.path, response.status_code, int((time.monotonic() - started) * 1000))
        return response

    @application.exception_handler(CrawlError)
    async def crawl_error(request: Request, exc: CrawlError):
        headers = {"Retry-After": str(settings.retry_after_seconds)} if exc.status_code in (429, 503) and exc.retryable else None
        return JSONResponse(status_code=exc.status_code, headers=headers, content={
            "request_id": request.state.request_id, "status": "error",
            "error": {"code": exc.code, "message": exc.message, "retryable": exc.retryable},
        })

    @application.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content={
            "request_id": request.state.request_id, "status": "error",
            "error": {"code": "INVALID_OPTIONS", "message": "Check url and download_images.", "retryable": False,
                      "details": [{"field": ".".join(map(str, item["loc"])), "message": item["msg"]} for item in exc.errors()]},
        })

    @application.post("/internal/v1/articles/crawl", dependencies=[Depends(authorize)], response_class=Response,
                      responses={200: {"description": "UTF-8 JSON file with the article, image and video rows", "content": {"application/json": {}}}})
    async def crawl(body: CrawlRequest, request: Request):
        try:
            result = await runtime.run(lambda deadline: crawl_service.crawl(body, request.state.request_id, deadline))
        except CrawlError:
            raise
        except Exception as exc:
            LOGGER.error("request_id=%s unexpected_error_type=%s", request.state.request_id, type(exc).__name__)
            raise CrawlError("INTERNAL_ERROR", "The crawl could not be completed.", 500) from None
        article_id = uuid.UUID(result["data"]["articles"][0]["id"])
        return Response(content=encode_article_export(result), media_type="application/json", headers={
            "Content-Disposition": f'attachment; filename="article_{article_id}.json"',
        })

    @application.get("/internal/v1/sites", dependencies=[Depends(authorize)])
    async def sites():
        return {"sites": [{"site_key": key, "base_url": cfg.base_url, "article_name": cfg.resolved_article_name()} for key, cfg in supported_sites().items()]}

    @application.get("/internal/openapi.json", dependencies=[Depends(authorize)], include_in_schema=False)
    async def openapi():
        return application.openapi()

    @application.get("/health/live", include_in_schema=False)
    async def live():
        return {"status": "alive"}

    @application.get("/health/ready", include_in_schema=False)
    async def ready():
        return {"status": "ready", "configured_sources": len(supported_sites())}

    return application


app = create_app()
