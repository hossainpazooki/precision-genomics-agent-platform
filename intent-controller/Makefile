.PHONY: build run test lint clean

build:
	go build -o bin/intent-controller ./cmd/server

run: build
	./bin/intent-controller

test:
	go test ./...

lint:
	go vet ./...

clean:
	rm -rf bin/
