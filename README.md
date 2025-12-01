# echo_server

Dead simple HTTP echo server for debugging webhooks, API clients, and whatnot. Catches everything you throw at it and spits back the parsed request as JSON.

## What it does

- Accepts any HTTP method (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS)
- Parses headers, query strings, form data (urlencoded + multipart), and JSON
- Prints pretty JSON to stdout for your terminal
- Returns the full parsed request as JSON to the client
- Pure Python3 stdlib, no deps, no nonsense

## Running it

### Bare metal
```bash
./echo.py
# Serves on http://0.0.0.0:8080
```

Test it:
```bash
curl -X POST http://localhost:8080/ \
  -H "Content-Type: application/json" \
  -d '{"foo": "bar"}'
```

### Docker
```bash
docker build -t echo-server .
docker run -p 8080:8080 echo-server
# or  make build && make run
```

### Behind nginx
```nginx
server {
    listen 80;
    server_name echo.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
