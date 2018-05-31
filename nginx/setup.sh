/etc/dehydrated-master/dehydrated -c --accept-terms

sed -i "/server_name recursion.ga;/i ssl_certificate /etc/dehydrated-master/certs/recursion.ga/fullchain.pem;" /etc/nginx/conf.d/default.conf
sed -i "/server_name recursion.ga;/i ssl_certificate_key /etc/dehydrated-master/certs/recursion.ga/privkey.pem;" /etc/nginx/conf.d/default.conf

sed -i "/server_name ws.recursion.ga;/i ssl_certificate /etc/dehydrated-master/certs/ws.recursion.ga/fullchain.pem;" /etc/nginx/conf.d/default.conf
sed -i "/server_name ws.recursion.ga;/i ssl_certificate_key /etc/dehydrated-master/certs/ws.recursion.ga/privkey.pem;" /etc/nginx/conf.d/default.conf

service nginx reload