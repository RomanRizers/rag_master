FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV UV_LINK_MODE=copy

COPY pyproject.toml uv.lock /app/
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev

COPY app /app/app

EXPOSE 5000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5000"]
