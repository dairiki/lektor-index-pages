## Changelog

### Version 0.1a3

Released 2020-05-08.

#### API changes

- Added a `key` field on the index virtual source object.  It is an
  alias to `_id`, but is syntactically more self-explanatory.

- The `keys` configuration key has been renamed to `key`.

- When the `key` expression is being evaluted, the record whose key(s)
  is(are) to be be computed is now available in the jinja context as
  `item` rather than `this`.

#### Documentation

- Documentation moved from README to Sphinx docs at RTFD.io

### Version 0.1a2

Released 2020-05-06.

#### API changes

- The `record` argument has been dropped from the (jinja) global
  `index_pages` function.  (Since indexes can not have multiple
  parents, it is not necessary.)

- The `parent` configuration key has been renamed to `parent_path`.

- The `slug` configuration key has been renamed to `slug_format`.

- The `attributes` config section has been renamed to `fields`.

  Though they are not quite like regular Lektor Record fields, they
  are more field-like than attribute-like.  (I.e. access is via
  *__getitem__* rather than *getattr*.)

### Version 0.1a1

Released 2020-05-05.

Initial release.
