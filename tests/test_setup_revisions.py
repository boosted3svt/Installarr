import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from installarr.setup_revisions import selected_setup, new_setup, activate_setup, prepare_switch
from installarr.credentials import read_private_json
from installarr.cli import save_config
from installarr.guided import run_setup
from test_layout import layout_configuration


class SetupRevisionTests(unittest.TestCase):
    def test_only_owned_local_netboot_child_is_archived_without_modifying_content(self):
        from installarr.setup_revisions import archive_local_netboot
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); parent=root/'netboot';parent.mkdir();assets=parent/'assets';assets.mkdir()
            (assets/'operator-file').write_bytes(b'keep unchanged')
            old=layout_configuration();old['storage']['netboot_assets']=str(assets)
            old['storage_mounts']['netboot_assets']={'kind':'local'}
            expected={'target':'/','source':'local-disk','fstype':'ext4'}
            old['storage_checks']['netboot_assets']={'mountpoint':'/','source':'local-disk','fstype':'ext4','sentinel':'health'}
            new=layout_configuration();new['storage']['netboot_assets']=str(assets)
            new['storage_mounts']['netboot_assets']={'kind':'nfs','mountpoint':str(parent),'source':'nas:/boot','fstype':'nfs','sentinel':'health'}
            with patch('installarr.anchors.open_anchors',return_value=[(os.open(str(parent),os.O_RDONLY|os.O_DIRECTORY),[],expected)]):
                archive_local_netboot(new,old,root)
            self.assertFalse(assets.exists())
            self.assertEqual((root/'retired-local-assets/assets/operator-file').read_bytes(),b'keep unchanged')
            self.assertEqual(list(parent.iterdir()),[])
            assets.mkdir();(parent/'unrelated').write_text('preserve')
            with patch('installarr.anchors.open_anchors',return_value=[(os.open(str(parent),os.O_RDONLY|os.O_DIRECTORY),[],expected)]),self.assertRaises(ValueError):
                archive_local_netboot(new,old,root)
            self.assertTrue(assets.exists());self.assertTrue((parent/'unrelated').exists())

    @unittest.skipUnless(os.geteuid() == 0, 'Persistence switch requires root-owned fixture files')
    def test_owned_mount_switch_preserves_other_fstab_lines_and_replays_idempotently(self):
        from types import SimpleNamespace
        from installarr.execution import Execution
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'setup';root.mkdir(mode=0o700)
            old = layout_configuration()
            for purpose in ('media','downloads','incomplete'):
                old['storage_mounts'][purpose] = dict(old['storage_checks'][purpose],kind='nfs')
            save_config(root/'settings.json',old)
            next_config = json.loads(json.dumps(old))
            for purpose in ('media','downloads','incomplete'):
                next_config['storage_mounts'][purpose]['source']='new:/export'
                next_config['storage_checks'][purpose]['source']='new:/export'
            previous={'config_file':str(root/'settings.json'),'state':str(root/'old-state'),'name':'family-media'}
            with Execution(root/'old-state',{'operation':'reference-apply-v1','config':old,'name':'family-media'}) as state:
                state.state['steps']['mounts']='verified';state._save()
            fstab=root/'fixture.fstab'
            original='# preserve\nnas:/isolated /srv/stack nfs defaults 0 0\nother:/keep /keep nfs defaults 0 0\n'
            fstab.write_text(original);fstab.chmod(0o644)
            mounted=[{'target':'/srv/stack','source':'nas:/isolated','fstype':'nfs'}]
            def unmount(*args,**kwargs):
                mounted.clear();return SimpleNamespace(returncode=0)
            with patch('installarr.mounts.runtime_mounts',side_effect=lambda:list(mounted)), patch('installarr.reference.existing_service',return_value=None), patch('installarr.lifecycle.command') as command, patch('installarr.storage_process.run_storage',side_effect=unmount) as umount:
                prepare_switch(next_config,root,previous,fstab)
                self.assertEqual((root/'before-switch.fstab').read_text(),original)
                self.assertEqual(fstab.read_text(),'# preserve\nother:/keep /keep nfs defaults 0 0\n')
                prepare_switch(next_config,root,previous,fstab)
            self.assertEqual(umount.call_count,1)
            command.assert_called_once_with(['systemctl','daemon-reload'])

    def test_selection_preserves_previous_settings_and_cancel_does_not_switch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'setup';root.mkdir(mode=0o700)
            c = layout_configuration();save_config(root / 'settings.json', c)
            original = (root / 'settings.json').read_bytes()
            self.assertEqual(selected_setup(root), root)
            revision = new_setup(root, root, 'family-media', c)
            self.assertEqual(selected_setup(root), root)
            save_config(revision / 'settings.json', c)
            activate_setup(root, revision)
            self.assertEqual(selected_setup(root), revision)
            self.assertEqual((root / 'settings.json').read_bytes(), original)
            metadata = read_private_json(revision / 'installation.json')
            self.assertEqual(metadata['previous']['config_file'], str(root / 'settings.json'))

    def test_fresh_saved_setup_selection_is_save_only_without_host_work(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'setup';root.mkdir(mode=0o700)
            c = layout_configuration();save_config(root / 'settings.json', c)
            with patch('sys.stdin.isatty', return_value=True), patch('installarr.guided.is_administrator', return_value=True), patch('builtins.input', side_effect=['yes','no','yes','yes','no']), patch('installarr.guided.collect_settings', return_value=c), patch('installarr.reference.apply_reference') as apply, patch('installarr.setup_revisions.prepare_switch') as switch, patch('sys.stdout', new_callable=io.StringIO):
                self.assertEqual(run_setup(root), 0)
            apply.assert_not_called();switch.assert_not_called()
            self.assertNotEqual(selected_setup(root), root)

    def test_active_pointer_cannot_select_outside_private_installations(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'setup';root.mkdir(mode=0o700)
            from installarr.compose import private_artifact
            private_artifact(root / 'active-setup.json',json.dumps({'directory':'/etc'}).encode(),0o600)
            with self.assertRaises(ValueError): selected_setup(root)

    def test_dangling_selection_symlink_is_refused_not_ignored_or_replaced(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'setup';root.mkdir(mode=0o700)
            pointer=root/'active-setup.json';pointer.symlink_to(root/'missing')
            revision=root/'installations/setup-test'
            with self.assertRaises(ValueError): selected_setup(root)
            with self.assertRaises(ValueError): activate_setup(root,revision)
            self.assertTrue(pointer.is_symlink())

    def test_unrelated_mount_refused_before_stopping_existing_service(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'setup';root.mkdir(mode=0o700)
            old = layout_configuration()
            for purpose in ('media', 'downloads', 'incomplete'):
                old['storage_mounts'][purpose] = dict(old['storage_checks'][purpose],kind='nfs')
            save_config(root / 'settings.json', old)
            next_config = layout_configuration()
            for purpose in ('media', 'downloads', 'incomplete'):
                next_config['storage_mounts'][purpose] = dict(next_config['storage_checks'][purpose],source='new:/export',kind='nfs')
                next_config['storage_checks'][purpose]['source']='new:/export'
            previous={'config_file':str(root/'settings.json'),'state':str(root/'old-state'),'name':'family-media'}
            with patch('installarr.accounts.provisioning_gate'), patch('installarr.mounts.runtime_mounts',return_value=[{'target':'/srv/stack','source':'foreign:/keep','fstype':'nfs'}]), patch('installarr.lifecycle.command') as command, self.assertRaises(ValueError):
                prepare_switch(next_config, root, previous)
            command.assert_not_called()
