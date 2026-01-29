#!/bin/sh

# Line to generate env-config.js
echo "window._env_ = {" > /usr/share/nginx/html/env-config.js
echo "  NEXT_PUBLIC_API_URL: \"${NEXT_PUBLIC_API_URL}\"," >> /usr/share/nginx/html/env-config.js
echo "};" >> /usr/share/nginx/html/env-config.js

# Start Nginx
exec "$@"
