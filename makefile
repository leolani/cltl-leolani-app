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
		cltl-dialogueclassification \
		cltl-emissor-data \
		cltl-knowledgerepresentation \
		cltl-knowledgeextraction \
		cltl-knowledgelinking \
		cltl-languagegeneration \
		cltl-mention-detection \
		cltl-emotionrecognition \
		cltl-dialogueclassification \
		cltl-g2ky \
		cltl-questionprocessor \
		cltl-visualresponder \
		cltl-about-agent \
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


nltk.lock:
	source venv/bin/activate; python -m nltk.downloader -d ~/nltk_data all
	touch nltk.lock


py-app/resources/face_models/models.lock:
	mkdir -p py-app/resources/face_models
	wget -qO- https://surfdrive.surf.nl/files/index.php/s/Qx80CsSNJUgebUg/download | tar xvz -C py-app/resources/face_models
	touch py-app/resources/face_models/models.lock


.PHONY: build
build: venv nltk.lock spacy.lock py-app/resources/face_models/models.lock


.PHONY: clean
clean:
	rm -rf venv dist
	rm -rf py-app/resources/face_models
	rm -f spacy.lock nltk.lock
