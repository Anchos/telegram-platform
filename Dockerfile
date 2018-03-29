FROM python:slim-stretch

WORKDIR /telegram-platform

COPY . .

RUN pip3 install -r requirements.txt

RUN cp config.example.json config.json

CMD ["python3", "main.py"]
