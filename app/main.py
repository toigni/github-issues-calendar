from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import requests
import sqlite3
import json
import os
import time
import logging

# set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

logger = logging.getLogger("github-calendar")

# FASTAPI
app = FastAPI()

# configure
# Read token safely (won't raise on missing env var)
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    logging.getLogger("github-calendar").warning("GITHUB_TOKEN not set; API requests may fail")

REPO = os.environ.get("REPO")
if not REPO:
    raise RuntimeError("REPO is not set")

CACHE_TTL = int(os.environ.get("CACHE_TTL", "3600"))

# SQLite setup
logger.info("Initializing SQLite cache database")
conn = sqlite3.connect("cache.db", check_same_thread=False)
conn.execute(
    """
    CREATE TABLE IF NOT EXISTS issue_cache (
        repo TEXT PRIMARY KEY,
        json TEXT NOT NULL,
        fetched_at INTEGER NOT NULL
    )
    """
)
conn.commit()

# キャッシュ取得
def load_cache(repo: str):
    # SQLiteからキャッシュを取得
    logger.debug("Checking cache for repo=%s", repo)
    cur = conn.cursor()
    cur.execute(
        "SELECT json,fetched_at FROM issue_cache WHERE repo=?", (repo,)
    )
    row = cur.fetchone()

    if not row:
        logger.info("cache miss (no entry): repo=%s", repo)
        return None

    cached_json, fetched_at = row
    age = time.time() - fetched_at

    if age > CACHE_TTL:
        logger.info("cache expired: repo=%s age=%.1fs ttl=%ds", repo, age, CACHE_TTL)
        return None
    
    logger.info("cache hit: repo=%s age=%.1fs", repo, age)
    return json.loads(cached_json)

# キャッシュ保存
def save_cache(repo: str, data):
    # API結果をSQLiteに保存
    logger.info("Saving cache: repo=%s items=%d", repo, len(data))

    conn.execute(
        "REPLACE INTO issue_cache (repo, json, fetched_at) VALUES (?,?,?)",
        (repo, json.dumps(data), int(time.time())),
    )

    conn.commit()

# APIエンドポイント
# static 配信
app.mount("/static", StaticFiles(directory="static"), name="static")

# ★ これが無いと Not Found になる
@app.get("/")
def index():
    return FileResponse("static/index.html")


@app.get("/api/issues")
def get_issues():
    # ISSUE一覧をカレンダー用イベントとして返す
    logger.info("Request received: /api/issues repo=%s",REPO)

    cached = load_cache(REPO)
    if cached is not None:
        logger.info("Returning cached response")
        return cached
    
    logger.info("Fetching issues from GitHub API")
    url = f"https://api.github.com/repos/{REPO}/issues"
    headers = {
        "Authorization":f"Bearer {GITHUB_TOKEN}",
        "Accept":"application/vnd.github.v3+json"
    }
    params = {
        "state":"open",
        "per_page":100
    }
    
    try:
        r = requests.get(url,headers=headers,params=params,timeout=10)
        r.raise_for_status()
    except requests.RequestException as e:
        logger.error("Github API request failed: %s",e)
        raise
    
    issues = r.json()
    logger.info("Github API returned %d issues",len(issues))
    events = []

    for issue in issues:
        if "pull_request" in issue:
            logger.debug("skipping pull request: #%s", issue.get("number"))
            continue
        
        start_date = (issue.get("milestone") or {}).get("due_on") or issue.get("updated_at")

        events.append({
            "title": issue.get("title"),
            "start": start_date,
            "url": issue.get("html_url"),
        })

    logger.info("converted to %d calendar events", len(events))

    # キャッシュ保存
    save_cache(REPO, events)

    # レスポンス
    logger.info("returning response")
    return events