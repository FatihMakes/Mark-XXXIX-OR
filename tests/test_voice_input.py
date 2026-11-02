import unittest

from core.voice_input import (
    ENGLISH_VOICE_INPUT_INSTRUCTION,
    build_voice_system_instruction,
)


class VoiceInputInstructionTests(unittest.TestCase):
    def test_instruction_prioritizes_english_without_rewriting_speech(self):
        instruction = ENGLISH_VOICE_INPUT_INSTRUCTION.lower()

        self.assertIn("primarily speaks english", instruction)
        self.assertIn("varied english accents", instruction)
        self.assertIn("preserve the words actually spoken", instruction)
        self.assertIn("do not translate", instruction)
        self.assertIn("ask a brief clarification instead of guessing", instruction)

    def test_system_instruction_keeps_context_and_omits_empty_memory(self):
        instruction = build_voice_system_instruction(
            "Current time context.",
            "",
            "Existing assistant rules.",
        )

        self.assertTrue(instruction.startswith("Current time context."))
        self.assertIn(ENGLISH_VOICE_INPUT_INSTRUCTION, instruction)
        self.assertTrue(instruction.endswith("Existing assistant rules."))
        self.assertNotIn("\n\n", instruction)

    def test_system_instruction_keeps_memory_context(self):
        instruction = build_voice_system_instruction(
            "Current time context.",
            "User memory.",
            "Existing assistant rules.",
        )

        self.assertLess(
            instruction.index("User memory."),
            instruction.index(ENGLISH_VOICE_INPUT_INSTRUCTION),
        )


if __name__ == "__main__":
    unittest.main()
