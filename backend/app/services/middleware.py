"""Request timing and tracing middleware for Masaad Estimator."""
import time
import uuid
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("masaad-api.middleware")

SKIP_LOG_PATHS = {"/health"}


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that:
    - Assigns a unique X-Request-ID (uuid4) to every request/response.
    - Measures end-to-end request duration in milliseconds.
    - Adds X-Process-Time header to every response.
    - Emits a structured log line for every request (except /health).
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())
        start_time = time.perf_counter()

        # Attach request_id to request state so route handlers can reference it
        request.state.request_id = request_id

        response: Response = await call_next(request)

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Inject headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(duration_ms)

        # Skip verbose logging for health-check probes
        if request.url.path not in SKIP_LOG_PATHS:
            extra = {"duration_ms": duration_ms}
            logger.info(
                "request completed",
                extra={
                    **extra,
                    "http_method": request.method,
                    "http_path": request.url.path,
                    "http_status": response.status_code,
                    "request_id": request_id,
                    "duration_ms": duration_ms,
                },
            )

        return response
