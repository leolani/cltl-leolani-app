SHELL = /bin/bash

project_root ?= $(realpath ..)
project_name ?= $(notdir $(realpath .))
project_version ?= $(shell cat version.txt)
project_compose ?= docker-app/docker-compose.yml

.PHONY: run
run:
	docker-compose up -d -f $(project_compose)

.PHONY: stop
stop:
	docker-compose stop
	docker-compose rm