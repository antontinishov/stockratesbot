BEGIN;
    CREATE TABLE "users" (
        "id" serial NOT NULL,
        "user_id" integer NOT NULL UNIQUE,
        "username" varchar(255) NOT NULL,
        "first_name" varchar(255) NOT NULL,
        "last_name" varchar(255),
        "date" timestamptz NOT NULL DEFAULT now(),
        "active" boolean default TRUE,
        PRIMARY KEY (id)
    );

    CREATE TABLE "rates" (
        "id" serial NOT NULL,
        "date" timestamptz NOT NULL DEFAULT now(),
        "rate" varchar(10),
        "cbr" numeric(7, 2),
        "tinkoff" numeric(7, 2),
        "sberbank" numeric (7, 2),
        "vtb" numeric (7, 2),
        "spbbank" numeric (7, 2),
        PRIMARY KEY (id)
    );

    CREATE TABLE "messages" (
        "id" serial NOT NULL,
        "date" timestamptz NOT NULL DEFAULT now(),
        "message" text,
        "from_user_id" integer NOT NULL,
        PRIMARY KEY (id),
        FOREIGN KEY (from_user_id) REFERENCES users (user_id)
    );
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO db_user;
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public to db_user;
COMMIT;
