The Configuration File
======================

This plugin is configured via a configuration file named
``index-pages.ini`` in the |configs directory|_ of the
Lektor tree.

.. |configs directory| replace:: ``configs`` subdirectory
.. _configs directory: https://www.getlektor.com/docs/plugins/howto/#configure-plugins


Top-Level Indexes
-----------------

Each section in the config file which has a *non-dotted* section name
and which includes a setting for the ``key`` key defines a top-level
index.  The index is named after the section name.

Recognized keys:

``parent_path``

    The lektor path_ of the record under which the index virtual
    source objects will be created.  This defaults to “:samp:`/`”.

.. _path: https://www.getlektor.com/docs/content/paths/

``items``

    A jinja-evaluated expression which specifies the query_ used to
    determine which records are to be indexed.  It defaults to
    :samp:`{parent}.children`, where :samp:`{parent}` is the record
    specified by the ``parent_path`` key (see above.)

.. _query: https://www.getlektor.com/docs/api/db/query/

``key``

    **Required**.
    This key defines the index key(s).
    It is a jinja-evaluated expression which is evaluated in a context with ``item``
    set to the record to be indexed.  This expression should evaluate
    either to a single string, or, for multi-valued keys, to a sequence of
    strings.

``template``

    The names of the the Jinja template used to generate each index page.
    Defaults to ``index-pages.html``.

``slug_format``

    Specifies the URL slug to be used for the index pages in this index.
    This is a jinja-evaluated expression evaulated in a context with ``this`` set
    to the index page virtual source object.
    The default is ``this.key`` (or, equivalently, ``this._id``).

``subindex``

    To declare a sub-index, this key is set to the name of the
    sub-index.  The sub-index must be configured in its own config
    section (see :ref:`below <subindex-config>`.)

Fields
------

There may be an additional section in the config file for each index named
:samp:`[{index-name}.fields]` which can be used to define fields which will be
made available on the index :term:`virtual source object`\s.

Each key in the *fields* config section defines a field of the same
name.  The value of the key is a jinja-evaluated expression which is
evaluated with ``this`` set to the index virtual source object.

Pagination
----------

Pagination settings applying to all indexes may be placed in the
``[pagination]`` config section.  Settings particular to a specific
index (and its sub-indexes) may be placed in a config section named
:samp:`[{index-name}.pagination]`.  (And so on: sub-index specific
pagination settings go in
:samp:`[{index-name}.{subindex-name}.pagination]`.)
Settings from all of these sections will be merged, with those from
more specific sections overriding the settings in the generic sections.

The keys recognized in this section are ``enabled``, ``per_page``, and
``url_suffix``.  These work the same as the like-named keys for
`Lektor’s built-in pagination system <pagination_>`_, with the exception
that the ``items`` key is not supported.

.. _pagination: https://www.getlektor.com/docs/models/children/#pagination


.. _subindex-config:

Sub-Indexes
-----------

Sub-indexes are configured in a section named
:samp:`[{index-name}.{subindex-name}]`, where :samp:`{subindex-name}`
is the name of the sub-index specified in the ``subindex`` key of the
parent indexes config section (:samp:`[{index-name}]`).


The only keys supported in the sub-index config section are ``key``,
``template``, ``slug_format``, and (to declare a sub-sub-index) ``subindex``.
These have the same meanings as they do for a top-level index.

Annotated Example
-----------------

Because an example is worth more than a few words, here's an annotated exmple configuration file:

.. literalinclude:: ../../example.ini
   :language: ini
