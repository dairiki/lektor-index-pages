# -*- coding: utf-8 -*-
"""Index pages for Lektor

FIXME: figure out how to get stale index files to prune correctly

"""
from threading import Lock

import jinja2

from lektor.environment import PRIMARY_ALT
from lektor.pluginsystem import Plugin

from .buildprog import IndexBuildProgram
from .config import (
    Config,
    NoSuchIndex,
    )
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
    URL requested through each plugin that registers a URL resolver.
    For each web request it does this using a fresh pad — so much for
    our caching on the pad.

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

        @jinja2.contextfunction
        def index_pages(jinja_ctx, index_name, alt=PRIMARY_ALT):
            pad = jinja_ctx.resolve('site')
            if jinja2.is_undefined(pad):
                return pad

            config = self.read_config()
            try:
                index_root = config.get_index_root(index_name, pad, alt)
            except NoSuchIndex as exc:
                return jinja_ctx.environment.undefined('index_pages: %s' % exc)
            return IndexPages(index_root)

        env.jinja_env.globals['index_pages'] = index_pages


class IndexPages(object):
    def __init__(self, index_root):
        self.index_root = index_root

    @property
    def indexes(self):
        return self.index_root.subindexes

    def __iter__(self):
        return iter(self.indexes)

    def __bool__(self):
        return bool(self.indexes)

    __nonzero__ = __bool__      # py2

    @property
    def index_name(self):
        return self.index_root._id

    @property
    def alt(self):
        return self.index_root.alt

    def __repr__(self):
        if self.alt == PRIMARY_ALT:
            fmt = "<index_pages({0.index_name!r})>"
        else:
            fmt = "<index_pages({0.index_name!r}, {0.alt!r})>"
        return fmt.format(self)
