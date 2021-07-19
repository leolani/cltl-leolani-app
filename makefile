SHELL = /bin/bash

project_root ?= $(realpath ..)
project_name ?= $(notdir $(realpath .))
project_version ?= $(shell cat version.txt)

project_repo ?= ${project_root}/cltl-requirements
project_mirror ?= ${project_root}/cltl-requirements/mirror

project_dependencies ?= $(addprefix $(project_root)/, \
		cltl-combot \
		cltl-chat-ui)

git_remote ?= https://github.com/leolani


include util/make/makefile.base.mk
include util/make/makefile.git.mk
include makefile.helm.mk
