FROM python:3.13-alpine AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /code
RUN --mount=type=cache,target=/root/.cache/uv \
#    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --no-install-project --no-editable

COPY . /code
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-editable

#RUN uv pip install --system /code/dist/mockserver-0.1.0.tar.gz
#RUN ls -l /code/



FROM python:3.13-alpine
USER nobody
# Copy the environment, but not the source code
COPY --from=builder --chown=app:app /code/.venv /code/.venv
ENV PATH="/code/.venv/bin:${PATH}"
WORKDIR /code/.venv/bin
CMD ["uvicorn", "mockserver.main:app", "--host", "0.0.0.0", "--port", "80"]