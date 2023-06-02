""" Virtual source objects for the indexes.

"""
from __future__ import annotations

import hashlib
import pickle
import sys
from collections.abc import Hashable
from itertools import chain
from operator import itemgetter
from typing import Any
from typing import Callable
from typing import Iterable
from typing import Sequence
from typing import TYPE_CHECKING
from typing import TypeVar

import jinja2
from lektor.db import _CmpHelper
from lektor.environment import PRIMARY_ALT
from lektor.pluginsystem import get_plugin
from lektor.sourceobj import VirtualSourceObject
from lektor.utils import build_url
from lektorlib.context import disable_dependency_recording
from lektorlib.query import PrecomputedQuery
from lektorlib.recordcache import get_or_create_virtual
from more_itertools import unique_everseen
from werkzeug.utils import cached_property

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal

if TYPE_CHECKING:
    from lektor.builder import PathCache
    from lektor.db import Record
    from lektor.pagination import Pagination
    from .indexmodel import IndexModel
    from .indexmodel import IndexRootModel
    from .plugin import Cache
    from .plugin import IndexPagesPlugin


_T = TypeVar("_T")


def get_system_data(model: IndexModel, id_: str) -> dict[str, Any]:
    jinja_env = model.env.jinja_env

    # NB: For any data descriptors in here,
    # IndexSource.__getitem__ will call its __get__
    return {
        "_id": id_,
        "key": id_,
        "_slug": IndexSource._slug,
        "_path": IndexSource.path,
        "_gid": IndexSource._gid,
        "_template": getattr(model, "template", None),
        "_hidden": IndexSource.is_hidden,
        "_discoverable": IndexSource.is_discoverable,  # always true
        "_alt": IndexSource.alt,
        # There is no source for these — they are virtual
        # So reasonable values seem to be either PRIMARY_ALT or Undefined
        "_source_alt": PRIMARY_ALT,
        "_model": jinja_env.undefined(
            "Missing value in field '_model': index is virtual"
        ),
        "_attachment_for": jinja_env.undefined(
            "Missing value in field '_attachment_for': not an attachment"
        ),
        "_attachment_type": jinja_env.undefined(
            "Missing value in field '_attachment_type': not an attachment"
        ),
    }


class IndexBase(VirtualSourceObject):  # type: ignore[misc]
    def __init__(
        self,
        model: IndexRootModel | IndexModel,
        parent: Record | IndexBase,
        id_: str,
        children: PrecomputedQuery[Record],
        page_num: int | None = None,
    ):
        VirtualSourceObject.__init__(self, parent.record)
        self._model = model
        self._id = id_
        self.children = children
        self.datamodel = model.datamodel
        self.page_num = page_num
        self.virtual_path = model.get_virtual_path(parent, id_, page_num)

    @property
    def has_subindex(self) -> bool:
        """True iff this index has a sub-index configured."""
        return self._model.subindex_model is not None

    @cached_property
    def subindexes(self) -> PrecomputedQuery[IndexSource]:
        """A Query containing the indexes.

        E.g. at the top level of a date index, this Query might
        iterate over the indexes for each year.

        """
        if not self.has_subindex:
            raise AttributeError("no sub-index is configured")
        # path without page number
        path = self.__for_page__(None).path
        return PrecomputedQuery(path, self.pad, self._subindex_ids, alt=self.alt)

    @cached_property
    def _subindex_ids(self) -> tuple[str, ...]:
        if self._model.subindex_model is None:
            raise AttributeError("no sub-index is configured")
        subindex_model = self._model.subindex_model

        def get_subindex_ids() -> tuple[str, ...]:
            with disable_dependency_recording():
                return tuple(
                    unique_everseen(
                        chain.from_iterable(
                            map(subindex_model.keys_for_post, self.children)
                        )
                    )
                )

        cache_key = "subindex_ids", self.path
        return self._get_cache().get_or_create(cache_key, get_subindex_ids)

    def _get_cache(self) -> Cache | DummyCache:
        try:
            plugin: IndexPagesPlugin = get_plugin("index-pages", self.pad.env)
        except LookupError:
            return DummyCache()  # testing
        else:
            return plugin.cache

    @cached_property
    def path(self) -> str:
        return f"{self.record.path}@{self.virtual_path}"

    def resolve_virtual_path(
        self, pieces: Sequence[str]
    ) -> IndexRoot | IndexSource | None:
        if not pieces:
            return self

        if self.has_subindex:
            if pieces[0] in self._subindex_ids:
                subindex = self._get_subindex(pieces[0])
                return subindex.resolve_virtual_path(pieces[1:])

        return self._model.match_path_pagination(self, pieces)

    def resolve_url_path(self, url_path: Sequence[str]) -> IndexSource | None:
        pagination_config = self.datamodel.pagination_config

        if not url_path:
            # resolve to first page rather than unpaginated version
            page_num = 1 if pagination_config.enabled else None
            return self.__for_page__(page_num)

        if self.has_subindex:
            subindex: IndexSource
            for subindex in self.subindexes:
                slug = subindex._slug.split("/")
                if url_path[: len(slug)] == slug:
                    return subindex.resolve_url_path(url_path[len(slug) :])

        if pagination_config.enabled:
            return pagination_config.match_pagination(  # type: ignore[no-any-return]
                self, url_path
            )

        return None

    def __for_page__(self, page_num: int | None) -> IndexRoot | IndexSource:
        raise NotImplementedError()

    def _get_subindex(self, id_: str, page_num: int | None = None) -> IndexSource:
        if self._model.subindex_model is None:
            raise LookupError("no sub-index is configured")
        subindex_model = self._model.subindex_model

        def get_child_ids() -> list[str]:
            keys_for_post = subindex_model.keys_for_post

            def match_key(post: Record) -> bool:
                return id_ in keys_for_post(post)

            children = self.children.filter(match_key)
            # We could just give the subindex the raw query, but if we do,
            # it generates unnecessary dependencies when iterated over in
            # a template.
            #
            # To avoid this, we precompute the list of matching ids (while
            # ignoring any dependencies), and return a custom Query class
            # which will iterate over only those matching children.
            with disable_dependency_recording():
                return list(map(itemgetter("_id"), children))

        cache_key = "child_ids", self.path, id_
        child_ids = self._get_cache().get_or_create(cache_key, get_child_ids)
        children: PrecomputedQuery[Record] = PrecomputedQuery(
            self.children.path, self.pad, child_ids, alt=self.children.alt
        )
        return IndexSource.get_index(subindex_model, self, id_, children, page_num)

    @cached_property
    def _gid(self) -> str:
        return hashlib.md5(self.path.encode("utf-8")).hexdigest()

    def get_checksum(self, path_cache: PathCache) -> str:
        return self._compute_checksum(self._get_checksum_data(path_cache))

    def _get_checksum_data(
        self, path_cache: PathCache
    ) -> tuple[tuple[str, ...] | str, ...]:
        # Checksum for this virtual source It should change if the
        # composition --- that is the sequence of subindexes or the
        # sequence of childeren (e.g. blog posts) --- changes.

        child_paths: tuple[str, ...] | str
        with disable_dependency_recording():
            if not self.datamodel.pagination_config.enabled:
                # Normal index page.
                # We change if the sequence of child identities changes
                child_paths = tuple(child.path for child in self.children)
            elif self.page_num is not None:
                # Pagination is in effect, we change if the sequence of
                # child identities on this page changes
                child_paths = tuple(child.path for child in self.pagination.items)
            else:
                # Pagination is in effect, but we're the unpaginated page.
                # We change if the number of pages changes
                child_paths = f"NPAGES={self.pagination.pages}"

        if self.has_subindex:
            # If we have subindexes the composition of the index
            # also depends on the sequence of subindexes
            return self.path, child_paths, self._subindex_ids
        return self.path, child_paths

    @staticmethod
    def _compute_checksum(data: tuple[tuple[str, ...] | str, ...]) -> str:
        return hashlib.sha1(pickle.dumps(data, protocol=0)).hexdigest()

    # is_discoverable = True (inherited from SourceObject)
    # alt = self.record.alt (inherited from VirtualSourceObject)

    # FIXME: to implement?
    # Page
    # has_prev
    # has_next
    # get_siblings

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, IndexBase):
            return NotImplemented
        return other.path == self.path and other.__class__ == self.__class__

    def __hash__(self) -> int:
        return hash(self.path)

    def __repr__(self) -> str:
        # path without page_num
        bits = [f"path={self.__for_page__(None).path!r}"]
        if self.alt is not PRIMARY_ALT:
            bits.append(f"alt={self.alt!r}")
        if self.page_num is not None:
            bits.append(f"page_num={self.page_num}")
        return f"<{self.__class__.__name__} {' '.join(bits)}>"


class IndexRoot(IndexBase):
    """Root source node for an index tree."""

    def __init__(self, model: IndexRootModel, record: Record):
        IndexBase.__init__(
            self, model, record, id_=model.index_name, children=model.get_items(record)
        )

    @classmethod
    def get_index(class_, model: IndexRootModel, record: Record) -> IndexRoot:
        def creator() -> IndexRoot:
            assert record.record == record
            return class_(model, record)

        virtual_path = model.get_virtual_path(record)
        return get_or_create_virtual(record, virtual_path, creator)

    @property
    def _slug(self) -> None:
        return None

    @property
    def url_path(self) -> str:
        return self.record.url_path  # type: ignore[no-any-return]

    def __for_page__(self, page_num: int | None) -> IndexRoot:
        """Get source object for a (possibly) different page number."""
        assert page_num is None
        return self

    @property
    def is_hidden(self) -> Literal[True]:
        # top level of the index trees does not actually produce an artifact
        return True


class IndexSource(IndexBase):
    """Index source node."""

    # override property in parent
    parent: IndexRoot | IndexSource = None  # type: ignore[assignment]

    _model: IndexModel

    def __init__(
        self,
        model: IndexModel,
        parent: IndexRoot | IndexSource,
        id_: str,
        children: PrecomputedQuery[Record],
        page_num: int | None = None,
    ):
        IndexBase.__init__(self, model, parent, id_, children, page_num)
        self.parent = parent
        self._data = get_system_data(model, id_)
        self._data.update(model.data_descriptors)

    @classmethod
    def get_index(
        class_,
        model: IndexModel,
        parent: IndexRoot | IndexSource,
        id_: str,
        children: PrecomputedQuery[Record],
        page_num: int | None = None,
    ) -> IndexSource:
        def creator() -> IndexSource:
            return class_(model, parent, id_, children, page_num)

        virtual_path = model.get_virtual_path(parent, id_, page_num)
        return get_or_create_virtual(parent.record, virtual_path, creator)

    def __contains__(self, name: str) -> bool:
        return name in self._data and not jinja2.is_undefined(self[name])

    def __getitem__(self, name: str) -> Any:
        rv = self._data[name]
        if hasattr(rv, "__get__"):
            rv = rv.__get__(self)
            self._data[name] = rv
        return rv

    @cached_property
    def pagination(self) -> Pagination:
        pagination_config = self.datamodel.pagination_config

        # XXX: get_pagination_controller raises RuntimeError if
        # pagination is not enabled.  Perhaps AttributeError would be
        # better or maybe an Undefined?  However this is what
        # lektor.db.Page.pagination does, so we’ll stick with it for
        # now.

        # The pagination controller’s constructor iterates over all
        # items just to count them.  This, normally, would register
        # all of self.children (not just self.pagination.items) as
        # dependencies.  We disable dependency recording here to
        # prevent that.
        #
        # As our checksum is constructed so that it will change if the
        # sequence of items on our page changes, we should be safe.
        #
        # Also note, that it’s likely our index page template will
        # iterate over self.pagination.items, thus registering all
        # the items on the page as dependencies.  (And if it doesn’t,
        # then they shouldn't needn’t be dependencies.)
        with disable_dependency_recording():
            return pagination_config.get_pagination_controller(self)

    @cached_property
    def _slug(self) -> str:
        return self._model.get_slug(self)

    @property
    def url_path(self) -> str:
        datamodel = self.datamodel
        slug = self._slug
        path = [self.parent.url_path, slug]
        if self.page_num is not None and self.page_num != 1:
            assert datamodel.pagination_config.enabled
            path.append(datamodel.pagination_config.url_suffix)
            path.append(f"{self.page_num:d}")
        _, _, slug_tail = slug.rstrip("/").rpartition("/")
        return build_url(  # type: ignore[no-any-return]
            path, trailing_slash=("." not in slug_tail)
        )

    def __for_page__(self, page_num: int | None) -> IndexSource:
        """Get source object for a (possibly) different page number."""
        if page_num == self.page_num:
            return self
        return self.get_index(
            self._model, self.parent, self._id, self.children, page_num
        )

    @property
    def is_hidden(self) -> bool:
        return self.record.is_hidden  # type: ignore[no-any-return]

    def get_sort_key(self, fields: Iterable[str]) -> list[_CmpHelper]:
        def cmp_val(field: str) -> _CmpHelper:
            reverse = field.startswith("-")
            if reverse or field.startswith("+"):
                field = field[1:]
            value = self[field] if field in self else None
            return _CmpHelper(value, reverse)

        return [cmp_val(field) for field in fields]


class DummyCache:
    def get_or_create(self, key: Hashable, creator: Callable[[], _T]) -> _T:
        return creator()
