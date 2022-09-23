### Components

The application is composed of the following components:

#### Backend Server

The Backend Server is a standalone application that provides a REST API with the basic raw signals.

#### Backend Container

The Backend Container connects to the backend server to retrieve raw signals and processes them to
make them available in the application. This involves:

* Managing access to the signal resources (e.g. mute mic while speaking).
* Store raw signal data.
* Publish events for the incoming signals, pointing to the storage location where the raw data can be retrieved.
* Subscribe to events that result in outgoing signals and send them to the backend server.

#### Voice Activity Detection (VAD)

Subscribes to audio signal events and detects voice activity in the audio data. For detected voice activity,
an event with the respective Mention on the audio signal is published.

#### Automatic Speech Recognition (ASR)

Subscribes to voice activity events and transcribes audio data referenced in the voice activity annotation
to text. For the transcribed text, a text signal event is published, referencing the respective segment in the
AudioSignal.

#### Leolani module

Subscribes to text signals where the robot is not the speaker, processes the text and publishes a new text signal
with a response.

#### Text To Speech (TTS)

Subscribes to text signals where the robot is the speaker, and converts the text to an audio signal.

#### Chat UI

Subscribes to text signals and publishes text signals from user input.