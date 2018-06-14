#!/bin/bash

echo "Installing the Python dependencies for Estuary Updater..."
python setup.py develop > /dev/null
python3 setup.py develop --prefix /usr > /dev/null
# Wait until Neo4j is up
while ! nc -z -w 2 neo4j 7687; do sleep 1; done;
# Run the tests
pytest-2 -vvv --cov-report term-missing --cov=estuary_updater tests/ && \
    pytest-3 -vvv --cov-report term-missing --cov=estuary_updater tests/ && \
    flake8
