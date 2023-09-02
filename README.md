# SocialText #

This repository contains the Django REST API of the text based social media app `SocialText`.
This document shows how to set up the backend and run the tests locally. Instructions are given for unix based machines
(Linux and MacOS).

## How to set up local development? ##

### Python version ###
The project uses Python version 3.11. [`pyenv`](https://github.com/pyenv/pyenv) is recommended if you have multiple
python versions in your machine:

* Installing pyenv on MacOS:
```
brew update
brew install pyenv
```

* Installing Python 3.11 with pyenv:
```
pyenv install 3.11
```

### Poetry version ###
[Poetry](https://python-poetry.org/) 1.6.1 is used for managing dependencies.

* Installing Poetry 1.6.1 on Unix:
```
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
CELERY_BROKER_URL=amqp://admin:mypass@rabbit:5672
CELERY_RESULT_BACKEND=redis://redis:6379
DATABASE=postgres
DJANGO_SECRET_KEY=django-insecure-key
POSTGRES_DB=postgres
POSTGRES_HOST=db
POSTGRES_PASSWORD=postgres
POSTGRES_PORT=5432
POSTGRES_USER=postgres
RABBITMQ_DEFAULT_USER=admin
RABBITMQ_DEFAULT_PASS=mypass
```

You can set the value of `DJANGO_SECRET_KEY` to any random string of characters. Then, run the following command:

```docker-compose up -d --build```

`-d` option runs the services in detached mode. You can omit `--build` if you did not make any change in the code after
the last build.

## Accessing the Services ##

### Django ###
Base url for Django backend (API) is http://localhost:1337.
* For Django Admin UI, go to http://localhost:1337/admin

### RabbitMQ Management UI ###
In a browser, go to http://localhost:15672/ and login with `RABBITMQ_DEFAULT_USER` and `RABBITMQ_DEFAULT_PASS` defined
in your `.env` file.

### Redis ###
The easiest way is to connect to a shell in the redis docker container, and use the `redis-cli`.

### PostgreSQL ###
You can connect to the postgresql server with your favorite DB tool using the localhost at port 5432.

## Running tests ##
The project uses [pytest](https://docs.pytest.org/) to implement and run unit tests.

## Contributing ##
You need to install [`pre-commit`](https://pre-commit.com/) to install git hooks that will run the unit tests
automatically before pushing changes to the origin.
After installing `pre-commit`, cd into the repository root and execute:

```pre-commit install```

which will install the hooks to your local machine.
