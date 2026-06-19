from pathlib import Path


def load_prompt(name: str) -> str:
    path = Path(__file__).parent / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8").strip()
