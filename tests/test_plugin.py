# -*- coding: utf-8 -*-
import re

import pytest

import jinja2
from lektor.db import Query
from lektor.environment import PRIMARY_ALT

from lektor_index_pages.indexmodel import VIRTUAL_PATH_PREFIX
from lektor_index_pages.plugin import (
    Cache,
    IndexPages,
    IndexPagesPlugin,
    )
from lektor_index_pages.sourceobj import IndexSource


@pytest.fixture
def record(lektor_pad, record_path):
    record = lektor_pad.get(record_path)
    assert record is not None
    return record


class TestCache(object):
    @pytest.fixture
    def cache(self):
        return Cache()

    def test_get_or_create(self, cache, mocker):
        creator = mocker.Mock(name='creator', spec=())
        assert cache.get_or_create('key', creator) is creator.return_value
        assert cache.get_or_create('key', creator) is creator.return_value
        assert creator.mock_calls == [mocker.call()]

        assert cache.get_or_create('other', creator) is creator.return_value
        assert creator.mock_calls == [mocker.call(), mocker.call()]

    def test_clear(self, cache, mocker):
        creator = mocker.Mock(name='creator', spec=())
        assert cache.get_or_create('key', creator) is creator.return_value
        assert creator.mock_calls == [mocker.call()]

        cache.clear()
        assert cache.get_or_create('key', creator) is creator.return_value
        assert creator.mock_calls == [mocker.call(), mocker.call()]


class TestIndexPagesPlugin(object):
    @pytest.fixture
    def plugin(self, lektor_env, my_plugin_id):
        return IndexPagesPlugin(lektor_env, my_plugin_id)

    def test_config_caching(self, plugin):
        config = plugin.read_config()
        assert plugin.read_config() is config

        plugin.on_before_build_all('builder')
        assert plugin.read_config() is not config

    @pytest.fixture
    def generate_index(self, plugin, lektor_env):
        plugin.on_setup_env()
        assert len(lektor_env.custom_generators) == 1
        return lektor_env.custom_generators[0]

    @pytest.mark.parametrize("record_path, expected", [
        ("/", []),
        ("/blog", ['/blog@index-pages/year-index']),
        ])
    def test_generate_index(self, generate_index, record, expected):
        assert [idx.path for idx in generate_index(record)] == expected

    def test_skip_build(self, plugin, lektor_env):
        plugin.on_setup_env(extra_flags={'index-pages': 'skip-build'})
        assert len(lektor_env.custom_generators) == 0

    @pytest.fixture
    def resolve_virtual_path(self, plugin, lektor_env):
        plugin.on_setup_env()
        return lektor_env.virtual_sources[VIRTUAL_PATH_PREFIX]

    def test_resolve_virtual_path(self, resolve_virtual_path, blog_record):
        index = resolve_virtual_path(blog_record, ['year-index', '2020'])
        assert index.path == '/blog@index-pages/year-index/2020'

    @pytest.fixture
    def resolve_url(self, plugin, lektor_env):
        plugin.on_setup_env()
        assert len(lektor_env.custom_url_resolvers) == 1
        return lektor_env.custom_url_resolvers[0]

    def test_resolve_url(self, resolve_url, blog_record):
        index = resolve_url(blog_record, ['2020'])
        assert index.path == '/blog@index-pages/year-index/2020'

    @pytest.fixture
    def jinja_env(self, lektor_env):
        return lektor_env.jinja_env

    @pytest.fixture
    def jinja_ctx(self, jinja_env, lektor_pad):
        return jinja_env.from_string("").new_context({'site': lektor_pad})

    @pytest.fixture
    def index_pages(self, plugin, jinja_env):
        plugin.on_setup_env()
        return jinja_env.globals['index_pages']

    def test_index_pages(self, index_pages, jinja_ctx):
        rv = index_pages(jinja_ctx, 'year-index')
        assert isinstance(rv.indexes, Query)

    def test_index_pages_returns_undefined(self, index_pages, jinja_ctx):
        rv = index_pages(jinja_ctx, 'missing-index')
        assert jinja2.is_undefined(rv)

    @pytest.mark.parametrize('lektor_pad', [jinja2.Undefined('undefined')])
    def test_index_pages_missing_site(self, index_pages, jinja_ctx):
        rv = index_pages(jinja_ctx, 'year-index')
        assert jinja2.is_undefined(rv)


class TestIndexPages(object):
    @pytest.fixture
    def alt(self):
        return PRIMARY_ALT

    @pytest.fixture
    def index_root(self, config, lektor_pad, alt):
        return config.get_index_root('year-index', lektor_pad, alt)

    @pytest.fixture
    def inst(self, index_root):
        return IndexPages(index_root)

    def test_indexes(self, inst):
        assert inst.indexes.count() > 0

    def test_iter(self, inst):
        first = next(iter(inst), None)
        assert isinstance(first, IndexSource)
        assert first['year'] == 2020

    def test_bool(self, inst):
        assert inst

    def test_index_name(self, inst):
        assert inst.index_name == 'year-index'

    def test_alt(self, inst, alt):
        assert inst.alt == alt

    @pytest.mark.parametrize('alt', [PRIMARY_ALT, 'xx'])
    def test_repr(self, inst):
        assert re.match(r"<index_pages\(u?'year-index'.*\)>", repr(inst))
