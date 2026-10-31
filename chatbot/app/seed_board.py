"""Seed the gap board before a demo, so it isn't empty.

These are questions our team asks. They go through the same path as the panel (the "before" answer
into gaps.record(), chat messages skipped), so they count as "questions asked today", and the board's
caption says that the counts include our team's test questions. Nothing here targets the entries our
survey repaired: they're ordinary founder questions.

Run once on the demo laptop:  .venv/bin/python chatbot/app/seed_board.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from chatbot.core.answer import answer  # noqa: E402
from chatbot.core.gaps import record  # noqa: E402

QUESTIONS = [
    "pre-seed AI fund for MIT alumni",
    "investors in Springfield",
    "wet-lab space in Worcester",
    "startup programs in Worcester",
    "GPU credits for an early-stage startup",
    "healthcare AI accelerator in Boston",
    "angel investors for a seed-stage robotics startup",
    "coworking space in Cambridge",
    "equity-free grants for climate tech",
    "mentors for a first-time founder",
    "AI meetups in Boston",
    "lab space for a biotech startup in Cambridge",
    "university AI research centers",
    "venture firms that invest in enterprise AI",
    "student founder programs at Northeastern",
]


def main():
    sent = 0
    for q in QUESTIONS:
        ans = answer(q, "before")  # the panel records the before answer (Contract 3)
        if ans.get("kind") != "chat":
            record(ans)
            sent += 1
    print(f"Asked {len(QUESTIONS)} questions and sent {sent} to record(). It stores only the gaps "
          "someone could fix, so the ledger may have fewer rows.")


if __name__ == "__main__":
    main()
