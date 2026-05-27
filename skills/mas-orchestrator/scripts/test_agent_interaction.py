#!/usr/bin/env python3
"""agent_interaction.py unit tests."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import agent_interaction as ai


class TestAgentMessageBus(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.bus = ai.AgentMessageBus(self.tmpdir)

    def test_start_and_post(self):
        iid = self.bus.start_interaction("review_round", ["worker_W1", "worker_W2"])
        msg_id = self.bus.post_message(iid, "worker_W1", {"verdict": "APPROVE"},
                                        msg_type="vote")
        self.assertIsNotNone(msg_id)
        msgs = self.bus.get_interaction_messages(iid)
        self.assertEqual(len(msgs), 1)

    def test_invalid_type_raises(self):
        with self.assertRaises(ValueError):
            self.bus.start_interaction("invalid_type", ["a"])

    def test_too_many_participants_raises(self):
        with self.assertRaises(ValueError):
            self.bus.start_interaction("review_round", [f"w{i}" for i in range(10)])

    def test_sender_not_in_participants(self):
        iid = self.bus.start_interaction("review_round", ["worker_W1"])
        with self.assertRaises(ValueError):
            self.bus.post_message(iid, "worker_W99", {"x": 1})

    def test_advance_round_max(self):
        iid = self.bus.start_interaction("review_round", ["a", "b"], max_rounds=1)
        self.bus.advance_round(iid)  # 0 -> 1
        self.bus.advance_round(iid)  # 1 -> 2 -> max reached, end
        interaction = self.bus.data["interactions"][iid]
        self.assertEqual(interaction["status"], "ended")

    def test_active_interactions(self):
        iid1 = self.bus.start_interaction("review_round", ["a"])
        iid2 = self.bus.start_interaction("debate_round", ["a", "b"])
        self.bus.end_interaction(iid1)
        active = self.bus.get_active_interactions()
        self.assertEqual(len(active), 1)


class TestReviewRound(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.bus = ai.AgentMessageBus(self.tmpdir)

    def test_unanimous_approval(self):
        iid = ai.initiate_review_round(self.bus, ["w1", "w2", "w3"], "test.md")
        for w in ["w1", "w2", "w3"]:
            ai.reviewer_post_opinion(self.bus, iid, w, "APPROVE", "ok")
        outcome = ai.aggregate_review_outcomes(self.bus, iid, current_round=0)
        self.assertEqual(outcome["consensus"], "APPROVE")
        self.assertEqual(outcome["method"], "unanimous")
        self.assertFalse(outcome["recommend_next_round"])

    def test_majority(self):
        iid = ai.initiate_review_round(self.bus, ["w1", "w2", "w3"], "test.md")
        ai.reviewer_post_opinion(self.bus, iid, "w1", "APPROVE", "ok")
        ai.reviewer_post_opinion(self.bus, iid, "w2", "APPROVE", "ok")
        ai.reviewer_post_opinion(self.bus, iid, "w3", "REJECT", "not ok")
        outcome = ai.aggregate_review_outcomes(self.bus, iid, current_round=0)
        self.assertEqual(outcome["consensus"], "APPROVE")
        self.assertEqual(outcome["method"], "majority")

    def test_split_recommends_round2(self):
        iid = ai.initiate_review_round(self.bus, ["w1", "w2"], "test.md")
        ai.reviewer_post_opinion(self.bus, iid, "w1", "APPROVE", "ok")
        ai.reviewer_post_opinion(self.bus, iid, "w2", "REJECT", "not ok")
        outcome = ai.aggregate_review_outcomes(self.bus, iid, current_round=0)
        self.assertEqual(outcome["consensus"], "DISPUTED")
        self.assertTrue(outcome["recommend_next_round"])


class TestDebateRound(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.bus = ai.AgentMessageBus(self.tmpdir)

    def test_counterargument_chain(self):
        iid = ai.initiate_debate_round(self.bus, ["adv", "worker"], "X causes Y")
        m1 = ai.debater_post_argument(self.bus, iid, "adv", "OPPOSE", "correlation only")
        m2 = ai.debater_post_argument(self.bus, iid, "worker", "SUPPORT",
                                       "RCT shows causation",
                                       counterargument_to=m1)
        msgs = self.bus.get_interaction_messages(iid)
        self.assertEqual(len(msgs), 2)
        self.assertEqual(msgs[1]["content"]["counterargument_to"], m1)


class TestPeerReview(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.bus = ai.AgentMessageBus(self.tmpdir)

    def test_handoff_within_limit(self):
        iid = ai.initiate_peer_review_chain(self.bus, ["w1", "w2", "w3"], "x.md")
        result = ai.peer_review_handoff(self.bus, iid, "w1", "w2", "needs review", 0)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["hop_count"], 1)

    def test_handoff_exceeds_limit(self):
        iid = ai.initiate_peer_review_chain(self.bus, ["w1", "w2"], "x.md")
        result = ai.peer_review_handoff(self.bus, iid, "w1", "w2", "review",
                                         hop_count=ai.DEFAULT_MAX_HOPS)
        self.assertFalse(result["accepted"])


class TestCostEstimation(unittest.TestCase):

    def test_cost_increases_with_rounds(self):
        interaction_1r = {"participants": ["a", "b", "c"], "current_round": 1}
        interaction_2r = {"participants": ["a", "b", "c"], "current_round": 2}
        cost_1 = ai.estimate_interaction_cost(interaction_1r)
        cost_2 = ai.estimate_interaction_cost(interaction_2r)
        self.assertGreater(cost_2["estimated_tokens"], cost_1["estimated_tokens"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
