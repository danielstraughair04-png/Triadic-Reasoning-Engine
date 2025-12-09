# ============================================================
# TRIADIC AGENT v7.0 — STRICT PHYSICAL + SANITIZED EXPLANATION
# ============================================================

import os
import re
import requests
from dataclasses import dataclass
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
print("DEBUG API KEY loaded:", bool(OPENROUTER_API_KEY))

# ============================================================
# QUERY / TOPIC UNDER TEST
# ============================================================
# Change this line to test different topics
topic = "How a black hole evaporates through Hawking radiation."


# ============================================================
# DATA STRUCTURES
# ============================================================

@dataclass
class TriadicResult:
    topic: str
    explanation: str
    negative: List[str]
    neutral: List[str]
    positive: List[str]
    diagnostics: List[str]


# ============================================================
# MODEL WRAPPER
# ============================================================

class TriadicAgent:

    def __init__(self):
        if not OPENROUTER_API_KEY:
            raise ValueError("Missing OPENROUTER_API_KEY")

    def call(self, model: str, prompt: str, max_tokens: int = 500):
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        body = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": max_tokens
        }
        try:
            r = requests.post(url, json=body, headers=headers).json()
            return r["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print("MODEL ERROR:", e)
            return ""


    # ========================================================
    # EXPLANATION SANITIZER (v7.0)
    # ========================================================
    def sanitize_explanation(self, explanation: str) -> str:

        # remove incomplete final sentence (common with some models)
        explanation = re.sub(r"\b\w+$", "", explanation).strip()

        # enforce final period
        if not explanation.endswith("."):
            explanation += "."

        # collapse multiline into single string
        lines = [l.strip() for l in explanation.split("\n") if l.strip()]
        clean = " ".join(lines)

        # strip conceptual / subjective fluff
        banned = [
            "perceive", "interpreted", "heard as", "listener", "music",
            "emotion", "harmony", "experience", "sensation"
        ]
        for b in banned:
            clean = clean.replace(b, "")

        return clean.strip()


    # ========================================================
    # EXPLANATION GENERATION (DeepSeek R1)
    # ========================================================
    def build_explanation(self, topic: str) -> str:
        prompt = f"""
Explain the topic below in 3–6 sentences using ONLY physical causality:

\"\"\"{topic}\"\"\"

No metaphor, no interpretation, no subjective description.
Pure physical sequence of events.
"""
        raw = self.call("deepseek/deepseek-r1", prompt)
        return self.sanitize_explanation(raw)


    # ========================================================
    # NEGATIVE EXTRACTION (STRICT PHYSICAL)
    # ========================================================
    def extract_negative(self, explanation: str) -> List[str]:
        prompt = f"""
Extract ONLY the physical initial components that exist BEFORE any process begins.

Rules:
- MUST be concrete objects, particles, energies, or measurable physical states.
- NO actions, NO processes, NO outcomes.
- NO abstract nouns (like "disturbance", "propagation", "region", "speed").
- 4–10 items MAX.
- Very strict physical filtering.

EXPLANATION:
\"\"\"{explanation}\"\"\"

Output as a simple list, one item per line.
"""
        raw = self.call("openai/gpt-4o-mini", prompt)
        items = [l.strip(" -*•\t").lower() for l in raw.splitlines() if l.strip()]

        # HARD FILTER TO ENSURE STRICT PHYSICAL COMPONENTS
        banned = [
            "wave", "propagation", "disturbance", "region",
            "pattern", "flow", "motion", "compression",
            "rarefaction", "nearby", "neighboring", "process",
            "interaction"
        ]

        clean = []
        for item in items:
            if any(b in item for b in banned):
                continue
            # over-long phrases are usually explanations, not components
            if len(item.split()) > 3:
                continue

            # filter out some "pure property" words when they appear alone
            property_keywords = ["density", "energy", "force"]
            if any(pk == item or (pk + " " in item) for pk in property_keywords):
                continue

            clean.append(item)

        return clean[:10]


    # ========================================================
    # NEUTRAL INTERACTIONS (DeepSeek R1)
    # ========================================================
    def extract_neutral(self, negative: List[str]) -> List[str]:

        neg_list = "\n".join(f"- {n}" for n in negative)

        prompt = f"""
Generate 4–8 NEUTRAL mechanisms describing HOW these physical components interact.

Rules:
- One sentence per line.
- Must reference AT LEAST TWO items from the NEGATIVE list.
- Pure causal mechanisms.
- No outcomes.
- No future consequences.

NEGATIVE LIST:
{neg_list}

Write only the mechanisms.
"""
        raw = self.call("deepseek/deepseek-r1", prompt)
        return [l.strip().rstrip(".") + "." for l in raw.splitlines() if l.strip()]


    # ========================================================
    # POSITIVE STATES (Realization Filter)
    # ========================================================
    def extract_positive(self, neutral: List[str]) -> List[str]:

        neu_list = "\n".join(f"- {n}" for n in neutral)

        prompt = f"""
Transform each NEUTRAL mechanism into a REALIZED STATE.

Rules:
- One item per line.
- MUST be either:
    (a) pure noun phrase, OR
    (b) passive-perfect realized condition ("is established", "is stabilized", "is present", "is formed", "is maintained").
- NO high-level causal verbs: no creates, leads to, results in, causes, produces.
- MUST represent a completed physical condition that exists AFTER the mechanism.
- DO NOT restate or paraphrase the neutral mechanism word-for-word.
- Prefer stable state descriptions like "a region of X is present", "Y is established", "Z pattern exists".

NEUTRAL MECHANISMS:
{neu_list}

Output one realized state per line, same order.
"""
        raw = self.call("openai/gpt-4o-mini", prompt)
        items = [l.strip(" -*•\t") for l in raw.splitlines() if l.strip()]

        # Light filter: only remove obviously causal/meta lines
        banned_verbs = [
            "creates", "leads to", "results in", "causes", "produces"
        ]

        clean = []
        for it in items:
            lower = it.lower()
            if any(b in lower for b in banned_verbs):
                continue
            clean.append(it)

        # keep alignment with neutral list length
        return clean[:len(neutral)]


    # ========================================================
    # DIAGNOSTICS
    # ========================================================
    def analyze(self, neg, neu, pos):
        out = []
        if not neg:
            out.append("NEGATIVE extraction failed.")
        if not neu:
            out.append("NEUTRAL extraction failed.")
        if not pos:
            out.append("POSITIVE extraction failed.")
        if len(neu) != len(pos):
            out.append("NEU/POS mismatch.")
        return out


    # ========================================================
    # RUN TRIAD
    # ========================================================
    def run(self, topic: str) -> TriadicResult:

        explanation = self.build_explanation(topic)
        negative = self.extract_negative(explanation)
        neutral = self.extract_neutral(negative)
        positive = self.extract_positive(neutral)

        diags = self.analyze(negative, neutral, positive)

        return TriadicResult(topic, explanation, negative, neutral, positive, diags)



# ============================================================
# EXECUTION
# ============================================================
if __name__ == "__main__":
    agent = TriadicAgent()
    result = agent.run(topic)

    print("===== TRIADIC AGENT v7.0 =====")
    print("TOPIC:", result.topic, "\n")
    print("EXPLANATION:", result.explanation, "\n")

    print("NEGATIVE — INITIAL STATES:")
    for n in result.negative:
        print(" ", n)

    print("\nNEUTRAL — INTERACTIONS:")
    for n in result.neutral:
        print(" ", n)

    print("\nPOSITIVE — REALIZED STATES:")
    for p in result.positive:
        print(" ", p)

    print("\nDIAGNOSTICS:")
    for d in result.diagnostics:
        print(" ", d)
