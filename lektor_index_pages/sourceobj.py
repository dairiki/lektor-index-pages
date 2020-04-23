# -*- coding: utf-8 -*-
""" Virtual source objects for the indexes.

"""
import hashlib
from itertools import chain
from operator import itemgetter
import pickle

from lektorlib.context import disable_dependency_recording
from lektorlib.query import PrecomputedQuery
from lektorlib.recordcache import get_or_create_virtual
from more_itertools import unique_everseen

import jinja2
from lektor.db import _CmpHelper
from lektor.environment import PRIMARY_ALT
from lektor.pluginsystem import get_plugin
from lektor.sourceobj import VirtualSourceObject
from lektor.utils import build_url
from werkzeug.utils import cached_property


def get_system_data(model, id_):
    jinja_env = model.env.jinja_env

    # NB: For any data descriptors in here,
    # IndexSource.__getitem__ will call its __get__
    return {
        '_id': id_,
        '_slug': IndexSource._slug,
        '_path': IndexSource.path,
        '_gid': IndexSource._gid,
        '_template': getattr(model, 'template', None),

        '_hidden': IndexSource.is_hidden,
        '_discoverable': IndexSource.is_discoverable,  # always true
        '_alt': IndexSource.alt,
        # There is no source for these — they are virtual
        # So reasonable values seem to be either PRIMARY_ALT or Undefined
        '_source_alt': PRIMARY_ALT,

        '_model': jinja_env.undefined(
            "Missing value in field '_model': index is virtual"),

        '_attachment_for': jinja_env.undefined(
            "Missing value in field '_attachment_for': not an attachment"),
        '_attachment_type': jinja_env.undefined(
            "Missing value in field '_attachment_type': not an attachment"),
        }


class IndexBase(VirtualSourceObject):

    def __init__(self, model, parent, id_, children, page_num=None):
        VirtualSourceObject.__init__(self, parent.record)
        self._model = model
        self._id = id_
        self.children = children
        self.datamodel = model.datamodel
        self.page_num = page_num
        self.virtual_path = model.get_virtual_path(parent, id_, page_num)

    @property
    def subindexes(self):
        """A Query containing the indexes.

        E.g. at the top level of a date index, this Query might
        iterate over the indexes for each year.

        """
        subindex_ids = self._subindex_ids
        # path without page number
        path = self.__for_page__(None).path
        return PrecomputedQuery(path, self.pad, subindex_ids, alt=self.alt)

    @cached_property
    def _subindex_ids(self):
        subindex_model = getattr(self._model, 'subindex_model', None)
        if subindex_model is None:
            raise AttributeError("sub-indexes are not enabled")

        def get_subindex_ids():
            with disable_dependency_recording():
                return tuple(unique_everseen(
                    chain.from_iterable(
                        map(subindex_model.keys_for_post, self.children))))

        cache_key = 'subindex_ids', self.path
        return self._get_cache().get_or_create(cache_key, get_subindex_ids)

    def _get_cache(self):
        try:
            plugin = get_plugin('index-pages', self.pad.env)
        except LookupError:
            return DummyCache()  # testing
        else:
            return plugin.cache

    @cached_property
    def path(self):
        return "{}@{}".format(self.record.path, self.virtual_path)

    def resolve_virtual_path(self, pieces):
        if not pieces:
            return self

        subindex_model = getattr(self._model, 'subindex_model', None)
        if subindex_model is not None:
            if pieces[0] in self._subindex_ids:
                subindex = self._get_subindex(pieces[0])
                return subindex.resolve_virtual_path(pieces[1:])

        return self._model.match_path_pagination(self, pieces)

    def resolve_url_path(self, url_path):
        pagination_config = self.datamodel.pagination_config

        if not url_path:
            # resolve to first page rather than unpaginated version
            page_num = 1 if pagination_config.enabled else None
            return self.__for_page__(page_num)

        subindex_model = getattr(self._model, 'subindex_model', None)
        if subindex_model is not None:
            for subindex in self.subindexes:
                slug = subindex._slug.split('/')
                if url_path[:len(slug)] == slug:
                    return subindex.resolve_url_path(url_path[len(slug):])

        if pagination_config.enabled:
            return pagination_config.match_pagination(self, url_path)

    def _get_subindex(self, id_, page_num=None):
        subindex_model = self._model.subindex_model

        def get_child_ids():
            keys_for_post = subindex_model.keys_for_post

            def match_key(post):
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
                return list(map(itemgetter('_id'), children))

        cache_key = 'child_ids', self.path, id_
        child_ids = self._get_cache().get_or_create(cache_key, get_child_ids)
        children = PrecomputedQuery(
            self.children.path, self.pad, child_ids, alt=self.children.alt)
        return IndexSource.get_index(
            subindex_model, self, id_, children, page_num)

    @cached_property
    def _gid(self):
        return hashlib.md5(self.path.encode('utf-8')).hexdigest()

    def get_checksum(self, path_cache):
        return self._compute_checksum(self._get_checksum_data(path_cache))

    def _get_checksum_data(self, path_cache):
        # Checksum for this virtual source It should change if the
        # composition --- that is the sequence of subindexes or the
        # sequence of childeren (e.g. blog posts) --- changes.

        with disable_dependency_recording():
            if not self.datamodel.pagination_config.enabled:
                # Normal index page.
                # We change if the sequence of child identities changes
                child_paths = [child.path for child in self.children]
            elif self.page_num is not None:
                # Pagination is in effect, we change if the sequence of
                # child identities on this page changes
                child_paths = [child.path for child in self.pagination.items]
            else:
                # Pagination is in effect, but we're the unpaginated page.
                # We change if the number of pages changes
                child_paths = "NPAGES={}".format(self.pagination.pages)

        subindex_ids = getattr(self, '_subindex_ids', None)
        if subindex_ids is not None:
            # If we have subindexes the composition of the index
            # also depends on the sequence of subindexes
            return self.path, child_paths, subindex_ids
        return self.path, child_paths

    @staticmethod
    def _compute_checksum(data):
        return hashlib.sha1(pickle.dumps(data, protocol=0)).hexdigest()

    # is_discoverable = True (inherited from SourceObject)
    # alt = self.record.alt (inherited from VirtualSourceObject)

    # FIXME: to implement?
    # Page
    # has_prev
    # has_next
    # get_siblings

    def __eq__(self, other):
        if self is other:
            return True
        return (self.__class__ == other.__class__
                and self.path == other.path)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.path)

    def __repr__(self):
        # path without page_num
        bits = ["path={path!r}"]
        if self.alt is not PRIMARY_ALT:
            bits.append("alt={alt!r}")
        if self.page_num is not None:
            bits.append("page_num={page_num}")
        desc = ' '.join(bits).format(
            path=self.__for_page__(None).path,  # path without page_num
            alt=self.alt,
            page_num=self.page_num)
        return "<%s %s>" % (self.__class__.__name__, desc)


class IndexRoot(IndexBase):
    """Root source node for an index tree.

    """
    def __init__(self, model, record):
        IndexBase.__init__(self, model, record,
                           id_=model.index_name,
                           children=model.get_items(record))

    @classmethod
    def get_index(class_, model, record):
        def creator():
            assert record.record == record
            return class_(model, record)
        virtual_path = model.get_virtual_path(record)
        return get_or_create_virtual(record, virtual_path, creator)

    @property
    def _slug(self):
        return None

    @property
    def url_path(self):
        return self.record.url_path

    def __for_page__(self, page_num):
        """Get source object for a (possibly) different page number.
        """
        assert page_num is None
        return self

    @property
    def is_hidden(self):
        # top level of the index trees does not actually produce an artifact
        return True


class IndexSource(IndexBase):
    """Index source node.

    """
    parent = None               # override property in parent

    def __init__(self, model, parent, id_, children, page_num=None):
        IndexBase.__init__(self, model, parent, id_, children, page_num)
        self.parent = parent
        self._data = get_system_data(model, id_)
        self._data.update(model.data_descriptors)

    @classmethod
    def get_index(class_, model, parent, id_, children, page_num=None):
        def creator():
            return class_(model, parent, id_, children, page_num)
        virtual_path = model.get_virtual_path(parent, id_, page_num)
        return get_or_create_virtual(parent.record, virtual_path, creator)

    def __contains__(self, name):
        return name in self._data and not jinja2.is_undefined(self[name])

    def __getitem__(self, name):
        rv = self._data[name]
        if hasattr(rv, '__get__'):
            rv = rv.__get__(self)
            self._data[name] = rv
        return rv

    @cached_property
    def pagination(self):
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
    def _slug(self):
        return self._model.get_slug(self)

    @property
    def url_path(self):
        datamodel = self.datamodel
        slug = self._slug
        path = [self.parent.url_path, slug]
        if self.page_num not in (None, 1):
            assert datamodel.pagination_config.enabled
            path.append(datamodel.pagination_config.url_suffix)
            path.append(self.page_num)
        _, _, slug_tail = slug.rstrip('/').rpartition('/')
        return build_url(path, trailing_slash=('.' not in slug_tail))

    def __for_page__(self, page_num):
        """Get source object for a (possibly) different page number.
        """
        if page_num == self.page_num:
            return self
        return self.get_index(
            self._model, self.parent, self._id, self.children, page_num)

    @property
    def is_hidden(self):
        return self.record.is_hidden

    def get_sort_key(self, fields):
        def cmp_val(field):
            reverse = field.startswith('-')
            if reverse or field.startswith('+'):
                field = field[1:]
            value = self[field] if field in self else None
            return _CmpHelper(value, reverse)

        return [cmp_val(field) for field in fields]


class DummyCache(object):
    def get_or_create(self, key, creator):
        return creator()
