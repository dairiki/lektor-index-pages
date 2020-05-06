# -*- coding: utf-8 -*-

import copy
import datetime
import inspect
import re

import pytest

from inifile import IniFile

from lektor_index_pages.indexmodel import (
    VIRTUAL_PATH_PREFIX,
    PaginationConfig,
    IndexRootModel,
    IndexModel,
    ExpressionCompiler,
    index_models_from_ini,
    _index_model_from_ini,
    _attribute_config_from_ini,
    _pagination_config_from_ini,
    )


@pytest.fixture
def pagination_config(lektor_env, pagination_enabled):
    kw = {}
    if not isinstance(pagination_enabled, bool):
        kw['per_page'] = int(pagination_enabled)
        pagination_enabled = bool(pagination_enabled)

    return PaginationConfig(lektor_env, enabled=pagination_enabled, **kw)


class DummyQuery(object):
    def __init__(self, count):
        self._count = count

    def count(self):
        return self._count


class DummyPaginatable(object):
    def __init__(self, page_num=None, record=None, nchildren=0):
        if record is None:
            record = object()
        self.page_num = page_num
        self.record = record
        self.children = DummyQuery(nchildren)

    def __for_page__(self, page_num):
        if page_num == self.page_num:
            return self
        clone = copy.copy(self)
        clone.page_num = page_num
        return clone


@pytest.mark.parametrize("page_num", [None, 1, 2])
class TestPaginationConfig(object):
    @pytest.fixture(params=[False, True])
    def source(self, request, lektor_pad):
        if request.param:
            # Dummy virtual source with .__for_page__ method
            return DummyPaginatable()
        else:
            # Concrete record
            return lektor_pad.get('/blog/first-post')

    def test_get_record_for_page(self, pagination_config, source, page_num):
        paginated = pagination_config.get_record_for_page(source, page_num)
        paginated.page_num == page_num
        paginated.record is source.record


class TestIndexRootModel(object):

    @pytest.fixture
    def items(self):
        return None

    @pytest.fixture
    def model(self, lektor_env, items, mocker):
        return IndexRootModel(
            lektor_env,
            index_name='test-index',
            index_model=mocker.sentinel.index_model,
            items=items,
            config_filename='dummy.ini')

    def test_datamodel(self, model):
        datamodel = model.datamodel
        assert datamodel.filename == 'dummy.ini'
        assert not datamodel.pagination_config.enabled

    def test_get_virtual_path(self, model, mocker):
        parent = mocker.sentinel.parent
        assert model.get_virtual_path(parent) \
            == VIRTUAL_PATH_PREFIX + '/test-index'

    def test_match_path_pagination(self, model, mocker):
        source = mocker.sentinel.parent
        assert model.match_path_pagination(source, ['page', '2']) is None

    @pytest.mark.parametrize(('items', 'paths'), [
        (None,
         ['/blog/second-post', '/blog/first-post']),
        ("this.children.filter(F._id == 'second-post')",
         ['/blog/second-post']),
        ])
    def test_get_items(self, model, blog_record, paths):
        assert [post.path for post in model.get_items(blog_record)] \
            == paths


class TestIndexModel(object):
    @pytest.fixture
    def nchildren(self):
        return 1

    @pytest.fixture
    def source(self, nchildren, lektor_pad, lektor_alt):
        source = DummyPaginatable(nchildren=nchildren)
        source.pad, source.alt = lektor_pad, lektor_alt
        source._id = 'source-id'
        return source

    @pytest.fixture
    def blog_post(self, lektor_pad, lektor_alt):
        blog_post = DummyPaginatable()
        blog_post.pad, blog_post.alt = lektor_pad, lektor_alt
        blog_post.pub_date = datetime.date(2020, 3, 21)
        blog_post.tags = ['tag1', 'tag2']
        blog_post.funky_tags = ['tag@1', 'täg2']
        return blog_post

    @pytest.fixture
    def keys(self):
        return "this.tags"

    @pytest.fixture
    def template(self):
        return None

    @pytest.fixture
    def slug(self):
        return None

    @pytest.fixture
    def attributes(self):
        return None

    @pytest.fixture
    def model(self, lektor_env, keys, template, slug, attributes,
              pagination_config, mocker):
        return IndexModel(
            lektor_env,
            keys=keys,
            template=template,
            slug=slug,
            attributes=attributes,
            pagination_config=pagination_config,
            subindex_model=mocker.sentinel.subindex_model,
            config_filename='dummy.ini')

    @pytest.mark.parametrize('template, expected', [
        (None, 'index-pages.html'),
        ('foo.html', 'foo.html'),
        ])
    def test_template(self, model, expected):
        assert model.template == expected

    def test_datamodel(self, model, pagination_enabled):
        datamodel = model.datamodel
        assert datamodel.filename == 'dummy.ini'
        assert datamodel.pagination_config.enabled is bool(pagination_enabled)

    @pytest.mark.parametrize(('parent_path', 'id_', 'page_num', 'expected'), [
        ('foo', 'bar', None, "foo/bar"),
        ('foo', 'bar', 42, "foo/bar/page/42"),
        ])
    def test_get_virtual_path(self, model,
                              parent_path, id_, page_num, expected,
                              mocker):
        parent = mocker.Mock(name='parent', spec=(),
                             virtual_path=parent_path,
                             page_num=None)
        assert model.get_virtual_path(parent, id_, page_num) == expected

    @pytest.mark.parametrize(
        'pieces, pagination_enabled, nchildren, page_num', [
            (['page', '1'], True, 10, 1),
            (['page', '1', 'x'], True, 10, False),
            (['PAGE', '1'], True, 10, False),
            (['page', '1'], False, 10, False),
            (['page', '0'], True, 10, False),
            (['page', '2'], True, 10, False),  # only one page
            (['page', '2'], True, 30, 2),
            ]
        )
    def test_match_path_pagination(self, model, source, pieces, page_num):
        rv = model.match_path_pagination(source, pieces)
        if page_num is False:
            assert rv is None
        else:
            assert rv.page_num == page_num
            assert rv.record == source.record

    @pytest.mark.parametrize('keys, expected', [
        ("this.tags", ['tag1', 'tag2']),
        ("'{:04d}'.format(this.pub_date.year)", ['2020']),
        ("this.funky_tags", ['tag_1', 'täg2']),
        ])
    def test_keys_for_post(self, model, blog_post, expected):
        assert list(model.keys_for_post(blog_post)) == expected

    @pytest.mark.parametrize('slug, expected', [
        (None, 'source-id'),
        ("'custom slug/%s'|format(this._id)", 'custom-slug/source-id'),
        ])
    def test_get_slug(self, model, source, expected):
        assert model.get_slug(source) == expected

    @pytest.mark.parametrize('attributes', [
        [('id_upper', 'this._id.upper()')],
        ])
    def test_data_descriptors(self, model, source):
        data = dict(model.data_descriptors)
        assert data['id_upper'].__get__(source) == 'SOURCE-ID'


class TestExpressionCompiler(object):
    @pytest.fixture
    def filename(self):
        return 'config.ini'

    @pytest.fixture
    def section(self):
        return 'some-section'

    @pytest.fixture
    def compiler(self, lektor_env, filename, section):
        return ExpressionCompiler(lektor_env, filename, section)

    @pytest.mark.parametrize('filename', ['config.ini', None])
    @pytest.mark.parametrize('section', ['section', None])
    def test_location(self, compiler, filename, section):
        if filename:
            expect = r'in .*\b%s\b' % re.escape(filename)
            assert re.search(expect, compiler.location)
        if section:
            expect = r'\[%s\]' % re.escape(section)
            assert re.search(expect, compiler.location)

    def test_error_report(self, compiler):
        with pytest.raises(RuntimeError,
                           match=r'syntax error in config') as excinfo:
            compiler('test', 'messed up')
        assert 'messed up' in str(excinfo.value)

    def test_call(self, compiler, blog_record):
        desc = compiler('test', 'this.path')
        assert desc.__get__(blog_record) == blog_record.path


class IniReaderBase(object):
    @pytest.fixture
    def inifile(self, test_ini):
        inifile = IniFile(str(test_ini))
        inifile.filename = '/dev/null'
        return inifile


class Test_index_models_from_ini(IniReaderBase):
    @pytest.fixture(scope='session')
    def test_ini(self, tmp_path_factory):
        test_ini = tmp_path_factory.mktemp('imsfi') / 'test.ini'
        test_ini.write_text(inspect.cleandoc(u'''
        [index1]
        parent = /blog
        keys = this.category

        [index2]
        keys = this.tags

        [index3]
        template = tmpl.html

        [index4.subindex]
        keys = this.tags
        '''))
        return test_ini

    def test(self, lektor_env, inifile):
        models = [
            (parent, model.index_name)
            for parent, model in index_models_from_ini(lektor_env, inifile)
            ]
        assert models == [('/blog', 'index1'), ('/', 'index2')]


class Test_index_model_from_ini(IniReaderBase):
    @pytest.fixture(scope='session')
    def test_ini(self, tmp_path_factory):
        test_ini = tmp_path_factory.mktemp('imfi') / 'test.ini'
        test_ini.write_text(inspect.cleandoc(u'''
        [index1]
        keys = this.category
        template = tmpl.html
        subindex = subidx
        slug = "c-" ~ this.category

        [index1.attributes]
        foo = bar

        [index1.pagination]
        per_page = 3

        [index1.subidx]
        keys = this.subcategory
        template = tmpl2.html
        '''))
        return test_ini

    def test(self, lektor_env, inifile):
        model = _index_model_from_ini(lektor_env, inifile, 'index1')
        assert model.keys_expr.expr == "this.category"
        assert model.template == "tmpl.html"
        assert model.slug_expr.expr == '"c-" ~ this.category'
        assert model.datamodel.pagination_config.per_page == 3
        assert len(model.data_descriptors) == 1
        assert model.data_descriptors[0][0] == "foo"

        assert model.subindex_model.keys_expr.expr == "this.subcategory"
        assert model.subindex_model.template == "tmpl2.html"

    def test_keys_required(self, lektor_env, inifile):
        del inifile['index1.keys']
        with pytest.raises(RuntimeError, match="keys required"):
            _index_model_from_ini(lektor_env, inifile, 'index1')


class Test_attribute_config_from_ini(IniReaderBase):
    @pytest.fixture(scope='session')
    def test_ini(self, tmp_path_factory):
        test_ini = tmp_path_factory.mktemp('acfi') / 'test.ini'
        test_ini.write_text(inspect.cleandoc(u'''
        [ind1.attributes]
        foo = bar

        [ind2.attributes.this-is-bad]
        foo = bar
        '''))
        return test_ini

    def test(self, inifile):
        assert _attribute_config_from_ini(inifile, 'ind1') == {
            'foo': 'bar',
            }

    def test_raises_error(self, inifile):
        with pytest.raises(RuntimeError,
                           match=r'should not contain periods'):
            _attribute_config_from_ini(inifile, 'ind2')


class Test_pagination_from_ini(IniReaderBase):
    @pytest.fixture(scope='session')
    def test_ini(self, tmp_path_factory):
        test_ini = tmp_path_factory.mktemp('pfi') / 'test.ini'
        test_ini.write_text(inspect.cleandoc(u'''
        [pagination]
        per_page = 10

        [myindex.pagination]
        enabled = yes

        [myindex.subindex.pagination]
        per_page = 5
        url_suffix = pg
        '''))
        return test_ini

    @pytest.fixture
    def pagination_config(self, lektor_env, inifile, index_name):
        return _pagination_config_from_ini(lektor_env, inifile, index_name)

    @pytest.mark.parametrize('index_name, expected', [
        ('',
         {'enabled': False, 'per_page': 10, 'url_suffix': 'page'}),
        ('otherindex',
         {'enabled': False, 'per_page': 10, 'url_suffix': 'page'}),
        ('myindex',
         {'enabled': True, 'per_page': 10, 'url_suffix': 'page'}),
        ('myindex.subindex',
         {'enabled': True, 'per_page': 5, 'url_suffix': 'pg'}),
        ('myindex.other',
         {'enabled': True, 'per_page': 10, 'url_suffix': 'page'}),
        ])
    def test_subindex(self, pagination_config, expected,
                      index_name, inifile):
        for key, value in expected.items():
            assert getattr(pagination_config, key) == value
