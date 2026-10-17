from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from app.api.deps import LOGIN, get_ctx
from app.auth import COOKIE_NAME, SESSION_DAYS, check_token, make_token, verify_password
from app.context import AppContext

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict:
    return {"ok": True}


class LoginBody(BaseModel):
    password: str


@router.get("/session")
def session(request: Request, ctx: AppContext = Depends(get_ctx)) -> dict:
    token = request.cookies.get(COOKIE_NAME, "")
    return {
        "logged_in": bool(token) and check_token(ctx.secret_key, token, ctx.session_epoch()),
        "password_configured": bool(ctx.settings.family_password or ctx.settings.family_password_hash),
    }


@router.post("/login")
def login(body: LoginBody, request: Request, response: Response, ctx: AppContext = Depends(get_ctx)) -> dict:
    s = ctx.settings
    if not (s.family_password or s.family_password_hash):
        raise HTTPException(status_code=503, detail="还没有设置家庭密码：在 .env 里填写 XT_FAMILY_PASSWORD 后重启")
    key = request.client.host if request.client else "unknown"
    wait = ctx.rate_limiter.check(key)
    if wait > 0:
        raise HTTPException(status_code=429, detail=f"密码错误次数太多，请 {int(wait // 60) + 1} 分钟后再试")
    if not verify_password(body.password, plain=s.family_password, hashed=s.family_password_hash):
        ctx.rate_limiter.fail(key)
        raise HTTPException(status_code=401, detail="密码不对")
    ctx.rate_limiter.succeed(key)
    response.set_cookie(COOKIE_NAME, make_token(ctx.secret_key, ctx.session_epoch()), max_age=SESSION_DAYS * 86400,
                        httponly=True, samesite="lax", secure=request.url.scheme == "https")
    return {"ok": True}


@router.post("/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}


@router.post("/logout-all", dependencies=LOGIN)
def logout_all(response: Response, ctx: AppContext = Depends(get_ctx)) -> dict:
    ctx.bump_session_epoch()
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}
