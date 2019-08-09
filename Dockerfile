FROM python:3.6
COPY requirements.txt /
RUN pip install -r requirements.txt
RUN mkdir -p /app
COPY main.py /app
WORKDIR /app

CMD ["uvicorn","--host", "0.0.0.0", "--port", "8080",  "--workers", "10", "main:app"]
