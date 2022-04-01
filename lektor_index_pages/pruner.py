'''
Static collector for build-artifact urls.
All non-tracked VPATH-urls will be pruned after build.
'''
from lektor.builder import Builder
from lektor.reporter import reporter
from lektor.utils import prune_file_and_folder

_cache = set()
# Note: this var is static or otherwise two instances of
#       this module would prune each others artifacts.


def track_not_prune(url: str) -> None:
    ''' Add url to build cache to prevent pruning. '''
    _cache.add(url.lstrip('/'))


def prune(builder: Builder, vpath: str) -> None:
    ''' Remove previously generated, unreferenced Artifacts. '''
    dest_path = builder.destination_path
    con = builder.connect_to_database()
    try:
        with builder.new_build_state() as build_state:
            for url, file in build_state.iter_artifacts():
                if url.lstrip('/') in _cache:
                    continue  # generated in this build-run
                infos = build_state.get_artifact_dependency_infos(url, [])
                for artifact_name, _ in infos:
                    if vpath not in artifact_name:
                        continue  # we only care about our Virtuals
                    reporter.report_pruned_artifact(url)
                    prune_file_and_folder(file.filename, dest_path)
                    build_state.remove_artifact(url)
                    break  # there is only one VPATH-entry per source
    finally:
        con.close()
    _cache.clear()
