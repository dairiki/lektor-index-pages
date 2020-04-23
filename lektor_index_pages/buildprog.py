# -*- coding: utf-8 -*-
""" Build program for the index pages.
"""

from lektor.build_programs import BuildProgram
from lektor.context import get_ctx


class IndexBuildProgram(BuildProgram):
    def produce_artifacts(self):
        source = self.source
        record = source.record

        if source.is_visible:
            pagination_enabled = source.datamodel.pagination_config.enabled
            if not pagination_enabled or source.page_num is not None:
                artifact_name = source.url_path
                if artifact_name.endswith('/'):
                    artifact_name += 'index.html'
                # We don't really depend on record — the index doesn't
                # change if the parent page contents do.  However, if
                # no sources are listed here, the index will be pruned
                # immediately after the build.  I guess this will do.
                sources = [record.source_filename]
                self.declare_artifact(artifact_name, sources=sources)

    def build_artifact(self, artifact):
        config_filename = self.source.datamodel.filename
        template = self.source._data['_template']

        if config_filename is not None:
            ctx = get_ctx()
            if ctx is not None:
                ctx.record_dependency(config_filename)

        artifact.render_template_into(template, this=self.source)

    def iter_child_sources(self):
        source = self.source
        pagination_config = source.datamodel.pagination_config

        if pagination_config.enabled and source.page_num is None:
            num_pages = pagination_config.count_pages(source)
            for page_num in range(1, num_pages + 1):
                yield source.__for_page__(page_num)

        subindexes = getattr(source, 'subindexes', None)
        if subindexes is not None:
            for subindex in subindexes:
                yield subindex
