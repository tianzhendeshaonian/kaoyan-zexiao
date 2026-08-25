from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from .config import settings
from .redis_client import redis_ping
from .api.v1 import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    ok = await redis_ping()
    logger.info("redis ping: {}", ok)
    yield
    try:
        await app.state.redis.close()
    except Exception:
        pass


def create_app() -> FastAPI:
    app = FastAPI(
        title="考研择校小程序 API",
        version="1.0.0",
        debug=settings.DEBUG,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health", tags=["meta"])
    async def health():
        return {"code": 0, "msg": "ok", "data": {"env": settings.APP_ENV}}

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "code": 422,
                "msg": "参数错误",
                "data": exc.errors(),
            },
        )

    @app.exception_handler(Exception)
    async def _exception(request: Request, exc: Exception):
        logger.opt(exception=exc).error("unhandled error on {}", request.url.path)
        code = getattr(exc, "status_code", 500) or 500
        msg = getattr(exc, "detail", "服务异常") if code < 500 else "服务异常"
        if isinstance(exc, HTTPException):
            code = exc.status_code
            msg = exc.detail
        return JSONResponse(
            status_code=code,
            content={"code": code, "msg": msg, "data": None},
        )

    return app


# keep at bottom for circular imports
from fastapi import HTTPException  # noqa: E402

app = create_app()
