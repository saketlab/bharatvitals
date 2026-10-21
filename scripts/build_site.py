"""Render README.md into the bharatvitals.in landing page.

Run from the repo root:
    uv run --project mcp --with markdown python scripts/build_site.py [out_dir]

Tool tables and llms.txt come from the server's own tool list.
"""

import asyncio
import html
import shutil
import sys
from pathlib import Path

import markdown
from fastmcp import Client

from bharatvitals.server import MODULES, mcp

SITE = "https://bharatvitals.in/"
MCP_URL = SITE + "mcp"
TITLE = "BharatVitals - India's health and demographic data over MCP"
LABELS = [m.LABEL for m in MODULES]
DESCRIPTION = (
    "A remote MCP server that lets Claude and other AI assistants query India's "
    f"official health and demographic statistics: {', '.join(LABELS[:-1])} and {LABELS[-1]}."
)
ASSETS = {
    "site/favicon.svg": "favicon.svg",
    "site/og-image.png": "og-image.png",
    "site/logo/logo.png": "site/logo/logo.png",  # README path, unchanged
    "site/logo/logo.svg": "logo.svg",
}
SOURCES = {m.SOURCE: m.LABEL for m in MODULES}

STYLE = """
:root { color-scheme: light dark; --fg:#1d1d1f; --bg:#fff; --muted:#6e6e73;
        --line:#d2d2d7; --link:#0071e3; --code-bg:#f5f5f7; }
@media (prefers-color-scheme: dark) {
  :root { --fg:#f5f5f7; --bg:#0d1117; --muted:#8b949e;
          --line:#30363d; --link:#5ac8fa; --code-bg:#161b22; }
}
* { box-sizing: border-box; }
body { max-width: 46rem; margin: 0 auto; padding: 3rem 1.25rem 5rem;
       background: var(--bg); color: var(--fg); line-height: 1.7;
       -webkit-font-smoothing: antialiased;
       font-family: "Albert Sans", -apple-system, BlinkMacSystemFont,
                    "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }
h1, h2, h3 { letter-spacing: -0.02em; line-height: 1.25; font-weight: 600; }
h1 { font-size: 2.25rem; margin: 0.5rem 0 0.25rem; text-align: center; }
h2 { font-size: 1.3rem; margin-top: 2.5rem; padding-bottom: 0.3rem;
     border-bottom: 1px solid var(--line); }
h3 { font-size: 1.05rem; margin-top: 1.75rem; }
a { color: var(--link); text-decoration: none; }
a:hover { text-decoration: underline; }
code { font-family: "SF Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
       font-size: 0.85em; background: var(--code-bg);
       padding: 0.1em 0.35em; border-radius: 0.25rem; }
pre { background: var(--code-bg); border: 1px solid var(--line);
      border-radius: 0.5rem; padding: 1rem; overflow-x: auto; }
pre code { background: none; padding: 0; font-size: 0.84rem; }
table { border-collapse: collapse; width: 100%; margin: 1.5rem 0; }
th, td { text-align: left; padding: 0.6rem 0.75rem; vertical-align: top;
         border-bottom: 1px solid var(--line); }
th { font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.06em;
     color: var(--muted); }
td:first-child { width: 42%; }
td code { word-break: break-all; }
p, li { overflow-wrap: anywhere; }
@media (max-width: 640px) {
  body { padding-top: 2rem; }
  table { display: block; overflow-x: auto; }
  th, td { padding: 0.5rem; }
}
img { max-width: 100%; }
.tagline { text-align: center; color: var(--muted); margin-top: 0; }
footer { margin-top: 4rem; padding-top: 1.25rem; border-top: 1px solid var(--line);
         font-size: 0.8125rem; color: var(--muted); }
"""

HEAD = f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{TITLE}</title>
<meta name="description" content="{DESCRIPTION}">
<meta name="keywords" content="BharatVitals, MCP, Model Context Protocol, India, \
public health, demography, {", ".join(LABELS)}, Claude">
<meta name="author" content="Saket Choudhary">
<link rel="canonical" href="{SITE}">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="alternate" type="text/plain" href="{SITE}llms.txt" title="llms.txt">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Albert+Sans:wght@400;600&display=swap">
<meta property="og:type" content="website">
<meta property="og:url" content="{SITE}">
<meta property="og:site_name" content="BharatVitals">
<meta property="og:title" content="{TITLE}">
<meta property="og:description" content="{DESCRIPTION}">
<meta property="og:image" content="{SITE}og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="BharatVitals">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">
{{"@context":"https://schema.org","@type":"SoftwareApplication","name":"BharatVitals",
 "applicationCategory":"DeveloperApplication","operatingSystem":"Any (MCP-compatible client)",
 "offers":{{"@type":"Offer","price":"0","priceCurrency":"INR"}},
 "description":"{DESCRIPTION}",
 "author":{{"@type":"Organization","name":"Saket Lab, IIT Bombay","url":"https://saketlab.org"}},
 "url":"{SITE}"}}
</script>
<style>{STYLE}</style>
</head><body>
"""

FOOT = """
<footer>BharatVitals is built by <a href="https://saketlab.org">Saket Lab, IIT Bombay</a>.
For LLMs: <a href="/llms.txt">llms.txt</a>.</footer>
</body></html>
"""

SITEMAP = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>{SITE}</loc></url>
</urlset>
"""

ROBOTS = f"User-agent: *\nAllow: /\nSitemap: {SITE}sitemap.xml\n"


def _list_tools() -> list[tuple[str, str]]:
    async def go() -> list[tuple[str, str]]:
        async with Client(mcp) as client:
            return [(t.name, t.description or "") for t in await client.list_tools()]

    return sorted(asyncio.run(go()))


def tools_html(tools: list[tuple[str, str]]) -> str:
    """One table per source, then the rest under Diagnostics: name and first docstring line."""
    groups: dict[str, list[tuple[str, str]]] = {}
    for name, desc in tools:
        groups.setdefault(SOURCES.get(name.split("_", 1)[0], "Diagnostics"), []).append(
            (name, desc)
        )
    parts = [f"<p>{len(tools)} tools:</p>"]
    for label in [*SOURCES.values(), "Diagnostics"]:
        rows = groups.get(label)
        if not rows:
            continue
        body = "\n".join(
            f"<tr><td><code>{n}</code></td>"
            f"<td>{html.escape((d.strip().splitlines() or [''])[0])}</td></tr>"
            for n, d in rows
        )
        parts.append(f"<h3>{label}</h3>\n<table>\n{body}\n</table>")
    return "\n".join(parts)


def llms_txt(tools: list[tuple[str, str]]) -> str:
    """Plain-text guide for LLMs: what the server is, how to connect, every tool."""
    lines = [
        "# BharatVitals",
        "",
        f"> {DESCRIPTION}",
        "",
        f"MCP endpoint (streamable HTTP, no auth): {MCP_URL}",
        f"Claude Code: claude mcp add --transport http bharatvitals {MCP_URL}",
        "",
        "## How to use the tools",
        "",
        mcp.instructions or "",
        "",
        'Multiple values are comma-separated, e.g. state="Kerala,Tamil Nadu".',
        "",
        "## Tools",
        "",
    ]
    for name, desc in tools:
        lines += [f"### {name}", "", desc.strip(), ""]
    return "\n".join(lines)


def build(root: Path, out_dir: Path) -> list[Path]:
    tools = _list_tools()
    readme = (root / "README.md").read_text()
    marker = "<!-- tools -->"
    if marker not in readme:
        raise ValueError(f"README.md lost its {marker} marker")
    missing = [label for label in LABELS if f"\n| {label}" not in readme]
    if missing:
        raise ValueError(f"README.md data table has no row for {', '.join(missing)}")
    body = markdown.markdown(readme, extensions=["tables", "fenced_code"])
    body = body.replace(marker, tools_html(tools))

    out_dir.mkdir(parents=True, exist_ok=True)
    written = {
        "index.html": HEAD + body + FOOT,
        "llms.txt": llms_txt(tools),
        "sitemap.xml": SITEMAP,
        "robots.txt": ROBOTS,
    }
    for name, text in written.items():
        (out_dir / name).write_text(text)
    for src, dst in ASSETS.items():
        (out_dir / dst).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / src, out_dir / dst)
    return [out_dir / n for n in [*written, *ASSETS.values()]]


if __name__ == "__main__":
    repo = Path(__file__).resolve().parent.parent
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else repo / "docs"
    for path in build(repo, target):
        print(f"wrote {path} ({path.stat().st_size} bytes)")
