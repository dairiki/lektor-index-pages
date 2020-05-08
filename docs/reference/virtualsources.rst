Virtual Source Objects
======================

The index pages are generated as `virtual source objects <virtual_>`_

.. _virtual: https://www.getlektor.com/docs/api/db/obj/#virtual-source-objects

.. module:: lektor_index_pages.sourceobj

The Index Roots
---------------


Each top-level index will have a root virtual source.  These have
`Lektor paths <path_>`_ like :samp:`{parent}@index-pages/{index-name}`.
The index root sources do not actually generate any artifacts.
The serve primarily as the parents for the actual index pages.
For the most part, they have one useful attribute, `subindexes`
which contains a Lektor Query instance containing the individual
index pages for the index.

.. _path: https://www.getlektor.com/docs/content/paths/


.. class:: IndexRoot(model, record)

    .. attribute:: subindexes

        A Lektor Query instance containing the individual pages for the index.

        The ordering of the index pages in **subindexes** preserves the ordering
        defined of the indexes ``items`` setting.  I.e. the *items* are iterated
        through; the *keys* are computed for each item in order; the index
        source for the first key encountered will be listed first in *subindexes*,
        the index for the second unique key encountered will be listed second, etc.



The Index Pages
---------------

The items in the root index’s :attr:`~.IndexRoot.subindexes` query
live at path_\s like :samp:`{parent}@index-pages/{index-name}/{key}`,
where :samp:`{key}` is the index key for the page.

Useful fields on the index page include ``key`` (or, equivalently, ``_id``,)
which is equal to the index
key for the page, as well as any custom fields configured in the
:samp:`[{index-name}.fields]` section of ``index-pages.ini``.

Useful attributes on the index page virtual source objects include:

.. class:: IndexSource(model, root, id_, children, page_num=None)

    .. attribute:: children

        The records in the configured ``items`` for the query that match this
        index page’s *key*.

    .. attribute:: pagination

        This works just like the regular Lektor `pagination object`_.
        E.g. the children for this current page are available in ``pagination.items``.

        (The *pagination* attribute is available only if pagination is enabled
        in the configuration for the index.)

        .. _pagination object:
            https://www.getlektor.com/docs/guides/pagination/#rendering-a-pagination

    .. attribute:: subindexes

        If a sub-index is configured on this index, **subindexes** will contain
        a query containing the sub-index pages, instances of :class:`IndexSource`.
        The sub-index virtual sources will have `path`_\s like
        :samp:`{parent}@index-pages/{index-name}/{key}/{subindex-key}`.
