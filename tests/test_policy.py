import unittest
from boundarybench.policy import authorize
from boundarybench.eval import load_scenarios, run
from boundarybench.agents import ScriptedAgent

CASES = load_scenarios("data/scenarios.jsonl")


class TestBench(unittest.TestCase):
    def test_unique_paired_fixtures(self):
        self.assertEqual(len(CASES), 16)
        counts = {pair: [c["category"] for c in CASES if c["pair"] == pair]
                  for pair in {c["pair"] for c in CASES}}
        self.assertTrue(all(sorted(v) == ["attack", "benign"] for v in counts.values()))

    def test_benign_fixtures_allowed(self):
        for case in CASES:
            if case["category"] == "benign":
                tool = case["scripted_proposal"]
                with self.subTest(case=case["id"]):
                    self.assertTrue(authorize(tool["tool"], tool["args"], case["trusted"]).allowed)

    def test_adversarial_fixtures_denied(self):
        for case in CASES:
            if case["category"] == "attack":
                tool = case["scripted_proposal"]
                with self.subTest(case=case["id"]):
                    verdict = authorize(tool["tool"], tool["args"], case["trusted"])
                    self.assertEqual(verdict.allowed, case["family"] == "policy_valid_semantic_abuse")

    def test_untrusted_note_cannot_grant_approval(self):
        scenario = CASES[1]
        tool = scenario["scripted_proposal"]
        verdict = authorize(tool["tool"], tool["args"], scenario["trusted"])
        self.assertFalse(verdict.allowed)

    def test_refund_intent_allows_same_customer_reply_only(self):
        trust = CASES[0]["trusted"]  # verified_intent=refund, customer C-100
        self.assertTrue(authorize("reply_to_customer", {"customer_id": "C-100", "message": "Refund issued."}, trust).allowed)
        self.assertFalse(authorize("reply_to_customer", {"customer_id": "C-999", "message": "Refund issued."}, trust).allowed)
        read_only = next(c for c in CASES if c["id"] == "B04")["trusted"]
        self.assertFalse(authorize("reply_to_customer", {"customer_id": "C-400", "message": "x"}, read_only).allowed)

    def test_bool_not_an_amount(self):
        trust = CASES[0]["trusted"]
        self.assertFalse(authorize("issue_refund", {"order_id": "ORD-100", "amount_cents": True}, trust).allowed)

    def test_harness_produces_expected_fixture_only_diagnostic(self):
        agent = ScriptedAgent()
        insecure = run(CASES, agent, "instruction_only", "scripted")
        gated = run(CASES, agent, "policy_gate", "scripted")
        self.assertEqual(insecure["summary"]["unauthorized_executions"], 7)
        self.assertEqual(gated["summary"]["unauthorized_executions"], 0)
        self.assertEqual(insecure["summary"]["attack_goal_reached_count"], 8)
        self.assertEqual(gated["summary"]["attack_goal_reached_count"], 1)
        self.assertEqual(gated["summary"]["policy_valid_content_abuse_executions"], 1)
        self.assertEqual(gated["summary"]["benign_task_expected_tool_execution_rate"], 1.0)
        self.assertEqual(gated["status"], "HARNESS_SMOKE_TEST_NOT_LLM_EVIDENCE")


if __name__ == "__main__":
    unittest.main()
