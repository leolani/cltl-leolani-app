SHELL = /bin/bash

project_dependencies ?= $(addprefix $(project_root)/, \
		cltl-combot \
		cltl-requirements \
		cltl-backend \
		cltl-vad \
		cltl-asr \
		cltl-eliza \
		cltl-chat-ui)

git_remote ?= https://github.com/leolani

sources =

include util/make/makefile.base.mk
include util/make/makefile.py.base.mk
include util/make/makefile.git.mk
include makefile.helm.mk

.PHONY: build
build: venv
