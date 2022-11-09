# Example Configurations

This folder contains a couple of example configurations to run the application.

## Example configurations for parent docker image

The `k8config/` directory contains configuration folders to run the docker parent
image as

* Chat only
* Locally
* On a robot (remote backend)

To use them ensure the directory is mounted to `/cltl_k8_config` in the container
when running the docker image, e.g. by coying the content to `docker-parent-app/config`
or adjusting `docker-parent-app/docker-compose.yml`.

## Example configurations for py-app

The `py-app/` directory contains configurations to run the Python application as 

* Chat only
* Locally
* On a robot (remote backend)

To use them copy the `pepper.config` file from the directory to `py-app/config`.


