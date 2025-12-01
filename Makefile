build:
	docker build -t echo_server .

run:
	docker run \
		--rm \
		--name echo_server \
		-p 8080:80 \
		-v .:/script \
		echo_server

