curl --request POST \
  --url https://api.dtf.ru/v1.6/comment/add \
  --header 'X-Device-Token: XXX' \
  --header 'X-Device-Possession-Token: XXX' \
  --form id=XXX \
  --form reply_to=XXX \
  --form text='api comment'