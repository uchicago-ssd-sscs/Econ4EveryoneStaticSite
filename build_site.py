"""Extract each activity zip's index.html into site/<slug>/ and build site/index.html from the manifests."""
import hashlib
import html
import json
import re
import sys
import zipfile
from pathlib import Path

src = Path(sys.argv[1])
out = src / "site"
SKIP = {"closed-for-the-holiday.zip"}  # superseded by closed-for-the-holiday-coursera-plugin.zip (v1.1.0)


def slugify(zip_name: str) -> str:
    s = zip_name[:-4].lower()
    s = s.replace(" (1)", "").replace("&", "-and-").replace("$", "")
    s = re.sub(r"[-_](coursera[-_])?(e4e[-_])?plugin$", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


# Researchers asked that the site stay out of search engines. robots.txt can't be used on a
# GitHub Pages project site (it's only read at the domain root), so every page gets this tag.
NOINDEX = b'<meta name="robots" content="noindex, nofollow">'


def add_noindex(page: bytes, source: str) -> bytes:
    if re.search(rb'<meta[^>]+name=["\']?robots', page, re.I):
        raise SystemExit(f"{source}: index.html already has a robots meta tag; check it by hand")
    new, n = re.subn(rb"<head(\s[^>]*)?>", lambda m: m.group(0) + b"\n" + NOINDEX, page, count=1, flags=re.I)
    if n != 1:
        raise SystemExit(f"{source}: no <head> tag found in index.html, can't add noindex")
    return new


out.mkdir(exist_ok=True)
seen_hashes = set()
entries = []
for z in sorted(src.glob("*.zip")):
    if z.name in SKIP:
        continue
    digest = hashlib.md5(z.read_bytes()).hexdigest()
    if digest in seen_hashes:
        continue
    seen_hashes.add(digest)
    slug = slugify(z.name)
    dest = out / slug
    dest.mkdir(exist_ok=True)
    with zipfile.ZipFile(z) as zf:
        (dest / "index.html").write_bytes(add_noindex(zf.read("index.html"), z.name))
        # manifest.json is Coursera-only metadata (and includes the maintainer's email), so it's
        # read for the index card but not published.
        m = json.loads(zf.read("manifest.json").decode("utf-8"))
    entries.append({"slug": slug, "name": m.get("name", slug),
                    "description": m.get("description", ""), "version": m.get("version", ""),
                    "source": z.name})

entries.sort(key=lambda e: re.sub(r"^the\s+", "", e["name"].lower()))

cards = "\n".join(
    f"""      <li class="card">
        <a href="{html.escape(e['slug'])}/">
          <h2>{html.escape(e['name'])}</h2>
          <p>{html.escape(e['description'])}</p>
          <span class="meta">v{html.escape(e['version'])}</span>
        </a>
      </li>"""
    for e in entries
)

page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex, nofollow">
  <title>Economics for Everyone: Interactive Activities</title>
  <style>
    :root {{
      --bg: #f7f7f5; --fg: #1d1d1f; --muted: #5f6368; --card: #fff;
      --border: #e2e2de; --accent: #800000;
    }}
    @media (prefers-color-scheme: dark) {{
      :root {{ --bg: #17181a; --fg: #ececec; --muted: #a0a4a8; --card: #222326;
              --border: #34363a; --accent: #e07a7a; }}
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font: 16px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
           background: var(--bg); color: var(--fg); }}
    header, main {{ max-width: 1100px; margin: 0 auto; padding: 0 1.25rem; }}
    header {{ padding-top: 3rem; padding-bottom: 1.5rem; }}
    h1 {{ margin: 0 0 .4rem; font-size: 2rem; }}
    header p {{ margin: 0; color: var(--muted); }}
    ul {{ list-style: none; margin: 0; padding: 0 0 3rem;
          display: grid; gap: 1rem; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); }}
    .card a {{ display: flex; flex-direction: column; height: 100%; padding: 1.25rem;
               background: var(--card); border: 1px solid var(--border); border-radius: 10px;
               color: inherit; text-decoration: none; transition: border-color .15s, transform .15s; }}
    .card a:hover, .card a:focus-visible {{ border-color: var(--accent); transform: translateY(-2px); }}
    .card a:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
    .card h2 {{ margin: 0 0 .5rem; font-size: 1.1rem; color: var(--accent); }}
    .card p {{ margin: 0 0 1rem; color: var(--muted); font-size: .95rem; flex: 1; }}
    .meta {{ font-size: .8rem; color: var(--muted); }}
  </style>
</head>
<body>
  <header>
    <h1>Economics for Everyone</h1>
    <p>Interactive activities &middot; {len(entries)} available</p>
  </header>
  <main>
    <ul>
{cards}
    </ul>
  </main>
</body>
</html>
"""
(out / "index.html").write_text(page, encoding="utf-8")
for e in entries:
    print(f"{e['slug']:45} <- {e['source']}")
