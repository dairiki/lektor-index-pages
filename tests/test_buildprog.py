# -*- coding: utf-8 -*-

import lektor.context
import pytest

from .conftest import Path

from lektor_index_pages.buildprog import IndexBuildProgram


@pytest.fixture
def index_root(config, lektor_pad):
    return config.get_index_root('year-index', lektor_pad)


class Test_build_index_root(object):
    @pytest.fixture
    def source(self, index_root):
        return index_root

    @pytest.fixture
    def prog(self, source, lektor_build_state):
        return IndexBuildProgram(source, lektor_build_state)

    def test_produce_artifacts(self, prog, source, mocker):
        declare_artifact = mocker.patch(
            'lektor.build_programs.BuildProgram.declare_artifact')
        prog.produce_artifacts()
        assert not declare_artifact.called

    def test_iter_child_sources_pages(self, prog, source):
        assert [src.path for src in prog.iter_child_sources()] \
            == ['/blog@index-pages/year-index/2020']


class TestIndexBuildProgram(object):
    @pytest.fixture
    def source(self, index_root):
        return index_root.resolve_virtual_path(['2020'])

    @pytest.fixture
    def prog(self, source, lektor_build_state):
        return IndexBuildProgram(source, lektor_build_state)

    def test_source_filename(self, source):
        # sanity check
        source_filename = Path(source.record.source_filename)
        assert source_filename.parts[-2:] == ('blog', 'contents.lr')

    def test_produce_artifacts(self, prog, source, mocker):
        source_filename = source.record.source_filename
        declare_artifact = mocker.patch(
            'lektor.build_programs.BuildProgram.declare_artifact')
        prog.produce_artifacts()
        assert declare_artifact.called_once_with(
            '/blog/2020/index.html', sources=[source_filename])

    def test_build_artifact(self, prog, source, mocker):
        template = "year-index.html"
        artifact = mocker.Mock(name='artifact', spec=('render_template_into',))

        prog.build_artifact(artifact)
        assert artifact.mock_calls == [
            mocker.call.render_template_into(template, this=source),
            ]

    def test_build_artifact_records_dependency(self, prog, source, inifile,
                                               mocker):
        artifact = mocker.Mock(name='artifact')
        with lektor.context.Context(artifact, pad=None) as ctx:
            prog.build_artifact(artifact)
        assert inifile.filename in ctx.referenced_dependencies

    @pytest.mark.parametrize('pagination_enabled', [True])
    def test_iter_child_sources_pages(self, prog, source):
        assert [src.path for src in prog.iter_child_sources()] \
            == ['/blog@index-pages/year-index/2020/page/1']

    @pytest.mark.parametrize(
        'pagination_enabled, month_index_enabled, expected', [
            (True, False, ['/blog@index-pages/year-index/2020/page/1']),
            (False, True, ['/blog@index-pages/year-index/2020/04',
                           '/blog@index-pages/year-index/2020/03']),
            ]
        )
    def test_iter_child_sources(self, prog, expected):
        assert [src.path for src in prog.iter_child_sources()] == expected
