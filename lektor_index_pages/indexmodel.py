""" Configurable logic that controls how indexes work

"""

from __future__ import annotations

from typing import Generator
from typing import Iterable
from typing import Sequence
from typing import TYPE_CHECKING
from typing import TypeVar

import lektor.datamodel
from jinja2 import TemplateSyntaxError
from lektor.environment import Expression
from lektor.utils import slugify
from more_itertools import always_iterable

if TYPE_CHECKING:
    from _typeshed import StrPath
    from inifile import IniFile
    from lektor.environment import Environment
    from lektor.db import Query
    from lektor.db import Record
    from lektor.sourceobj import SourceObject
    from .sourceobj import IndexBase
    from .sourceobj import IndexRoot
    from .sourceobj import IndexSource

VIRTUAL_PATH_PREFIX = "index-pages"


class IndexDataModel:
    def __init__(
        self, id: str, config_filename: StrPath, pagination_config: PaginationConfig
    ):
        self.id = id
        self.filename = config_filename
        self.pagination_config = pagination_config

    parent = None

    has_own_children = True
    child_config = lektor.datamodel.ChildConfig()

    has_own_attachments = False
    attachment_config = lektor.datamodel.AttachmentConfig()

    has_own_children = False


class PaginationConfig(lektor.datamodel.PaginationConfig):  # type: ignore[misc]
    # ``lektor.datamodel.PaginationConfig.get_record_for_page`` does not
    # work for virtual sources.

    _Paginatable = TypeVar("_Paginatable", "Record", "IndexBase")

    def get_record_for_page(self, source: _Paginatable, page_num: int) -> _Paginatable:
        for_page = getattr(source, "__for_page__", None)
        if callable(for_page):
            return for_page(page_num)  # type: ignore[no-any-return]
        return super().get_record_for_page(  # type: ignore[no-any-return]
            source, page_num
        )


class IndexModelBase:
    def __init__(
        self,
        env: Environment,
        *,
        pagination_config: PaginationConfig | None = None,
        subindex_model: IndexModel | None = None,
        config_filename: StrPath,
    ):
        datamodel_id = f"@{self.__class__.__name__}"
        if pagination_config is None:
            pagination_config = PaginationConfig(env, enabled=False)
        datamodel = IndexDataModel(datamodel_id, config_filename, pagination_config)

        self.env = env
        self.datamodel = datamodel
        self.subindex_model = subindex_model


class IndexRootModel(IndexModelBase):
    data_descriptors = ()

    def __init__(
        self,
        env: Environment,
        index_name: str,
        index_model: IndexModel,
        *,
        parent_path: str | None = None,
        items: str | None = None,
        config_filename: StrPath,
    ):
        super().__init__(
            env, subindex_model=index_model, config_filename=config_filename
        )

        if parent_path is None:
            parent_path = "/"

        expr = ExpressionCompiler(env, section=index_name, filename=config_filename)

        self.index_name = index_name
        self.parent_path = parent_path
        self.items_expr = expr("items", items) if items else None

    def get_virtual_path(
        self, parent: SourceObject, id_: str | None = None, page_num: int | None = None
    ) -> str:
        assert page_num is None
        assert id_ is None or id_ == self.index_name
        return f"{VIRTUAL_PATH_PREFIX}/{self.index_name}"

    def match_path_pagination(self, source: IndexRoot, url_path: Sequence[str]) -> None:
        return None

    def get_items(self, record: IndexBase) -> Query:
        items_expr = self.items_expr
        if items_expr is None:
            return record.children
        return items_expr.__get__(record)


class IndexModel(IndexModelBase):
    def __init__(
        self,
        env: Environment,
        key: str,
        *,
        template: str | None = None,
        slug_format: str | None = None,
        fields: dict[str, str],
        pagination_config: PaginationConfig,
        subindex_model: IndexModel | None = None,
        index_name: str,
        config_filename: StrPath,
    ):
        super().__init__(
            env,
            pagination_config=pagination_config,
            subindex_model=subindex_model,
            config_filename=config_filename,
        )

        if template is None:
            template = "index-pages.html"
        expr = ExpressionCompiler(env, section=index_name, filename=config_filename)
        self.template = template
        self.key_expr = expr("key", key)
        self.slug_expr = expr("slug_format", slug_format) if slug_format else None

        fields_section = "%s.fields" % index_name
        field = ExpressionCompiler(
            env, section=fields_section, filename=config_filename
        )
        self.data_descriptors = [
            (name, field(name, expr)) for name, expr in dict(fields or ()).items()
        ]

    def get_virtual_path(
        self, parent: IndexBase, id_: str, page_num: int | None = None
    ) -> str:
        assert id_ is not None
        assert parent.page_num is None
        pieces = [parent.virtual_path, id_]
        if page_num is not None:
            pieces.append(f"page/{page_num:d}")
        return "/".join(pieces)

    def match_path_pagination(
        self, source: IndexSource, pieces: Sequence[str]
    ) -> IndexSource | None:
        pagination_config = self.datamodel.pagination_config
        if (
            pagination_config.enabled
            and len(pieces) == 2
            and pieces[0] == "page"
            and pieces[1].isdigit()
        ):
            page_num = int(pieces[1])
            pages = pagination_config.count_pages(source)
            # must have children
            if page_num > 0 and page_num <= pages:
                return pagination_config.get_record_for_page(source, page_num)
        return None

    def keys_for_post(self, record: Record) -> Iterable[str]:
        keys = self.key_expr.evaluate(
            record.pad, values={"item": record}, alt=record.alt
        )
        return filter(bool, map(_idify, always_iterable(keys)))

    def get_slug(self, source: IndexSource) -> str:
        slug_expr = self.slug_expr
        if slug_expr is None:
            slug = source._id
        else:
            slug = str(slug_expr.__get__(source))
        return slugify(slug)  # type: ignore[no-any-return]


class ExpressionCompiler:
    # This is here to provide useful error messages in case
    # there is a jinja syntax error within one of the evaluated
    # fields in the config file.

    def __init__(self, env: Environment, filename: StrPath, section: str):
        self.env = env
        self.filename = filename
        self.section = section

    @property
    def location(self) -> str:
        bits = []
        if self.section:
            bits.append(f" in section [{self.section}]")
        if self.filename:
            bits.append(f"\n    in file {self.filename}")
        return "".join(bits)

    def __call__(self, name: str, expr: str) -> FieldDescriptor:
        try:
            return FieldDescriptor(self.env, expr)
        except TemplateSyntaxError as exc:
            raise RuntimeError(
                f"Jinja expression syntax error in config file: {exc}\n"
                f"    in expression {expr!r}\n"
                f"    for name {name!r}{self.location}"
            )


class FieldDescriptor:
    def __init__(self, env: Environment, expr: str):
        self.expr = expr
        self.evaluate = Expression(env, expr).evaluate

    def __get__(self, source: SourceObject) -> object:
        return self.evaluate(source.pad, this=source, alt=source.alt)


def _idify(value: object) -> str:
    """Coerce value to valid path component."""
    # Must be strings.  Can not contain '@'
    return str(value).replace("@", "_")


def index_models_from_ini(
    env: Environment, inifile: IniFile
) -> Generator[IndexRootModel]:
    def is_index(section_name: str) -> bool:
        if "." in section_name:
            return False
        return (section_name + ".key") in inifile

    for index_name in filter(is_index, inifile.sections()):
        parent_path = inifile.get(index_name + ".parent_path")
        items = inifile.get(index_name + ".items")
        index_model = _index_model_from_ini(env, inifile, index_name)

        model = IndexRootModel(
            env,
            index_name=index_name,
            parent_path=parent_path,
            items=items,
            index_model=index_model,
            config_filename=inifile.filename,
        )
        yield model


def _index_model_from_ini(
    env: Environment, inifile: IniFile, index_name: str, is_subindex: bool = False
) -> IndexModel:
    prefix = index_name + "."

    if is_subindex:
        # XXX: warn if ``parent_path`` or ``items`` is set?
        # (We ignore them on subindexes.)
        pass

    key = inifile.get(prefix + "key")
    slug_format = inifile.get(prefix + "slug_format")
    template = inifile.get(prefix + "template")
    if not key:
        raise RuntimeError("key required")

    fields = _field_config_from_ini(inifile, index_name)
    pagination_config = _pagination_config_from_ini(env, inifile, index_name)

    subindex = inifile.get(prefix + "subindex")
    if not subindex:
        subindex_model = None
    else:
        subindex_name = prefix + subindex
        subindex_model = _index_model_from_ini(
            env, inifile, subindex_name, is_subindex=True
        )

    return IndexModel(
        env,
        key=key,
        template=template,
        slug_format=slug_format,
        fields=fields,
        pagination_config=pagination_config,
        subindex_model=subindex_model,
        index_name=index_name,
        config_filename=inifile.filename,
    )


def _field_config_from_ini(inifile: IniFile, index_name: str) -> dict[str, str]:
    section_name = index_name + ".fields"
    fields: dict[str, str] = inifile.section_as_dict(section_name)

    def has_dot(s: str) -> bool:
        return "." in s

    if any(map(has_dot, fields.keys())):
        raise RuntimeError(
            f"{inifile.filename}: section [{section_name}]: "
            "field names should not contain periods"
        )
    return fields


def _pagination_config_from_ini(
    env: Environment, inifile: IniFile, index_name: str
) -> PaginationConfig:
    # Inherit pagination configuration from "parent" sections.
    # E.g. for some-index.subindex, we merge in settings from:
    #
    # [pagination]
    # [some-index.pagination]
    # [some-index.subindex.pagination]
    #
    # NB: any ``items`` in config is ignored
    #
    def find_key(name: str) -> str:
        pieces = index_name.split(".")
        while len(pieces) > 0:
            key = ".".join(pieces + ["pagination", name])
            if key in inifile:
                return key
            pieces.pop()
        return f"pagination.{name}"

    return PaginationConfig(
        env,
        enabled=inifile.get_bool(find_key("enabled")),
        per_page=inifile.get_int(find_key("per_page")),
        url_suffix=inifile.get(find_key("url_suffix")),
    )
