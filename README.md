# Lektor Index Pages Plugin

[![PyPI version](https://img.shields.io/pypi/v/lektor-index-pages.svg)](https://pypi.org/project/lektor-index-pages/)
[![PyPI Supported Python Versions](https://img.shields.io/pypi/pyversions/lektor-index-pages.svg)](https://pypi.python.org/pypi/lektor-index-pages/)
[![GitHub license](https://img.shields.io/github/license/dairiki/lektor-index-pages)](https://github.com/dairiki/lektor-index-pages/blob/master/LICENSE)
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

## Installation

Add `lektor-index-pages` to your project from command line:

```
lektor plugins add lektor-index-pages
```

See [the Lektor plugin documentation][plugins] for more information.

[plugins]: <https://www.getlektor.com/docs/plugins/>

## Configuration

This plugin is configured via a configuration file named
`index-pages.ini` in the [`configs` subdirectory][configs] of
the Lektor tree.

[configs]: <https://www.getlektor.com/docs/plugins/howto/#configure-plugins>
        (Lektor Plugin Configuration Documentation)

### Top-Level Indexes

Each section in the config file which has a non-dotted section name and which
includes a setting for the `keys` key defines a top-level index.  The index is
named after the section name.

Recognized keys:

#### parent_path

The lektor [path][] of the record under which the index virtual source
objects will be created.  This defaults to “`/`”.

[path]: <https://www.getlektor.com/docs/content/paths/>
        (Lektor Documentation on Paths)

#### items

A jinja-evaluated expression which specifies the
[query][] used to determine which records are to be indexed.
It defaults to `<parent>.children`, where `<parent>` is the record specified by
the `parent_path` key (see above.)

[query]: <https://www.getlektor.com/docs/api/db/query/>

#### keys

**Required**.
This key defines the index key(s).
It is a jinja-evaluated expression which is evaluated in a context with `this`
set to the record to be indexed.  This expression should evaluate
either to a single string, or, for multi-valued keys to a sequence of
strings.

#### template

The names of the the Jinja template used to generate each index page.
Defaults to `index-pages.html`.

#### slug_format

Specifies the URL slug to be used for the index pages in this index.
This is a jinja-evaluated expression evaulated in a context with `this` set
to the index page virtual source object.
The default is `this._id`.

#### subindex

To declare a sub-index, this key is set to the name of the sub-index.
The sub-index must be configured in its own config section (see below.) 

### Fields

There may be an additional section in the config file for each index named
`[<index-name>.fields]` which can be used to define fields which will be
made available on the index virtual source objects.

Each key in the *fields* config section defines a field of the same name.
The value of the key is a jinja-evaluated expression which is evaluated with `this`
set to the index virtual source object.

### Pagination

Pagination settings may be placed in the `[pagination]` config
section, on in the `[<index-name>.pagination]` config section.  The
settings in the `[pagination]` section apply to all indexes — settings
in the `[<index-name>.pagination]` section are, not surprisingly,
specific to the named index (and any sub-index of that index.)
(Pagination configuration specific to a sub-index may be placed in
the `[<index-name>.<sub-index-name>.pagination]` section.)

The keys recognized in this section are `enabled`, `per_page`, and
`url_suffix`.  These work the same as the like-named keys for
[Lektor’s built-in pagination system][pagination], with the exception
that the `items` key is not supported.

[pagination]: <https://www.getlektor.com/docs/models/children/#pagination>


### Sub-Indexes

Subindexes are configured in a section named `[<index-name>.<subindex-name>]`.

The only keys supported in the sub-index config section are `keys`,
`template`, `slug_format`, and (to declare a sub-sub-index) `subindex`.
These have the same meanings as they do for a top-level index.

## Virtual Source Objects

The index pages are generated as [virtual source objects][virtual].

### The Index Roots

Each top-level index will have a root virtual source.  These have
[Lektor path][path]s like `<parent>@index-pages/<index-name>`.  These
do not generate any artifacts.  For the most part, they have one
useful attribute, `subindexes` which contains a Lektor Query instance
containing the individual index pages for the index.

The ordering of the index pages in `subindexes` preserves the ordering
defined of the indexes `items` setting.  I.e. the `items` are iterated
through; the `keys` are computed for each item in order; the first key
encountered will be listed first in `subindexes`, the second key
encountered will be listed second, etc.

[virtual]: <https://www.getlektor.com/docs/api/db/obj/#virtual-source-objects>
        (Lektor Documentation on Virtual Source Objects)


### The Index Pages

The items in the root index’s `attributes` query live at [path][]s like
`<parent>@index-pages/<index-name>/<key>`, where `<key>` is the index
key for the page.

Useful fields on the index page include `_id`, which is equal to the index
key for the page, as well as any custom fields configured in the `[<index-name>.fields]` section of `index-pages.ini`.

Useful attributes on the index page virtual source objects include:

#### children

The records in the configured `items` for the query that match this
index page’s *key*.

#### pagination

(Only If pagination is configured for the index.) This works just like
the regular Lektor [pagination object][pagination].  E.g. the children
for this current page are available in `pagination.items`.

[pagination]: <https://www.getlektor.com/docs/guides/pagination/#rendering-a-pagination>

#### subindexes

If a sub-index is configured on this index, `subindexes` will contain
a query containing the sub-index pages.  The sub-index virtual sources
will have [path][]s like
`<parent>@index-pages/<index-name>/<key>/<subindex-key>`.

## Template API

This plugin inserts a template global function `index_pages` which can
be used to access the index pages for an index. 

`index_pages(index_name, alt=PRIMARY_ALT)`

FIXME: more detail

----

## Examples

### “Simple” Example: A Category Index

Let’s assume your blog posts already include a string-valued `category`
field in their [datamodel][], and the blog posts live under the blog
at Lektor path `/blog`. A category index could be generated with the following
configuration in `configs/index-pages.ini`.

[datamodel]: <https://www.getlektor.com/docs/models/> "Lektor Data Model Documentation"

```ini
[category]

# index page are rooted at /
parent_path = /

# the blog children are what is indexed
items = site.get('/blog').children

# the category of each post is what is being indexed
keys = this.category

# the index pages will be placed at URL path /category/<category>/
slug_format = 'category/{}'.format(this._id)

# this template will be rendered, once for each category to generate the indexes
template = category-index.html

[category.fields]
# Define the `category` field of the index pages to be an alias for the index `id`
# (which is the key for the index page — in this case the category.)
category = this._id
```

The index template, in this case `category-index.html`, might look like:

```html+jinja
{% extends "layout.html" %}
{% block body %}
  <h1>Category {{ this.category }}</h1>
  <p>Posts in this category:</p>
  <ul>
    {% for post in this.children %}
      <li><a href="{post|url}">{{ post.title }}</a></li>
    {% endfor %}
  </ul>
{% endblock %}
```

In the template for the blog parent page (at `/blog`) one could do something
like this to link to the category index pages:

```html+jinja
{% extends "layout.html" %}
{% block body %}
  <h1>The Blog!</h1>
  <p>Categories in this blog</p>
  <ul>
    {% for cat_idx in index_pages('category') %}
      <li><a href="{cat_idx|url}">{{ cat_idx.category }}</a></li>
    {% endfor %}
  </ul>
{% endblock %}
```

### A Hairier Example: Date Index by Year then Month

In `configs/index-pages.ini`:

```ini
[date]
parent_path = /blog
keys = '{.year:04d}'.format(this.pub_date)
template = blog-year-index.html
subindex = month

[date.fields]
date = this.children.first().pub_date.replace(month=1, day=1)
year = this._id|int

[date.month]
keys = '{.month:02d}'.format(this.pub_date)
template = blog-month-index.html

[date.month.fields]
# this.parent is the year-index page this month-index belongs to.
date = this.parent.date.replace(month=this._id|int)
year = this.parent.year
month = this._id|int
```

This will create year-index pages at URL path `/blog/<yyyy>/` and
month-indexes at `/blog/<yyyy>/<mm>/`.  Note that if the blog-post
children.slug_format for the blog is set to something like
`{.year:04d}/{.month:02d}/{._id}'.format(this)`, then the individual
blog posts will be placed at `/blog/<yyyy>/<mm>/<post-id>/` which will
jibe nicely with the index URL layout.


## Author

Jeff Dairiki <dairiki@dairiki.org>
