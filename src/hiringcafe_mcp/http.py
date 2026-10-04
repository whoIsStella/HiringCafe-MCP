"""Request-scoped HTTP transport; no persistent event streams or sessions."""
import hmac
import os

from starlette.responses import JSONResponse, Response

from .server import mcp


async def app(scope, receive, send):
    if scope["type"] == "lifespan":
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return
    if scope["type"] != "http":
        return
    path, method = scope["path"], scope["method"]
    if path in ("/", "/health"):
        response = JSONResponse({"service": "HiringCafe MCP", "status": "ok"})
    elif path not in ("/mcp", "/mcp/"):
        response = Response(status_code=404)
    elif method != "POST":
        # MCP permits 405 when standalone SSE is unavailable. GET previously held
        # the function open even though these tools never send unsolicited events.
        response = Response(status_code=405, headers={"Allow": "POST"})
    else:
        token = os.getenv("MCP_ACCESS_TOKEN", "")
        headers = dict(scope["headers"])
        authorization = headers.get(b"authorization", b"")
        if os.getenv("VERCEL") and not token:
            response = JSONResponse({"error": "MCP_ACCESS_TOKEN must be configured"}, status_code=503)
        elif token and not hmac.compare_digest(authorization, ("Bearer " + token).encode()):
            response = Response(status_code=401, headers={"WWW-Authenticate": "Bearer"})
        else:
            # Vercel need not run ASGI lifespan hooks. Own a fresh stateless
            # manager per request, so repeated and concurrent invocations are safe.
            transport = mcp.streamable_http_app(
                streamable_http_path="/mcp", stateless_http=True,
                json_response=True, max_request_body_size=64 * 1024,
                host=os.getenv("MCP_HOST", "127.0.0.1") if not os.getenv("VERCEL") else "0.0.0.0",
            )
            request_scope = {**scope, "path": "/mcp"}
            async with transport.router.lifespan_context(transport):
                await transport(request_scope, receive, send)
            return
    await response(scope, receive, send)
