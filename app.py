"""Local dashboard and hosted access with device-local credentials."""
import asyncio
import secrets
import os
from contextlib import asynccontextmanager
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
import httpx
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from config import CONFIG_PATH, ROOT, Settings, HoyoSettings, load_config, save_config
from errors import HubError
from enka_client import allowed_image
from services import HubService
from hoyolab_client import HoYoLABClient
from datetime import datetime, timezone


def merge(target, changes):
    for key, value in changes.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            merge(target[key], value)
        else:
            target[key] = value
    return target


def create_app(config_path=CONFIG_PATH, service=None):
    public_mode = os.environ.get("VERCEL") == "1" or os.environ.get("HOYO_HUB_PUBLIC") == "1"
    # Host policy is read once at startup; changing it requires a restart.
    settings = Settings() if public_mode else load_config(config_path)

    @asynccontextmanager
    async def lifespan(app):
        app.state.hub = service or HubService(settings if public_mode else load_config(config_path))
        app.state.csrf = secrets.token_urlsafe(32)
        app.state.config_lock = asyncio.Lock()
        yield
        await app.state.hub.close()

    app = FastAPI(title="HoYo-Akasha Hub", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    hosts = settings.server.trusted_hosts
    if public_mode:
        hosts += [os.environ[key] for key in ("VERCEL_URL", "VERCEL_PROJECT_PRODUCTION_URL", "VERCEL_BRANCH_URL") if os.environ.get(key)]
        hosts += [host.strip() for host in os.environ.get("HOYO_HUB_ALLOWED_HOSTS", "").split(",") if host.strip()]
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts)
    app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
    templates = Jinja2Templates(directory=ROOT / "templates")

    @app.middleware("http")
    async def local_security(request, call_next):
        if public_mode and (request.url.path.startswith("/api/v1/auth/") or request.url.path in (
                "/api/v1/notes", "/api/v1/explore", "/api/v1/accounts/hoyolab")
                or (request.url.path == "/api/v1/config" and request.method != "GET")):
            return JSONResponse({"error": {"code": "PUBLIC_ONLY", "message": "Use browser-local settings and request-scoped HoYoLAB endpoints on this hosted site."}}, 403)
        if request.method in ("POST", "PATCH", "DELETE", "PUT"):
            origin = request.headers.get("origin", "")
            parsed = urlsplit(origin)
            if (parsed.scheme not in ("http", "https") or parsed.netloc != request.headers.get("host")
                    or (not public_mode and not secrets.compare_digest(request.headers.get("x-csrf-token", ""), request.app.state.csrf))):
                return JSONResponse({"error": {"code": "INVALID_ORIGIN", "message": "Reload the local dashboard and retry."}}, 403)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; font-src 'self'; "
            "img-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        return response

    @app.exception_handler(HubError)
    async def hub_error(request, exc):
        return JSONResponse(exc.payload(), exc.status)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        return JSONResponse({"error": {"code": "INVALID_INPUT", "message": "Invalid request fields."}}, 422)

    @app.exception_handler(Exception)
    async def unexpected_error(request, exc):
        return JSONResponse({"error": {"code": "INTERNAL_ERROR", "message": "Request could not be completed."}}, 500)

    async def body(request):
        # Do not allow unbounded cookie/config payloads.
        payload = bytearray()
        async for chunk in request.stream():
            payload.extend(chunk)
            if len(payload) > 16384:
                raise HubError("PAYLOAD_TOO_LARGE", "Request exceeds 16 KB.", status=413)
        import json
        try:
            result = json.loads(payload)
            if not isinstance(result, dict):
                raise ValueError
            return result
        except (ValueError, UnicodeDecodeError):
            raise HubError("INVALID_JSON", "Expected a JSON object.", status=400) from None

    async def update(request, changes, auth=False):
        async with app.state.config_lock:
            current = load_config(config_path, env=False)
            data = current.model_dump()
            if "hoyolab" in changes and not isinstance(changes["hoyolab"], dict):
                raise HubError("INVALID_CONFIG", "hoyolab must be an object.", status=422)
            if not auth and "cookies" in changes.get("hoyolab", {}):
                raise HubError("INVALID_INPUT", "Use the authentication endpoint for cookies.", status=400)
            try:
                settings = Settings.model_validate(merge(data, changes))
            except (ValidationError, TypeError, ValueError):
                raise HubError("INVALID_CONFIG", "Invalid configuration. Check UID and field types.", status=422) from None
            save_config(settings, config_path)
            app.state.hub.reload(load_config(config_path))
            return {"data": app.state.hub.config()}

    @app.get("/")
    @app.get("/showcase")
    @app.get("/rankings")
    @app.get("/notes")
    @app.get("/explore")
    @app.get("/settings")
    async def dashboard(request: Request):
        return templates.TemplateResponse(request=request, name="dashboard.html",
            context={"csrf": app.state.csrf, "accent": app.state.hub.settings.ui.accent, "public_mode": public_mode})

    @app.get("/api/v1/health")
    async def health():
        return {"data": {"status": "ok", "version": "1.0.0"}}

    @app.get("/api/v1/status")
    async def status():
        return app.state.hub.status()

    @app.get("/api/v1/image")
    async def image(src: str):
        if not allowed_image(src):
            raise HubError("INVALID_IMAGE", "Unsupported image source.", status=400)
        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
                response = await client.get(src)
            if response.status_code != 200 or not response.content:
                raise HubError("IMAGE_UNAVAILABLE", "Image could not be loaded.", status=502)
            return Response(response.content, media_type="image/png")
        except httpx.HTTPError:
            raise HubError("IMAGE_UNAVAILABLE", "Image could not be loaded.", status=502) from None

    @app.get("/api/v1/config")
    async def config():
        return {"data": app.state.hub.config()}

    @app.patch("/api/v1/config")
    async def patch_config(request: Request):
        return await update(request, await body(request))

    @app.post("/api/v1/auth/hoyolab")
    async def auth(request: Request):
        payload = await body(request)
        cookies = payload.get("cookies", {})
        allowed = {"ltuid_v2", "ltoken_v2", "ltmid_v2", "cookie_token_v2", "account_id_v2", "account_mid_v2"}
        if not isinstance(cookies, dict) or set(cookies) - allowed or not all(isinstance(v, str) for v in cookies.values()):
            raise HubError("INVALID_COOKIES", "Unsupported cookie fields.", status=422)
        if not all(cookies.get(k) for k in ("ltuid_v2", "ltoken_v2")):
            raise HubError("INVALID_COOKIES", "ltuid_v2 and ltoken_v2 are required.", status=422)
        # Replacement, rather than merge, prevents obsolete cookies from surviving.
        async with app.state.config_lock:
            current = load_config(config_path, env=False)
            current.hoyolab.cookies = {}
            try:
                settings = Settings.model_validate(merge(current.model_dump(), {"hoyolab": {
                    "enabled": True, "region": payload.get("region", "os"), "cookies": cookies,
                    "game_uid": "", "server": ""}}))
            except ValidationError:
                raise HubError("INVALID_COOKIES", "Invalid authentication fields.", status=422) from None
            save_config(settings, config_path)
            app.state.hub.reload(load_config(config_path))
        return {"data": {"configured": True}}

    @app.delete("/api/v1/auth/hoyolab")
    async def delete_auth(request: Request):
        async with app.state.config_lock:
            current = load_config(config_path, env=False)
            current.hoyolab.cookies = {}
            current.hoyolab.enabled = False
            current.hoyolab.game_uid = current.hoyolab.server = ""
            save_config(current, config_path)
            app.state.hub.reload(load_config(config_path))
        return {"data": {"status": "disabled"}}

    @app.post("/api/v1/auth/hoyolab/test")
    @app.get("/api/v1/accounts/hoyolab")
    async def accounts():
        return {"data": await app.state.hub.hoyo.accounts()}

    @app.post("/api/v1/hoyolab/{operation}")
    async def device_hoyolab(operation: str, request: Request):
        # Hosted credentials and private results live only within this request.
        if not public_mode or operation not in ("accounts", "notes", "explore"):
            raise HubError("NOT_FOUND", "Unknown HoYoLAB operation.", status=404)
        payload = await body(request)
        cookies = payload.get("cookies", {})
        allowed = {"ltuid_v2", "ltoken_v2", "ltmid_v2", "cookie_token_v2", "account_id_v2", "account_mid_v2"}
        if (not isinstance(cookies, dict) or set(cookies) - allowed
                or not all(isinstance(value, str) for value in cookies.values())):
            raise HubError("INVALID_COOKIES", "Unsupported cookie fields.", status=422)
        if not all(cookies.get(key) for key in ("ltuid_v2", "ltoken_v2")):
            raise HubError("HOYOLAB_NEEDS_CONFIGURATION", "Configure ltuid_v2 and ltoken_v2 first.", "hoyolab", 401)
        try:
            private_settings = HoyoSettings.model_validate(payload)
        except ValidationError:
            raise HubError("INVALID_COOKIES", "Invalid HoYoLAB settings.", status=422) from None
        client = HoYoLABClient(private_settings, settings.network.timeout_seconds, app.state.hub.enka)
        if operation == "accounts":
            return {"data": await client.accounts()}
        data, _ = await getattr(client, operation)()
        ttl = settings.cache.notes_ttl_seconds if operation == "notes" else settings.cache.public_ttl_seconds
        return {"data": data, "meta": {"source": "hoyolab", "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source_updated_at": None, "cached": False, "stale": False, "refresh_after_seconds": ttl}}

    @app.get("/api/v1/profile/{uid}")
    async def profile(uid: str):
        result = await app.state.hub.fetch("showcase", uid)
        return {**result, "data": result["data"]["profile"]}

    @app.get("/api/v1/showcase/{uid}")
    async def showcase(uid: str):
        return await app.state.hub.fetch("showcase", uid)

    @app.get("/api/v1/showcase/{uid}/characters/{character_id}")
    async def character(uid: str, character_id: int):
        result = await app.state.hub.fetch("showcase", uid)
        selected = next((c for c in result["data"]["characters"] if c["id"] == character_id), None)
        if selected is None:
            raise HubError("CHARACTER_NOT_FOUND", "Character is not in this public showcase.", status=404)
        return {**result, "data": selected}

    @app.get("/api/v1/rankings/{uid}")
    async def rankings(uid: str):
        return await app.state.hub.fetch("rankings", uid)

    @app.get("/api/v1/akasha-build/{uid}/{build_hash}")
    async def akasha_build(uid: str, build_hash: str):
        import re
        if not re.fullmatch(r"[a-f0-9]{32}", build_hash):
            raise HubError("INVALID_BUILD", "Invalid Akasha build hash.", "akasha", 400)
        hub = app.state.hub
        rankings = await hub.fetch("rankings", uid)
        row = next((r for r in rankings["data"] if r.get("build_hash") == build_hash and r.get("build_snapshot")), None)
        if row is None:
            raise HubError("BUILD_NOT_FOUND", "Akasha ranking snapshot is unavailable.", "akasha", 404)
        return await hub.cache.get(("akasha-build", uid, build_hash), "akasha",
            hub.settings.cache.ranking_ttl_seconds, lambda: hub.akasha.build_detail(uid, row))

    @app.get("/api/v1/notes")
    async def notes():
        return await app.state.hub.fetch("notes")

    @app.get("/api/v1/explore")
    async def explore():
        return await app.state.hub.fetch("explore")

    @app.post("/api/v1/refresh")
    async def refresh(request: Request):
        payload = await body(request)
        source = payload.get("source")
        if public_mode and source not in ("showcase", "rankings"):
            raise HubError("PUBLIC_ONLY", "Only public showcase and rankings are available.", status=403)
        if source not in ("showcase", "rankings", "notes", "explore"):
            raise HubError("INVALID_SOURCE", "Choose showcase, rankings, notes, or explore.", status=400)
        return await app.state.hub.fetch(source, payload.get("uid"), refresh=True)

    return app


app = create_app()
