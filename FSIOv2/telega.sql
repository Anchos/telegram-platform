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