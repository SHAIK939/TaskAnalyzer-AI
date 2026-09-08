import os
import time
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()

SYSTEM_INSTRUCTION = """You are TaskAnalyzer, a helpful AI workspace assistant.
Be accurate, practical, and well structured. Use headings and bullets when useful.
If the user uploads a file, answer from the file and clearly say when information is not present.
Do not claim to have performed actions you did not perform."""


@lru_cache(maxsize=1)
def get_client():
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY_2")
    if not api_key:
        raise RuntimeError("Gemini API key is missing. Add GEMINI_API_KEY to your .env file.")
    from google import genai
    return genai.Client(api_key=api_key)


def get_model_name():
    return os.getenv("GEMINI_MODEL", "gemini-3.6-flash")


def compact_history(messages, max_messages=12, max_chars=24000):
    """Keep recent context bounded so every chat does not grow indefinitely."""
    selected = messages[-max_messages:]
    result = []
    total = 0
    for m in reversed(selected):
        content = (m.get("content") or "").strip()
        if not content:
            continue
        if total + len(content) > max_chars:
            content = content[: max(0, max_chars-total)]
        if content:
            result.append({"role": m.get("role"), "content": content})
            total += len(content)
        if total >= max_chars:
            break
    return list(reversed(result))


def _contents(history, prompt):
    parts = [SYSTEM_INSTRUCTION]
    for item in compact_history(history):
        role = "model" if item["role"] == "assistant" else "user"
        parts.append(f"{role.upper()}: {item['content']}")
    parts.append(f"USER: {prompt}")
    return "\n\n".join(parts)


def _call(contents):
    client = get_client()
    last_error = None
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=get_model_name(),
                contents=contents,
            )
            text = getattr(response, "text", None)
            if text:
                return True, text
            return False, "The AI returned an empty response."
        except Exception as exc:
            last_error = exc
            time.sleep(1.5 * (attempt + 1))
    return False, f"AI request failed after retries: {last_error}"


def generate_response(user_message, conversation_history=None):
    try:
        return _call(_contents(conversation_history or [], user_message))
    except Exception as exc:
        return False, str(exc)


def analyze_file(user_message, uploaded_file, conversation_history=None):
    """Multimodal request. Uses one bounded history + current file."""
    try:
        client = get_client()
        history_text = _contents(conversation_history or [], user_message)
        file_bytes = uploaded_file.getvalue()
        mime_type = uploaded_file.type or "application/octet-stream"

        # Guard accidental massive uploads.
        if len(file_bytes) > 15 * 1024 * 1024:
            return False, "This file is too large for direct analysis. Please upload a file under 15 MB."

        from google.genai import types
        prompt_part = types.Part.from_text(text=history_text)
        file_part = types.Part.from_bytes(data=file_bytes, mime_type=mime_type)

        last_error = None
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=get_model_name(),
                    contents=[prompt_part, file_part],
                )
                text = getattr(response, "text", None)
                if text:
                    return True, text
                return False, "The AI could not analyze this file."
            except Exception as exc:
                last_error = exc
                time.sleep(1.5 * (attempt + 1))
        return False, f"File analysis failed after retries: {last_error}"
    except Exception as exc:
        return False, str(exc)
