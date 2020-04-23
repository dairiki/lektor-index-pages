# -*- coding: utf-8 -*-

from lektor.builder import Builder
from lektor.db import Database
from lektor.environment import Environment
from lektor.project import Project
from lektor.reporter import CliReporter
import pytest


@pytest.fixture(scope="module")
def demo_output(site_path, my_plugin_id, my_plugin_cls, tmp_path_factory):
    """ Build the demo site.

    Return path to output directory.

    """
    project = Project.from_path(str(site_path))
    env = Environment(project, load_plugins=False)

    # Load our plugin
    env.plugin_controller.instanciate_plugin(my_plugin_id, my_plugin_cls)
    env.plugin_controller.emit('setup-env')

    pad = Database(env).new_pad()
    output_path = tmp_path_factory.mktemp('demo-site')
    builder = Builder(pad, str(output_path))
    with CliReporter(env):
        failures = builder.build_all()
        assert failures == 0
    return output_path


def test_year_index(demo_output):
    year_index_html = demo_output / 'blog/2020/index.html'
    assert "Blog - 2020" in year_index_html.read_text()


@pytest.mark.parametrize("id, expect_text", [
    ('1999/03', None),
    ('2020/03', "March 2020"),
    ('2020/04', "April 2020"),
    ])
def test_month_index(demo_output, id, expect_text):
    month_index_html = demo_output / 'blog' / id / 'index.html'
    if expect_text:
        assert expect_text in month_index_html.read_text()
    else:
        assert not month_index_html.exists()
