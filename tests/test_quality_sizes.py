import copy
import unittest
from installarr.quality_sizes import ensure_quality_sizes, factory_sizes
from installarr.profiles import Catalog
from installarr.arr import AppAPIError


class Client:
    def __init__(self, app):
        self.app, self.writes, self.interrupt = app, [], None
        name = app + '/quality-size/' + ('movie' if app == 'radarr' else 'series') + '.json'
        self.rows = [dict(id=i + 40, quality={'name': r['quality']}, title='Preserve title',
                          **factory_sizes(app, r['quality'])) for i, r in enumerate(Catalog().documents[name]['qualities'])]
        self.rows.append({'id': 999, 'quality': {'name': 'Unrelated'}, 'minSize': 8})
    def json(self, method, endpoint, payload=None):
        if endpoint == 'qualitydefinition/limits': return {'min': 0, 'max': 2000 if self.app == 'radarr' else 1000}
        if method == 'GET': return copy.deepcopy(self.rows)
        if self.interrupt == len(self.writes): raise AppAPIError('Interrupted')
        self.writes.append(payload)
        index = next(i for i, r in enumerate(self.rows) if r['id'] == payload['id'])
        self.rows[index] = copy.deepcopy(payload)
        return payload


class QualitySizeTests(unittest.TestCase):
    def test_exact_limits_unlimited_conversion_preservation_and_rerun(self):
        for app in ('sonarr', 'radarr'):
            c = Client(app); unrelated = copy.deepcopy(c.rows[-1])
            result = ensure_quality_sizes(c, app); writes = len(c.writes)
            self.assertGreater(result['qualities'], 10)
            self.assertTrue(all(r.get('maxSize') is None for r in c.rows[:-1]))
            self.assertTrue(all(r['title'] == 'Preserve title' for r in c.rows[:-1]))
            self.assertEqual(c.rows[-1], unrelated)
            ensure_quality_sizes(c, app); self.assertEqual(len(c.writes), writes)

    def test_custom_settings_refuse_before_any_writes(self):
        c = Client('radarr'); c.rows[-2]['minSize'] = 0.12345
        with self.assertRaises(AppAPIError): ensure_quality_sizes(c, 'radarr')
        self.assertFalse(c.writes)

    def test_interrupted_writes_resume_without_resetting_other_qualities(self):
        c = Client('sonarr'); c.interrupt = 2
        with self.assertRaises(AppAPIError): ensure_quality_sizes(c, 'sonarr')
        c.interrupt = None
        ensure_quality_sizes(c, 'sonarr')
        self.assertEqual(len(c.writes), len(c.rows) - 1)
