curl -vv --request POST \
--url https://api.dtf.ru/v1.8/auth/possess \
--header "X-Device-Token: $1" \
--form "id=$2"
