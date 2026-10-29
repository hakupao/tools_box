"""Output path planning and input file expansion."""
from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path


def plan_output(
    source: Path,
    *,
    new_name: str,
    output_dir: Path | None = None,
    overwrite_source: bool = False,
) -> Path:
    """Return a non-conflicting output path (or ``source`` when overwriting)."""
    if overwrite_source:
        return source
    directory = Path(output_dir) if output_dir is not None else source.parent
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / new_name
    if not target.exists():
        return target
    stem, suffix = Path(new_name).stem, Path(new_name).suffix
    counter = 1
    while True:
        candidate = directory / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def iter_input_files(
    paths: Iterable[Path], extensions: tuple[str, ...], recursive: bool = False
) -> list[Path]:
    """Expand files/folders into matching files; skips lock files and missing paths."""
    exts = {e.lower() for e in extensions}
    result: list[Path] = []
    seen: set[Path] = set()

    def accept(file: Path) -> None:
        if file.name.startswith("~$") or file.suffix.lower() not in exts:
            return
        key = file.resolve()
        if key in seen:
            return
        seen.add(key)
        result.append(file)

    for raw in paths:
        path = Path(raw)
        if path.is_file():
            accept(path)
        elif path.is_dir():
            walker = path.rglob("*") if recursive else path.iterdir()
            files = [p for p in walker if p.is_file()]
            for file in sorted(files, key=lambda p: (p.parent.as_posix(), p.name)):
                accept(file)
    return result
