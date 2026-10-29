import json
import threading
import unittest
from unittest.mock import Mock, patch

from installarr.compose import bundle_identity, render_bundle
from installarr.lifecycle import BoundedProbe, Controller, LifecycleError, Supervisor, health_spec
from test_compose import compose_configuration


class SupervisionTests(unittest.TestCase):
    def test_failure_stops_before_reporting_and_never_starts(self):
        events = []
        controller = Mock()
        controller.stop.side_effect = lambda: events.append("stop")
        probe = Mock()
        probe.check.return_value = {"healthy": False}
        supervisor = Supervisor(controller, probe, lambda phase, health: events.append(phase))
        supervisor.step()
        self.assertEqual(events, ["stop", "waiting_storage"])
        controller.reconcile.assert_not_called()
        probe.check.return_value = {"healthy": True}
        supervisor.step()
        controller.reconcile.assert_called_once()
        self.assertEqual(events[-1], "containers_running")

    def test_policy_failure_stops_and_backs_off(self):
        controller = Mock()
        controller.reconcile.side_effect = LifecycleError("changed policy")
        probe = Mock()
        probe.check.return_value = {"healthy": True}
        report = Mock()
        supervisor = Supervisor(controller, probe, report)
        supervisor.step()
        supervisor.step()
        controller.stop.assert_called_once()
        controller.reconcile.assert_called_once()
        self.assertEqual(report.call_args.args[0], "retry_backoff")
        probe.check.return_value = {"healthy": False}
        supervisor.step()
        self.assertEqual(controller.stop.call_count, 2)

    @patch("installarr.lifecycle.subprocess.Popen")
    def test_unreaped_worker_prevents_new_probe_process(self, popen):
        probe = BoundedProbe({"uid": 2000, "gid": 2000})
        probe.pending = Mock()
        probe.pending.poll.return_value = None  # Models uninterruptible kernel I/O.
        for _ in range(3):
            self.assertFalse(probe.check(threading.Event())["healthy"])
        popen.assert_not_called()

    @patch('installarr.lifecycle.subprocess.Popen')
    def test_multiple_identity_checks_do_not_fork_and_block_when_any_worker_unreaped(self, popen):
        probe = BoundedProbe({'uid': 2000, 'gid': 2000, 'checks': [
            {'path': '/media/test'}, {'path': '/configs/netbootxyz', 'uid': 911, 'gid': 1001}]})
        self.assertEqual([(p.spec['uid'], p.spec['gid']) for p in probe.probes], [(2000, 2000), (911, 1001)])
        probe.probes[1].pending = Mock()
        probe.probes[1].pending.poll.return_value = None
        for _ in range(3):
            self.assertEqual(probe.check(threading.Event())['reason'], 'previous_probe_unreaped')
        popen.assert_not_called()

    def test_check_definitions_use_exact_mounts_and_configured_identity(self):
        config = compose_configuration()
        local = {"target": "/", "source": "disk", "fstype": "ext4"}
        result = health_spec(config, local)
        self.assertEqual((result["uid"], result["gid"]), (2000, 2000))
        self.assertEqual(result["checks"][0]["expected"], {"target": "/srv/stack", "source": "nas:/isolated", "fstype": "nfs"})
        self.assertEqual(result["checks"][-1]["expected"], local)


class OwnershipTests(unittest.TestCase):
    def row(self, config, app="sonarr"):
        service = render_bundle(config)["compose"]["services"][app]
        return {"Id": "a" * 64, "Config": {"Labels": {**service["labels"], "com.docker.compose.project": "installarr-test",
                "com.docker.compose.service": app}, "Image": service["image"], "Entrypoint": service["entrypoint"]},
                "HostConfig": {"NetworkMode": "none", "RestartPolicy": {"Name": "no"}},
                "Mounts": [{"Destination": volume["target"], "Source": volume["source"], "RW": not volume["read_only"],
                            "Type": "bind", "Propagation": "rprivate"} for volume in service["volumes"]],
                "State": {"Running": True}}

    def test_foreign_project_collision_never_stopped_or_replaced(self):
        config = compose_configuration()
        run = Mock()
        controller = Controller(config, "installarr-test", run)
        foreign = self.row(config)
        foreign["Config"]["Labels"]["org.installarr.bundle"] = "operator"
        with self.assertRaises(LifecycleError):
            controller.audit([foreign])
        with patch.object(controller, "inventory", return_value=[foreign]):
            controller.stop()
        run.assert_not_called()

    def test_only_matching_ids_stopped_even_with_foreign_container_present(self):
        config = compose_configuration()
        controller = Controller(config, "installarr-test", Mock())
        owned = self.row(config)
        foreign = self.row(config)
        foreign["Id"] = "b" * 64
        foreign["Config"]["Labels"]["org.installarr.bundle"] = "operator"
        stopped = {**owned, "State": {"Running": False}}
        with patch.object(controller, "inventory", side_effect=[[owned, foreign], [stopped, foreign]]):
            controller.stop()
        args = controller.run.call_args.args[0]
        self.assertIn("a" * 64, args)
        self.assertNotIn("b" * 64, args)

    def test_changed_restart_or_bind_policy_refused(self):
        config = compose_configuration()
        controller = Controller(config, "installarr-test", Mock())
        for field in ("restart", "bind"):
            row = self.row(config)
            if field == "restart":
                row["HostConfig"]["RestartPolicy"]["Name"] = "always"
            else:
                row["Mounts"][0]["Source"] = "/operator/path"
            self.assertTrue(controller.owns(row))
            with self.assertRaises(LifecycleError):
                controller.audit([row])

    def test_shared_namespace_must_belong_to_matching_live_sab(self):
        config = compose_configuration()
        config['apps'] = ['radarr', 'sabnzbd']
        controller = Controller(config, 'installarr-test', Mock())
        owner = self.row(config, 'sabnzbd')
        owner['Id'] = 'b' * 64
        owner['State']['Pid'] = 101
        app = self.row(config, 'radarr')
        app['State']['Pid'] = 102
        app['HostConfig']['NetworkMode'] = 'container:' + owner['Id']
        with patch('installarr.lifecycle.os.stat', return_value=Mock(st_ino=7)):
            self.assertTrue(controller.audit([owner, app]))
        with patch('installarr.lifecycle.os.stat', side_effect=[Mock(st_ino=7), Mock(st_ino=8)]):
            with self.assertRaises(LifecycleError):
                controller.audit([owner, app])
        app['HostConfig']['NetworkMode'] = 'container:' + 'c' * 64
        with patch('installarr.lifecycle.os.stat', return_value=Mock(st_ino=7)):
            with self.assertRaises(LifecycleError):
                controller.audit([owner, app])
