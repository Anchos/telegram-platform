FROM python:slim-stretch

WORKDIR /bot

COPY . .

RUN scripts/generate_keys.sh

RUN cat public.pem

RUN cat private.key

RUN pip3 install -r requirements.txt

CMD ["python3", "main.py"]
