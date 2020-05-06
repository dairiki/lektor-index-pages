# -*- coding: utf-8 -*-

try:
    from pathlib import Path
except ImportError:             # pragma: no cover
    from pathlib2 import Path

import pkg_resources
import pytest

from inifile import IniFile
import lektor.builder
import lektor.context
import lektor.datamodel
import lektor.db
import lektor.environment
import lektor.pagination
import lektor.project


@pytest.fixture(scope="session")
def my_plugin_id():
    dist = pkg_resources.get_distribution('lektor_index_pages')
    prefix = 'lektor-'
    assert dist.project_name.lower().startswith(prefix)
    return dist.project_name[len(prefix):]


@pytest.fixture(scope="session")
def my_plugin_cls(my_plugin_id):
    dist = pkg_resources.get_distribution('lektor_index_pages')
    return dist.load_entry_point('lektor.plugins', my_plugin_id)


@pytest.fixture(scope="session")
def site_path():
    return Path(__file__).parent / 'demo-site'


@pytest.fixture
def lektor_project(site_path):
    return lektor.project.Project.from_path(str(site_path))


@pytest.fixture
def lektor_env(lektor_project):
    return lektor_project.make_env(load_plugins=False)


@pytest.fixture
def lektor_pad(lektor_env):
    return lektor.db.Database(lektor_env).new_pad()


@pytest.fixture
def lektor_builder(lektor_pad, tmp_path):
    return lektor.builder.Builder(lektor_pad, str(tmp_path / "builder_output"))


@pytest.fixture
def lektor_build_state(lektor_builder):
    with lektor_builder.new_build_state() as build_state:
        yield build_state


@pytest.fixture
def lektor_context(lektor_pad):
    with lektor.context.Context(pad=lektor_pad) as ctx:
        yield ctx


@pytest.fixture
def lektor_alt():
    return lektor.environment.PRIMARY_ALT


@pytest.fixture
def blog_record(lektor_pad, lektor_alt):
    return lektor_pad.get('/blog', alt=lektor_alt)


@pytest.fixture
def month_index_enabled():
    return False


@pytest.fixture
def pagination_enabled():
    # Set to a positive integer to also set pagination.per_page
    return False


@pytest.fixture(scope='session')
def junk_ini(tmp_path_factory):
    return tmp_path_factory.mktemp('junk') / 'junk.ini'


@pytest.fixture
def inifile(site_path, junk_ini, my_plugin_id,
            pagination_enabled, month_index_enabled):
    # Make a temporary copy of our .ini file
    config_name = '%s.ini' % my_plugin_id
    orig_ini = site_path / 'configs' / config_name
    inifile = IniFile(str(orig_ini))
    inifile.filename = str(junk_ini)

    def yesno(val):
        return 'yes' if val else 'no'

    inifile['pagination.enabled'] = yesno(pagination_enabled)
    if not month_index_enabled:
        del inifile['year-index.subindex']

    if not isinstance(pagination_enabled, bool):
        inifile['pagination.per_page'] = pagination_enabled
    return inifile


@pytest.fixture
def plugin(lektor_env, my_plugin_id, my_plugin_cls, inifile):
    # install our plugin
    plugin_controller = lektor_env.plugin_controller
    plugin_controller.instanciate_plugin(my_plugin_id, my_plugin_cls)

    # patch in our test inifile
    plugin = lektor_env.plugins[my_plugin_id]
    plugin._inifile = inifile

    plugin_controller.emit('setup-env')
    return plugin


@pytest.fixture
def config(plugin):
    return plugin.read_config()
