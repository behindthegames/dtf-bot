curl --request POST \
--url https://api.dtf.ru/v1.6/webhooks/add \
--header 'X-Device-Token: XXX' \
--form 'url=http://requestbin.fullcontact.com/XXX' \
--form 'event=new_comment'
