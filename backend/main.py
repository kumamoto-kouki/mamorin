"""おとりDM デモ用バックエンド（FastAPI + WebSocket + SQLite）

役割:
- 会場の人（stranger）と子ども（kid）のDMを中継する
- 知らない相手への返信に含まれる個人情報を、相手ごとに違う「おとり情報」に差し替える
- おとりに仕込んだ地図リンクが開かれたら「足取り」を記録して保護者画面に通知する

これは発表用のモックアップです。登場する人物・住所・番号はすべて架空です。
"""

from __future__ import annotations

import json
import random
import re
import secrets
import sqlite3
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "demo.sqlite3"
DIST = BASE.parent / "frontend" / "dist"

# 子どもの「本当の」プロフィール（架空）。これが知らない相手に渡らないように守る。
KID = {
    "name": "ひなた",
    "fullname": "山田ひなた",
    "grade": "3年生",
    "school": "さくら小学校",
    "address": "東京都みどり区さくら町3-12-5",
    "phone": "090-1234-5678",
}

# 親が対面で確認した友だち（この相手には本物が届く）
VERIFIED_FRIENDS = ["ゆうと"]

# 怪しさの手がかり（AIの会話判定の代わりに、デモではキーワードで表現）
RISK_WORDS = {
    "住所": 30, "どこ住": 30, "家どこ": 30, "どこに住": 30, "おうち": 15,
    "何小": 25, "学校": 15, "何年": 10, "電話": 25, "番号": 20,
    "会お": 35, "会え": 35, "あそぼ": 15, "LINE": 25, "ライン": 25,
    "写真": 20, "ないしょ": 30, "ひみつ": 30, "ひとり": 20, "親": 15,
}

FAKE_TOWNS = ["ひかり台", "そよかぜ町", "にじが丘", "ほしの森", "つばさ町", "こもれび台"]
FAKE_SCHOOLS = ["ひかりの森小学校", "そよかぜ小学校", "にじが丘小学校", "ほしの森小学校"]
FAKE_SURNAMES = ["佐藤", "鈴木", "高橋", "田中", "伊藤", "渡辺"]


def db() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db() -> None:
    with db() as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS strangers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nickname TEXT NOT NULL,
                token TEXT NOT NULL UNIQUE,
                decoy TEXT NOT NULL,
                risk INTEGER NOT NULL DEFAULT 0,
                created REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stranger_id INTEGER NOT NULL,
                sender TEXT NOT NULL,          -- 'stranger' | 'kid'
                original TEXT NOT NULL,        -- 子どもが実際に打った文（子どもの画面に出る）
                delivered TEXT NOT NULL,       -- 相手に届いた文（おとりに差し替え後）
                swapped TEXT NOT NULL DEFAULT '[]',
                ts REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS traces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stranger_id INTEGER NOT NULL,
                kind TEXT NOT NULL,            -- 'open' | 'leak'
                detail TEXT NOT NULL,
                ts REAL NOT NULL
            );
            """
        )


def make_decoy(seed: int) -> dict:
    rnd = random.Random(seed * 7919 + int(time.time()))
    town = rnd.choice(FAKE_TOWNS)
    return {
        "fullname": f"{rnd.choice(FAKE_SURNAMES)}ひなた",
        "school": rnd.choice(FAKE_SCHOOLS),
        # 架空の区と、実在しにくい番地にして実在の人に迷惑がかからないようにする
        "address": f"東京都みどり区{town}{rnd.randint(7, 9)}-{rnd.randint(60, 99)}-{rnd.randint(30, 99)}",
        # 090-0000 から始まる番号は割り当てがない想定のデモ用
        "phone": f"090-0000-{rnd.randint(1000, 9999)}",
    }


PHONE_RE = re.compile(r"0\d{1,4}-?\d{1,4}-?\d{3,4}")
ADDRESS_RE = re.compile(r"(東京都|道|府|県)?[^\s、。]{1,6}(区|市)[^\s、。]{1,8}(町|丁目)[0-9０-９\-ー]+")
SCHOOL_RE = re.compile(r"[^\s、。]{1,8}小学校")


def protect(text: str, decoy: dict) -> tuple[str, list[str]]:
    """本物の個人情報をおとりに差し替える。差し替えた種類のリストも返す。"""
    swapped: list[str] = []
    out = text
    pairs = [
        ("address", KID["address"], "住所"),
        ("phone", KID["phone"], "電話番号"),
        ("school", KID["school"], "学校"),
        ("fullname", KID["fullname"], "本名"),
    ]
    for key, real, label in pairs:
        if real in out:
            out = out.replace(real, decoy[key])
            swapped.append(label)
    # プロフィールと完全一致しない書き方でも拾う
    if "住所" not in swapped and ADDRESS_RE.search(out):
        out = ADDRESS_RE.sub(decoy["address"], out)
        swapped.append("住所")
    if "電話番号" not in swapped and PHONE_RE.search(out) and decoy["phone"] not in out:
        out = PHONE_RE.sub(decoy["phone"], out)
        swapped.append("電話番号")
    if "学校" not in swapped and SCHOOL_RE.search(out) and decoy["school"] not in out:
        out = SCHOOL_RE.sub(decoy["school"], out)
        swapped.append("学校")
    return out, swapped


def risk_of(text: str) -> int:
    return sum(score for word, score in RISK_WORDS.items() if word in text)


# ---------------------------------------------------------------- realtime


class Hub:
    def __init__(self) -> None:
        self.clients: list[tuple[WebSocket, str, int | None]] = []

    async def join(self, ws: WebSocket, role: str, sid: int | None) -> None:
        await ws.accept()
        self.clients.append((ws, role, sid))

    def leave(self, ws: WebSocket) -> None:
        self.clients = [c for c in self.clients if c[0] is not ws]

    async def send(self, event: dict, roles: set[str], sid: int | None = None) -> None:
        dead = []
        for ws, role, csid in self.clients:
            if role not in roles:
                continue
            if role == "stranger" and csid != sid:
                continue
            try:
                await ws.send_text(json.dumps(event, ensure_ascii=False))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.leave(ws)


hub = Hub()
app = FastAPI(title="おとりDM デモ")
init_db()


def stranger_row(sid: int) -> sqlite3.Row:
    with db() as con:
        row = con.execute("SELECT * FROM strangers WHERE id=?", (sid,)).fetchone()
    if not row:
        raise HTTPException(404, "not found")
    return row


def msg_view(row: sqlite3.Row, role: str) -> dict:
    d = dict(row)
    d["swapped"] = json.loads(d["swapped"])
    if role == "stranger":
        return {"id": d["id"], "sender": d["sender"], "text": d["delivered"], "ts": d["ts"]}
    if role == "kid":
        return {"id": d["id"], "sender": d["sender"], "text": d["original"], "ts": d["ts"], "stranger_id": d["stranger_id"]}
    return d


def stranger_view(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["decoy"] = json.loads(d["decoy"])
    return d


class Join(BaseModel):
    nickname: str


class Say(BaseModel):
    stranger_id: int
    text: str


@app.get("/api/config")
def config() -> dict:
    return {"kid": KID, "friends": VERIFIED_FRIENDS}


@app.post("/api/strangers")
async def join(body: Join) -> dict:
    nickname = body.nickname.strip()[:16] or "なまえなし"
    with db() as con:
        cur = con.execute(
            "INSERT INTO strangers(nickname, token, decoy, created) VALUES (?,?,?,?)",
            (nickname, secrets.token_urlsafe(8), "{}", time.time()),
        )
        sid = cur.lastrowid
        con.execute("UPDATE strangers SET decoy=? WHERE id=?", (json.dumps(make_decoy(sid), ensure_ascii=False), sid))
    row = stranger_row(sid)
    await hub.send({"type": "stranger", "stranger": stranger_view(row)}, {"kid", "parent"})
    return {"id": sid, "nickname": nickname}


@app.get("/api/state")
def state() -> dict:
    with db() as con:
        strangers = [stranger_view(r) for r in con.execute("SELECT * FROM strangers ORDER BY id")]
        messages = [msg_view(r, "parent") for r in con.execute("SELECT * FROM messages ORDER BY id")]
        traces = [dict(r) for r in con.execute("SELECT * FROM traces ORDER BY id")]
    return {"strangers": strangers, "messages": messages, "traces": traces}


@app.get("/api/strangers/{sid}/messages")
def stranger_messages(sid: int) -> list[dict]:
    stranger_row(sid)
    with db() as con:
        rows = con.execute("SELECT * FROM messages WHERE stranger_id=? ORDER BY id", (sid,)).fetchall()
    return [msg_view(r, "stranger") for r in rows]


@app.post("/api/stranger/say")
async def stranger_say(body: Say) -> dict:
    row = stranger_row(body.stranger_id)
    text = body.text.strip()[:300]
    if not text:
        raise HTTPException(400, "empty")
    risk = min(100, row["risk"] + risk_of(text))
    with db() as con:
        cur = con.execute(
            "INSERT INTO messages(stranger_id, sender, original, delivered, ts) VALUES (?,?,?,?,?)",
            (row["id"], "stranger", text, text, time.time()),
        )
        con.execute("UPDATE strangers SET risk=? WHERE id=?", (risk, row["id"]))
        m = con.execute("SELECT * FROM messages WHERE id=?", (cur.lastrowid,)).fetchone()
    await hub.send({"type": "message", "message": msg_view(m, "kid")}, {"kid"})
    await hub.send({"type": "message", "message": msg_view(m, "stranger")}, {"stranger"}, row["id"])
    await hub.send({"type": "message", "message": msg_view(m, "parent"), "risk": risk}, {"parent"})
    return {"ok": True}


@app.post("/api/kid/say")
async def kid_say(body: Say, request: Request) -> dict:
    row = stranger_row(body.stranger_id)
    text = body.text.strip()[:300]
    if not text:
        raise HTTPException(400, "empty")
    decoy = json.loads(row["decoy"])
    is_friend = row["nickname"] in VERIFIED_FRIENDS
    delivered, swapped = (text, []) if is_friend else protect(text, decoy)
    if "住所" in swapped:
        base = str(request.base_url).rstrip("/")
        delivered += f"\n🗺 おうちの地図はこちら → {base}/t/{row['token']}"
    with db() as con:
        cur = con.execute(
            "INSERT INTO messages(stranger_id, sender, original, delivered, swapped, ts) VALUES (?,?,?,?,?,?)",
            (row["id"], "kid", text, delivered, json.dumps(swapped, ensure_ascii=False), time.time()),
        )
        m = con.execute("SELECT * FROM messages WHERE id=?", (cur.lastrowid,)).fetchone()
    await hub.send({"type": "message", "message": msg_view(m, "kid")}, {"kid"})
    await hub.send({"type": "message", "message": msg_view(m, "stranger")}, {"stranger"}, row["id"])
    await hub.send({"type": "message", "message": msg_view(m, "parent")}, {"parent"})
    return {"ok": True}


async def add_trace(sid: int, kind: str, detail: dict) -> None:
    with db() as con:
        cur = con.execute(
            "INSERT INTO traces(stranger_id, kind, detail, ts) VALUES (?,?,?,?)",
            (sid, kind, json.dumps(detail, ensure_ascii=False), time.time()),
        )
        t = dict(con.execute("SELECT * FROM traces WHERE id=?", (cur.lastrowid,)).fetchone())
    await hub.send({"type": "trace", "trace": t}, {"parent"})
    await hub.send({"type": "trace", "stranger_id": sid}, {"kid"})


REVEAL_HTML = """<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>地図</title>
<style>body{margin:0;font-family:system-ui,sans-serif;background:#0f172a;color:#f8fafc;display:grid;place-items:center;min-height:100vh;text-align:center}
.box{padding:32px 24px;max-width:360px}.big{font-size:64px}.t{font-size:26px;font-weight:800;margin:12px 0}.s{opacity:.8;line-height:1.7}</style>
</head><body><div class="box"><div class="big">🪤</div><div class="t">それ、おとりです</div>
<div class="s">あなたが受け取った住所は本物ではありません。<br>保護者に通知されました。</div>
<div class="s" style="margin-top:20px;font-size:12px">※ AI勉強会のデモです</div></div></body></html>"""


@app.get("/t/{token}", response_class=HTMLResponse)
async def decoy_link(token: str) -> str:
    with db() as con:
        row = con.execute("SELECT * FROM strangers WHERE token=?", (token,)).fetchone()
    if row:
        # デモでは閲覧者の情報は取らず、決まった見本データを記録する
        await add_trace(row["id"], "open", {"label": "おとりの地図リンクが開かれた",
                                             "region": "東京都内（見本）", "device": "スマホ（見本）", "ip": "203.0.*.*（見本）"})
    return REVEAL_HTML


@app.post("/api/demo/leak/{sid}")
async def demo_leak(sid: int) -> dict:
    """デモ用: おとり住所が名簿サイトに出回ったのを検知した、という場面を再現する。"""
    row = stranger_row(sid)
    decoy = json.loads(row["decoy"])
    await add_trace(
        sid,
        "leak",
        {
            "label": "おとりの住所が名簿サイトに掲載されたのを検知",
            "where": "「子ども名簿まとめ」（架空のサイト）",
            "found": decoy["address"],
        },
    )
    return {"ok": True}


@app.post("/api/reset")
async def reset() -> dict:
    with db() as con:
        con.executescript("DELETE FROM strangers; DELETE FROM messages; DELETE FROM traces;")
    await hub.send({"type": "reset"}, {"kid", "parent", "stranger"})
    return {"ok": True}


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket, role: str = "parent", sid: int | None = None) -> None:
    await hub.join(ws, role, sid)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        hub.leave(ws)


# ---------------------------------------------------------------- static (built Vue)

if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str) -> FileResponse:
        f = DIST / path
        if path and f.is_file():
            return FileResponse(f)
        return FileResponse(DIST / "index.html")
