"""Index pages for Lektor

FIXME: figure out how to get stale index files to prune correctly

"""
from __future__ import annotations

from collections.abc import Hashable
from threading import Lock
from typing import Any
from typing import Callable
from typing import Generator
from typing import Iterator
from typing import Sequence
from typing import TYPE_CHECKING
from typing import TypeVar

import jinja2
from lektor.environment import PRIMARY_ALT
from lektor.pluginsystem import Plugin

from .buildprog import IndexBuildProgram
from .config import Config
from .config import NoSuchIndex
from .indexmodel import VIRTUAL_PATH_PREFIX
from .sourceobj import IndexBase

if TYPE_CHECKING:
    from inifile import IniFile
    from lektor.builder import Builder
    from lektor.db import Pad
    from lektor.db import Record
    from lektor.environment import Environment
    from lektorlib.query import PrecomputedQuery

    from .sourceobj import IndexRoot
    from .sourceobj import IndexSource


_T = TypeVar("_T")


class Cache:
    """Cache expensive computations by the indexes.

    This cache is used to store expensive computations made by the index source
    objects (see lektor_index_pages.sourceobj.IndexBase).

    Already, our index source objects are cached in Lektor's pad.
    That, by itself, takes care of most of our caching needs during
    regular builds.

    The devserver HTTP server, however, tries to resolve nearly every
    URL requested through each plugin that registers a URL resolver.
    For each web request it does this using a fresh pad — so much for
    our caching on the pad.

    So this is a separate cache, whose main purpose is to keep the devserver
    from being too slow responding to http requests.

    """

    def __init__(self) -> None:
        self.lock = Lock()
        self.data: dict[Hashable, Any] = {}

    def get_or_create(self, key: Hashable, creator: Callable[[], _T]) -> _T:
        with self.lock:
            if key in self.data:
                return self.data[key]  # type: ignore[no-any-return]
        value = creator()
        with self.lock:
            self.data[key] = value
        return value

    def clear(self) -> None:
        with self.lock:
            self.data.clear()


class IndexPagesPlugin(Plugin):  # type: ignore[misc]
    name = "Index Pages"
    description = "Lektor plugin to index pages."

    _inifile: IniFile | None = None  # for testing

    def __init__(self, env: Environment, id: str):
        super().__init__(env, id)
        self.cache = Cache()

    def read_config(self) -> Config:
        def parse_config() -> Config:
            inifile = self._inifile or self.get_config()
            return Config.from_ini(self.env, inifile)

        return self.cache.get_or_create("config", parse_config)

    def on_before_build_all(self, builder: Builder, **extra: Any) -> None:
        self.cache.clear()

    def on_setup_env(
        self, extra_flags: dict[str, str] | None = None, **extra: Any
    ) -> None:
        env = self.env

        skip_build = False
        if extra_flags:
            flags = extra_flags.get("index-pages", "").split(",")
            skip_build = "skip-build" in flags

        env.add_build_program(IndexBase, IndexBuildProgram)

        if not skip_build:

            @env.generator  # type: ignore[misc]
            def generate_index(record: Record) -> Generator[IndexRoot, None, None]:
                config = self.read_config()
                return config.iter_index_roots(record)

        @env.virtualpathresolver(VIRTUAL_PATH_PREFIX)  # type: ignore[misc]
        def resolve_virtual_path(
            record: Record, pieces: Sequence[str]
        ) -> IndexRoot | IndexSource | None:
            config = self.read_config()
            return config.resolve_virtual_path(record, pieces)

        @env.urlresolver  # type: ignore[misc]
        def resolve_url(record: Record, url_path: Sequence[str]) -> IndexSource | None:
            config = self.read_config()
            return config.resolve_url_path(record, url_path)

        @jinja2.pass_context
        def index_pages(
            jinja_ctx: jinja2.runtime.Context, index_name: str, alt: str = PRIMARY_ALT
        ) -> IndexPages | jinja2.Undefined:
            pad: Pad | jinja2.Undefined = jinja_ctx.resolve("site")
            if jinja2.is_undefined(pad):
                return pad

            config = self.read_config()
            try:
                index_root = config.get_index_root(index_name, pad, alt)
            except NoSuchIndex as exc:
                return jinja_ctx.environment.undefined("index_pages: %s" % exc)
            return IndexPages(index_root)

        env.jinja_env.globals["index_pages"] = index_pages


class IndexPages:
    def __init__(self, index_root: IndexRoot):
        self.index_root = index_root

    @property
    def indexes(self) -> PrecomputedQuery[IndexSource]:
        return self.index_root.subindexes

    def __iter__(self) -> Iterator[IndexSource]:
        return iter(self.indexes)

    def __bool__(self) -> bool:
        return bool(self.indexes)

    @property
    def index_name(self) -> str:
        return self.index_root._id

    @property
    def alt(self) -> str:
        return self.index_root.alt  # type: ignore[no-any-return]

    def __repr__(self) -> str:
        args: tuple[str, ...]
        if self.alt == PRIMARY_ALT:
            args = (self.index_name,)
        else:
            args = self.index_name, self.alt
        return f"<index_pages{args!r}>"
