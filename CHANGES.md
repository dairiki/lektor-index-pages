## Changelog

### Unreleased

#### API changes

- The `attributes` config section has been renamed to `fields`.

  Though they are not quite like regular Lektor Record fields, they
  are more field-like than attribute-like.  (I.e. access is via
  *__getitem__* rather than *getattr*.)

### 0.1a1 — 2020-05-05

Initial release.
