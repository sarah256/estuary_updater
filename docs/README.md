# Estuary Updater Documentation


## Installing Sphinx

The documentation is built with Sphinx.  To install it along with the documentation's other dependencies, run the following command **in a virtualenv**:
```
$ pip install -r docs-requirements.txt
```

## Build the Docs

To build and run the docs, run the following commands:
```
$ sphinx-build -E docs docs/_build
$ google-chrome docs/_build/index.html
```

## Expanding the Docs

To add a new section:
* Create an rst file in the docs folder, such as `handlers.rst`, where handlers is the name of the new section, with the following format:
```
:github_url: https://github.com/release-engineering/estuary-updater/path/to/section

========
Handlers
========

.. automodule:: path.to.section
   :members:
```
* In the `docs/index.rst` file, in the toctree, add the name of the section (in this example, handlers)

To document a new handler file:
* In `docs/handlers.rst`, add the following code:
```
Handler Name
==========
.. automodule:: estuary_updater.handlers.model_name
   :members:
   :undoc-members:
```

*Note that it is not necessary to document new methods in classes that are already documented, as Sphinx will generate documentation for them automatically*