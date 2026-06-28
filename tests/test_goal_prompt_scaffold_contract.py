from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCAFFOLD = ROOT / "skills" / "goal-prompt" / "references" / "prompt-scaffold.md"


class GoalPromptScaffoldContractTest(unittest.TestCase):
    def test_verify_judge_abstentions_are_pending_and_rerun(self):
        text = SCAFFOLD.read_text(encoding="utf-8")

        required_fragments = [
            "Abstention handling",
            "null / errored / rate-limited",
            "ABSTENTION, not a verdict",
            "PENDING",
            "RE-RUN",
            "`.catch(() => null)` plus `filter(Boolean)`",
        ]

        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)

    def test_scaffold_keeps_three_state_judge_pattern(self):
        text = SCAFFOLD.read_text(encoding="utf-8")

        self.assertIn("state: 'pending'", text)
        self.assertIn(".catch(() => ({it, state: 'pending'}))", text)
        forbidden = "`.catch(() => null)` plus `filter(Boolean)`"
        forbidden_index = text.find(forbidden)

        self.assertNotEqual(forbidden_index, -1)
        self.assertIn("never", text[max(0, forbidden_index - 80) : forbidden_index])
