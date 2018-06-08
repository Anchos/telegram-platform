FROM nginx:latest

COPY default.nginx /etc/nginx/conf.d/default.conf

RUN nginx -t

COPY setup.sh /

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install wget unzip curl -y && \
    wget https://github.com/lukas2511/dehydrated/archive/master.zip && \
    unzip master.zip -d /etc/ && rm -rf master.zip && \
    mkdir -p /var/www/dehydrated/

WORKDIR /etc/dehydrated-master

RUN printf 'WELLKNOWN="/var/www/dehydrated"' >> config

# Uncomment to use test SSL certs
# RUN printf '\nCA="https://acme-staging.api.letsencrypt.org/directory"' >> config

RUN printf "recursion.ga" >> domains.txt && \
    printf "\nws.recursion.ga" >> domains.txt
