curl --request POST \
  --url https://api.dtf.ru/v1.8/comment/add \
  --header "X-Device-Token: $1" \
  --header "X-Device-Possession-Token: $2" \
  --form "id=$3" \
  --form "reply_to=$4" \
  --form text='api comment'
