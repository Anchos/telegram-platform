# telegram-platform

## Installation

#### OS X
```bash
brew install postgresql
pg_ctl -D /usr/local/var/postgres start && brew services start postgresql

brew install python3
pip3 install -r requirements.txt

cp config.example.json config.json
```

#### Docker
```bash
cd <your_repo_dir>/server/
docker build -t tg-platform-server:latest .
```

## Configure

1. Run SQL console: `psql postgres`
2. Create database project user: `CREATE ROLE tpu WITH LOGIN PASSWORD 'tpu_def_pass';`
3. Create project database: `CREATE DATABASE telegram_platform;`
4. Grant privileges to database: `GRANT ALL PRIVILEGES ON DATABASE telegram_platform TO tpu;`
5. Exit from SQL console: `\q`
6. Edit `config.json` if this is necessary

## Starting

```bash
./start.sh
```

or via docker

```bash
docker run -d --name db --network host postgres
docker run -d --name tg-server --network host tg-platform-server:latest
```

## Tests
* WebSocket test: `tests\index.html`

## Credits

* [Petr](https://github.com/chebyrash)
* [Altair](https://github.com/CQAltair)
* [m-2k](https://github.com/m-2k)
