"""Generate API documentation pages and their flat index."""

from dataclasses import fields, is_dataclass
from importlib import import_module
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
    for module in modules:
        excluded_members = dataclass_fields(module)
        if excluded_members:
            add_excluded_members(API_DIR / f"{module}.rst", excluded_members)

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


def dataclass_fields(module_name: str) -> list[str]:
    """Return fields that autodoc should not list separately from ``__init__``."""
    module = import_module(module_name)
    return sorted(
        field.name
        for member in vars(module).values()
        if is_dataclass(member)
        for field in fields(member)
    )


def add_excluded_members(path: Path, excluded_members: list[str]) -> None:
    """Exclude dataclass fields from autodoc's generated member list."""
    content = path.read_text(encoding="utf-8")
    content = content.replace(
        "   :members:\n",
        f"   :members:\n   :exclude-members: {', '.join(excluded_members)}\n",
        1,
    )
    path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
