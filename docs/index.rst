.. Lektor Index Pages documentation master file, created by
   sphinx-quickstart on Thu May  7 10:23:28 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

==================
Lektor Index Pages
==================

**Lektor-index-pages** is a `Lektor`_ plugin can be used to generate
“index pages” for a blog or similar collection of pages.  These index
pages list the blog posts segregated by some key, with each index page
containing only those posts which match that key.

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

.. _lektor: https://www.getlektor.com/

Contents
========

.. toctree::
   :caption: Usage
   :maxdepth: 2

   usage/installation
   usage/examples

.. toctree::
   :caption: Reference
   :maxdepth: 2

   reference/configuration
   reference/virtualsources
   reference/templateapi

   CHANGES

Indices and tables
==================

..
  * :ref:`genindex`
  * :ref:`modindex`
  * :ref:`search`

* :ref:`genindex`
* :ref:`search`
