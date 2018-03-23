## База данных

### Скрипт разметки PostgreSQL

```sql
CREATE TABLE "Users" (
  "id" serial NOT NULL,
  "telegram_id" integer NOT NULL UNIQUE,
  "user_info" json,
  CONSTRAINT Users_pk PRIMARY KEY ("id")
) WITH (
  OIDS=FALSE
);
CREATE TABLE "Sessions" (
  "session_id" uuid NOT NULL UNIQUE,
  "expiration" TIMESTAMP NOT NULL DEFAULT (now()+interval '2 days'),
  "user_id" integer,
  CONSTRAINT Sessions_pk PRIMARY KEY ("session_id")
) WITH (
  OIDS=FALSE
);
ALTER TABLE "Sessions" ADD CONSTRAINT "Sessions_fk0" FOREIGN KEY ("user_id") REFERENCES "Users"("id");
```

Необходим пользователь `devUser` с правами на все действия с данной базой данных и всем, что внутри неё, с паролем `1234567890QQ`.

Либо использовать скрипт [`initPostgreSQL.bat`](https://github.com/m-2k/telegram-platform/blob/master/FSIOv2/initPostgreSQL.bat) (под Windows), который надо положить в директорию `%POSTGRESQL_DIR%/bin`, и оттуда запустить.

## Сервер

### Установка необходимых пакетов для Python 3.5

```bash
pip3 install flask
pip3 install flask-socketio
pip3 install eventlet
pip3 install py-postgresql
pip3 install python-telegram-bot
```

Либо использовать скрипт [`installPyPackeges.bat`](https://github.com/m-2k/telegram-platform/blob/master/FSIOv2/installPyPackeges.bat) (под Windows).

### Информация о сервере

Сервер запускается по адресу `127.0.0.1:5000`, доступные пути:

* `/`
* `/login`
* `/user/{name}`
* `/api` (stream)
  * `INIT`
  * `AUTH`
  * `USER`

### Telegram бот

Никнейм бота - [`@UristLikotBot`](https://t.me/UristLikotBot), доступные команды:

* `/start {session_id[uuid]}`

### Запуск сервера

1.  Запускаете базу данных по стандартному адресу `127.0.0.1` и порту `5432`.
2.  Выполняете файл [`MainServer.py`](https://github.com/m-2k/telegram-platform/blob/master/FSIOv2/MainServer.py).
