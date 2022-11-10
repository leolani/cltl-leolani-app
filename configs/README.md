# Example Configurations

This folder contains a couple of example configurations to run the application.

## Example configurations for parent docker image

The `k8config/` directory contains configuration folders to run the docker parent
image as

* [Chat only](./k8config/chatonly)
* [Locally](./k8config/local)
* [On a robot (remote backend)](./k8config/robot)

To use them ensure the directory is mounted to `/cltl_k8_config` in the container
when running the docker image, e.g. by copying the content of any of the directories
to `docker-parent-app/config` or by adjusting the volume mount point in
`docker-parent-app/docker-compose.yml`.

## Example configurations for Python app

The `py-app/` directory contains configurations to run the Python application as 

* [Chat only](./py-config/chatonly)
* [On a robot (remote backend)](./py-config/robot)

To use them, copy the `pepper.config` file from any of the directories to
`py-app/config` next to the `default.config`.


