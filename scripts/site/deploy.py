"""Deploy the static site to the web root with cache busting (docs/ARCHITECTURE.md, "Живий сайт").

Cloudflare tells browsers to keep JS, CSS and SVG files for 4 hours, so a plain copy leaves a visitor with old scripts
next to a new page. The deployed HTML pages therefore get every stylesheet, script and icon URL with ?v=<content hash>
and an import map that does the same for every JS module, so static and dynamic imports both load the new files. The
repo files stay plain, so the local server keeps working. Only what is committed goes live (git archive of HEAD), never
a file an agent is still editing; a scene listed in scenes/index.js whose file is not committed yet is left out of the
deployed list. api/ (written by the live cycle) and dev/ are never touched.

    .venv/bin/python -I scripts/site/deploy.py [--out /var/www/kyianyn-routine]
"""
import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path("/var/www/kyianyn-routine")
PAGES = ("index.html", "privacy.html")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()[:10]


def prune_scenes(out):
    """Drop the scenes whose file is missing from the deployed scenes/index.js; returns the dropped names."""
    index = out / "assets" / "js" / "scenes" / "index.js"
    lines, dropped = [], []
    for line in index.read_text(encoding="utf-8").splitlines(keepends=True):
        m = re.match(r"\s*'\./([\w-]+\.js)',", line)
        if m and not (index.parent / m.group(1)).exists():
            dropped.append(m.group(1))
            continue
        lines.append(line)
    index.write_text("".join(lines), encoding="utf-8")
    return dropped


def versioned(out):
    """{'/assets/...': '/assets/...?v=hash'} for every JS, CSS and SVG file under assets/, and the favicon."""
    files = [p for p in (out / "assets").rglob("*") if p.suffix in (".js", ".css", ".svg")] + [out / "favicon.svg"]
    return {"/" + p.relative_to(out).as_posix(): f"/{p.relative_to(out).as_posix()}?v={digest(p)}" for p in files}


def stamp(page, urls):
    """The page with versioned href and src attributes and the import map before its first module script."""
    html = page.read_text(encoding="utf-8")
    for plain, ver in urls.items():
        html = re.sub(rf'((?:href|src)=")\.?/?{re.escape(plain.lstrip("/"))}(")', rf"\g<1>{ver}\g<2>", html)
    js = {k: v for k, v in urls.items() if k.endswith(".js")}
    tag = '<script type="importmap">' + json.dumps({"imports": js}, ensure_ascii=False) + "</script>\n"
    at = html.find('<script type="module"')
    if at >= 0 and 'type="importmap"' not in html:
        html = html[:at] + tag + html[at:]
    page.write_text(html, encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -I scripts/site/deploy.py")
    ap.add_argument("--out", type=Path, default=OUT, help="the web root (default %(default)s)")
    out = ap.parse_args(argv).out
    with tempfile.TemporaryDirectory() as tmp:
        tar = subprocess.run(["git", "-C", str(ROOT), "archive", "HEAD", "site"], check=True, capture_output=True).stdout
        subprocess.run(["tar", "-x", "-C", tmp], input=tar, check=True)
        subprocess.run(["rsync", "-a", "--delete", "--exclude", "api/", "--exclude", "dev/", "--exclude", "*.md",
                        f"{tmp}/site/", f"{out}/"], check=True)
    dropped = prune_scenes(out)
    urls = versioned(out)
    for name in PAGES:
        stamp(out / name, urls)
    print(f"{out}: {len(urls)} files versioned, pages {', '.join(PAGES)}"
          + (f"; scenes left out (no file yet): {', '.join(dropped)}" if dropped else ""))


if __name__ == "__main__":
    main()
