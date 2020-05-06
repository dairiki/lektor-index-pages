# -*- coding: utf-8 -*-

import pytest

from lektor_index_pages.config import (
    Config,
    NoSuchIndex,
    )
from lektor_index_pages.sourceobj import IndexRoot


class TestConfig(object):
    @pytest.fixture
    def parent_path(self):
        return '/blog'

    @pytest.fixture
    def inifile(self, inifile, parent_path):
        inifile['year-index.parent_path'] = parent_path
        return inifile

    @pytest.fixture
    def config(self, lektor_env, inifile):
        return Config.from_ini(lektor_env, inifile)

    def test_get_index_root(self, config, lektor_pad):
        root = config.get_index_root('year-index', lektor_pad)
        assert isinstance(root, IndexRoot)
        assert root._id == 'year-index'

    def test_get_index_root_fails_if_name_unknown(self, config, lektor_pad):
        with pytest.raises(NoSuchIndex,
                           match=r'no index named .* is configured'):
            config.get_index_root('missing', lektor_pad)

    @pytest.mark.parametrize('parent_path', ['/missing-parent'])
    def test_get_index_root_fails_if_parent_unknown(self, config, lektor_pad):
        with pytest.raises(NoSuchIndex, match=r'no parent .*\bexists'):
            config.get_index_root('year-index', lektor_pad)

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
