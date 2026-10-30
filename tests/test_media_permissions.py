import copy
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

from installarr.media_permissions import (repair_batch, repair_spec, MediaPermissions,
                                         INTERVAL, WORKER_TIMEOUT)
from installarr.lifecycle import Supervisor
from test_layout import layout_configuration


class MediaPermissionTests(unittest.TestCase):
    def test_scope_only_selected_plex_media_and_readonly_secondary_preserved(self):
        config = layout_configuration()
        spec = repair_spec(config)
        paths = {r['path'] for r in spec['roots']}
        self.assertEqual(paths, set(config['folder_map'].values()) | {config['storage']['media_secondary']})
        self.assertFalse(set(config['storage'][p] for p in ('downloads', 'configs', 'backups')) & paths)
        config.pop('folder_map'); config['plex_libraries'] = [
            {'name': 'Movies', 'type': 'movie', 'relative_paths': ['Movies', 'Movies-2'], 'language': 'en-US'}]
        config['secondary_media_read_only'] = True
        self.assertNotIn(config['storage']['media_secondary'], {r['path'] for r in repair_spec(config)['roots']})
        config['apps'] = ['sonarr']
        with self.assertRaises(ValueError): repair_spec(config)

    def fixture(self, root):
        media = root/'media'; media.mkdir()
        (media/'health').write_text('healthy\n')
        return media, {'uid': 2000, 'gid': 2000, 'roots': [
            {'path': str(media), 'anchor': str(media), 'sentinel': 'health',
             'expected': {'target': '/', 'source': 'fixture', 'fstype': 'ext4'}}]}

    @unittest.skipUnless(os.geteuid() == 0, 'Real identity permission repair requires root')
    def test_root_owned_750_movies_repair_rerun_real_identity_and_no_other_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); root.chmod(0o755)
            media, spec = self.fixture(root)
            movie=media/'Movie'; movie.mkdir(mode=0o750)
            video=movie/'Movie.mkv'; video.write_bytes(b'unchanged media bytes'); video.chmod(0o600)
            before=video.stat()
            expected=spec['roots'][0]['expected']
            with patch('installarr.directories.observed_mount',return_value=expected):
                result=repair_batch(spec)
                self.assertTrue(result['complete']); self.assertEqual(result['denied'],0)
                self.assertEqual(result['changed'],2)
                self.assertEqual(repair_batch(spec)['changed'],0)
            self.assertEqual(video.stat().st_uid,0)
            self.assertEqual(video.stat().st_gid,2000)
            self.assertEqual(video.stat().st_mtime_ns,before.st_mtime_ns)
            self.assertEqual(video.read_bytes(),b'unchanged media bytes')
            pid=os.fork()
            if pid==0:
                try:
                    os.setgroups([]);os.setgid(2000);os.setuid(2000)
                    assert video.read_bytes()==b'unchanged media bytes'
                    os._exit(0)
                except BaseException: os._exit(1)
            self.assertEqual(os.waitpid(pid,0)[1],0)

    @unittest.skipUnless(os.geteuid() == 0, 'Real ownership fixture requires root')
    def test_symlink_hardlink_nested_mount_and_nas_metadata_are_not_touched(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);media,spec=self.fixture(root)
            outside=root/'outside';outside.write_text('keep');outside.chmod(0o600)
            (media/'link').symlink_to(outside)
            os.link(outside,media/'hardlink')
            thumb=media/'.@__thumb';thumb.mkdir(mode=0o700)
            nested=media/'nested';nested.mkdir(mode=0o700)
            original=(outside.stat().st_mode,outside.stat().st_gid)
            from installarr.media_permissions import mount_id
            def identity(fd):
                if os.fstat(fd).st_ino==nested.stat().st_ino:return 'different-mount'
                return mount_id(fd)
            with patch('installarr.directories.observed_mount',return_value=spec['roots'][0]['expected']),patch('installarr.media_permissions.mount_id',side_effect=identity):
                result=repair_batch(spec)
            self.assertGreaterEqual(result['skipped'],4)
            self.assertEqual((outside.stat().st_mode,outside.stat().st_gid),original)
            self.assertEqual(thumb.stat().st_mode & 0o777,0o700)
            self.assertEqual(nested.stat().st_mode & 0o777,0o700)

    def test_wrong_mount_or_missing_marker_refuses_before_mutation(self):
        with tempfile.TemporaryDirectory() as temporary:
            media,spec=self.fixture(Path(temporary))
            movie=media/'movie';movie.mkdir(mode=0o700)
            with patch('installarr.directories.observed_mount',return_value={'target':'/','source':'wrong','fstype':'ext4'}),patch('os.fchmod') as chmod:
                with self.assertRaises(ValueError):repair_batch(spec)
                chmod.assert_not_called()
            (media/'health').unlink()
            with patch('installarr.directories.observed_mount',return_value=spec['roots'][0]['expected']),patch('os.fchown') as chown:
                with self.assertRaises(FileNotFoundError):repair_batch(spec)
                chown.assert_not_called()

    @unittest.skipUnless(os.geteuid() == 0, 'Real denied ownership mutation requires root')
    def test_server_denial_is_reported_and_does_not_claim_repair(self):
        with tempfile.TemporaryDirectory() as temporary:
            media,spec=self.fixture(Path(temporary))
            movie=media/'movie';movie.mkdir(mode=0o700)
            with patch('installarr.directories.observed_mount',return_value=spec['roots'][0]['expected']),patch('os.fchown',side_effect=PermissionError):
                result=repair_batch(spec)
            self.assertGreater(result['denied'],0)
            self.assertEqual(result['changed'],0)
            self.assertEqual(movie.stat().st_mode & 0o777,0o700)

    def test_batched_walk_continues_to_later_folders(self):
        with tempfile.TemporaryDirectory() as temporary:
            media,spec=self.fixture(Path(temporary))
            for i in range(15):
                folder=media/str(i);folder.mkdir();(folder/'video').write_text('unchanged')
            cursor=None;checked=0
            with patch('installarr.directories.observed_mount',return_value=spec['roots'][0]['expected']):
                for _ in range(50):
                    result=repair_batch(spec,cursor,limit=4)
                    cursor=result['cursor'];checked+=result['checked']
                    if result['complete']:break
                else:self.fail('Walk never completed')
            self.assertGreaterEqual(checked,31)

    def test_cursor_cannot_escape_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            media,spec=self.fixture(Path(temporary))
            for part in ('..','/etc','a/b',''):
                cursor={'root':0,'stack':[{'parts':[part],'offset':0}]}
                with self.assertRaises(ValueError):repair_batch(spec,cursor)

    def test_scheduling_first_pass_interval_and_no_overlapping_threads(self):
        config=layout_configuration();clock=Mock(return_value=0)
        task=MediaPermissions(config,Path('/private'),clock)
        policy={'schema_version':1,'enabled':True,'interval_seconds':60}
        with patch('os.path.lexists',return_value=True),patch('installarr.lifecycle.root_json',return_value=policy),patch('threading.Thread') as thread:
            task.tick();thread.assert_called_once();thread.return_value.start.assert_called_once()
            thread.return_value.is_alive.return_value=True
            task.tick();thread.assert_called_once()
            thread.return_value.is_alive.return_value=False
            task.result={'complete':True,'cursor':None,'changed':3}
            task.tick();self.assertEqual(task.next_due,60)
            clock.return_value=59;task.tick();thread.assert_called_once()
            clock.return_value=60;task.tick();self.assertEqual(thread.call_count,2)
        self.assertEqual(INTERVAL,60);self.assertEqual(WORKER_TIMEOUT,30)

    def test_mount_failure_cancels_repair_before_stopping_owned_containers(self):
        events=[];repair=Mock();repair.cancel.side_effect=lambda:events.append('cancel')
        controller=Mock();controller.stop.side_effect=lambda:events.append('stop')
        probe=Mock();probe.check.return_value={'healthy':False}
        supervisor=Supervisor(controller,probe,lambda *x:None,media_permissions=repair)
        supervisor.step();self.assertEqual(events,['cancel','stop']);repair.tick.assert_not_called()

    def test_disabling_cancels_worker_and_keeps_opt_in_explicit(self):
        task=MediaPermissions(layout_configuration(),Path('/private'))
        with patch('os.path.lexists',return_value=False),patch.object(task,'cancel') as cancel,patch('threading.Thread') as thread:
            self.assertEqual(task.tick(),{'enabled':False});cancel.assert_called_once();thread.assert_not_called()
