# -*- coding: utf-8 -*-
""" Configurable logic that controls how indexes work

"""
from more_itertools import always_iterable

from jinja2 import TemplateSyntaxError
import lektor.datamodel
from lektor.environment import Expression
from lektor.utils import slugify


VIRTUAL_PATH_PREFIX = 'index-pages'


class IndexDataModel(object):

    def __init__(self, id, config_filename, pagination_config):
        self.id = id
        self.filename = config_filename
        self.pagination_config = pagination_config

    parent = None

    has_own_children = True
    child_config = lektor.datamodel.ChildConfig()

    has_own_attachments = False
    attachment_config = lektor.datamodel.AttachmentConfig()

    has_own_children = False


class PaginationConfig(lektor.datamodel.PaginationConfig):
    # ``lektor.datamodel.PaginationConfig.get_record_for_page`` does not
    # work for virtual sources.
    def get_record_for_page(self, source, page_num):
        for_page = getattr(source, '__for_page__', None)
        if callable(for_page):
            return for_page(page_num)
        return super(PaginationConfig, self).get_record_for_page(
            source, page_num)


class IndexModelBase(object):

    def __init__(self, env,
                 pagination_config=None,
                 subindex_model=None,
                 config_filename=None):

        datamodel_id = '@{}'.format(self.__class__.__name__)
        if pagination_config is None:
            pagination_config = PaginationConfig(env, enabled=False)
        datamodel = IndexDataModel(datamodel_id,
                                   config_filename, pagination_config)

        self.env = env
        self.datamodel = datamodel
        self.subindex_model = subindex_model


class IndexRootModel(IndexModelBase):

    data_descriptors = ()

    def __init__(self, env,
                 index_name,
                 index_model,
                 parent_path=None,
                 items=None,
                 config_filename=None):
        super(IndexRootModel, self).__init__(
            env,
            subindex_model=index_model,
            config_filename=config_filename)

        if parent_path is None:
            parent_path = '/'

        expr = ExpressionCompiler(
            env, section=index_name, filename=config_filename)

        self.index_name = index_name
        self.parent_path = parent_path
        self.items_expr = expr('items', items) if items else None

    def get_virtual_path(self, parent, id_=None, page_num=None):
        assert page_num is None
        assert id_ is None or id_ == self.index_name
        return "{}/{}".format(VIRTUAL_PATH_PREFIX, self.index_name)

    def match_path_pagination(self, source, url_path):
        return None

    def get_items(self, record):
        items_expr = self.items_expr
        if items_expr is None:
            return record.children
        return items_expr.__get__(record)


class IndexModel(IndexModelBase):
    def __init__(self, env,
                 keys,
                 template=None,
                 slug_format=None,
                 fields=None,
                 pagination_config=None,
                 subindex_model=None,
                 index_name=None,
                 config_filename=None):
        super(IndexModel, self).__init__(
            env,
            pagination_config=pagination_config,
            subindex_model=subindex_model,
            config_filename=config_filename)

        if template is None:
            template = 'index-pages.html'
        expr = ExpressionCompiler(
            env, section=index_name, filename=config_filename)
        self.template = template
        self.keys_expr = expr('keys', keys)
        self.slug_expr = expr('slog', slug_format) if slug_format else None

        fields_section = "%s.fields" % index_name if index_name else None
        field = ExpressionCompiler(
            env, section=fields_section, filename=config_filename)
        self.data_descriptors = [
            (name, field(name, expr))
            for name, expr in dict(fields or ()).items()]

    def get_virtual_path(self, parent, id_, page_num=None):
        assert id_ is not None
        assert parent.page_num is None
        pieces = [parent.virtual_path, id_]
        if page_num is not None:
            pieces.append('page/{:d}'.format(page_num))
        return '/'.join(pieces)

    def match_path_pagination(self, source, pieces):
        pagination_config = self.datamodel.pagination_config
        if pagination_config.enabled \
           and len(pieces) == 2 \
           and pieces[0] == 'page' \
           and pieces[1].isdigit():
            page_num = int(pieces[1])
            pages = pagination_config.count_pages(source)
            # must have children
            if page_num > 0 and page_num <= pages:
                return pagination_config.get_record_for_page(source, page_num)

    def keys_for_post(self, record):
        keys = self.keys_expr.__get__(record)
        return filter(bool, map(_idify, always_iterable(keys)))

    def get_slug(self, source):
        slug_expr = self.slug_expr
        if slug_expr is None:
            slug = source._id
        else:
            slug = str(slug_expr.__get__(source))
        return slugify(slug)


class ExpressionCompiler(object):
    # This is here to provide useful error messages in case
    # there is a jinja syntax error within one of the evaluated
    # fields in the config file.

    def __init__(self, env, filename=None, section=None):
        self.env = env
        self.filename = filename
        self.section = section

    @property
    def location(self):
        bits = []
        if self.section:
            bits.append(" in section [{.section}]".format(self))
        if self.filename:
            bits.append("\n    in file {.filename}".format(self))
        return ''.join(bits)

    def __call__(self, name, expr):
        try:
            return FieldDescriptor(self.env, expr)
        except TemplateSyntaxError as exc:
            raise RuntimeError(
                "Jinja expression syntax error in config file: {exc}\n"
                "    in expression {expr!r}\n"
                "    for name {name!r}{location}".format(
                    location=self.location, name=name, expr=expr, exc=exc))


class FieldDescriptor(object):
    def __init__(self, env, expr):
        self.expr = expr
        self.evaluate = Expression(env, expr).evaluate

    def __get__(self, source):
        return self.evaluate(source.pad, this=source, alt=source.alt)


def _idify(value):
    """Coerce value to valid path component."""
    # Must be strings.  Can not contain '@'
    return str(value).replace('@', '_')


def index_models_from_ini(env, inifile):
    def is_index(section_name):
        if '.' in section_name:
            return False
        return (section_name + '.keys') in inifile

    for index_name in filter(is_index, inifile.sections()):
        parent_path = inifile.get(index_name + '.parent_path')
        items = inifile.get(index_name + '.items')
        index_model = _index_model_from_ini(env, inifile, index_name)

        model = IndexRootModel(
            env,
            index_name=index_name,
            parent_path=parent_path,
            items=items,
            index_model=index_model,
            config_filename=inifile.filename)
        yield model


def _index_model_from_ini(env, inifile, index_name,
                          is_subindex=False):
    prefix = index_name + '.'

    if is_subindex:
        # XXX: warn if ``parent_path`` or ``items`` is set?
        # (We ignore them on subindexes.)
        pass

    keys = inifile.get(prefix + 'keys')
    slug_format = inifile.get(prefix + 'slug_format')
    template = inifile.get(prefix + 'template')
    if not keys:
        raise RuntimeError("keys required")

    fields = _field_config_from_ini(inifile, index_name)
    pagination_config = _pagination_config_from_ini(
        env, inifile, index_name)

    subindex = inifile.get(prefix + 'subindex')
    if not subindex:
        subindex_model = None
    else:
        subindex_name = prefix + subindex
        subindex_model = _index_model_from_ini(
            env, inifile, subindex_name, is_subindex=True)

    return IndexModel(
        env,
        keys=keys,
        template=template,
        slug_format=slug_format,
        fields=fields,
        pagination_config=pagination_config,
        subindex_model=subindex_model,
        index_name=index_name,
        config_filename=inifile.filename)


def _field_config_from_ini(inifile, index_name):
    section_name = index_name + '.fields'
    fields = inifile.section_as_dict(section_name)

    def has_dot(s):
        return '.' in s
    if any(map(has_dot, fields.keys())):
        raise RuntimeError(
            "{}: section [{}]: field names should not contain periods"
            .format(inifile.filename, section_name))
    return fields


def _pagination_config_from_ini(env, inifile, index_name):
    # Inherit pagination configuration from "parent" sections.
    # E.g. for some-index.subindex, we merge in settings from:
    #
    # [pagination]
    # [some-index.pagination]
    # [some-index.subindex.pagination]
    #
    # NB: any ``items`` in config is ignored
    #
    config = {}
    pieces = index_name.split('.')
    params = (('enabled', inifile.get_bool),
              ('per_page', inifile.get_int),
              ('url_suffix', inifile.get))

    for n in range(len(pieces) + 1):
        prefix = '.'.join(pieces[:n] + ['pagination.'])
        for name, getter in params:
            key = prefix + name
            if n == 0 or key in inifile:
                config[name] = getter(key)

    return PaginationConfig(env, **config)
