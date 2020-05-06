# -*- coding: utf-8 -*-

import copy
import datetime
from operator import itemgetter

import pytest
from lektor.environment import PRIMARY_ALT

from lektor_index_pages.indexmodel import (
    VIRTUAL_PATH_PREFIX,
    index_models_from_ini,
    )
from lektor_index_pages.sourceobj import (
    IndexRoot,
    IndexSource,
    )


@pytest.fixture
def year_index_slug():
    return None


@pytest.fixture
def inifile(inifile, year_index_slug,
            # XXX: not sure why I need to explicitly call these out
            # They are used by our inherited inifile fixture
            pagination_enabled, month_index_enabled):
    if year_index_slug is not None:
        inifile['year-index.slug'] = year_index_slug
    return inifile


@pytest.fixture
def index_root_model(lektor_env, inifile):
    for parent, model in index_models_from_ini(lektor_env, inifile):
        break
    assert parent == '/blog'
    assert model.index_name == 'year-index'
    return model


@pytest.fixture
def year_index_model(index_root_model):
    return index_root_model.subindex_model


@pytest.fixture
def page_num():
    return None


@pytest.fixture
def index_root(index_root_model, blog_record, lektor_alt, page_num):
    record = blog_record
    if lektor_alt != PRIMARY_ALT:
        record = record.pad.get(record.path, alt=lektor_alt)
    return IndexRoot(index_root_model, record)


@pytest.fixture
def year_index(index_root):
    return index_root.subindexes.first()


@pytest.fixture(params=['index_root', 'year_index'])
def index(request, lektor_alt):
    return request.getfixturevalue(request.param)


@pytest.mark.usefixtures('plugin')
class TestIndexSource(object):
    # FIXME: these tests should be reorganized

    def test_get_index_root(self, index_root_model, blog_record):
        index_root = IndexRoot.get_index(index_root_model, blog_record)
        assert index_root.path == '/blog@index-pages/year-index'

        reget = IndexRoot.get_index(index_root_model, blog_record)
        # should return cached value
        assert reget is index_root

    @pytest.mark.parametrize('page_num', [None, 1, 2])
    def test_get_index(self, year_index_model, index_root, page_num):
        id_ = '2020'
        children = index_root.children
        year_index = IndexSource.get_index(
            year_index_model, index_root, id_, children, page_num)
        assert year_index.page_num == page_num

        reget = IndexSource.get_index(
            year_index_model, index_root, id_, children, page_num)
        # should return cached value
        assert reget is year_index

    def test_parent(self, year_index, index_root):
        assert year_index.parent == index_root

    def test_slug(self, index_root, year_index):
        # FIXME: this should be split up
        assert index_root._slug is None
        assert year_index._slug == '2020'

    @pytest.mark.parametrize('name, expected', [
        ('_hidden', True),
        ('_model', False),      # Undefined
        ])
    def test_contains(self, year_index, name, expected):
        assert (name in year_index) is expected

    def test_getitem(self, year_index):
        assert year_index['_id'] == '2020'

    def test_getitem_with_descriptor(self, year_index):
        assert year_index['_gid'] == year_index._gid

    def test_children(self, index_root, blog_record):
        assert list(index_root.children) == list(blog_record.children)

    def test_pagination(self, year_index, blog_record, pagination_enabled):
        if pagination_enabled:
            assert year_index.pagination.total == blog_record.children.count()
        else:
            with pytest.raises(RuntimeError):
                year_index.pagination

    def test_subindexes(self, index, index_root):
        if index is index_root:
            assert list(map(itemgetter('_id'), index.subindexes)) == ['2020']
        else:
            assert not hasattr(index, 'subindexes')

    def test__subindex_ids(self, index_root):
        assert index_root._subindex_ids == ('2020',)

    def test_path(self, index_root):
        assert index_root.path == "/blog@%s/year-index" % VIRTUAL_PATH_PREFIX

    def test__gid(self, index_root):
        # md5("/blog@index-pages/year-index")
        assert index_root._gid == "7797910bec275f5dd5e07c6eefb4be4d"

    @pytest.mark.parametrize("year_index_slug, expected", [
        (None, "/blog/2020/"),
        ("this._id ~ '_html'", "/blog/2020_html/"),
        ("'{}.html'.format(this._id)", "/blog/2020.html"),
        ])
    def test_url_path(self, year_index, expected):
        assert year_index.url_path == expected

    @pytest.mark.parametrize('pagination_enabled', [True])
    def test_url_path_paginated(self, year_index):
        assert year_index.__for_page__(2).url_path == "/blog/2020/page/2/"

    @pytest.mark.parametrize("path, should_resolve", [
        ('', 'root'),
        ('199', False),
        ('2020', 'year'),
        ('2020/page', False),
        ('2020/page/1', 'year-with-page'),
        ('2020/page/2', False),  # page must be non-empty
        ('2020/page/1/1', False),
        ('2020/3', False),
        ('2020/03', 'month'),
        ('2019/03', False),
        ('2020/04/page', False),
        ('2020/04/page/1', 'month-with-page'),
        ('2020/05/page/1', False),
        ('2020/04/page/1/x', False),
        ])
    @pytest.mark.parametrize('pagination_enabled', [True, False])
    @pytest.mark.parametrize('month_index_enabled', [True, False])
    def test_resolve_virtual_path(self, index_root, path, should_resolve,
                                  pagination_enabled,
                                  month_index_enabled):
        if should_resolve:
            flags = should_resolve.split('-')
            if 'month' in flags and not month_index_enabled:
                should_resolve = False
            if 'page' in flags and not pagination_enabled:
                should_resolve = False

        pieces = path.split('/') if path else []
        source = index_root.resolve_virtual_path(pieces)

        if should_resolve:
            expected_path = '/'.join(['/blog@index-pages/year-index'] + pieces)
            assert source.path == expected_path
        else:
            assert source is None

    @pytest.mark.parametrize(
        'pagination_enabled, url_path, index_type, path', [
            (False, '', 'root',
             '/blog@index-pages/year-index'),
            (False, 'x', None, None),
            (False, '2020', 'year',
             '/blog@index-pages/year-index/2020'),
            (1, '2020', 'year',
             '/blog@index-pages/year-index/2020/page/1'),
            (1, '2020/page', None, None),
            (1, '2020/page/1', None, None),
            (1, '2020/page/2', 'year',
             '/blog@index-pages/year-index/2020/page/2'),
            (1, '2020/page/3', None, None),
            (False, '2020/04', 'month',
             '/blog@index-pages/year-index/2020/04'),
            (False, '2020/13', None, None),
            (True, '2020/03', 'month',
             '/blog@index-pages/year-index/2020/03/page/1'),
            (False, '2020/02/x', None, None),
            ])
    @pytest.mark.parametrize('month_index_enabled', [True, False])
    def test_resolve_url_path(self, index_root,
                              url_path, index_type, path,
                              month_index_enabled):
        url_path = url_path.split('/') if url_path else []

        should_resolve = bool(index_type)
        if not month_index_enabled and index_type == 'month':
            should_resolve = False

        source = index_root.resolve_url_path(url_path)

        if should_resolve:
            assert source.path == path
        else:
            assert source is None

    @pytest.mark.parametrize('page_num', [None, 1, 2])
    def test_for_page(self, year_index, page_num):
        paginated = year_index.__for_page__(page_num)
        assert paginated.page_num == page_num

    @pytest.mark.parametrize('month_index_enabled', [True])
    def test_get_checksum(self, index):
        assert index.get_checksum('ignored') \
            == index._compute_checksum(index._get_checksum_data('ignored'))

    def test_get_checksum_data(self, index_root):
        assert index_root._get_checksum_data('ignored') == (
            '/blog@index-pages/year-index',
            ['/blog/second-post', '/blog/first-post'],
            ('2020',),
            )

    @pytest.mark.parametrize('pagination_enabled', [True])
    @pytest.mark.parametrize('month_index_enabled', [True])
    def test_get_checksum_data_paginated(self, year_index):
        assert year_index._get_checksum_data('ignored') == (
            '/blog@index-pages/year-index/2020',
            "NPAGES=1",
            ('04', '03'),
            )
        assert year_index.__for_page__(1)._get_checksum_data('ignored') == (
            '/blog@index-pages/year-index/2020/page/1',
            ['/blog/second-post', '/blog/first-post'],
            ('04', '03'),
            )

    def test_get_checksum_data_no_subindexes(self, year_index):
        assert year_index._get_checksum_data('ignored') == (
            '/blog@index-pages/year-index/2020',
            ['/blog/second-post', '/blog/first-post'],
            )

    @pytest.mark.parametrize('data, checksum', [
        ((u"path", [u"c1"], (u"id")),
         "e2df3e68cc1a7573ec975aad5b2eb17e1d445165"),
        ])
    def test_compute_checksum(self, data, checksum):
        assert IndexSource._compute_checksum(data) == checksum

    @pytest.mark.parametrize('blog_is_hidden', [True, False])
    def test_is_hidden(self, year_index, blog_is_hidden, blog_record):
        if blog_is_hidden:
            blog_record._data['_hidden'] = True
        assert year_index.is_hidden is blog_is_hidden

    @pytest.mark.parametrize('blog_is_hidden', [True, False])
    def test_index_root_is_hidden(self, index_root, blog_is_hidden,
                                  blog_record):
        if blog_is_hidden:
            blog_record._data['_hidden'] = True
        assert index_root.is_hidden

    @pytest.mark.parametrize("fields, expect_reverse", [
        (['date', 'non-existing'], False),
        (['-date', 'non-existing'], True),
        (['+date', 'non-existing'], False),
        ])
    def test_get_sort_key(self, year_index, fields, expect_reverse):
        sort_key = year_index.get_sort_key(fields)
        assert len(sort_key) == 2
        assert sort_key[0].value == datetime.date(2020, 1, 1)
        assert sort_key[0].reverse == expect_reverse
        assert sort_key[1].value is None

    def test_eq_self(self, index):
        assert index == index
        assert not (index != index)
        assert hash(index) == hash(index)

    def test_eq_copy(self, index):
        index_copy = copy.copy(index)
        assert index == index_copy
        assert not (index != index_copy)
        assert hash(index) == hash(index_copy)

    def test_ne_other(self, year_index):
        other = year_index.__for_page__(1)
        assert year_index != other
        assert not (year_index == other)
        assert hash(year_index) != hash(other)

    def test_repr(self, year_index):
        assert repr(year_index) == \
            "<IndexSource path='/blog@index-pages/year-index/2020'>"

    def test_repr_with_page_num(self, year_index):
        assert repr(year_index.__for_page__(2)) == \
            "<IndexSource path='/blog@index-pages/year-index/2020' page_num=2>"

    @pytest.mark.parametrize('lektor_alt', ['xx'])
    def test_repr_with_alt(self, index):
        assert repr(index).endswith(" alt='xx'>")
