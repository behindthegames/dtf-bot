curl --request POST \
--url https://api.dtf.ru/v1.8/webhooks/del \
--header "X-Device-Token: $1" \
--form 'event=new_comment'
