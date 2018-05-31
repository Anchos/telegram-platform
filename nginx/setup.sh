/etc/dehydrated-master/dehydrated -c --accept-terms

rm -rf /etc/nginx/conf.d/default.conf && mv /default.nginx /etc/nginx/conf.d/default.conf

service nginx reload