# ai_client.py
from typing import Optional
import requests
from config import PERPLEXITY_API_KEY

PPLX_URL = "https://api.perplexity.ai/chat/completions"


class PerplexityError(Exception):
    pass


def is_enabled() -> bool:
    return PERPLEXITY_API_KEY is not None and PERPLEXITY_API_KEY.strip() != ""


def get_movie_insights(title: str, plot: str) -> str:
    if not is_enabled():
        return "Perplexity API key not configured. Add PERPLEXITY_API_KEY in your .env to enable AI insights."

    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    prompt = (
        f"Give a short, fun summary, trivia, and 3 similar movie recommendations for the movie. Don't use any fancy markdown formats"
        f"'{title}'. Here is the plot:\n\n{plot}\n\n"
        f"Format your answer as:\n"
        f"- Short summary\n- Trivia bullets\n- Recommended movies"
    )

    payload = {
        "model": "sonar",  # or sonar-pro if you have access
        "messages": [
            {"role": "system", "content": "You are a friendly movie expert."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.5,
        "max_tokens": 512,
        "stream": False,
    }

    resp = requests.post(PPLX_URL, headers=headers, json=payload)
    data = resp.json()
    if resp.status_code != 200:
        msg = data.get("error", {}).get("message", "Perplexity API error")
        raise PerplexityError(msg)

    # standard chat completion shape
    try:
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        raise PerplexityError(f"Unexpected API response: {e}")
