FROM python:3.12-alpine
WORKDIR /code
COPY app/requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt
COPY app/main.py main.py
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]