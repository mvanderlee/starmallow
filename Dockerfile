FROM python:3.11

WORKDIR /app

RUN pip install brotli-asgi gunicorn starlette_context

COPY . /app
RUN pip install --no-cache-dir .[all]

CMD ["gunicorn", "--config", "examples/gunicorn.py", "examples.cache_server:app"]
