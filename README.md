# Lektor Index Pages Plugin

[![PyPI version](https://img.shields.io/pypi/v/lektor-index-pages.svg)](https://pypi.org/project/lektor-index-pages/)
[![PyPI Supported Python Versions](https://img.shields.io/pypi/pyversions/lektor-index-pages.svg)](https://pypi.python.org/pypi/lektor-index-pages/)
[![GitHub license](https://img.shields.io/github/license/dairiki/lektor-index-pages)](https://github.com/dairiki/lektor-index-pages/blob/master/LICENSE)
[![Documentation Status](https://readthedocs.org/projects/lektor-index-pages/badge/?version=latest)](https://lektor-index-pages.readthedocs.io/en/latest/?badge=latest)
[![GitHub Actions (Tests)](https://github.com/dairiki/lektor-index-pages/workflows/Tests/badge.svg)](https://github.com/dairiki/lektor-index-pages)


This [Lektor][] plugin can be used to generate “index pages” for a
blog or similar collection of pages.  These index pages list the blog posts
segregated by some key, with each index page containing only those posts
which match that key.

Examples of what this can be used for include:

- *Category Indexes*: A set of index pages, one for each category,
  which lists all the posts in that category.  (Multi-valued index keys
  are also supported, so that each post can appear on more than a single
  index page: e.g. *keyword indexes*.)

- *Date Indexes*: A set of index pages, one for each year (say), which
  list all the posts in that year.  (Sub-indexes are supported
  subindexes — e.g., each year index may have as children a sequence
  of month indexes.)

Behind the scenes, judicious caching of indexing results, and careful
control of Lektor’s dependency tracking prevent all this from slowing
the build process down too excruciatingly much.

[lektor]: <https://www.getlektor.com/> "Lektor Static Content Management System"

## Project Links

* [Documentation](https://lektor-index-pages.rtfd.io/en/latest/)
* [Github](https://github.com/dairiki/lektor-index-pages/)
* [PyPI](https://pypi.org/project/lektor-index-pages/)

## Author

Jeff Dairiki <dairiki@dairiki.org>
