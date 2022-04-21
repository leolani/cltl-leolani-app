#!/bin/bash

# ASR implementation writes this files for some unknown reason
rm *.wav

rm storage/audio/*.wav
rm storage/audio/*.json

rm storage/video/*.png
rm storage/video/*.json

rm -r storage/rdf/**/*
rmdir storage/rdf/*

rm -r storage/emissor/**/*
rmdir storage/emissor/*