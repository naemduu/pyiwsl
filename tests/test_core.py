import re
from pathlib import Path

def test_version_matches_pyproject(capsys):
    root = Path(__file__).resolve().parents[1]
    text = (root / "pyproject.toml").read_text(encoding="utf-8")

    def find_version_in_section(section_header: str) -> str | None:
        m = re.search(
            rf"(?ms)^\[{re.escape(section_header)}\]\s*(.*?)(?=^\[|\Z)",
            text,
        )
        if not m:
            return None
        block = m.group(1)
        lines = []
        for line in block.splitlines():
            line = line.split("#", 1)[0].strip()
            if line:
                lines.append(line)
        block = "\n".join(lines)
        mv = re.search(r'(?m)^\s*version\s*=\s*"([^"]+)"\s*$', block)
        return mv.group(1) if mv else None
    pyproject_version = (
        find_version_in_section("project")
        or find_version_in_section("tool.poetry")
    )
    assert pyproject_version is not None, "no [version] in pyproject.toml"

    from pyiwsl import hello
    hello()
    out = capsys.readouterr().out
    m = re.search(r"\bpyiwsl\s+v+([0-9]+(?:\.[0-9]+){1,3})\b", out, re.IGNORECASE)
    assert m, f"no version in hello() out: {out!r}"
    hello_version = m.group(1)
    assert hello_version == pyproject_version, (
        f"Version mismatch: hello()={hello_version}, pyproject.toml={pyproject_version}"
    )
