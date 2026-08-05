"""Generate API documentation pages and their flat index."""

from pathlib import Path
import subprocess
import sys


DOCS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = DOCS_DIR.parent
API_DIR = DOCS_DIR / "api"
PACKAGE_DIR = PROJECT_DIR / "src" / "nolito"
INDEX_PATH = API_DIR / "index.rst"


def main() -> None:
    API_DIR.mkdir(exist_ok=True)

    for path in API_DIR.glob("nolito*.rst"):
        path.unlink()

    subprocess.run(
        [
            sys.executable,
            "-m",
            "sphinx.ext.apidoc",
            "--separate",
            "--no-toc",
            "--force",
            "-o",
            str(API_DIR),
            str(PACKAGE_DIR),
        ],
        check=True,
    )

    # The package landing page duplicates the flat index's purpose.
    (API_DIR / "nolito.rst").unlink()
    modules = sorted(path.stem for path in API_DIR.glob("nolito.*.rst"))

    INDEX_PATH.write_text(
        "API reference\n"
        "=============\n"
        "\n"
        ".. toctree::\n"
        "   :maxdepth: 1\n"
        "\n"
        + "".join(f"   {module}\n" for module in modules),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
