/etc/dehydrated-master/dehydrated -c --accept-terms

rm -rf /etc/nginx/conf.d/default.conf && mv /default.conf /etc/nginx/conf.d/default.conf

service nginx reload