FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV UV_LINK_MODE=copy

COPY pyproject.toml /app/
RUN pip install --no-cache-dir uv && uv sync --no-dev

COPY app /app/app

EXPOSE 5000

ENV FLASK_APP=app.app:create_app
ENV FLASK_RUN_HOST=0.0.0.0

CMD ["uv", "run", "flask", "run", "--host=0.0.0.0", "--port=5000"]
