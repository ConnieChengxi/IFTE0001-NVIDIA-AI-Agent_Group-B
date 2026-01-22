# src/llm_report.py
import os
from openai import OpenAI

def generate_llm_summary(metrics: dict, strategy_desc: str) -> str:
    """
    Uses the OpenAI Responses API to generate a short, report-ready narrative
    based on your strategy description + computed metrics.
    """
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is not set. On macOS run:\n"
            "export OPENAI_API_KEY='your_key_here'"
        )

    client = OpenAI()

    prompt = f"""
Write a concise MSc-level 'Results + Discussion' narrative (2–4 short paragraphs)
for a technical trading strategy.

Strategy (plain English):
{strategy_desc}

Metrics:
{metrics}

Writing style requirements:
- sound like a human student (not robotic)
- be specific about what the metrics imply
- include 2–3 limitations (e.g., regime dependence, parameter sensitivity, transaction costs, using one stock)
- no hype, no guarantees, no “this proves” language
"""

    response = client.responses.create(
        model="gpt-4o-mini",
        input=prompt,
    )

    return response.output_text


def save_llm_summary(text: str, out_path: str = "outputs/llm_summary.md") -> None:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text.strip() + "\n")
