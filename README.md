# Digital ID Platform

![CI](https://github.com/Infectious-07/IOT452U-Individual-Coursework/actions/workflows/ci.yml/badge.svg)

A console based backend that lets a central authority manage Digital IDs while authorised consumer organisations verify them through dedicated portals.

This project is built for the IOT452U Individual Coursework. Implementation is in Python 3.14 with only the standard library at runtime, plus pytest, coverage and ruff for development.

## Running

```
python -m pip install -r requirements-dev.txt
python -m pip install -e .
python -m digital_id
```

The shell starts at portal selection. Pick a number to enter a portal, type `help` to see the commands for that portal, and `quit` to exit.

## Tests and lint

```
ruff check src tests
coverage run -m pytest
coverage report
```

## Status

Modules and CI in place. README will grow as the system takes shape.
