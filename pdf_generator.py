"""Generate the Project Alpha technical report PDF from its Markdown source."""
from pathlib import Path
from typing import Optional

from backend.core.pdf_generator import generate_pdf_from_markdown


PROJECT_ROOT = Path(__file__).resolve().parent
SOURCE_PATH = PROJECT_ROOT / "workspace" / "Project_Alpha_Technical_Report.md"
OUTPUT_PATH = PROJECT_ROOT / "workspace" / "Project_Alpha_Technical_Report.pdf"


def generate_report(source_path: Path = SOURCE_PATH, output_path: Path = OUTPUT_PATH) -> Path:
    """Read the Markdown report and write a formatted PDF beside it."""
    source_path = Path(source_path)
    output_path = Path(output_path)

    if not source_path.is_file():
        raise FileNotFoundError(f"Markdown source not found: {source_path}")

    markdown_content = source_path.read_text(encoding="utf-8")
    return generate_pdf_from_markdown(markdown_content, output_path)


def main() -> Optional[Path]:
    """Generate the report and print the resulting path for command-line use."""
    output_path = generate_report()
    print(f"[OK] PDF report generated: {output_path}")
    return output_path


if __name__ == "__main__":
    main()