FROM python:3.6
COPY requirements.txt /
RUN pip install -r requirements.txt
RUN mkdir -p /app
COPY main.py /app
WORKDIR /app

CMD ["uvicorn", "main:app"]
