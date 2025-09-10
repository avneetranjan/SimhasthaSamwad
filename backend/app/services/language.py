from langdetect import detect, DetectorFactory


# Ensure deterministic results
DetectorFactory.seed = 0


def detect_language(text: str) -> str:
    try:
        return detect(text)
    except Exception:
        return "unknown"

