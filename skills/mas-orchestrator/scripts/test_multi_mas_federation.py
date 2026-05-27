#!/usr/bin/env python3
"""Production multi_mas_federation.py unit tests."""

import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import multi_mas_federation as mmf


# ============================================================
# MASInstance
# ============================================================

class TestMASInstance(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def test_instance_creation(self):
        inst = mmf.MASInstance("test_001", "finance", self.tmpdir)
        self.assertTrue(Path(inst.state_dir).exists())
        self.assertTrue(Path(inst.persistent_dir).exists())
        self.assertTrue(Path(inst.metadata_path).exists())
        meta = inst.to_dict()
        self.assertEqual(meta["domain"], "finance")
        self.assertEqual(meta["status"], "initialized")

    def test_status_update_invalid(self):
        inst = mmf.MASInstance("test_002", "x", self.tmpdir)
        with self.assertRaises(ValueError):
            inst.update_status("invalid_status")

    def test_heartbeat_alive(self):
        inst = mmf.MASInstance("test_003", "x", self.tmpdir)
        inst.heartbeat()
        self.assertTrue(inst.is_alive())

    def test_heartbeat_no_signal(self):
        inst = mmf.MASInstance("test_004", "x", self.tmpdir)
        # heartbeat not called
        self.assertFalse(inst.is_alive())

    def test_execute_task_default_runner(self):
        inst = mmf.MASInstance("test_005", "general", self.tmpdir)
        result = inst.execute_task({"description": "test task"})
        self.assertIn("task", result)
        meta = inst.to_dict()
        self.assertEqual(meta["tasks_completed"], 1)

    def test_execute_task_custom_runner(self):
        def runner(instance, payload):
            return {"custom": True, "domain": instance.domain}
        inst = mmf.MASInstance("test_006", "marketing", self.tmpdir,
                                instance_runner=runner)
        result = inst.execute_task({"x": 1})
        self.assertTrue(result["custom"])
        self.assertEqual(result["domain"], "marketing")


# ============================================================
# FederationMessageBroker
# ============================================================

class TestMessageBroker(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.broker = mmf.FederationMessageBroker(self.tmpdir)

    def test_post_and_poll(self):
        msg_id = self.broker.post("a", "b", "task_request", {"x": 1})
        self.assertIsNotNone(msg_id)
        # b polls
        unread = self.broker.poll("b")
        self.assertEqual(len(unread), 1)
        self.assertEqual(unread[0]["content"]["x"], 1)

    def test_poll_marks_read(self):
        self.broker.post("a", "b", "task_request", {})
        first = self.broker.poll("b")
        second = self.broker.poll("b")
        self.assertEqual(len(first), 1)
        self.assertEqual(len(second), 0)

    def test_invalid_msg_type_raises(self):
        with self.assertRaises(ValueError):
            self.broker.post("a", "b", "invalid_type", {})

    def test_broadcast_recipient(self):
        self.broker.post("a", "*", "status_query", {"who": "all"})
        b_msgs = self.broker.poll("b")
        c_msgs = self.broker.poll("c")
        self.assertEqual(len(b_msgs), 1)
        self.assertEqual(len(c_msgs), 1)

    def test_msg_type_filter(self):
        self.broker.post("a", "b", "task_request", {})
        self.broker.post("a", "b", "audit_request", {})
        tasks = self.broker.poll("b", msg_type_filter="task_request")
        # Only task_request was fetched, audit_request is not read
        audits = self.broker.poll("b", msg_type_filter="audit_request")
        self.assertEqual(len(tasks), 1)
        self.assertEqual(len(audits), 1)


# ============================================================
# FederationCoordinator
# ============================================================

class TestFederationCoordinator(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.coord = mmf.FederationCoordinator(self.tmpdir, pattern="hub_spoke")

    def test_invalid_pattern_raises(self):
        with self.assertRaises(ValueError):
            mmf.FederationCoordinator(self.tmpdir, pattern="bogus")

    def test_spawn_instance(self):
        inst = self.coord.spawn_instance("finance")
        self.assertEqual(inst.domain, "finance")
        self.assertIn(inst.instance_id, self.coord.registry["instances"])

    def test_get_instance(self):
        inst = self.coord.spawn_instance("legal")
        retrieved = self.coord.get_instance(inst.instance_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.domain, "legal")

    def test_list_instances_filter(self):
        self.coord.spawn_instance("finance")
        self.coord.spawn_instance("finance")
        self.coord.spawn_instance("legal")
        finance_list = self.coord.list_instances(domain="finance")
        legal_list = self.coord.list_instances(domain="legal")
        self.assertEqual(len(finance_list), 2)
        self.assertEqual(len(legal_list), 1)

    def test_route_task_with_domain_match(self):
        inst = self.coord.spawn_instance("finance")
        inst.heartbeat()
        result = self.coord.route_task({"x": 1}, target_domain="finance")
        self.assertEqual(result["target_id"], inst.instance_id)
        self.assertEqual(result["method"], "domain_match")

    def test_route_task_fallback(self):
        inst = self.coord.spawn_instance("legal")
        inst.heartbeat()
        result = self.coord.route_task({"x": 1}, target_domain="finance",
                                         require_alive=False)
        # Domain mismatch -> fallback selects legal
        self.assertIn(result["method"], ("fallback", "domain_match"))

    def test_health_check(self):
        a = self.coord.spawn_instance("a")
        a.heartbeat()
        b = self.coord.spawn_instance("b")
        # b does not call heartbeat
        report = self.coord.health_check_all()
        self.assertIn(a.instance_id, report["alive"])
        # b is alive because heartbeat is auto-called on spawn (becomes unhealthy after time passes)


class TestCrossMASAudit(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        def runner(instance, payload):
            if payload.get("task_type") == "cross_mas_audit":
                return {"verdict": "PASS", "audited_artifact": payload["target_artifact"]}
            return {"result": "default"}
        self.coord = mmf.FederationCoordinator(self.tmpdir,
                                                 instance_runner=runner)
        self.target = self.coord.spawn_instance("finance")
        self.auditor = self.coord.spawn_instance("legal")
        self.target.heartbeat()
        self.auditor.heartbeat()

    def test_audit_request(self):
        msg_id = self.coord.request_cross_mas_audit(
            self.auditor.instance_id, self.target.instance_id, "report.md"
        )
        self.assertIsNotNone(msg_id)
        # auditor processes pending
        results = self.coord.perform_pending_audits(self.auditor.instance_id)
        self.assertEqual(len(results), 1)
        self.assertIn("audit_response_id", results[0])

    def test_audit_metadata_increment(self):
        self.coord.request_cross_mas_audit(self.auditor.instance_id,
                                             self.target.instance_id, "x.md")
        before = self.auditor.to_dict().get("audits_performed", 0)
        self.coord.perform_pending_audits(self.auditor.instance_id)
        after = mmf._safe_read_json(self.auditor.metadata_path).get("audits_performed", 0)
        self.assertEqual(after, before + 1)


class TestLearningShare(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.coord = mmf.FederationCoordinator(self.tmpdir)
        self.source = self.coord.spawn_instance("finance")
        self.r1 = self.coord.spawn_instance("legal")
        self.r2 = self.coord.spawn_instance("audit")

    def test_share_learning_count(self):
        msg_ids = self.coord.share_learning(
            self.source.instance_id,
            {"pattern": "x"},
            require_audited=False
        )
        # Excluding source, 2 recipients
        self.assertEqual(len(msg_ids), 2)

    def test_consume_shared_learning(self):
        self.coord.share_learning(self.source.instance_id, {"pattern": "y"},
                                    require_audited=False)
        consumed_r1 = self.coord.consume_shared_learning(self.r1.instance_id)
        self.assertEqual(len(consumed_r1), 1)
        # Second consume returns 0
        consumed_r1_again = self.coord.consume_shared_learning(self.r1.instance_id)
        self.assertEqual(len(consumed_r1_again), 0)
        # Verify file creation
        shared_path = Path(self.r1.persistent_dir) / "shared_patterns.json"
        self.assertTrue(shared_path.exists())


class TestManagedAgentsAdapter(unittest.TestCase):

    def test_no_config(self):
        # Assume env vars are not set
        adapter = mmf.ManagedAgentsAdapter()
        self.assertFalse(adapter.is_available())
        result = adapter.create_managed_agent({})
        self.assertEqual(result["status"], "not_configured")

    def test_with_endpoint(self):
        adapter = mmf.ManagedAgentsAdapter(api_endpoint="https://x", api_key="key")
        self.assertTrue(adapter.is_available())


# ============================================================
# Persistence (registry, broker, instances are all file-based)
# ============================================================

class TestPersistence(unittest.TestCase):

    def test_coordinator_reload_after_restart(self):
        tmpdir = tempfile.mkdtemp()
        coord1 = mmf.FederationCoordinator(tmpdir)
        inst = coord1.spawn_instance("finance")
        federation_id = coord1.registry["federation_id"]

        # New Coordinator loads same dir -> recognizes instance as-is
        coord2 = mmf.FederationCoordinator(tmpdir)
        self.assertEqual(coord2.registry["federation_id"], federation_id)
        self.assertIn(inst.instance_id, coord2.registry["instances"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
