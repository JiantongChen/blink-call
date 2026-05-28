from pathlib import Path


def on_page_markdown(markdown, **kwargs):
    version_file = Path(__file__).resolve().parent.parent / "VERSION"
    version = version_file.read_text(encoding="utf-8").strip()
    return markdown.replace("{{ blink_call_version }}", version)
