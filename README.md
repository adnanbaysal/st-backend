# SocialText #

This repository contains the Django REST API of the text based social media app `SocialText`.
This document shows how to set up the backend and run the tests locally. Instructions are given for unix based machines
(Linux and MacOS).

## How to set up local development? ##

### Python version ###
The project uses Python version 3.11. [`pyenv`](https://github.com/pyenv/pyenv) is recommended if you have multiple
python versions in your machine:

* Installing pyenv on MacOS:
```commandline
brew update
brew install pyenv
```

* Installing Python 3.11 with pyenv:
```commandline
pyenv install 3.11
```

### Poetry version ###
[Poetry](https://python-poetry.org/) 1.6.1 is used for managing dependencies.

* Installing Poetry 1.6.1 on Unix:
```commandline
curl -sSL https://install.python-poetry.org | python3 - --version 1.6.1
```

### Setting up virtual environment ###

* Clone the repository and `cd` into it
* Use Python 3.11 in the current directory: `pyenv local 3.11`
* Create a virtual environment with poetry. You can use:
  * An IDE like Pycharm to create the virtual environment from project settings
  * Or, you can run `poetry shell` or `poetry install` to create the environment on the fly. The latter will also
  install dependencies.
* Installing dependencies: `poetry install`. You can skip this if you already run it in the previous step.

## Running the backend and services locally ##
You need to install [Docker](https://www.docker.com/) to run services easily and smoothly. To run the backend with all
required services, first create a file named `.env` in the root directory of the repository with the following content:

```
ABSTRACT_API_EMAIL_URL=https://emailvalidation.abstractapi.com/v1/
ABSTRACT_API_EMAIL_KEY=64ab8e748f644f31a6793503804e209d
CELERY_BROKER_URL=amqp://admin:mypass@rabbit:5672
CELERY_RESULT_BACKEND=redis://redis:6379
DATABASE=postgres
DJANGO_ROOT_URLCONF=social_text.urls
DJANGO_SECRET_KEY=django-insecure-key
POSTGRES_DB=postgres
POSTGRES_HOST=localhost
POSTGRES_HOST_DOCKER=db
POSTGRES_PASSWORD=postgres
POSTGRES_PORT=5432
POSTGRES_PORT_TEST=6543
POSTGRES_USER=postgres
RABBITMQ_DEFAULT_USER=admin
RABBITMQ_DEFAULT_PASS=mypass
```

You can set the value of `DJANGO_SECRET_KEY` to any random string of characters. Then, run the following command to run
all services including the API:

```commandline
docker-compose --profile runserver up -d --build
```

`-d` option runs the services in detached mode. You can omit `--build` if you did not make any change in the code after
the last build. If the option `--profile runserver` is omitted, only DB, RabbitMQ, Redis and Celery worker services run.
This can be used, for example, to run the server in debug mode.

If you want to run only PostgreSQL DB as a docker service, you can call:
```commandline
docker run --publish 5432:5432 --name db -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=postgres \
-e POSTGRES_HOST=localhost -e POSTGRES_PORT=5432 -e POSTGRES_USER=postgres -d postgres
```
Note that the DB will be wiped when the container is deleted in the above command.

## Accessing the Services ##

### Django ###
When running the API with `--profile runserver`, the port for the API is 1337. If the API is run with
`./manage.py runserver`, the default port is 8000, but it can be changed with the `--port` option of `manage.py`.
For the following, the port is assumed to be 1337. Under this assumption, the base url for Django backend (API) is
http://localhost:1337.

* For Django Admin UI, go to http://localhost:1337/admin
* For swagger API documentation (uses openAPI 3.0), go to: http://localhost:1337/api/schema/swagger-ui

### RabbitMQ Management UI ###
In a browser, go to http://localhost:15672/ and login with `RABBITMQ_DEFAULT_USER` and `RABBITMQ_DEFAULT_PASS` defined
in your `.env` file.

### Redis ###
The easiest way is to connect to a shell in the redis docker container, and use the `redis-cli`.

### PostgreSQL ###
You can connect to the postgresql server with your favorite DB tool using the localhost at port 5432.

## Running tests ##
The project uses [pytest](https://docs.pytest.org/) to implement and run unit and integration tests.

To run all tests:

1. Create a file named `.env_test` in the root directory of the repository with the following content:
   ```
   ABSTRACT_API_EMAIL_URL=https://emailvalidation.abstractapi.com/v1/
    ABSTRACT_API_EMAIL_KEY=64ab8e748f644f31a6793503804e209d
    CELERY_BROKER_URL=amqp://admin:mypass@rabbit:5672
    CELERY_RESULT_BACKEND=redis://redis:6379
    DATABASE=postgres
    DJANGO_ROOT_URLCONF=social_text.urls
    DJANGO_SECRET_KEY=django-insecure-key
    POSTGRES_DB=postgres_test
    POSTGRES_HOST=localhost
    POSTGRES_HOST_DOCKER=db-test
    POSTGRES_PASSWORD=postgres
    POSTGRES_PORT=5432
    POSTGRES_PORT_TEST=6543
    POSTGRES_USER=postgres
    RABBITMQ_DEFAULT_USER=admin
    RABBITMQ_DEFAULT_PASS=mypass
   ```
2. Run the docker services with:
    ```commandline
    docker-compose --env-file .env_test --profile test up -d --build
    ```
3. Then, run this command from repository root:
    ```commandline
    poetry run pytest --cov
    ```
   If the poetry environment is already activated, leading `poetry run can be omitted.

## Contributing ##
You need to install [`pre-commit`](https://pre-commit.com/) to install git pre-commit hooks that will run the linting
related stuff automatically before committing.
After installing `pre-commit`, cd into the repository root and execute:

```commandline
pre-commit install
```

which will install the hooks to your local machine.

To run unit tests before pushing changes to the remote repository, call this command once:

```commandline
cp .pre-push.hook .git/hooks/pre-push
```

After that, unit tests will run whenever you try to push changes. The changes will be pushed only if the tests pass.
Before pushing changes, make sure to run docker services so that tests requiring db connection can access it.

NOTE: Currently, integration tests are not running in neither pre-push, nor in the Bitbucket pipeline. Reasons fo
these are:
1. `pre-push`: To reduce the number of `abstractapi` calls since they are limited for free plan
2. Bitbucket pipelines: This needs a separate service structure in the file `bitbucket-pipelines.yml` since it's not
obvious to run `docker-compose.yml` in Bitbucket pipelines. If time permits, pipeline file will be updated to run integration tests on
push as an improvement.

Therefore, currently it's developer's responsibility to run the integration tests locally.

### Updating the OpenAPI schema ###
Whenever there is a change in API specs, the OpenAPI schema can be updated with the following command in the
`social_text` directory under the root repository directory:
```commandline
./manage.py spectacular --color --file schema.yml
```
