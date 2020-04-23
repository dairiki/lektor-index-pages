# -*- coding: utf-8 -*-

import pytest

from lektor_index_pages.config import Config
from lektor_index_pages.indexmodel import index_models_from_ini
from lektor_index_pages.sourceobj import IndexRoot


@pytest.fixture
def index_root_model(lektor_env, inifile):
    for parent, model in index_models_from_ini(lektor_env, inifile):
        break
    return model


class TestConfig(object):

    @pytest.fixture
    def config(self, lektor_env, inifile):
        return Config.from_ini(lektor_env, inifile)

    @pytest.mark.parametrize("name, should_resolve", [
        ('year-index', True),
        ('missing', False),
        ])
    def test_get_index_root(self, config, blog_record, name, should_resolve):
        root = config.get_index_root(blog_record, name)
        if should_resolve:
            assert isinstance(root, IndexRoot)
            assert root._id == name
        else:
            assert root is None

    def test_iter_index_roots(self, config, blog_record):
        roots = list(config.iter_index_roots(blog_record))
        assert len(roots) == 1
        assert isinstance(roots[0], IndexRoot)
        assert roots[0]._id == 'year-index'

    def test_resolve_virtual_path(self, config, blog_record):
        root = config.resolve_virtual_path(blog_record, ['year-index'])
        assert isinstance(root, IndexRoot)

    def test_resolve_virtual_path_caching(self, config, blog_record):
        source = config.resolve_virtual_path(blog_record, ['year-index'])
        assert source._id == 'year-index'
        reget = config.resolve_virtual_path(blog_record, ['year-index'])
        assert reget is source

    def test_resolve_virtual_path_failure(self, config, blog_record):
        assert config.resolve_virtual_path(blog_record, ['missing']) is None

    @pytest.mark.usefixtures('plugin')
    def test_resolve_url_path(self, config, blog_record):
        year_idx = config.resolve_url_path(blog_record, ['2020'])
        assert year_idx['year'] == 2020
