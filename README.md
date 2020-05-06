# Lektor Index Pages Plugin

[![PyPI version](https://img.shields.io/pypi/v/lektor-index-pages.svg)](https://pypi.org/project/lektor-index-pages/)
[![PyPI Supported Python Versions](https://img.shields.io/pypi/pyversions/lektor-index-pages.svg)](https://pypi.python.org/pypi/lektor-index-pages/)
[![GitHub license](https://img.shields.io/github/license/dairiki/lektor-index-pages)](https://github.com/dairiki/lektor-index-pages/blob/master/LICENSE)
[![GitHub Actions (Tests)](https://github.com/dairiki/lektor-index-pages/workflows/Tests/badge.svg)](https://github.com/dairiki/lektor-index-pages)


This [Lektor][] plugin can be used to generate “index pages” for a
blog or similar collection of pages.  These index pages list the blog posts
segregated by some key, with each index page containing only those posts
which match that key.

Examples include:

- *Category Indexes*: A set of index pages, one for each category,
  which lists all the posts in that category.  (Multi-valued index keys
  are also supported, so that each post can appear on more than a single
  index page: e.g. *keyword indexes*.)

- *Date Indexes*: A set of index pages, one for each year (say),
  which list all the posts in by year.
  (The indexes can be configured to support subindexes, so that each
  year index may have as children a set of month indexes.)

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

This plugin is configured by creating a configfile named `index-pages.ini` in
the `configs` subdirectory of the Lektor tree.

Each section in the config file which does not have a dotted section name and which
includes a setting for the `keys` key defines a top-level index.  The index is
named after the section name.

## Examples

### “Simple” Example: A Category Index

Let’s assume your blog posts already include a string-valued ``category``
field in their [datamodel][], and the blog posts live under the blog
at Lektor path `/blog`. A category index could be generated with the following
configuration in `configs/index-pages.ini`.

[datamodel]: <https://www.getlektor.com/docs/models/> "Lektor Data Model Documentation"

```ini
[category]

# index page are rooted at /
parent = /

# the blog children are what is indexed
items = site.get('/blog').children

# the category of each post is what is being indexed
keys = this.category

# the index pages will be placed at URL path /category/<category>/
slug = 'category/{}'.format(this._id)

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
    {% for cat_idx in index_pages(site.root, 'category') %}
      <li><a href="{cat_idx|url}">{{ cat_idx.category }}</a></li>
    {% endfor %}
  </ul>
{% endblock %}
```

### A Hairier Example: Date Index by Year then Month

In `configs/index-pages.ini`:

```ini
[date]
parent = /blog
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
