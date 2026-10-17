from fastapi import Depends, HTTPException, Request

from app.auth import require_login
from app.context import AppContext


def get_ctx(request: Request) -> AppContext:
    return request.app.state.ctx


LOGIN = [Depends(require_login)]


def not_found(what: str = "记录") -> HTTPException:
    return HTTPException(status_code=404, detail=f"{what}不存在")


def bad_request(msg: str) -> HTTPException:
    return HTTPException(status_code=400, detail=msg)
