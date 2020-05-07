Template API
============

Globals
-------

This plugin inserts a template global function **index_pages** which can
be used to access the index pages for an index.

.. module:: lektor_index_pages

.. function:: index_pages(index_name, alt=PRIMARY_ALT)

    **Index_pages** returns an interable of :class:`IndexSource` instances
    for the top-level index pages of the index named **index_name**.

    This function is provided mostly as syntactic sugar —
    :samp:`index_pages({index-name}, {alt})` is roughly equivalent to
    :samp:`site.get({parent-path}@index-pages/{index-name} [,{alt}]).subindexes`
    (where :samp:`{parent-path}` is the value of ``parent_path`` configured
    for the index.)
