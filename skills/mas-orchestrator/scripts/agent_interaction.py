"""
Inter-Agent Harness Interaction
===============================

Event bus + protocols supporting direct conversation and review rounds between agents.

Key differences from the prior state-file approach:
- State-file approach: asynchronous messaging via state files (immutable history, 1-way per phase)
- This module: agent_messages.json time-ordered queue + review/debate/peer-review protocols
                with multi-turn conversation support and enforced round limits

Token cost controls:
- ReviewRound: max 2 rounds (default)
- DebateRound: max 2 rounds (same pattern as Watchdog Pool)
- PeerReview: hop count <= 3 (same pattern as Handoff)
- Every interaction requires PM activation decision + Verifier post-hoc check
"""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict


def now_iso():
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# Constants
# ============================================================

INTERACTION_TYPES = {"review_round", "debate_round", "peer_review",
                     "interactive_factcheck", "iterative_refinement",
                     "standup_sync"}

DEFAULT_MAX_ROUNDS = 2
DEFAULT_MAX_HOPS = 3
DEFAULT_MAX_PARTICIPANTS = 5  # prevent token cost explosion


# ============================================================
# AgentMessageBus - Event Bus for Inter-Agent Communication
# ============================================================

class AgentMessageBus:
    """
    Time-ordered message queue between agents.

    Stored in state/agent_messages.json. All messages are immutable append-only
    so the audit trail is preserved. It is queue-shaped but history is retained.
    """

    def __init__(self, state_dir):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.file_path = self.state_dir / "agent_messages.json"
        self._load()

    def _load(self):
        if self.file_path.exists():
            with open(self.file_path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        else:
            self.data = {
                "version": 1,
                "created_at": now_iso(),
                "interactions": {},  # interaction_id -> metadata
                "messages": []        # all messages in time order
            }
            self._save()

    def _save(self):
        # Atomic write is recommended; this module is simplified (uses atomic write when integrated with state_manager)
        self.data["last_updated"] = now_iso()
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def start_interaction(self, interaction_type, participants, context=None,
                          max_rounds=DEFAULT_MAX_ROUNDS, max_hops=DEFAULT_MAX_HOPS):
        """
        Start a new interaction.

        Returns: interaction_id (UUID4)
        """
        if interaction_type not in INTERACTION_TYPES:
            raise ValueError(f"Invalid type: {interaction_type}. Must be {INTERACTION_TYPES}")
        if len(participants) > DEFAULT_MAX_PARTICIPANTS:
            raise ValueError(f"Too many participants: {len(participants)} > {DEFAULT_MAX_PARTICIPANTS}")

        interaction_id = str(uuid.uuid4())
        self.data["interactions"][interaction_id] = {
            "interaction_id": interaction_id,
            "type": interaction_type,
            "participants": participants,
            "started_at": now_iso(),
            "max_rounds": max_rounds,
            "max_hops": max_hops,
            "current_round": 0,
            "status": "active",
            "context": context or {},
            "termination_reason": None,
            "ended_at": None
        }
        self._save()
        return interaction_id

    def post_message(self, interaction_id, sender, content, round_num=None,
                     references=None, msg_type="message"):
        """
        Post a message into the interaction.

        Args:
            sender: sending agent (e.g., "worker_W1", "watchdog_pool_W2")
            content: message body (compressed essentials)
            round_num: round number (uses current round if None)
            references: referenced state files or other message IDs
            msg_type: "message" | "vote" | "question" | "answer" | "verdict"
        """
        interaction = self.data["interactions"].get(interaction_id)
        if not interaction:
            raise KeyError(f"Interaction {interaction_id} not found")
        if interaction["status"] != "active":
            raise RuntimeError(f"Interaction {interaction_id} is not active (status: {interaction['status']})")
        if sender not in interaction["participants"]:
            raise ValueError(f"Sender {sender} not in participants {interaction['participants']}")

        # Auto-advance round
        if round_num is None:
            round_num = interaction["current_round"]

        # Token control
        if round_num > interaction["max_rounds"]:
            raise RuntimeError(f"Round {round_num} exceeds max_rounds {interaction['max_rounds']}")

        message = {
            "message_id": f"msg_{len(self.data['messages']) + 1:04d}",
            "interaction_id": interaction_id,
            "sender": sender,
            "content": content,
            "round": round_num,
            "references": references or [],
            "type": msg_type,
            "timestamp": now_iso()
        }
        self.data["messages"].append(message)
        self._save()
        return message["message_id"]

    def advance_round(self, interaction_id):
        """Advance the round. Auto-terminates when max_rounds is reached."""
        interaction = self.data["interactions"].get(interaction_id)
        if not interaction:
            raise KeyError(f"Interaction {interaction_id} not found")
        new_round = interaction["current_round"] + 1
        if new_round > interaction["max_rounds"]:
            self.end_interaction(interaction_id, reason="max_rounds_reached")
            return interaction["current_round"]
        interaction["current_round"] = new_round
        self._save()
        return new_round

    def end_interaction(self, interaction_id, reason="completed", outcome=None):
        """End the interaction."""
        interaction = self.data["interactions"].get(interaction_id)
        if not interaction:
            raise KeyError(f"Interaction {interaction_id} not found")
        interaction["status"] = "ended"
        interaction["termination_reason"] = reason
        interaction["ended_at"] = now_iso()
        if outcome is not None:
            interaction["outcome"] = outcome
        self._save()

    def get_interaction_messages(self, interaction_id, round_num=None):
        """Query messages for a specific interaction (optional round filter)."""
        msgs = [m for m in self.data["messages"] if m["interaction_id"] == interaction_id]
        if round_num is not None:
            msgs = [m for m in msgs if m["round"] == round_num]
        return msgs

    def get_active_interactions(self):
        return [i for i in self.data["interactions"].values() if i["status"] == "active"]


# ============================================================
# ReviewRound Protocol (GroupChat pattern, 2-round limit)
# ============================================================

def initiate_review_round(bus, reviewers, target_artifact, max_rounds=2):
    """
    Start a round in which multiple reviewers review a single artifact.

    Use cases: multiple Workers reviewing each other's output (Worker peer review)
               Verifier reviewing along with the Watchdog Pool synthesis

    Round 1: each reviewer gives an independent opinion
    Round 2: re-review after seeing the others' opinions (optional, only if opinions are split)
    """
    interaction_id = bus.start_interaction(
        "review_round",
        participants=reviewers,
        context={"target_artifact": target_artifact, "purpose": "review"},
        max_rounds=max_rounds
    )
    return interaction_id


def reviewer_post_opinion(bus, interaction_id, reviewer, verdict, rationale,
                          confidence=None, references=None):
    """Reviewer submits an opinion."""
    content = {
        "verdict": verdict,  # APPROVE | REJECT | CONDITIONAL
        "rationale": rationale,
        "confidence": confidence
    }
    return bus.post_message(interaction_id, reviewer, content,
                            references=references, msg_type="vote")


def aggregate_review_outcomes(bus, interaction_id, current_round):
    """
    Aggregate opinions after the round ends.

    Returns: {verdict_distribution, consensus_method, recommend_next_round}
    """
    msgs = bus.get_interaction_messages(interaction_id, round_num=current_round)
    votes = [m["content"]["verdict"] for m in msgs if m.get("type") == "vote"]
    if not votes:
        return {"status": "no_votes_yet"}
    from collections import Counter
    cnt = Counter(votes)
    most_common, count = cnt.most_common(1)[0]
    total = len(votes)
    consensus_threshold = (total * 2 + 2) // 3  # ceil(2N/3)

    if len(set(votes)) == 1:
        return {"verdict_distribution": dict(cnt), "consensus": most_common,
                "method": "unanimous", "recommend_next_round": False}
    if count >= consensus_threshold:
        return {"verdict_distribution": dict(cnt), "consensus": most_common,
                "method": "majority", "recommend_next_round": False}
    # Split -> recommend round 2
    return {"verdict_distribution": dict(cnt), "consensus": "DISPUTED",
            "method": "split", "recommend_next_round": True}


# ============================================================
# DebateRound Protocol (generalization of the Watchdog Pool pattern)
# ============================================================

def initiate_debate_round(bus, debaters, claim, max_rounds=2):
    """
    Multiple agents debate around a single claim.

    Use cases: Worker A concludes X, Worker B concludes not-X -> attempt consensus via debate
               Adversarial Critic vs Worker (counter-scenario vs defense)
    """
    interaction_id = bus.start_interaction(
        "debate_round",
        participants=debaters,
        context={"claim": claim, "purpose": "debate"},
        max_rounds=max_rounds
    )
    return interaction_id


def debater_post_argument(bus, interaction_id, debater, position, argument,
                          counterargument_to=None):
    """Debater submits a position and argument."""
    content = {
        "position": position,  # SUPPORT | OPPOSE | CONDITIONAL
        "argument": argument,
        "counterargument_to": counterargument_to  # message ID being rebutted
    }
    references = [counterargument_to] if counterargument_to else None
    return bus.post_message(interaction_id, debater, content,
                            references=references, msg_type="argument")


# ============================================================
# PeerReview Protocol (Worker handoff extended into a review dimension)
# ============================================================

def initiate_peer_review_chain(bus, reviewer_chain, target_artifact, max_hops=3):
    """
    Sequential peer review Worker A -> B -> C (similar to handoff but for review).

    Use cases: a Worker hands off to another Worker to verify task results outside its own domain
               a Researcher hands a source's credibility to another Researcher for verification
    """
    interaction_id = bus.start_interaction(
        "peer_review",
        participants=reviewer_chain,
        context={"target_artifact": target_artifact, "purpose": "peer_review",
                 "chain_order": reviewer_chain},
        max_hops=max_hops
    )
    return interaction_id


def peer_review_handoff(bus, interaction_id, from_agent, to_agent, review_notes,
                         hop_count):
    """Peer review handoff."""
    if hop_count >= DEFAULT_MAX_HOPS:
        return {"accepted": False, "reason": f"max_hops_exceeded({hop_count})"}
    content = {
        "from": from_agent,
        "to": to_agent,
        "review_notes": review_notes,
        "hop_count": hop_count + 1
    }
    bus.post_message(interaction_id, from_agent, content,
                     msg_type="handoff_request")
    return {"accepted": True, "hop_count": hop_count + 1}


# ============================================================
# InteractiveFactCheck (Researcher <-> Watchdog conversation)
# ============================================================

def initiate_interactive_factcheck(bus, researcher, watchdog, claim_to_verify):
    """
    Upgrade the one-way watchdog_verdicts.json verification into an interactive dialog.

    Researcher: presents claim + sources
    Watchdog: responds with verdict + needs_clarification
    Researcher: supplies additional evidence
    Watchdog: final verdict

    Hard 2-round limit. Token cost controlled.
    """
    interaction_id = bus.start_interaction(
        "interactive_factcheck",
        participants=[researcher, watchdog],
        context={"claim": claim_to_verify, "purpose": "interactive_factcheck"},
        max_rounds=2
    )
    return interaction_id


# ============================================================
# IterativeRefinement (Adversarial Critic <-> Worker)
# ============================================================

def initiate_iterative_refinement(bus, worker, critic, target_artifact):
    """
    Adversarial Critic identifies vulnerabilities -> Worker refines -> Critic re-reviews.

    Implements an Actor-Evaluator-SelfReflection loop as an explicit dialog.
    """
    interaction_id = bus.start_interaction(
        "iterative_refinement",
        participants=[worker, critic],
        context={"target_artifact": target_artifact, "purpose": "iterative_refinement"},
        max_rounds=2
    )
    return interaction_id


# ============================================================
# StandupSync (PM + all agents, short status sync)
# ============================================================

def initiate_standup_sync(bus, pm, all_agents):
    """
    PM briefly syncs progress across all agents.
    Each agent posts a single message (status + blockers + needs).

    Restriction: 1 round only. PM only broadcasts.
    """
    interaction_id = bus.start_interaction(
        "standup_sync",
        participants=[pm] + all_agents,
        context={"purpose": "standup_sync"},
        max_rounds=1
    )
    return interaction_id


def agent_standup_report(bus, interaction_id, agent, status, blockers=None, needs=None):
    """Standup report."""
    content = {"status": status, "blockers": blockers or [], "needs": needs or []}
    return bus.post_message(interaction_id, agent, content, msg_type="standup")


# ============================================================
# Token Cost Estimation (operational visibility)
# ============================================================

def estimate_interaction_cost(interaction):
    """Estimate the token cost of an interaction (heuristic)."""
    # Simple estimate: number of messages * average length
    n_participants = len(interaction.get("participants", []))
    n_rounds = interaction.get("current_round", 0)
    msg_per_round = n_participants
    avg_tokens_per_msg = 300  # average for a compressed review/debate message
    estimated_cost = msg_per_round * n_rounds * avg_tokens_per_msg
    return {
        "estimated_tokens": estimated_cost,
        "n_participants": n_participants,
        "n_rounds": n_rounds,
        "vs_state_file_baseline": f"{estimated_cost / 1000:.1f}x state-file (baseline)"
    }


# ============================================================
# Gate Definitions
# ============================================================

INTERACTION_GATES = {
    "review_round_continue": {
        "phase": 3,
        "trigger": "Opinions split after round 1 (consensus split)",
        "decision_type": "direction",
        "options": ["proceed_to_round_2", "accept_majority", "abort_review"],
        "data_to_present": ["agent_messages.json"]
    },
    "peer_review_hop_limit": {
        "phase": 3,
        "trigger": "Peer review chain hop count >= MAX_HOPS",
        "decision_type": "direction",
        "options": ["force_consensus", "extend_chain", "fall_back_to_pm"],
        "data_to_present": ["agent_messages.json"]
    },
    "interaction_token_budget_breach": {
        "phase": 3,
        "trigger": "Interaction estimated token cost exceeds PM budget",
        "decision_type": "direction",
        "options": ["allow_breach", "halt_interaction", "switch_to_state_file_mode"],
        "data_to_present": ["agent_messages.json", "telemetry.json"]
    }
}


# ============================================================
# Self-test
# ============================================================

if __name__ == "__main__":
    import tempfile
    tmpdir = tempfile.mkdtemp()
    bus = AgentMessageBus(tmpdir)

    print("[Test 1] ReviewRound - 3 reviewers")
    iid = initiate_review_round(bus, ["worker_W1", "worker_W2", "worker_W3"],
                                 target_artifact="report.md")
    reviewer_post_opinion(bus, iid, "worker_W1", "APPROVE", "looks good", confidence=0.9)
    reviewer_post_opinion(bus, iid, "worker_W2", "APPROVE", "minor nits", confidence=0.85)
    reviewer_post_opinion(bus, iid, "worker_W3", "REJECT", "missing data", confidence=0.7)
    outcome = aggregate_review_outcomes(bus, iid, current_round=0)
    print(f"  outcome: {outcome}")

    print("\n[Test 2] DebateRound - 2 debaters")
    iid = initiate_debate_round(bus, ["adversarial_critic", "worker_W1"],
                                 claim="X causes Y")
    msg_id = debater_post_argument(bus, iid, "adversarial_critic", "OPPOSE",
                                    "correlation, not causation")
    debater_post_argument(bus, iid, "worker_W1", "SUPPORT",
                          "controlled experiment shows X->Y",
                          counterargument_to=msg_id)
    print(f"  messages: {len(bus.get_interaction_messages(iid))}")

    print("\n[Test 3] PeerReview chain")
    iid = initiate_peer_review_chain(bus, ["worker_W1", "worker_W2", "worker_W3"],
                                      target_artifact="analysis.md")
    result = peer_review_handoff(bus, iid, "worker_W1", "worker_W2",
                                  "domain expert needed", hop_count=0)
    print(f"  handoff: {result}")

    print("\n[Test 4] InteractiveFactCheck")
    iid = initiate_interactive_factcheck(bus, "researcher", "watchdog_W1",
                                          claim_to_verify="GDP 2025 = $30T")
    print(f"  iid: {iid}")

    print("\n[Test 5] Cost estimation")
    for iid_ in bus.data["interactions"].keys():
        cost = estimate_interaction_cost(bus.data["interactions"][iid_])
        print(f"  {iid_[:8]}: ~{cost['estimated_tokens']} tokens")

    print(f"\nState file: {bus.file_path}")
