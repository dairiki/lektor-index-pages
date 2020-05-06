## Changelog

### 0.1a2 — 2020-05-06

#### API changes

- Drop the `record` argument from the (jinja) global `index_pages` function.
  (Since indexes can not have multiple parents, it is not necessary.)

- The `parent` configuration key has been renamed to `parent_path`.

- The `slug` configuration key has been renamed to `slug_format`.

- The `attributes` config section has been renamed to `fields`.

  Though they are not quite like regular Lektor Record fields, they
  are more field-like than attribute-like.  (I.e. access is via
  *__getitem__* rather than *getattr*.)

### 0.1a1 — 2020-05-05

Initial release.
