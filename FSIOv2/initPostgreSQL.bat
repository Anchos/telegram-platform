::%cd%
@echo off
echo "This script must me placed at directory [postgresql direcory]\bin"
pause
taskkill /f /im postgres.exe

rmdir /S /Q ..\DataDirTelega
mkdir ..\DataDirTelega
initdb ..\DataDirTelega
pg_ctl -D ..\DataDirTelega start
createdb --encoding=utf-8 --template=template0 telega
createuser "devUser"

del /F ..\DataDirTelega\psqlScript.sql
echo ALTER USER "devUser" WITH superuser; >> ..\DataDirTelega\psqlScript.sql
echo ALTER USER "devUser" WITH PASSWORD '1234567890Qq'; >> ..\DataDirTelega\psqlScript.sql
echo CREATE TABLE "Users" ("id" serial NOT NULL,	"telegram_id" integer NOT NULL UNIQUE,	"user_info" json,	CONSTRAINT Users_pk PRIMARY KEY ("id")) WITH (  OIDS=FALSE); >> ..\DataDirTelega\psqlScript.sql
echo CREATE TABLE "Sessions" (	"session_id" uuid NOT NULL UNIQUE,	"expiration" TIMESTAMP NOT NULL DEFAULT (now()+interval '2 days'),	"user_id" integer,	CONSTRAINT Sessions_pk PRIMARY KEY ("session_id")) WITH (  OIDS=FALSE); >> ..\DataDirTelega\psqlScript.sql
echo ALTER TABLE "Sessions" ADD CONSTRAINT "Sessions_fk0" FOREIGN KEY ("user_id") REFERENCES "Users"("id"); >> ..\DataDirTelega\psqlScript.sql
psql -d telega -f ..\DataDirTelega\psqlScript.sql
pause

