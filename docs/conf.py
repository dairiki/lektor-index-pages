# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))


# -- Project information -----------------------------------------------------

project = 'Lektor Index Pages'
copyright = '2020-2021, Jeff Dairiki'
author = 'Jeff Dairiki'

master_doc = 'index'

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'myst_parser',
]

myst_gfm_only = True

# CHANGES.md starts with a level-2 header (so that it can be concatenated
# with README.md to form the PyPI long description
suppress_warnings = ["myst.header"]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'alabaster'
html_theme_options = {
    'fixed_sidebar': True,
    'show_relbars': True,

    'github_button': True,
    'github_type': 'watch',
    'github_count': False,
    'github_user': 'dairiki',
    'github_repo': 'lektor-index-pages',

    'extra_nav_links': {
        "PyPI releases": "https://pypi.org/project/lektor-index-pages/",
        "Source Code": "https://github.com/dairiki/lektor-index-pages/",
        },
    }

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

html_sidebars = {
    '**': [
        'about.html',
        'navigation.html',
        'relations.html',
        'searchbox.html',
        'donate.html',
        ],
    }
