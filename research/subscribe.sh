curl --request POST \
--url https://api.dtf.ru/v1.8/webhooks/add \
--header "X-Device-Token: $1" \
--form "url=$2" \
--form 'event=new_comment'
