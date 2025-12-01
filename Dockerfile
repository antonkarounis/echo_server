FROM alpine:latest

RUN apk add --no-cache python3

WORKDIR /script

COPY echo.sh .

CMD ["/script/echo.sh"]