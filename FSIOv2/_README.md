```
!~~~ Database ~~~!
____________________
__Скрипт разметки БД PostgreSQL__
Название БД "telega"
Адрес старта и порт стандартные
127.0.0.1:5432
"""
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
"""
__:Необходим пользователь devUser с правами на все действия с данной базой данных и всем, что внутри неё, с паролем 1234567890Qq
- ! - ! - ! - ! - !  -
__:Либо использовать bat скрипт (Под винду) initPostgreSQL.bat , который надо положить в директорию [postgresql installed dir]/bin, и оттуда запустить
____________________



!~~~ Server ~~~!
____________________
__Скрипт установки необходимых пакетов для Python 3.5__
pip3 install flask
pip3 install flask-socketio
pip3 install eventlet
pip3 install py-postgresql
pip3 install python-telegram-bot
- ! - ! - ! - ! - !  -
__:Тот же скрипт в bat файле installPyPackeges.bat , под винду
____________________

!~~~ INFO ~~~!
____________________
__Некоторая инфа о сервере__

_Flask + Flask-SocketIO_
127.0.0.1:5000

_SocketIO_
/api 'stream'
type INIT -> type AUTH -> type USER

_Flask_
/
/login
/user/<name>/

_TelegramBot_
/start {session_id[uuid]}
/start 0518fc28-4018-42e2-bd9c-fdcb8bf7ec50
Ник: @UristLikotBot
____________________


!~~~ START ~~~!
____________________
1. Зпускаете бд по стандартному адресу (127.0.0.1) и порту (5432)
2. Запускаете MainServer.py
____________________

-=-=-=-=-=-=-=-=-=-
To be continued...
```
