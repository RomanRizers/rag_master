import time
import uuid

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse

from backend.core.rate_limit import classify_rate_limit_bucket
from backend.core.responses import error_response_payload

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

    response = None
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "request_finished",
            request_id=request_id,
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=duration_ms,
        )


async def rate_limit_middleware(request: Request, call_next):
    limiter = getattr(request.app.state, "rate_limiter", None)
    if limiter is None:
        return await call_next(request)

    bucket = classify_rate_limit_bucket(request.method, request.url.path)
    if bucket is None:
        return await call_next(request)

    client_id = request.client.host if request.client else "unknown"
    allowed, retry_after = limiter.check(bucket=bucket, identity=client_id)
    if not allowed:
        return JSONResponse(
            content=error_response_payload(
                code="rate_limited",
                message=f"Rate limit exceeded for {bucket}",
                details={"bucket": bucket, "retry_after_seconds": retry_after},
            ),
            status_code=429,
        )

    return await call_next(request)
