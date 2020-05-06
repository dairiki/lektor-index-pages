# -*- coding: utf-8 -*-
"""Index pages for Lektor

FIXME: figure out how to get stale index files to prune correctly

"""
from threading import Lock

import jinja2
from werkzeug.utils import cached_property

from lektor.context import get_ctx
from lektor.db import Record
from lektor.environment import PRIMARY_ALT
from lektor.pluginsystem import Plugin

from .buildprog import IndexBuildProgram
from .config import Config
from .indexmodel import VIRTUAL_PATH_PREFIX
from .sourceobj import IndexBase


class Cache(object):
    """Cache expensive computations by the indexes.

    This cache is used to store expensive computations made by the index source
    objects (see lektor_index_pages.sourceobj.IndexBase).

    Already, our index source objects are cached in Lektor's pad.
    That, by itself, takes care of most of our caching needs during
    regular builds.

    The devserver HTTP server, however, tries to resolve nearly every
    URL requested through each plugin.  For each web request it does
    this using a fresh pad — so much for our caching on the pad.

    So this is a separate cache, whose main purpose is to keep the devserver
    from being too slow responding to http requests.

    """
    def __init__(self):
        self.lock = Lock()
        self.data = {}

    def get_or_create(self, key, creator):
        with self.lock:
            if key in self.data:
                return self.data[key]
        value = creator()
        with self.lock:
            self.data[key] = value
        return value

    def clear(self):
        with self.lock:
            self.data.clear()


class IndexPagesPlugin(Plugin):
    name = 'Index Pages'
    description = u'Lektor plugin to index pages.'

    _inifile = None         # for testing

    def __init__(self, env, id):
        super(IndexPagesPlugin, self).__init__(env, id)
        self.cache = Cache()

    def read_config(self):
        def parse_config():
            inifile = self._inifile or self.get_config()
            return Config.from_ini(self.env, inifile)
        return self.cache.get_or_create('config', parse_config)

    def on_before_build_all(self, builder, **extra):
        self.cache.clear()

    def on_setup_env(self, extra_flags=None, **extra):
        env = self.env

        skip_build = False
        if extra_flags:
            flags = extra_flags.get('index-pages', '').split(',')
            skip_build = 'skip-build' in flags

        env.add_build_program(IndexBase, IndexBuildProgram)

        if not skip_build:
            @env.generator
            def generate_index(record):
                config = self.read_config()
                return config.iter_index_roots(record)

        @env.virtualpathresolver(VIRTUAL_PATH_PREFIX)
        def resolve_virtual_path(record, pieces):
            config = self.read_config()
            return config.resolve_virtual_path(record, pieces)

        @env.urlresolver
        def resolve_url(record, url_path):
            config = self.read_config()
            return config.resolve_url_path(record, url_path)

        @jinja2.environmentfunction
        def index_pages(jinja_env, record_or_path, index_name):
            config = self.read_config()
            try:
                return IndexPages(config, record_or_path, index_name)
            except ReturnUndefined as exc:
                return jinja_env.undefined('index_pages: %s' % exc)

        env.jinja_env.globals['index_pages'] = index_pages


class ReturnUndefined(Exception):
    pass


class IndexPages(object):
    def __init__(self, config, record_or_path, index_name):
        record = coerce_to_record(record_or_path)
        index_root = config.get_index_root(record, index_name)
        if index_root is None:
            raise ReturnUndefined("no index %r is configured on %r"
                                  % (index_name, record))

        self.index_root = index_root
        self.index_name = index_name
        self.record = record

    @cached_property
    def indexes(self):
        return self.index_root.subindexes

    def __iter__(self):
        return iter(self.indexes)

    def __bool__(self):
        return bool(self.indexes)

    __nonzero__ = __bool__      # py2

    def __repr__(self):
        return "<index_pages({!r}, {!r})>".format(self.record, self.index_name)


def coerce_to_record(record_or_path):
    if isinstance(record_or_path, Record):
        record = record_or_path
        # get unpaginated version
        assert record.record is record or record.page_num is not None
        return record.record
    elif isinstance(record_or_path, str):
        path = record_or_path
        ctx = get_ctx()
        if ctx is None:
            raise RuntimeError("No context found")
        alt = getattr(ctx.source, 'alt', PRIMARY_ALT)
        record = ctx.pad.get(path, alt=alt, allow_virtual=False)
        if record is None:
            raise ReturnUndefined("no record exists for path %r" % path)
        return record
    else:
        raise ReturnUndefined(
            "expected a record or path, not %r" % record_or_path)
