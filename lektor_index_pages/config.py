# -*- coding: utf-8 -*-
""" Configuration and config-related logic.

"""
from collections import defaultdict
from itertools import chain

from lektorlib.recordcache import get_or_create_virtual

from .indexmodel import (
    VIRTUAL_PATH_PREFIX,
    index_models_from_ini,
    )
from .sourceobj import IndexRoot


class Config(object):
    def __init__(self, index_models):
        self.index_models = index_models

    def get_index_root(self, record, index_name):
        try:
            index_model = self.index_models[record.path][index_name]
        except KeyError:
            return None
        return IndexRoot.get_index(index_model, record)

    def iter_index_roots(self, record):
        for index_model in self.index_models.get(record.path, {}).values():
            yield IndexRoot.get_index(index_model, record)

    def resolve_virtual_path(self, record, pieces):
        # Lektor's Pad.get or Pad.get_virtual does not cache virtual
        # sources, so we need to cache them ourself or things get
        # dreadfully slow.
        #
        # Interestingly, Lektor's RecordCache is perfectly capable of caching
        # virtual source objects, so we will use it...
        def creator():
            return self._resolve_virtual_path(record, pieces)
        virtual_path = '/'.join(chain([VIRTUAL_PATH_PREFIX], pieces))
        return get_or_create_virtual(record, virtual_path, creator)

    def _resolve_virtual_path(self, record, pieces):
        index_root = self.get_index_root(record, pieces[0])
        if index_root:
            return index_root.resolve_virtual_path(pieces[1:])

    def resolve_url_path(self, record, url_path):
        for index_root in self.iter_index_roots(record):
            source = index_root.resolve_url_path(url_path)
            if source is not None:
                return source

    @classmethod
    def from_ini(cls, env, inifile):
        index_models = defaultdict(dict)
        for parent, root_model in index_models_from_ini(env, inifile):
            index_name = root_model.index_name
            index_models[parent][index_name] = root_model
        return cls(dict(index_models))
