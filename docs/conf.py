# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# http://www.sphinx-doc.org/en/master/config

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys

from athletics_performance import __version__

sys.path.extend(
    [
        os.path.abspath("../../"),
        os.path.abspath(".."),
        os.path.abspath("."),
    ]
)


# Ensure that the __init__ method gets documented.
def skip(
    app,
    what,
    name,
    obj,
    skip,
    options,
):
    if name == "__init__":
        return False
    return skip


def setup(app):
    app.connect(
        "autodoc-skip-member",
        skip,
    )


# -- Project information -----------------------------------------------------

project = "athletics_performance"
copyright = "bioMérieux 2026"
author = "Guillaume PERRIN - Athletic Club du Lyonnais"

# The full version, including alpha/beta/rc tags
release = __version__

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.doctest",
    "numpydoc",
]


# this is needed for some reason...
# see https://github.com/numpy/numpydoc/issues/69
numpydoc_class_members_toctree = False

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
]

# -- Options for HTML output -------------------------------------------------

html_theme = "sphinx_rtd_theme"
