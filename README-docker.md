### Containerized application

Alternatively to the local application, modules can be run in a containerized runtime system. In this setup
each (or a subset of) module(s) used in the application runs in a separate containerized runtime systems that
provides the requirements needed by the module. This provides full separation between the modules in terms of
software and hardware requirements, as well as isolation of their runtime state. In exchange this requires
additional infrastructure to enable the communication between the modules, as for instance a messaging bus,
resource management, container orchestration etc. In exchange this can be harder to setup and to debug, as
each module and the communication between them has to be inspected separately.

Container management can be done different tools. The next sections describe such setups. Also
see the [Docker documentation](https://docs.docker.com/get-started/orchestration/).

#### Docker compose parent app application

The `docker-parent-app/` directory provides a docker-compose setup to run a dockerized version of the local Python
application provided in `py-app/`.

* It is recommended to create a virtual environment

      python -m venv venv

  and activate it with

      source venv/bin/activate

  on Linux/OS X or for Windows in cmd.exe

      venv\Scripts\activate.bat

  or in a PowerShell

      venv\Scripts\Activate.ps1

* Install the backend including the `[host]` dependencies:

      pip install cltl.backend[host]==0.0.dev5
      
      or
      
      pip install 'cltl.backend[host]'==0.0.dev5

* Run the backend server on the local machine, on Linux/OS X with

      ./venv/bin/leoserv --channels 1 --port 8080 --resolution VGA

  on Windows in cmd.exe

      venv\Scripts\leoserv.exe --channels 1 --port 8080 --resolution VGA

  The `server_image_url` and `server_audio_url` parameters should match the configured values
  in `py-app/config/default.config` and `docker-parent-app/config/cltl.backend`. This needs to keep running in the background.

* Start GraphDB on your local machine.

* Enable speech recognition either via Google Cloud services or locally
    * To use Google Cloud services for speech recognition, setup that up a project as described on
      their [homepage](https://cloud.google.com/speech-to-text/docs/before-you-begin).
      Copy the `google_cloud_key.json` obtained there into the `docker-parent-app/credentials/` folder.

    * To use a local speech recognition implementation, in the `docker-parent-app/config` folder create a
      file with the name `cltl.asr` containing the line

          implementation: wav2vec

      and a file called `cltl.asr.wav2vec` with content

          model: jonatasgrosman/wav2vec2-large-xlsr-53-english

* Start the docker-compose application from `docker-parent-app/` with

      docker compose up

  The first time you run this it will take a few minutes to launch, as it will donload all models and resources
  necessary from the web.

  For more information on docker compose see the [documentation](https://docs.docker.com/compose/).

##### Build it yourself

To build the Docker image from scratch, from the Leolani parent directory run

    docker build -t <MY_IMAGE_NAME> .

and replace the `leolani` image in `docker-parent-app/docker-compose.yml` with your tag name.

#### Docker compose app application

Docker provides Docker compose and Docker swarm as a tool to orchestrate applications with multiple containers.

#### Kubernetes application

A widely used tool to run containerized applications is [Kubernetes](https://kubernetes.io).

### Troubleshooting

1. Remember to upgrade your pip version as such
   `python -m pip install --upgrade pip`

1. Depending on the setup of your `venv`, you might get an error like this:
   `ImportError: cannot import name 'find_namespace_packages' from 'setuptools' `
   You can solve this by simply installing the `setuptools` library, as such:
   `pip install -U setuptools `

2. 


