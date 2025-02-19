FROM python:3.13-alpine
RUN mkdir /app
COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt
COPY loader.py /app/loader.py
ENTRYPOINT ["python", "/app/loader.py"]