import copy
import itertools
import unittest
from installarr.cli import validate
from installarr.compose import render_bundle, application_paths
from installarr.directories import directory_plan
from installarr.layout import default_folders, libraries
from installarr.ombi_family import family_paths
from installarr.plex import library_paths
from installarr.lifecycle import health_spec
from test_compose import compose_configuration


def layout_configuration():
    c = compose_configuration()
    c['apps'] = ['plex', 'sonarr', 'radarr', 'sabnzbd', 'bazarr', 'ombi', 'tautulli', 'jackett', 'netbootxyz']
    c['data_root'] = c['storage']['media'] = '/srv/stack/data'
    c['storage']['downloads'] = '/srv/stack/data/finished-downloads'
    c['storage']['incomplete'] = '/srv/stack/data/unfinished-downloads'
    c['folder_map'] = default_folders(c['storage']['media'])
    for purpose in ('media', 'downloads', 'incomplete'):
        c['storage_mounts'][purpose] = dict(c['storage_checks'][purpose], kind='existing')
    c['storage']['media_secondary'] = '/secondary/media-movies-2'
    check = {'mountpoint': '/secondary', 'source': 'nas:/secondary', 'fstype': 'nfs', 'sentinel': 'health'}
    c['storage_mounts']['media_secondary'] = dict(check, kind='existing')
    c['secondary_media_read_only'] = False
    c['plex_libraries'] = libraries(c)
    return c


class LayoutTests(unittest.TestCase):
    def test_all_apps_exact_scopes_and_plex_library_paths(self):
        c = layout_configuration(); validate(c)
        bundle = render_bundle(c)
        scopes = {}
        for app, service in bundle['compose']['services'].items():
            media = [v for v in service['volumes'] if v['target'].startswith('/data')]
            self.assertFalse(any(v['target'] in ('/data', '/media-secondary') for v in service['volumes']))
            self.assertTrue(all(v['read_only'] == (app == 'plex') for v in media))
            scopes[app] = {v['target'] for v in media}
        self.assertEqual(scopes['sabnzbd'], {'/data/finished-downloads', '/data/unfinished-downloads'})
        self.assertNotIn('/data/media-tv', scopes['radarr'])
        self.assertNotIn('/data/unfinished-downloads', scopes['radarr'])
        self.assertNotIn('/data/media-movies', scopes['sonarr'])
        self.assertFalse(scopes['ombi'] | scopes['tautulli'] | scopes['jackett'] | scopes['netbootxyz'])
        self.assertNotIn('/data/finished-downloads', scopes['plex'])
        self.assertIn('/data/media-movies-2', scopes['radarr'] & scopes['bazarr'] & scopes['plex'])
        self.assertEqual([r['name'] for r in library_paths(c)], ['Movies', 'TV Shows', 'Sports', 'Standup'])
        self.assertEqual(application_paths(c, 'radarr')['media_root'], '/data/media-movies')
        self.assertEqual(set(application_paths(c, 'sonarr')['additional_media_roots']), {'/data/media-lenoratv', '/data/media-jeremytv'})
        self.assertTrue({'/data/media-lenoramovies', '/data/media-jeremymovies', '/data/media-movies-2'} <= set(application_paths(c, 'radarr')['additional_media_roots']))
        self.assertEqual(family_paths(c)['lenora8']['sonarr']['container_path'], '/data/media-lenoratv')

    def test_custom_host_names_do_not_change_container_paths_or_access(self):
        c = layout_configuration(); c['folder_map']['movies'] = '/srv/stack/data/Existing-Movies'
        validate(c)
        movies = library_paths(c)[0]
        self.assertIn('/srv/stack/data/Existing-Movies', movies['host_paths'])
        self.assertIn('/data/media-movies', movies['container_paths'])

    def test_mixed_nvme_downloads_and_nas_media_keep_separate_assertions(self):
        c = layout_configuration()
        for purpose in ('downloads', 'incomplete'):
            c['storage'][purpose] = '/nvme/' + purpose
            c['storage_checks'][purpose] = {'mountpoint': '/nvme', 'source': '/dev/nvme1n1p1', 'fstype': 'ext4', 'sentinel': 'health'}
            c['storage_mounts'][purpose] = {'kind': 'local'}
        validate(c)
        bundle = render_bundle(c)
        self.assertIn('source=/dev/nvme1n1p1', bundle['guards']['sabnzbd.guard.sh'])
        self.assertIn('source=nas:/isolated', bundle['guards']['radarr.guard.sh'])
        self.assertIn('source=/dev/nvme1n1p1', bundle['guards']['radarr.guard.sh'])

    def test_category_and_role_directories_are_prepared_and_supervised(self):
        c = layout_configuration()
        plan = {r['path']: r for r in directory_plan(c)}
        self.assertIn('/srv/stack/data/finished-downloads/movies', plan)
        self.assertIn('/srv/stack/data/finished-downloads/tv', plan)
        self.assertEqual(plan[c['folder_map']['tv']]['check']['source'], 'nas:/isolated')
        self.assertEqual(plan[c['folder_map']['tv']]['sentinel'], 'health')
        health = health_spec(c, {'target': '/', 'source': 'disk', 'fstype': 'ext4'})
        paths = {r['path'] for r in health['checks']}
        self.assertTrue(set(c['folder_map'].values()) <= paths)
        self.assertIn('/srv/stack/data/finished-downloads/tv', paths)

    def test_bad_layouts_refuse_without_rendering(self):
        for mutation in ('overlap', 'outside', 'private', 'missing', 'wrong_assertion', 'assets_overlap'):
            c = layout_configuration()
            if mutation == 'overlap': c['folder_map']['tv'] = c['folder_map']['movies']
            if mutation == 'outside': c['folder_map']['tv'] = '/unasserted/TV'
            if mutation == 'private': c['storage']['configs'] = c['folder_map']['tv'] + '/config'
            if mutation == 'missing': del c['folder_map']['tv']
            if mutation == 'wrong_assertion': c['storage_checks']['downloads']['mountpoint'] = '/absent-nas'
            if mutation == 'assets_overlap':
                c['storage']['netboot_assets'] = c['folder_map']['tv']
                c['storage_mounts']['netboot_assets'] = dict(c['storage_mounts']['media'])
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): validate(c)

    def test_all_optional_subsets_render_scoped_binds(self):
        original = layout_configuration(); apps = original['apps']
        for size in range(1, len(apps) + 1):
            for chosen in itertools.combinations(apps, size):
                c = copy.deepcopy(original); c['apps'] = list(chosen)
                if 'plex' not in chosen: c.pop('plex_libraries')
                if not set(chosen) & {'plex', 'radarr', 'bazarr'}:
                    c['storage'].pop('media_secondary'); c['storage_mounts'].pop('media_secondary');c.pop('secondary_media_read_only')
                bundle = render_bundle(c)
                self.assertEqual(set(bundle['compose']['services']), set(chosen))

