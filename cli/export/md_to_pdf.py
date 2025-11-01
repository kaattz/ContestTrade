from __future__ import annotations

"""
Markdown → HTML → PDF export utilities.

Design goals
- Keep formatting close to Markdown defaults
- Pay special attention to list indentation (parent/child)
- Avoid external binaries; rely on Python-Markdown + WeasyPrint
"""

from pathlib import Path
from typing import Optional, Tuple
import re


def _default_css() -> str:
    """Default CSS tuned for Markdown semantics and proper list indentation."""
    # Note: Use common CJK-capable fonts on Windows/macOS/Linux where possible.
    # WeasyPrint supports a good subset of CSS2.1 and parts of CSS3.
    return r"""
    @page {
      size: A4;
      margin: 20mm 18mm 20mm 18mm;
    }

    html, body {
      font-family: "Microsoft YaHei", "Noto Sans CJK SC", "PingFang SC",
                   "Hiragino Sans GB", "Segoe UI", "Helvetica Neue",
                   Arial, sans-serif;
      font-size: 12pt;
      color: #222;
      line-height: 1.6;
    }

    .markdown-body {
      max-width: 100%;
      word-wrap: break-word;
    }

    h1, h2, h3, h4, h5, h6 {
      line-height: 1.25;
      margin: 1.2em 0 0.6em 0;
      font-weight: 700;
    }

    h1 { font-size: 1.8em; }
    h2 { font-size: 1.6em; }
    h3 { font-size: 1.4em; }
    h4 { font-size: 1.2em; }
    h5 { font-size: 1.05em; }
    h6 { font-size: 1.0em; color: #444; }

    p { margin: 0.6em 0; }

    /* List indentation: keep Markdown’s visual hierarchy */
    ul, ol {
      margin: 0.3em 0 0.6em 1.6em; /* left indent */
      padding-left: 0;             /* let margin handle indent */
      list-style-position: outside;
    }

    /* Extra indent for nested lists */
    .markdown-body li > ul,
    .markdown-body li > ol { margin-left: 2.0em; }

    /* Common pattern from legacy MD where an ordered list follows a bullet list */
    .markdown-body ul + ol { margin-left: 2.0em; }

    ul { list-style-type: disc; }
    ul ul { list-style-type: circle; }
    ul ul ul { list-style-type: square; }

    ol { list-style-type: decimal; }
    ol ol { list-style-type: lower-alpha; }
    ol ol ol { list-style-type: lower-roman; }

    li { margin: 0.2em 0; }
    li > p { margin: 0.2em 0; }

    /* Avoid awkward breaks inside list items/paragraphs */
    p, li { page-break-inside: avoid; }

    /* Tables */
    table { border-collapse: collapse; width: 100%; margin: 0.8em 0; }
    th, td { border: 1px solid #ddd; padding: 6px 8px; }
    thead th { background: #f7f7f7; }

    /* Code blocks */
    code, pre { font-family: Consolas, "Courier New", monospace; font-size: 0.95em; }
    pre { background: #f7f7f7; padding: 10px; border-radius: 4px; overflow: auto; }

    /* Images */
    img { max-width: 100%; height: auto; }
    """


def _normalize_nested_list_indents(md_text: str) -> str:
    """Normalize nested list indentation for known parent bullets.

    - 支撑证据 / Supporting Evidence: ensure child "1. ..." are 4-space indented
    - 风险提示 / Risk Warnings: ensure child "- ..." are 4-space indented
    Works even if a blank line exists between parent and children.
    """
    evidence_heads = (
        "- **支撑证据",
        "- **Supporting Evidence",
    )
    risk_heads = (
        "- **风险提示",
        "- **Risk Warnings",
    )

    lines = md_text.splitlines()
    out = []
    mode = None  # 'evidence' | 'risk' | None
    for line in lines:
        stripped = line.lstrip(" \t")
        if any(line.startswith(h) for h in evidence_heads):
            mode = 'evidence'
            out.append(line)
            continue
        if any(line.startswith(h) for h in risk_heads):
            mode = 'risk'
            out.append(line)
            continue

        if mode == 'evidence':
            if stripped == "":
                out.append(line)
                continue
            if re.match(r"\d+\.\s", stripped):
                out.append("    " + stripped)
                continue
            # Stop on a new top-level item or header
            if not line.startswith((" ", "\t")) or re.match(r"-\s+\*\*", stripped):
                mode = None
            out.append(line)
            continue

        if mode == 'risk':
            if stripped == "":
                out.append(line)
                continue
            if stripped.startswith("- "):
                out.append("    " + stripped)
                continue
            if not line.startswith((" ", "\t")) or re.match(r"-\s+\*\*", stripped):
                mode = None
            out.append(line)
            continue

        out.append(line)

    return "\n".join(out)


def _normalize_ol_sublist_indents(md_text: str) -> str:
    """Ensure `- ` bullet lines directly under numeric list items become nested.

    Many Markdown authors indent 1–3 spaces before `- ` under lines like
    `1. 标题：` which some parsers treat as separate lists. This normalizes by
    rewriting such `- ` lines to 4-space indented `- ` so they are children of
    the preceding ordered list item.
    """
    lines = md_text.splitlines()
    out = []
    in_ol = False
    for i, line in enumerate(lines):
        stripped = line.lstrip(" \t")
        # Enter ordered list item mode
        if re.match(r"^\s*\d+\.\s", line):
            in_ol = True
            out.append(line)
            continue

        if in_ol:
            # If blank line, keep and continue; remain in mode
            if stripped == "":
                out.append(line)
                continue
            # If next top-level ordered item, exit mode
            if re.match(r"^\s*\d+\.\s", line):
                in_ol = True  # start new item implicitly
                out.append(line)
                continue
            # If see a less-indented non-list line, exit mode gracefully
            if not line.startswith((" ", "\t")) and not stripped.startswith(("- ", "* ")):
                in_ol = False
                out.append(line)
                continue
            # If bullet with 1–3 leading spaces, make it 4 spaces
            m = re.match(r"^(\s{1,3})([-*])\s+", line)
            if m:
                out.append("    " + line[len(m.group(1)):])
                continue
            # Already nested or some other content
            out.append(line)
            continue

        out.append(line)

    return "\n".join(out)


def _ensure_blank_line_before_lists(md_text: str) -> str:
    """Insert a blank line before list starts if missing.

    Many Markdown parsers (including Python-Markdown) require a blank line
    between a paragraph and a following list. If the source omits it, the
    list may be rendered inline. This normalizes by inserting an empty line
    before any top-level list marker when the previous line is non-empty and
    not a list/heading.
    """
    lines = md_text.splitlines()
    out = []
    prev = ""
    list_re = re.compile(r"^\s*(?:\d+\.\s|[-*+]\s)")
    for line in lines:
        if list_re.match(line) and prev.strip() and not prev.lstrip().startswith(("- ", "* ", "+ ", "#", ">")):
            # Insert a blank line to start a proper list block
            out.append("")
        out.append(line)
        prev = line
    return "\n".join(out)


def markdown_to_html(
    md_text: str,
    *,
    title: Optional[str] = None,
    css: Optional[str] = None,
    extra_css: Optional[str] = None,
    normalize_ol_sublist: bool = False,
) -> str:
    """Convert Markdown text to a self-contained HTML document string.

    Uses python-markdown with sane defaults (tables, fenced_code, extra, sane_lists)
    and injects CSS for consistent rendering + proper list indentation.
    """
    import markdown  # Python-Markdown

    extensions = ["extra", "sane_lists", "tables", "fenced_code"]
    # Normalize nested lists for report-specific sections
    md_text = _normalize_nested_list_indents(md_text)
    if normalize_ol_sublist:
        md_text = _ensure_blank_line_before_lists(md_text)
        md_text = _normalize_ol_sublist_indents(md_text)

    body = markdown.markdown(md_text, extensions=extensions, output_format="html5")

    css_text = css if css is not None else _default_css()
    if extra_css:
        css_text = f"{css_text}\n\n/* Extra overrides */\n{extra_css}"
    page_title = title or "Report"

    html = f"""<!DOCTYPE html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{page_title}</title>
  <style>
  {css_text}
  </style>
  <meta http-equiv=\"X-UA-Compatible\" content=\"IE=edge\" />
</head>
<body>
  <article class=\"markdown-body\">{body}</article>
  </body>
</html>"""
    return html


def html_to_pdf(html: str, pdf_path: Path, *, base_url: Optional[Path] = None) -> None:
    """Render HTML to a PDF file using WeasyPrint.

    - html: Full HTML document string.
    - pdf_path: Output PDF path (will be created/overwritten).
    - base_url: Base directory for resolving relative resources (images, etc.).
    """
    from weasyprint import HTML

    pdf_path = Path(pdf_path)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    base = str(base_url) if base_url is not None else None
    HTML(string=html, base_url=base).write_pdf(str(pdf_path))


def export_markdown_to_pdf(
    md_path: Path | str,
    *,
    output_dir: Optional[Path] = None,
    html_filename: Optional[str] = None,
    pdf_filename: Optional[str] = None,
    title: Optional[str] = None,
    css: Optional[str] = None,
    extra_css: Optional[str] = None,
    normalize_ol_sublist: bool = False,
) -> Tuple[Path, Path]:
    """End-to-end export: Markdown file → HTML file → PDF file.

    Returns (html_path, pdf_path).
    """
    md_path = Path(md_path)
    if not md_path.exists():
        raise FileNotFoundError(f"Markdown file not found: {md_path}")

    output_dir = Path(output_dir) if output_dir else md_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    stem = md_path.stem
    html_name = html_filename or f"{stem}.html"
    pdf_name = pdf_filename or f"{stem}.pdf"

    html_path = output_dir / html_name
    pdf_path = output_dir / pdf_name

    md_text = md_path.read_text(encoding="utf-8")
    html = markdown_to_html(
        md_text,
        title=title or stem,
        css=css,
        extra_css=extra_css,
        normalize_ol_sublist=normalize_ol_sublist,
    )
    html_path.write_text(html, encoding="utf-8")

    # Resolve resources (e.g., images) relative to the Markdown file location
    base = md_path.parent
    html_to_pdf(html, pdf_path, base_url=base)

    return html_path, pdf_path
