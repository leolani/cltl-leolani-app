SHELL = /bin/bash

project_dependencies ?= $(addprefix $(project_root)/, \
		emissor \
		cltl-combot \
		cltl-requirements \
		cltl-backend \
		cltl-face-recognition \
		cltl-object-recognition \
		cltl-vad \
		cltl-asr \
		cltl-emissor-data \
		cltl-knowledgerepresentation \
		cltl-knowledgeextraction \
		cltl-knowledgelinking \
		cltl-languagegeneration \
		cltl-mention-detection \
		cltl-eliza \
		cltl-leolani \
		cltl-chat-ui)

git_remote ?= https://github.com/leolani

sources =

include util/make/makefile.base.mk
include util/make/makefile.py.base.mk
include util/make/makefile.git.mk
include makefile.helm.mk


spacy.lock:
	source venv/bin/activate; python -m spacy download en
	touch spacy.lock


.PHONY: build
build: venv spacy.lock


.PHONY: clean
clean:
	rm -rf venv dist
	rm -f spacy.lock
