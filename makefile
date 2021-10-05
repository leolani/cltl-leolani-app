SHELL = /bin/bash

project_dependencies ?= $(addprefix $(project_root)/, \
		cltl-combot \
		cltl-chat-ui)

git_remote ?= https://github.com/leolani


include util/make/makefile.base.mk
include util/make/makefile.git.mk
include makefile.helm.mk
#include makefile.compose.mk
