import time
import uuid

import structlog
from fastapi import Request


logger = structlog.get_logger("http")


async def request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = request_id

    path = request.url.path
    method = request.method
    client_host = request.client.host if request.client else None

    start = time.perf_counter()
    logger.info(
        "request_started",
        request_id=request_id,
        method=method,
        path=path,
        client_ip=client_host,
    )

    response = await call_next(request)

    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Request-ID"] = request_id

    logger.info(
        "request_finished",
        request_id=request_id,
        method=method,
        path=path,
        status_code=response.status_code,
        duration_ms=duration_ms,
    )
    return response
