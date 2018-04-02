FROM python:slim-stretch

WORKDIR /server

COPY . .

RUN pip3 install -r requirements.txt

CMD ["python3", "main.py"]
