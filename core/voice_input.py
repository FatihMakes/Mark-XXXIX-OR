ENGLISH_VOICE_INPUT_INSTRUCTION = (
    "The user primarily speaks English. For incoming microphone audio, "
    "prioritize recognizing English, including natural phrasing, contractions, "
    "and varied English accents. Preserve the words actually spoken, names, "
    "and technical terms; do not translate or silently rewrite them. The user "
    "may speak another language or switch languages. If the audio is genuinely "
    "unclear, ask a brief clarification instead of guessing."
)


def build_voice_system_instruction(
    time_context: str,
    memory_context: str,
    system_prompt: str,
) -> str:
    parts = [time_context]
    if memory_context:
        parts.append(memory_context)
    parts.extend((ENGLISH_VOICE_INPUT_INSTRUCTION, system_prompt))
    return "\n".join(parts)
