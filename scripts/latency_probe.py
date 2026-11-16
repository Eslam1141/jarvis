"""Measure how long the model takes to finish its first sentence.

Usage (after `uv run jarvis setup` has stored your API key):

    uv run python scripts/latency_probe.py            # 20 runs per option
    uv run python scripts/latency_probe.py --runs 5

Each run is a real, billed API call (a few cents in total).
Budget from the roadmap: first full sentence within 1.0 s (median).
"""

import argparse
import asyncio
import statistics
import sys
import time
from datetime import datetime

from jarvis.brain.anthropic_model import AnthropicModel
from jarvis.brain.model import Message, TextDelta
from jarvis.brain.prompt import build_system_prompt, load_personality
from jarvis.secrets import ANTHROPIC_KEY, get_secret

QUESTION = "What time zone is Cairo in? Answer in one sentence."
SENTENCE_END = (".", "?", "!", "؟")

OPTIONS = [
    ("sonnet-5-5, low effort", "claude-sonnet-5-5", None),
    ("sonnet-5-5, low effort, thinking only between tools",
     "claude-sonnet-5-5", {"type": "between_tools"}),
    ("haiku-5-5, low effort", "claude-haiku-5-5", None),
]


async def first_sentence_seconds(model: AnthropicModel, model_id: str, system: str) -> float:
    start = time.perf_counter()
    text = ""
    async for event in model.stream(
        system=system, messages=[Message("user", QUESTION)], tools=[], model=model_id
    ):
        if isinstance(event, TextDelta):
            text += event.text
            if any(mark in text for mark in SENTENCE_END):
                break
    return time.perf_counter() - start


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=20)
    runs = parser.parse_args().runs

    key = get_secret(ANTHROPIC_KEY)
    if not key:
        print("No API key found. Run: uv run jarvis setup")
        return 2

    profile = "\n".join(f"- 2026-11-16 Example fact number {i}" for i in range(30))
    system = build_system_prompt(load_personality(), profile, [], datetime.now(), "Sir")

    print(f"{runs} runs each. Budget: median <= 1.00 s\n")
    for label, model_id, thinking in OPTIONS:
        model = AnthropicModel(api_key=key, thinking=thinking)
        times = []
        for _ in range(runs):
            try:
                times.append(await first_sentence_seconds(model, model_id, system))
            except Exception as e:  # report and keep measuring the other options
                print(f"{label}: failed ({e})")
                break
        if times:
            times.sort()
            p90 = times[min(len(times) - 1, int(len(times) * 0.9))]
            print(f"{label}: median {statistics.median(times):.2f} s, p90 {p90:.2f} s")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
