FROM python:3.12-alpine
WORKDIR /code
RUN pip install --no-cache-dir --upgrade uvicorn fastapi fastapi[standard]
COPY main.py main.py
CMD ["fastapi", "run", "main.py", "--port", "80"]