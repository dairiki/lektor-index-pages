## Changelog

### Next Release

This release drops support for python 3.7, and starts testing under python 3.12.

#### Bugs Fixed

- Fix typo/braino in
  `test_buildprog.py::TestIndexBuildProgram::test_produce_artifacts`. ([5c01e17])

[5c01e17]: https://github.com/dairiki/lektor-index-pages/commit/5c01e17dc653599e259f079d66189c557e917bd6

### Release 1.1.0 (2023-06-16)

- Drop support for Lektor 3.2.x
- Test under python 3.11
- Add type annotations
- Convert packaging from setuptools to [PDM]
- Disuse `pkg_resources` in favor of `importlib.metadata`
- Add [pre-commit] configuration
- Run [black] and [reorder-python-imports] on code

[PDM]: https://pdm.fming.dev/latest/
[pre-commit]: https://pre-commit.com/
[black]: https://black.readthedocs.io/en/stable/index.html
[reorder-python-imports]: https://github.com/asottile/reorder-python-imports

### Release 1.0 (2022-01-28)

- Drop support for python 2.7 and 3.6.
- Fix deprecation warning from `jinja2`. Jinja2 version 3 is now required.

#### Documentation

- Documentation clarifications, updates and fixes.
    (PR [#2][] — Thank you Bart Van Loon!)

- Add missing requirement `recommonmark` to `docs/requirements.txt`.

- Add `docs` enviroment to `tox.ini` to test that docs will build cleanly.

[#2]: <https://github.com/dairiki/lektor-index-pages/pull/2>

#### Testing

- Test under python 3.10 and lektor<3.3

### Release 0.1 (2021-02-05)

No code changes.

Update development status classifier to "stable".

### Release 0.1a3 (2020-05-08)

#### API changes

- Added a `key` field on the index virtual source object.  It is an
  alias to `_id`, but is syntactically more self-explanatory.

- The `keys` configuration key has been renamed to `key`.

- When the `key` expression is being evaluted, the record whose key(s)
  is(are) to be be computed is now available in the jinja context as
  `item` rather than `this`.

#### Documentation

- Documentation moved from README to Sphinx docs at RTFD.io

### Release 0.1a2 (2020-05-06)

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

### Release 0.1a1 (2020-05-05)

Initial release.
