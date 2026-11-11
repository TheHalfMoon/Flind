"""Rename the product name PostHog to Flind in prose (full rename stage 2).

Only text people read changes: Python strings, comments and docstrings; Markdown outside code; templates and
snapshots. TS/JS prose goes through rename_text_ts.cjs, which uses the TypeScript parser. Code identifiers
(PostHogConfig), module and package names, GitHub paths (PostHog/posthog) and the company name (PostHog Inc.) are
left alone: identifiers belong to later stages, and "Flind Inc." would claim a company that does not exist.

    python tools/flind/rename_text.py <file-list> <report>
"""

import io
import re
import sys
import tokenize
from pathlib import Path

WORD = re.compile(r"(?<![\w@./-])PostHog(?![\w/])(?!,? Inc\b)")
# Provenance, licensing and upstream records must keep naming PostHog truthfully.
EXEMPT_PREFIXES = (
    "LICENSE",
    "ee/LICENSE",
    "docs/flind/",
    "flind/rename/",
    "flind/upstream-sync/",
    "flind/source-registry/",
    "flind/qualification/",
    "products/legal_documents/",
    "frontend/src/mocks/fixtures/_billing",
    "tools/flind/",
    ".github/workflows/flind-rename-ratchet.yml",
)
PROSE_SUFFIXES = (".html", ".txt", ".ambr", ".snap", ".jinja", ".j2", ".hbs", ".mjml")
FENCE = re.compile(r"^(\s*)(```|~~~)")
INLINE_CODE = re.compile(r"(`+)(.+?)\1")


def rename(text: str) -> tuple[str, int]:
    return WORD.subn("Flind", text)


def python_file(text: str) -> tuple[str, int]:
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except (tokenize.TokenError, SyntaxError, IndentationError):
        return text, 0
    lines = text.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    prose = {tokenize.STRING, tokenize.COMMENT}
    prose |= {getattr(tokenize, n) for n in ("FSTRING_MIDDLE", "TSTRING_MIDDLE") if hasattr(tokenize, n)}
    spans = []
    for tok in tokens:
        if tok.type in prose and "PostHog" in tok.string:
            start = offsets[tok.start[0] - 1] + tok.start[1]
            end = offsets[tok.end[0] - 1] + tok.end[1]
            spans.append((start, end))
    out, last, total = [], 0, 0
    for start, end in sorted(spans):
        if start < last:
            continue
        out.append(text[last:start])
        piece, n = rename(text[start:end])
        out.append(piece)
        total += n
        last = end
    out.append(text[last:])
    return "".join(out), total


def markdown_file(text: str) -> tuple[str, int]:
    out, total, fenced = [], 0, None
    for line in text.splitlines(keepends=True):
        m = FENCE.match(line)
        if m:
            fenced = None if fenced == m.group(2) else (fenced or m.group(2))
            out.append(line)
            continue
        if fenced:
            out.append(line)
            continue
        parts, last = [], 0
        for code in INLINE_CODE.finditer(line):
            piece, n = rename(line[last : code.start()])
            parts += [piece, code.group(0)]
            total += n
            last = code.end()
        piece, n = rename(line[last:])
        parts.append(piece)
        total += n
        out.append("".join(parts))
    return "".join(out), total


def main() -> int:
    files = [l.strip() for l in open(sys.argv[1], encoding="utf-8") if l.strip()]
    report = []
    for f in files:
        if f.startswith(EXEMPT_PREFIXES):
            continue
        p = Path(f)
        try:
            text = p.read_bytes().decode("utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if "PostHog" not in text:
            continue
        if f.endswith(".py"):
            new, n = python_file(text)
        elif f.endswith((".md", ".mdx")):
            new, n = markdown_file(text)
        elif f.endswith(PROSE_SUFFIXES):
            new, n = rename(text)
        else:
            continue
        if n:
            p.write_bytes(new.encode("utf-8"))
            report.append(f"{n}\t{f}")
    Path(sys.argv[2]).write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"{len(report)} files changed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
