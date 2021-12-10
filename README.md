# cltl-eliza

Eliza implementation using the combot framework.

This application also serves as a blue-print for applications in the combot framework.

## Application Architecture

![Eliza app - Architectur](doc/ElizaCombot.png)

### Backend Server

The Backend Server is a standalone application that provides a REST API with the basic raw signals.

### Backend Container

The Backend Container connects to the backend server to retrieve raw signals and processes them to
make them available in the application. This involves:
* Managing access to the signal resources (e.g. mute mic while speaking).
* Store raw signal data.
* Publish events for the incoming signals, pointing to the storage location where the raw data can be retrieved.
* Subscribe to events that result in outgoing signals and send them to the backend server.

### Voice Activity Detection (VAD)

Subscribes to audio signal events and detects voice activity in the audio data. For detected voice activity,
an event with the respective Mention on the audio signal is published.

### Automatic Speech Recognition (ASR)

Subscribes to voice activity events and transcribes audio data referenced in the voice activity annotation
to text. For the transcribed text, a text signal event is published, referencing the respective segment in the
AudioSignal.

### Elize module

Subscribes to text signals where the robot is not the speaker, processes the text and publishes a new text signal
with a response.

### Text To Speech (TTS)

Subscribes to text signals where the robot is the speaker, and converts the text to an audio signal.

## Application Runtimes

The application is setup for multiple runtime systems where it can be executed.

### Local Python application

The simplest is a local Python installation. This uses Python packages built for each module of the application
and has a main application script that configures and starts the modules from Python code.

The advantage is that communication between the modules can happen directly within the application, without the
need to setup external infrastructure components, as e.g. a messaging bus. Also, debugging of the application
can be easier, as everything run in a single process.

The disadvantage is, that this limits the application to first, use modules that are written in Python, and second,
all modules must have compatible requirements (Python version, package versions, hardware requirements, etc.).
As much as the latter is desirable, it is not always possible to fulfill.

##### Setup

The local Python application is setup in the `py-app/` folder and has the following structure:

    py-app
    ├── app.py
    ├── requirements.txt
    ├── config
    │   ├── default.config
    │   └── logging.config
    └── storage
        ├── audio
        └── video

The entry point of the application is the `app.py` script and from the `py-app/` directory after installing the necessary dependencies

    python -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt

it can be run via

    python app.py

### Containerized application

Alternatively to the local application, modules can be run in a containerized runtime system. In this setup
each (or a subset of) module(s) used in the application runs in a separate containerized runtime systems that
provides the requirements needed by the module. This provides full separation between the modules in terms of
software and hardware requirements, as well as isolation of their runtime state. In exchange this requires
additional infrastructure to enable the communication between the modules, as for instance a messaging bus,
resource management, container orchestration etc. In exchange this can be harder to setup and to debug, as
each module and the communication between them has to be inspected separately.

Container management can be done different tools. The next two sections describe two such setups. Also
see the [Docker documentation](https://docs.docker.com/get-started/orchestration/).

#### Docker compose app application

Docker provides Docker compose and Docker swarm as a tool to orchestrate applications with multiple containers.

#### Kubernetes application

A widely used tool for to run containerized applications is [Kubernetes].

## Development

**TODO** Move to eliza-parent 

### Workflow using PyCharm

* Checkout the repository with submodules (recursive)
* Build the project with `make build`. This will create all *venvs*.
* Open `cltl-eliza-app` in PyCharm. PyCharm will list the workbench with this project name in `Recently Opened`.
* Select and open all other projects in PyCharm and for each `Attach` to current workbench.
Existing *venvs* will be used automatically by PyCharm.
* Code changes in one module do not require any special workflow, try to add unit tests to make sure the code works. 
* To make code changes visible across modules, run `make build` from the parent project to update `venvs`.
* Commit and push the code changes in the individual modules.
* Commit the submodules in the parent project when the application with its submodules is in a consistent state. 