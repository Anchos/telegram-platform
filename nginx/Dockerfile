FROM nginx:latest

COPY setup.sh /

COPY temp_default.nginx /etc/nginx/conf.d/default.conf

COPY default.nginx /

RUN nginx -t

RUN apt-get update && apt-get upgrade -y

RUN apt-get install wget unzip curl -y

RUN wget https://github.com/lukas2511/dehydrated/archive/master.zip

RUN unzip master.zip -d /etc/ && rm -rf master.zip

WORKDIR /etc/dehydrated-master

RUN printf 'WELLKNOWN="/var/www/dehydrated"' >> config

RUN mkdir -p /var/www/dehydrated/

RUN printf "recursion.ga\nws.recursion.ga" >> domains.txt

# RUN ./dehydrated -c --accept-terms