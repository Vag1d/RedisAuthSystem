#!/bin/bash

BASE_URL="http://localhost:8000"

echo " ---- Регистрация пользователя ----"
curl -s -X POST $BASE_URL/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"standard_user","password":"123","role":"user"}'
echo -e "\n"

echo "---- Регистрация администратора ----"
curl -s -X POST $BASE_URL/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"123","role":"admin"}'
echo -e "\n"

echo "---- Логин ----"
LOGIN_RESPONSE=$(curl -s -X POST $BASE_URL/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"standard_user","password":"123"}')

# Извлечение access_token без jq
ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d '"' -f 4)
REFRESH_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"refresh_token":"[^"]*"' | cut -d '"' -f 4)

# Альтернативный способ через sed (на случай, если в JSON есть пробелы)
# ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')
# REFRESH_TOKEN=$(echo "$LOGIN_RESPONSE" | sed -n 's/.*"refresh_token":"\([^"]*\)".*/\1/p')

echo "$LOGIN_RESPONSE"
echo ""

if [ -z "$ACCESS_TOKEN" ]; then
    echo "Ошибка: не удалось получить access_token. Проверьте логин и работу сервера."
    exit 1
fi

echo "---- Общий контент ----"
curl -s -X GET $BASE_URL/content/common \
  -H "Authorization: Bearer $ACCESS_TOKEN"
echo -e "\n"

echo "---- Контент для роли user ----"
curl -s -X GET $BASE_URL/content/user \
  -H "Authorization: Bearer $ACCESS_TOKEN"
echo -e "\n"

echo "---- Контент для роли admin вернуть 403 Insufficient permissions, так как standard_user не admin ----"
curl -s -X GET $BASE_URL/content/admin \
  -H "Authorization: Bearer $ACCESS_TOKEN"
echo -e "\n"

echo "---- Логаут ----"
curl -s -X POST $BASE_URL/auth/logout \
  -H "Authorization: Bearer $ACCESS_TOKEN"
echo -e "\n"

echo "---- Обновление токенов ----"
curl -s -X POST $BASE_URL/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"$REFRESH_TOKEN\"}"
echo -e "\n"

echo "---- Проверка, что старый access_token более не работает ----"
curl -s -X GET $BASE_URL/content/common \
  -H "Authorization: Bearer $ACCESS_TOKEN"
echo -e "\n"