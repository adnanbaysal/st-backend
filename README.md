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
  * Or, you can run `poetry shell` or `poetry install` to create the environment on the fly. The latter will also install dependencies.
* Installing dependencies: `poetry install`. You can skip this if you already run it in the previous step.

## Running the backend and services locally ##
You need to install [Docker](https://www.docker.com/) to run services easily and smoothly.

## Running tests ##
The project uses [pytest](https://docs.pytest.org/) to implement and run unit tests.
