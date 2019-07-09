APP_NAME=cred-stuffing-tester

.PHONY: test docker-build

all: docker-build run

docker-build:
	docker build -f Dockerfile.local -t ${APP_NAME} .

run: docker-build
	@docker run -it \
	--rm \
	-d \
	--name ${APP_NAME} \
	--env-file=./prod.env \
	-p 8080:8080 \
	${APP_NAME}

test: docker-build
	@docker stop test-${APP_NAME} > /dev/null || true
	@docker run --rm -d --name test-${APP_NAME} --env-file=./test.env ${APP_NAME}
	@sleep 5
	docker exec -it test-${APP_NAME} python test.py

stop:
	@docker stop test-${APP_NAME} > /dev/null || true
	
clean:
	@docker stop test-${APP_NAME} > /dev/null || true
	@docker rmi -f ${APP_NAME}
