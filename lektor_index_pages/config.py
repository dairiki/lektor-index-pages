"""Configuration and config-related logic."""

from __future__ import annotations

from itertools import chain
from typing import Generator
from typing import Sequence
from typing import TYPE_CHECKING

from lektor.environment import PRIMARY_ALT
from lektorlib.recordcache import get_or_create_virtual

from .indexmodel import index_models_from_ini
from .indexmodel import VIRTUAL_PATH_PREFIX
from .sourceobj import IndexRoot

if TYPE_CHECKING:
    from inifile import IniFile
    from lektor.db import Pad
    from lektor.db import Record
    from lektor.environment import Environment

    from .indexmodel import IndexRootModel
    from .sourceobj import IndexSource


class NoSuchIndex(KeyError):
    pass


class Config:
    def __init__(self, index_models: dict[str, IndexRootModel]):
        self.index_models = index_models

    def get_index_root(
        self, index_name: str, pad: Pad, alt: str = PRIMARY_ALT
    ) -> IndexRoot:
        index_model = self.index_models.get(index_name)
        if index_model is None:
            raise NoSuchIndex(f"no index named {index_name!r} is configured")
        record = pad.get(index_model.parent_path, alt=alt)
        if record is None:
            raise NoSuchIndex(
                "no parent record exists at "
                f"{index_model.parent_path!r} for index {index_name!r}"
            )
        return IndexRoot.get_index(index_model, record)

    def iter_index_roots(self, record: Record) -> Generator[IndexRoot]:
        record_path = record.path
        for index_model in self.index_models.values():
            if index_model.parent_path == record_path:
                yield IndexRoot.get_index(index_model, record)

    def resolve_virtual_path(
        self, record: Record, pieces: Sequence[str]
    ) -> IndexRoot | IndexSource | None:
        # Lektor's Pad.get or Pad.get_virtual does not cache virtual
        # sources, so we need to cache them ourself or things get
        # dreadfully slow.
        #
        # Interestingly, Lektor's RecordCache is perfectly capable of caching
        # virtual source objects, so we will use it...
        def creator() -> IndexRoot | IndexSource | None:
            return self._resolve_virtual_path(record, pieces)

        virtual_path = "/".join(chain([VIRTUAL_PATH_PREFIX], pieces))
        return get_or_create_virtual(record, virtual_path, creator)

    def _resolve_virtual_path(
        self, record: Record, pieces: Sequence[str]
    ) -> IndexRoot | IndexSource | None:
        index_model = self.index_models.get(pieces[0])
        if index_model and index_model.parent_path == record.path:
            index_root = IndexRoot.get_index(index_model, record)
            return index_root.resolve_virtual_path(pieces[1:])
        return None

    def resolve_url_path(
        self, record: Record, url_path: Sequence[str]
    ) -> IndexSource | None:
        for index_root in self.iter_index_roots(record):
            source = index_root.resolve_url_path(url_path)
            if source is not None:
                return source
        return None

    @classmethod
    def from_ini(cls, env: Environment, inifile: IniFile) -> Config:
        index_models = {}
        for root_model in index_models_from_ini(env, inifile):
            index_name = root_model.index_name
            index_models[index_name] = root_model
        return cls(dict(index_models))
