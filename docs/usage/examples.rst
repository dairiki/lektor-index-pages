Examples
========

"Simple" Example: A Category Index
----------------------------------

Let's assume your blog posts already include a string-valued **category** field in their `datamodel`_, and the blog posts live under the blog at Lektor path ``/blog``. 
A category index could be generated with the following configuration in ``configs/index-pages.ini``.

.. _datamodel: https://www.getlektor.com/docs/models/

.. code-block:: ini
   :caption: ``configs/index-pages.ini``

   [category]

   # index page is rooted at /
   parent_path = /

   # the blog children are what is indexed
   items = site.get('/blog').children

   # the category field of each post is what is being indexed
   key = item.category

   # the index pages will be placed at URL path /category/<category>/
   slug_format = 'category/{}'.format(this.key)

   # this template will be rendered, once for each category to generate the index pages
   template = category-index.html

   [category.fields]
   # Define the `category` field of an index pages to be an alias for the index key
   # (in this case the category)
   category = this.key


The index template, in configured above to be ``category-index.html``, might look like:

.. code-block:: html+jinja
   :caption: ``templates/category-index.html``

   {% extends "layout.html" %}

   {% block body %}
     <h1>Category {{ this.category }}</h1>
     <p>Posts in this category:</p>
     <ul>
       {% for post in this.children %}
         <li><a href="{{ post|url }}">{{ post.title }}</a></li>
       {% endfor %}
     </ul>
   {% endblock %}


In the template for the blog parent page (at ``/blog``) one could do something like this to link to the category index pages:

.. code-block:: html+jinja
   :caption: ``templates/blog.html``

   {% extends "layout.html" %}

   {% block body %}
     <h1>The Blog!</h1>
     <p>Categories in this blog</p>
     <ul>
       {% for cat_idx in index_pages('category') %}
         <li><a href="{{ cat_idx|url }}">{{ cat_idx.category }}</a></li>
       {% endfor %}
     </ul>
   {% endblock %}


A Hairier Example: Date Index by Year and Month
------------------------------------------------

In ``configs/index-pages.ini``:

.. code-block:: ini
   :caption: ``config/index-pages.ini``

   [year]
   parent_path = /blog
   key = '{.year:04d}'.format(item.pub_date)
   template = blog-year-index.html
   subindex = month

   [year.fields]
   date = this.children.first().pub_date.replace(month=1, day=1)
   year = this.key|int

   [year.month]
   key = '{.month:02d}'.format(item.pub_date)
   template = blog-month-index.html

   [year.month.fields]
   # this.parent is the year-index page this month-index belongs to.
   date = this.parent.date.replace(month=this.key|int)
   year = this.parent.year
   month = this.key|int


This will create year-index pages at URL path :samp:`/blog/{YYYY}/` and month-indexes at :samp:`/blog/{YYYY}/{MM}/`.

Note that if the blog-post post slug format is properly configured — something like

.. code-block:: ini
   :caption: models/blog.ini

   [...]

   [children]
   slug_format = '{0.pub_date.year:04d}/{0.pub_date.month:02d}/{0._id}'.format(this)

   [...]

then blog posts will be placed at :samp:`/blog/{YYYY}/{MM}/{post-id}/` which will jibe nicely with the index URL layout described above.
