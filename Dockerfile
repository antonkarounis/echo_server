FROM alpine:latest

RUN apk add --no-cache python3

WORKDIR /script

COPY echo.py .

EXPOSE 8080

CMD ["/script/echo.py"]