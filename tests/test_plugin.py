# -*- coding: utf-8 -*-
import re

import pytest

import jinja2
from lektor.db import Query

from lektor_index_pages.indexmodel import VIRTUAL_PATH_PREFIX
from lektor_index_pages.plugin import (
    coerce_to_record,
    Cache,
    IndexPages,
    IndexPagesPlugin,
    ReturnUndefined,
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
    def index_pages(self, plugin, jinja_env):
        plugin.on_setup_env()
        return jinja_env.globals['index_pages']

    def test_index_pages(self, index_pages, jinja_env, blog_record):
        rv = index_pages(jinja_env, blog_record, 'year-index')
        assert isinstance(rv.indexes, Query)

    def test_index_pages_returns_undefined(
            self, index_pages, jinja_env, lektor_pad):
        rv = index_pages(jinja_env, lektor_pad.root, 'year-index')
        assert jinja2.is_undefined(rv)


class TestIndexPages(object):
    @pytest.fixture
    def inst(self, config, blog_record):
        return IndexPages(config, blog_record, 'year-index')

    @pytest.mark.parametrize("record_path, index_name", [
        ("/", 'year-index'),
        ("/blog/first-post", 'year-index'),
        ("/blog", 'no-such-index'),
        ])
    def test_no_such_index(self, config, record, index_name):
        with pytest.raises(ReturnUndefined,
                           match=r'no index .* is configured'):
            return IndexPages(config, record, index_name)

    def test_indexes(self, inst):
        assert inst.indexes.count() > 0

    def test_iter(self, inst):
        first = next(iter(inst), None)
        assert isinstance(first, IndexSource)
        assert first['year'] == 2020

    def test_bool(self, inst):
        assert inst

    def test_repr(self, inst):
        assert re.match(r'<index_pages(.*)>\Z', repr(inst))


class Test_coerce_to_record(object):
    @pytest.fixture
    def source(self, lektor_pad, source_path):
        source = lektor_pad.get(source_path)
        assert source is not None
        return source

    @pytest.mark.parametrize("source_path, record_path", [
        ("/blog", "/blog"),
        ("/blog@1", "/blog"),
        ("/", "/"),
        ("/blog/first-post", "/blog/first-post"),
        ])
    def test_from_source(self, source, record_path):
        record = coerce_to_record(source)
        assert record.path == record_path

    def test_from_virtual_source(self, lektor_pad):
        source = lektor_pad.get("/blog@index-pages/2020")
        with pytest.raises(ReturnUndefined, match=r'expected a record'):
            coerce_to_record(source)

    @pytest.mark.usefixtures('lektor_context')
    def test_from_path(self):
        path = "/blog/first-post"
        source = coerce_to_record(path)
        assert source.path == path

    @pytest.mark.usefixtures('lektor_context')
    def test_missing_path(self):
        with pytest.raises(ReturnUndefined, match=r'no record exists'):
            coerce_to_record("/missing")

    def test_no_context(self):
        with pytest.raises(RuntimeError, match=r'(?i)no context'):
            coerce_to_record("/path")
