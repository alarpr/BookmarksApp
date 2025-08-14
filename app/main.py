from fastapi import FastAPI, Request, Depends, UploadFile, Form
from fastapi.responses import RedirectResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, text, func, delete
from sqlalchemy.orm import selectinload
import os
from typing import Optional, List
import urllib.parse
import httpx
from bs4 import BeautifulSoup
import markdown2
import csv
import io
import json

from .db import engine, Base, get_session, DB_PATH
from .models import Topic, Bookmark
from .parse_bookmarks import parse_bookmarks_html


app = FastAPI(title="Bookmark Organizer")

BASE_DIR = os.path.dirname(__file__)
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Jinja filter for favicon URL from bookmark URL
def favicon_from_url(url: str) -> str:
    try:
        host = urllib.parse.urlsplit(url).hostname or ""
    except Exception:
        host = ""
    return f"https://www.google.com/s2/favicons?domain={host}&sz=32"

templates.env.filters["favicon"] = favicon_from_url
templates.env.filters["urlencode"] = lambda v: urllib.parse.quote_plus(str(v), safe="")

# Create DB tables on startup
Base.metadata.create_all(bind=engine)
# Deduplicate existing bookmarks and ensure unique index (topic_id, url)
with engine.begin() as conn:
    # Remove duplicates keeping the smallest id per (topic_id, url)
    conn.exec_driver_sql(
        """
        DELETE FROM bookmarks
        WHERE id NOT IN (
            SELECT MIN(id) FROM bookmarks GROUP BY topic_id, url
        )
        """
    )
    # Create the unique index after cleanup
    conn.exec_driver_sql(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_bookmarks_topic_url ON bookmarks (topic_id, url)"
    )


# Helpers
def get_root_topic(session):
    root = session.execute(
        select(Topic).where(Topic.parent_id == None, Topic.name == "Minu kogud")
    ).scalar_one_or_none()
    if not root:
        root = Topic(name="Minu kogud", parent_id=None)
        session.add(root)
        session.commit()
    return root


def ensure_topic_path(session, path):
    # path: ["Elektroonika", "Mikrokontrollerid"]
    parent = get_root_topic(session)
    # Normalize root label collision from Safari exports (e.g., 'Favorites')
    normalized_path = [n for n in path if n and n.strip().lower() not in {"favorites", "bookmarks", "bookmarks bar"}]
    for name in normalized_path:
        existing = session.execute(
            select(Topic).where(Topic.parent_id == parent.id, Topic.name == name)
        ).scalar_one_or_none()
        if not existing:
            existing = Topic(name=name, parent_id=parent.id)
            session.add(existing)
            session.commit()
        parent = existing
    return parent


@app.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    session=Depends(get_session),
    q: Optional[str] = None,
    topic_id: Optional[int] = None,
    open_url: Optional[str] = None,
    imported: Optional[int] = None,
    skipped: Optional[int] = None,
    include_sub: Optional[int] = 0,
    domain: Optional[str] = None,
):
    root = get_root_topic(session)

    # load full tree (children relation used in template)
    def fetch_children(t: Topic):
        session.refresh(t)
        for child in t.children:
            fetch_children(child)

    fetch_children(root)

    # determine current topic
    if topic_id:
        current = session.get(Topic, topic_id) or root
    else:
        # Default to root so root-level import links are visible immediately
        current = root

    # bookmarks for current topic (with optional search)
    def collect_bookmarks(t: Topic):
        items = list(t.bookmarks)
        if include_sub:
            for ch in t.children:
                items.extend(collect_bookmarks(ch))
        return items

    bookmarks = collect_bookmarks(current)
    if q:
        ql = q.lower()
        bookmarks = [
            b
            for b in bookmarks
            if ql in (b.title or "").lower() or ql in (b.url or "").lower()
        ]
    if domain:
        d = domain.lower().strip()
        bookmarks = [b for b in bookmarks if urllib.parse.urlsplit(b.url or "").hostname and d in urllib.parse.urlsplit(b.url or "").hostname.lower()]

    # sort by title for more variety when duplicates existed previously
    bookmarks = sorted(bookmarks, key=lambda b: (b.title or "").lower())

    return templates.TemplateResponse(
        "topic.html",
        {
            "request": request,
            "root": root,
            "current": current,
            "bookmarks": bookmarks,
            "q": q or "",
            "open_url": open_url,
            "imported": imported,
            "skipped": skipped,
            "include_sub": include_sub,
            "domain": domain or "",
        },
    )


# Topic CRUD
@app.post("/topics/create")
def create_topic(
    name: str = Form(...),
    parent_id: Optional[int] = Form(None),
    session=Depends(get_session),
):
    parent = session.get(Topic, parent_id) if parent_id else get_root_topic(session)
    t = Topic(name=name.strip() or "Uus kaust", parent_id=parent.id if parent else None)
    session.add(t)
    session.commit()
    return RedirectResponse(url=f"/?topic_id={t.id}", status_code=303)


@app.post("/topics/rename/{topic_id}")
def rename_topic(topic_id: int, name: str = Form(...), session=Depends(get_session)):
    t = session.get(Topic, topic_id)
    if t:
        t.name = name.strip() or t.name
        session.commit()
    return RedirectResponse(url=f"/?topic_id={topic_id}", status_code=303)


@app.post("/topics/delete/{topic_id}")
def delete_topic(topic_id: int, session=Depends(get_session)):
    t = session.get(Topic, topic_id)
    root = get_root_topic(session)
    if t and t.id != root.id:
        parent_id = t.parent_id or root.id
        session.delete(t)
        session.commit()
        return RedirectResponse(url=f"/?topic_id={parent_id}", status_code=303)
    return RedirectResponse(url="/", status_code=303)


# Bookmark CRUD
@app.post("/bookmarks/create")
def create_bookmark(
    title: str = Form(...), url: str = Form(...), topic_id: int = Form(...), session=Depends(get_session)
):
    b = Bookmark(title=title.strip() or url, url=url.strip(), topic_id=topic_id)
    session.add(b)
    session.commit()
    return RedirectResponse(url=f"/?topic_id={topic_id}&open_url={b.url}", status_code=303)


@app.post("/bookmarks/delete/{bookmark_id}")
def delete_bookmark(bookmark_id: int, session=Depends(get_session)):
    b = session.get(Bookmark, bookmark_id)
    topic_id = b.topic_id if b else None
    if b:
        session.delete(b)
        session.commit()
    return RedirectResponse(url=f"/?topic_id={topic_id}", status_code=303)


@app.post("/bookmarks/move/{bookmark_id}")
def move_bookmark(bookmark_id: int, target_topic_id: int = Form(...), session=Depends(get_session)):
    b = session.get(Bookmark, bookmark_id)
    if b and session.get(Topic, target_topic_id):
        b.topic_id = target_topic_id
        session.commit()
        return RedirectResponse(url=f"/?topic_id={target_topic_id}", status_code=303)
    return RedirectResponse(url="/", status_code=303)


@app.post("/bookmarks/bulk_delete")
def bulk_delete(ids: str = Form(...), current_topic_id: int = Form(...), session=Depends(get_session)):
    id_list = [int(x) for x in ids.split(",") if x.strip().isdigit()]
    for bid in id_list:
        b = session.get(Bookmark, bid)
        if b:
            session.delete(b)
    session.commit()
    return RedirectResponse(url=f"/?topic_id={current_topic_id}", status_code=303)


@app.post("/bookmarks/bulk_move")
def bulk_move(ids: str = Form(...), target_topic_id: int = Form(...), current_topic_id: int = Form(...), session=Depends(get_session)):
    id_list = [int(x) for x in ids.split(",") if x.strip().isdigit()]
    if not session.get(Topic, target_topic_id):
        return RedirectResponse(url=f"/?topic_id={current_topic_id}", status_code=303)
    for bid in id_list:
        b = session.get(Bookmark, bid)
        if b:
            b.topic_id = target_topic_id
    session.commit()
    return RedirectResponse(url=f"/?topic_id={target_topic_id}", status_code=303)


@app.post("/topics/move/{topic_id}")
def move_topic(topic_id: int, target_parent_id: int = Form(...), session=Depends(get_session)):
    t = session.get(Topic, topic_id)
    target = session.get(Topic, target_parent_id)
    root = get_root_topic(session)
    if not t or not target or t.id == root.id or target.id == t.id:
        return RedirectResponse(url=f"/?topic_id={t.id if t else root.id}", status_code=303)
    # prevent moving under own descendant
    anc = target
    while anc:
        if anc.id == t.id:
            return RedirectResponse(url=f"/?topic_id={t.id}", status_code=303)
        anc = session.get(Topic, anc.parent_id) if anc.parent_id else None
    t.parent_id = target.id
    session.commit()
    return RedirectResponse(url=f"/?topic_id={t.id}", status_code=303)


# Import & Export
@app.post("/import")
def import_bookmarks(file: UploadFile, request: Request, session=Depends(get_session)):
    try:
        html = file.file.read().decode("utf-8", errors="ignore")
        items = parse_bookmarks_html(html)

        created = 0
        skipped = 0
        seen_keys = set()  # avoid duplicates within the same upload batch
        for path, title, href in items:
            parent = ensure_topic_path(session, path)
            url_value = (href or "").strip()
            key = (parent.id, url_value)
            if key in seen_keys:
                skipped += 1
                continue
            # skip duplicates already in DB
            exists = session.execute(
                select(Bookmark.id).where(Bookmark.topic_id == parent.id, Bookmark.url == url_value)
            ).first()
            if exists:
                skipped += 1
                continue
            session.add(Bookmark(title=(title or url_value).strip(), url=url_value, topic_id=parent.id))
            seen_keys.add(key)
            created += 1
        session.commit()

        return RedirectResponse(url=f"/?imported={created}&skipped={skipped}", status_code=303)
    except Exception as e:
        # Roll back any partial changes and show a helpful error
        try:
            session.rollback()
        except Exception:
            pass
        return templates.TemplateResponse(
            "import.html",
            {
                "request": request,
                "title": "Import HTML",
                "accept": "text/html,.html,.htm",
                "action": "/import",
                "error": f"Import ebaõnnestus: {type(e).__name__}: {str(e)}",
            },
            status_code=500,
        )


@app.post("/import_csv")
def import_csv(file: UploadFile, session=Depends(get_session)):
    text = file.file.read().decode("utf-8", errors="ignore")
    reader = csv.DictReader(io.StringIO(text))
    created = 0
    skipped = 0
    seen_keys = set()
    for row in reader:
        path_str = (row.get("topic_path") or "").strip()
        path = [p for p in path_str.split("/") if p]
        title = (row.get("title") or "").strip()
        url_value = (row.get("url") or "").strip()
        if not url_value:
            continue
        parent = ensure_topic_path(session, path)
        key = (parent.id, url_value)
        if key in seen_keys:
            skipped += 1
            continue
        exists = session.execute(
            select(Bookmark.id).where(Bookmark.topic_id == parent.id, Bookmark.url == url_value)
        ).first()
        if exists:
            skipped += 1
            continue
        session.add(Bookmark(title=title or url_value, url=url_value, topic_id=parent.id))
        seen_keys.add(key)
        created += 1
    session.commit()
    return RedirectResponse(url=f"/?imported={created}&skipped={skipped}", status_code=303)


@app.post("/import_json")
def import_json(file: UploadFile, session=Depends(get_session)):
    data = json.loads(file.file.read().decode("utf-8", errors="ignore") or "[]")
    created = 0
    skipped = 0
    seen_keys = set()

    def add_item(path, title, url_value):
        nonlocal created, skipped
        if not url_value:
            return
        parent = ensure_topic_path(session, path)
        key = (parent.id, url_value)
        if key in seen_keys:
            skipped += 1
            return
        exists = session.execute(
            select(Bookmark.id).where(Bookmark.topic_id == parent.id, Bookmark.url == url_value)
        ).first()
        if exists:
            skipped += 1
            return
        session.add(Bookmark(title=title or url_value, url=url_value, topic_id=parent.id))
        seen_keys.add(key)
        created += 1

    # Support two formats: flat rows and tree from export.json
    if isinstance(data, list):
        # Detect tree vs flat by keys
        if data and isinstance(data[0], dict) and set(data[0].keys()) & {"id", "name", "children", "bookmarks"}:
            def walk(node, path):
                name = node.get("name")
                cur_path = path + ([name] if name else [])
                for b in node.get("bookmarks", []) or []:
                    add_item(cur_path, b.get("title"), b.get("url"))
                for ch in node.get("children", []) or []:
                    walk(ch, cur_path)
            for root_node in data:
                walk(root_node, [])
        else:
            for row in data:
                path_str = (row.get("topic_path") or "").strip()
                path = [p for p in path_str.split("/") if p]
                add_item(path, (row.get("title") or "").strip(), (row.get("url") or "").strip())
    session.commit()
    return RedirectResponse(url=f"/?imported={created}&skipped={skipped}", status_code=303)


@app.get("/check")
def check_url(url: str):
    """Basic health check for a URL; tries HEAD, falls back to GET."""
    timeout = httpx.Timeout(5.0, connect=5.0)
    status = None
    ok = False
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            r = client.head(url)
            status = r.status_code
            ok = 200 <= status < 400
            if not ok:
                r = client.get(url)
                status = r.status_code
                ok = 200 <= status < 400
    except Exception:
        status = None
        ok = False
    return {"ok": ok, "status": status}


def _preview_fallback(url: str, message: str) -> HTMLResponse:
    """Generates a standardized, user-friendly fallback page for the preview iframe."""
    # The inline CSS is necessary because the content is rendered in an iframe,
    # so it cannot access the main application's stylesheet.
    html = f"""
    <html>
    <head>
        <meta charset='utf-8'>
        <title>Eelvaade ebaõnnestus</title>
        <style>
            body {{
                background: #0b0c10;
                color: #e9eaee;
                font: 16px/1.6 -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Inter, Ubuntu;
                text-align: center;
                display: flex;
                align-items: center;
                justify-content: center;
                height: 100vh;
                margin: 0;
                padding: 20px;
            }}
            .container {{ max-width: 500px; }}
            p {{ color: #9aa0aa; }}
            .btn {{
                display: inline-block;
                padding: 12px 20px;
                background: #4f8cff;
                color: #fff;
                border-radius: 8px;
                text-decoration: none;
                margin-top: 20px;
                transition: background-color 0.2s;
            }}
            .btn:hover {{ background: #699eff; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Eelvaade pole saadaval</h2>
            <p>{message}</p>
            <a class='btn' target='_blank' href='{url}'>Ava uues aknas</a>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(html, media_type="text/html")


@app.get("/preview", response_class=HTMLResponse)
def preview(url: str):
    """Server-side preview that works for sites blocking iframes.
    - YouTube watch links → embed player
    - GitHub repo links → render README.md
    - Fallback: simple fetch and strip scripts; show title + limited content
    """
    try:
        parsed = urllib.parse.urlsplit(url)
        host = (parsed.hostname or "").lower()

        # YouTube embed
        if "youtube.com" in host or "youtu.be" in host:
            video_id = None
            qs = urllib.parse.parse_qs(parsed.query)
            if "v" in qs:
                video_id = qs.get("v", [None])[0]
            if not video_id and host == "youtu.be":
                video_id = parsed.path.lstrip("/")
            if video_id:
                embed = f"https://www.youtube.com/embed/{video_id}"
                # This is a trusted format, so we don't need the fallback.
                return HTMLResponse(
                    f'<html><body style="margin:0;background:#0b0c10"><iframe src="{embed}" style="border:0;width:100%;height:100vh" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen sandbox="allow-scripts allow-same-origin allow-forms allow-popups"></iframe></body></html>',
                    media_type="text/html",
                )

        # GitHub README
        if host == "github.com":
            parts = parsed.path.strip("/").split("/")
            if len(parts) >= 2:
                owner, repo = parts[0], parts[1]
                raw_candidates = [
                    f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/README.md",
                    f"https://raw.githubusercontent.com/{owner}/{repo}/main/README.md",
                    f"https://raw.githubusercontent.com/{owner}/{repo}/master/README.md",
                ]
                md = None
                with httpx.Client(timeout=10) as client:
                    for raw in raw_candidates:
                        r = client.get(raw)
                        if r.status_code == 200 and r.text.strip():
                            md = r.text
                            break
                if md:
                    html = markdown2.markdown(md)
                    title = f"{owner}/{repo} — README"
                    # This is also trusted, no fallback needed.
                    return HTMLResponse(
                        f"<html><head><meta charset='utf-8'><title>{title}</title><style>body{{background:#0b0c10;color:#e9eaee;font:14px/1.5 -apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Inter,Ubuntu}} a{{color:#4f8cff}}</style></head><body><h2>{title}</h2>{html}</body></html>",
                        media_type="text/html",
                    )

        # Generic fetch and sanitize
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        with httpx.Client(timeout=10, follow_redirects=True, headers=headers) as client:
            r = client.get(url)

        if r.status_code >= 400:
            return _preview_fallback(url, f"Saiti ei saanud laadida (HTTP staatus: {r.status_code}).")

        soup = BeautifulSoup(r.text or "", "html.parser")
        for tag in soup(["script", "noscript", "style", "iframe", "header", "footer", "nav"]):
            tag.decompose()
        
        title = soup.title.get_text(strip=True) if soup.title else url
        body = soup.body or soup
        
        raw_text = (body.get_text(" ", strip=True) if body else "").lower()
        if "attention required" in raw_text or "cloudflare" in raw_text and "blocked" in raw_text:
            return _preview_fallback(url, "Sait kasutab Cloudflare'i või sarnast kaitset, mis takistab eelvaate kuvamist.")

        content = "".join(str(el) for el in body.find_all(["h1", "h2", "h3", "p", "ul", "ol", "pre", "article", "main", "div"], limit=80))
        
        # Check if the extracted content is too short or meaningless
        if len(content.strip()) < 150:
             return _preview_fallback(url, "Selle lehe sisu ei saa eelvaates kuvada, kuna see on liiga lühike või nõuab JavaScripti.")

        open_btn = f"<p style='margin-top:2rem;'><a class='btn' style='background:#4f8cff;color:#fff;padding:8px 12px;border-radius:8px;text-decoration:none' target='_blank' href='{url}'>Ava uues aknas</a></p>"
        html = f"<html><head><meta charset='utf-8'><title>{title}</title><style>body{{background:#0b0c10;color:#e9eaee;font:14px/1.6 -apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Inter,Ubuntu;padding:20px}} a{{color:#4f8cff}}</style></head><body><h2>{title}</h2>{content}{open_btn}</body></html>"
        return HTMLResponse(html, media_type="text/html")

    except httpx.ConnectError:
        return _preview_fallback(url, "Selle aadressiga ei saanud ühendust. Kontrolli, kas URL on õige.")
    except Exception as e:
        # A generic catch-all for any other unexpected errors.
        return _preview_fallback(url, f"Ilmnes ootamatu viga: {type(e).__name__}.")


@app.get("/export", response_class=HTMLResponse)
def export_html(session=Depends(get_session)):
    # Simple Netscape Bookmarks HTML
    root_topics = session.execute(select(Topic).where(Topic.parent_id == None)).scalars().all()

    def render_topic(t: Topic) -> str:
        parts = [f"<DT><H3>{t.name}</H3>\n<DL><p>\n"]
        for b in t.bookmarks:
            parts.append(f"<DT><A HREF=\"{b.url}\">{b.title}</A>\n")
        for c in t.children:
            parts.append(render_topic(c))
        parts.append("</DL><p>\n")
        return "".join(parts)

    body = [
        "<!DOCTYPE NETSCAPE-Bookmark-file-1>\n<META HTTP-EQUIV=\"Content-Type\" CONTENT=\"text/html; charset=UTF-8\">\n<TITLE>Bookmarks</TITLE>\n<H1>Bookmarks</H1>\n<DL><p>\n"
    ]
    for r in root_topics:
        body.append(render_topic(r))
    body.append("</DL><p>\n")

    return HTMLResponse(content="".join(body), media_type="text/html")


@app.get("/export.json")
def export_json(session=Depends(get_session)):
    import json
    def serialize_topic(t: Topic):
        return {
            "id": t.id,
            "name": t.name,
            "bookmarks": [{"id": b.id, "title": b.title, "url": b.url} for b in t.bookmarks],
            "children": [serialize_topic(c) for c in t.children],
        }
    roots = session.execute(select(Topic).where(Topic.parent_id == None)).scalars().all()
    data = [serialize_topic(r) for r in roots]
    return HTMLResponse(json.dumps(data, ensure_ascii=False, indent=2), media_type="application/json")


@app.get("/export.csv")
def export_csv(session=Depends(get_session)):
    import io, csv
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["topic_path", "title", "url"])
    def walk(t: Topic, path):
        p = path + [t.name]
        for b in t.bookmarks:
            writer.writerow(["/".join(p), b.title, b.url])
        for c in t.children:
            walk(c, p)
    roots = session.execute(select(Topic).where(Topic.parent_id == None)).scalars().all()
    for r in roots:
        walk(r, [])
    return HTMLResponse(output.getvalue(), media_type="text/csv")


@app.get("/sample.csv")
def sample_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["topic_path", "title", "url"])
    writer.writerow(["AI Tools", "Claude", "https://claude.ai/"])
    writer.writerow(["Youtube AI", "The AI Advantage - YouTube", "https://www.youtube.com/@aiadvantage"])
    return HTMLResponse(output.getvalue(), media_type="text/csv")


@app.get("/sample.json")
def sample_json():
    data = [
        {"topic_path": "AI Tools", "title": "Claude", "url": "https://claude.ai/"},
        {"topic_path": "Youtube AI", "title": "The AI Advantage - YouTube", "url": "https://www.youtube.com/@aiadvantage"}
    ]
    return HTMLResponse(json.dumps(data, ensure_ascii=False, indent=2), media_type="application/json")


@app.get("/backup")
def backup_db():
    """Download current SQLite DB file."""
    filename = f"bookmarks-backup.sqlite3"
    return FileResponse(os.path.abspath(DB_PATH), filename=filename, media_type="application/octet-stream")


@app.post("/restore")
def restore_db(file: UploadFile):
    """Restore SQLite DB from uploaded file (overwrites current DB)."""
    data = file.file.read()
    # basic safety: require non-empty
    if not data:
        return RedirectResponse(url="/", status_code=303)
    target = os.path.abspath(DB_PATH)
    tmp = target + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
    # simple check: file should be an SQLite header
    with open(tmp, "rb") as f:
        head = f.read(16)
    if b"SQLite format 3" not in head:
        os.remove(tmp)
        return RedirectResponse(url="/", status_code=303)
    # replace
    os.replace(tmp, target)
    return RedirectResponse(url="/", status_code=303)


# Duplicates
@app.get("/duplicates", response_class=HTMLResponse)
def view_duplicates(request: Request, session=Depends(get_session)):
    # Find URLs that are duplicated
    duplicate_urls_query = (
        select(Bookmark.url)
        .group_by(Bookmark.url)
        .having(func.count(Bookmark.id) > 1)
        .order_by(func.lower(Bookmark.url))
    )
    duplicate_urls = session.execute(duplicate_urls_query).scalars().all()

    # For each duplicate URL, get the full bookmark objects, including topic info
    duplicates_map = {}
    if duplicate_urls:
        # This is more efficient than N+1 queries in a loop
        all_duplicates_query = (
            select(Bookmark)
            .where(Bookmark.url.in_(duplicate_urls))
            .options(selectinload(Bookmark.topic)) # Eager load topic to avoid N+1
            .order_by(Bookmark.url, Bookmark.id)
        )
        all_bookmarks = session.execute(all_duplicates_query).scalars().all()
        for b in all_bookmarks:
            if b.url not in duplicates_map:
                duplicates_map[b.url] = []
            duplicates_map[b.url].append(b)

    return templates.TemplateResponse(
        "duplicates.html",
        {"request": request, "duplicates": duplicates_map, "root": get_root_topic(session)},
    )


@app.post("/duplicates/delete")
def delete_duplicates(delete_ids: List[int] = Form(...), session=Depends(get_session)):
    if delete_ids:
        # Make sure we don't have empty strings if form is weird
        id_list = [int(id) for id in delete_ids if str(id).isdigit()]
        if id_list:
            stmt = delete(Bookmark).where(Bookmark.id.in_(id_list))
            session.execute(stmt)
            session.commit()
    # Redirect back to the duplicates page to see the result
    return RedirectResponse(url="/duplicates?deleted=" + str(len(delete_ids)), status_code=303)


# Simple UI pages for file uploads (work around Safari restrictions)
@app.get("/ui/import/{kind}", response_class=HTMLResponse)
def import_ui(kind: str, request: Request):
    kind = (kind or "").lower()
    mapping = {
        "html": {"title": "Import HTML", "accept": "text/html,.html,.htm", "action": "/import"},
        "csv": {"title": "Import CSV", "accept": "text/csv,.csv", "action": "/import_csv"},
        "json": {"title": "Import JSON", "accept": "application/json,.json", "action": "/import_json"},
    }
    cfg = mapping.get(kind)
    if not cfg:
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(
        "import.html",
        {
            "request": request,
            "title": cfg["title"],
            "accept": cfg["accept"],
            "action": cfg["action"],
        },
    )


@app.get("/ui/restore", response_class=HTMLResponse)
def restore_ui(request: Request):
    return templates.TemplateResponse(
        "import.html",
        {
            "request": request,
            "title": "Taasta DB",
            "accept": "application/octet-stream,.sqlite,.sqlite3",
            "action": "/restore",
        },
    )

