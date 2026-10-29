import copy
import json
from pathlib import Path
import tempfile
import unittest

from installarr.arr import AppAPIError
from installarr.profiles import Catalog, COMMIT, render_quality_profile, recommended_profiles, validate_selections


class ProfileTests(unittest.TestCase):
    def test_all_pinned_profiles_resolve_full_default_and_required_formats(self):
        catalog = Catalog()
        for app, count in (('radarr', 38), ('sonarr', 22)):
            profiles = catalog.list_profiles(app)
            self.assertEqual(len(profiles), count)
            for item in profiles:
                snapshot = catalog.resolve(app, item['id'])
                self.assertEqual(snapshot['commit'], COMMIT)
                self.assertGreaterEqual(len(snapshot['formats']), len(snapshot['profile']['formatItems']))
                self.assertEqual(len({cf['id'] for cf in snapshot['formats']}), len(snapshot['formats']))
        snapshot = catalog.resolve('radarr', 'd1d67249d3890e49bc12e275d989a7e9')
        formats = {item['definition']['name']: item['score'] for item in snapshot['formats']}
        self.assertEqual(len(formats), 41)  # Nine listed CFs plus complete guide defaults.
        self.assertEqual(formats['Repack/Proper'], 5)
        self.assertEqual(formats['BR-DISK'], -10000)
        self.assertEqual(formats['AMZN'], 0)

    def test_movie_choices_cap_default_at_remux_1080_and_offer_separate_2160(self):
        choices = recommended_profiles(['radarr', 'sonarr'])
        validate_selections({'apps': ['radarr', 'sonarr'], 'quality_profiles': choices})
        catalog = Catalog()
        hd, uhd = [catalog.resolve('radarr', i)['profile'] for i in choices['radarr']['available']]
        self.assertEqual(hd['cutoff'], 'Remux-1080p')
        self.assertEqual(uhd['cutoff'], 'Remux-2160p')
        self.assertFalse(any(row['allowed'] and '2160' in row['name'] for row in hd['items']))
        self.assertEqual(choices['radarr']['default'], hd['trash_id'])
        for invalid in ({'default': 'unknown', 'available': [hd['trash_id']]},
                        {'default': hd['trash_id'], 'available': [hd['trash_id'], hd['trash_id']]}):
            with self.assertRaises(ValueError):
                validate_selections({'apps': ['radarr'], 'quality_profiles': {'radarr': invalid}})
        with self.assertRaises(ValueError):
            validate_selections({'apps': ['sonarr'], 'quality_profiles': {'radarr': choices['radarr']}})

    def test_tampered_snapshot_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'changed.json').write_text('{}')
            (root / 'manifest.json').write_text(json.dumps({'commit': COMMIT,
                'repository': 'https://github.com/TRaSH-Guides/Guides', 'files': {'changed.json': '0' * 64}}))
            with self.assertRaises(ValueError):
                Catalog(root)

    def test_runtime_quality_ids_order_and_cutoff_are_resolved_without_dropping_qualities(self):
        snapshot = Catalog().resolve('radarr', 'd1d67249d3890e49bc12e275d989a7e9')
        names = [name for row in snapshot['profile']['items'] for name in row.get('items', [row['name']])]
        schema = {'items': [{'quality': {'id': i + 20, 'name': name}, 'items': [], 'allowed': False}
                            for i, name in enumerate(names)]}
        ids = {row['id']: i + 500 for i, row in enumerate(snapshot['formats'])}
        payload = render_quality_profile(snapshot, schema, ids, [{'id': -8, 'name': 'Original'}])
        self.assertEqual(payload['items'][-1]['quality']['name'], 'Bluray-1080p')
        self.assertEqual(payload['cutoff'], 20)
        self.assertEqual(payload['language']['id'], -8)
        self.assertEqual(len(payload['formatItems']), 41)
        broken = copy.deepcopy(schema)
        broken['items'].pop()
        with self.assertRaises(AppAPIError):
            render_quality_profile(snapshot, broken, ids, [{'id': -8, 'name': 'Original'}])
