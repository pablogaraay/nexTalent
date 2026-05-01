#!/bin/sh
set -eu

envsubst '${VITE_API_URL}' \
  < /usr/share/nginx/html/config.template.js \
  > /usr/share/nginx/html/config.js
