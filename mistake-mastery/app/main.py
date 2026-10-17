"""FastAPI 入口：接口 + 前端页面 + 后台任务 + GitHub 同步。"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import auth, bank, capture, core, knowledge, mistakes, printing
from app.config import Settings, get_settings
from app.context import AppContext
from app.services import bank as bank_service
from app.services import capture as capture_service
from app.services import lessons as lessons_service
from app.services import tutoring as tutoring_service
from app.services import printing as printing_service

WEB_DIST = Path(__file__).resolve().parent.parent / "web" / "dist"

log = logging.getLogger(__name__)


def create_app(settings: Settings | None = None, *, start_background: bool = True) -> FastAPI:
    settings = settings or get_settings()
    ctx = AppContext(settings)
    capture_service.register(ctx)
    bank_service.register(ctx)
    printing_service.register(ctx)
    lessons_service.register(ctx)
    tutoring_service.register(ctx)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        if start_background:
            ctx.start()
        yield
        ctx.stop()

    app = FastAPI(title="学透", lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.ctx = ctx
    for r in (auth.router, core.router, capture.router, mistakes.router, printing.router, bank.router,
              knowledge.router):
        app.include_router(r)

    @app.middleware("http")
    async def no_index(request, call_next):  # noqa: ANN001
        response = await call_next(request)
        response.headers["X-Robots-Tag"] = "noindex"
        return response

    if WEB_DIST.exists():
        app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            if path.startswith("api/"):
                return JSONResponse({"detail": "Not Found"}, status_code=404)
            target = (WEB_DIST / path).resolve()
            if path and target.is_file() and WEB_DIST in target.parents:
                return FileResponse(target)
            return FileResponse(WEB_DIST / "index.html")  # 前端路由（含二维码落地页 /p/{id}）

    return app
