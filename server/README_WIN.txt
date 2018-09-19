Tested on:


Windows 10 Pro, build: 17134.285, version: 1803, x64
Docker version 18.06.1-ce, build e68fc7a

You have next docker images:

postgres, ngninx, aplpine, python (3.7), tg-platform-proxy, tg-platform-server


Installation guide:

- open proxy folder (cd proxy) and build telegram proxy server by the next docker command:
docker build -t tg-platform-proxy .
(will be build proxy server and ngninx server)

- run postgres database from exist docker image:
docker run -d --network host postgres db
(it is the main database where user, channels, ... info take place)

- next, you must set default user and password from alpine docker os for your postgres db:

type next command in running postgres container by its name alias (db by default):
docker exec -it db /bin/bash (execute command in local container)
psql -U postgres (enter in db with user key as -U)
\password postgres (enter password and repeat)
\q
exit

###MAYBE NOT NEED###
- it might be to stop that container to take updates for login and pass:
docker stop <CONTAINER_ID>
docker rm <CONTAINER_ID>
###MAYBE NOT NEED###

- and run postgres container as host again:
docker run -d --network host --name db postgres

- if you have in congig.json null ip subnet as: 0.0.0.0, change it to default localhost: 127.0.0.1
server can listen any port (like 5000, check it in index.html and fake_client.js and setup there as written before localhost ip)


Migrations:

- go to the root project folder and type:
alembic upgrade head

- and than run the server:

cd server
python main.py

If you are located in Country with censorship for the internet, domain rules, check your Telegram advantage status, if it block in your Country,
you must use proxies or VPN service, to update db with new channels.

Tests, UI:

- for test get front-end side of project telegram-platform-web:
cd <TEST_FOLDER>
git init
git clone https://github.com/Anchos/telegram-platform-web.git

- than check readme.txt
