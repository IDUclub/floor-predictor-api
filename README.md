# Floor Predictor API

This API provides methods to predict number of floors for living buildings.

Library with the main business logic is [here](https://github.com/IDUclub/floor-predictor).

## Running locally

1. To install python dependencies run `poetry install`. You may also want to use `venv` before that.
2. Create .env and config.yaml files as provided in *.example files.
3. Run backend locally with `poetry run launch_app` or `make run-api`.

You can open [localhost:5400](http://localhost:5400) (or different host/port if you configured it) to get a redirect to Swagger UI with endpoints list.


## Running in docker 

1. In addition to .env and config.yaml files also create logrotate.conf and supervisord.conf as specified in the *.example files.
2. Run the command `docker-compose up -d --build`

You can open [localhost:5400](http://localhost:5400) (or different host/port if you configured it) to get a redirect to Swagger UI with endpoints list.

## Logging

Floor Predictor API uses structlog lib to write logs. When saving to file, it is formatted as jsonlines. You can use `pygmentize -l json <filename>`
to colorfully print results to terminal.
