"""Owner panel: every subscription client on this server in one screen.

A separate small web app (started by `deploy/client.sh owner DOMAIN`, image = the backend image):
  uvicorn app.owner_panel.main:app
It reads the clients from clients/*.env (mounted read-only), asks each installation over the Docker network
(GET/PUT /api/owner/* with that client's OWNER_TOKEN) and lets the owner extend or close a subscription.
For a client whose user management is kept here (`admin_in_app` off) the owner manages users, roles, invitations,
passwords and reads the activity log on /clients/<slug>/users and /clients/<slug>/log.

Settings (deploy/owner.env): OWNER_PASSWORD (login), OWNER_SECRET (signs the session, ≥ 32 chars),
OWNER_CLIENTS_DIR (default /clients), OWNER_BACKEND_URL (default http://{slug}-backend:8000).
"""
import asyncio
import hashlib
import hmac
import html
import os
import time
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, quote
from zoneinfo import ZoneInfo

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

SESSION_COOKIE = "owner_session"
SESSION_HOURS = 12
MAX_FAILS, LOCK_SECONDS = 5, 15 * 60

app = FastAPI(title="Owner panel", docs_url=None, redoc_url=None, openapi_url=None)
_fails: dict[str, tuple[int, float]] = {}
transport: httpx.AsyncBaseTransport | None = None  # tests plug the backend app in here


def _cfg(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _secret() -> bytes:
    s = _cfg("OWNER_SECRET")
    if len(s) < 32:
        raise RuntimeError("OWNER_SECRET must be at least 32 characters")
    return s.encode()


# ---------- clients ----------

@dataclass
class Client:
    slug: str
    domain: str
    brand: str
    token: str
    contact: str


def read_env(path: Path) -> dict[str, str]:
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def clients() -> list[Client]:
    folder = Path(_cfg("OWNER_CLIENTS_DIR", "/clients"))
    result = []
    for f in sorted(folder.glob("*.env")):
        env = read_env(f)
        result.append(Client(slug=f.stem, domain=env.get("DOMAIN", ""), brand=env.get("BRAND_NAME", f.stem),
                             token=env.get("OWNER_TOKEN", ""), contact=env.get("SUBSCRIPTION_CONTACT", "")))
    return result


def _url(c: Client, path: str) -> str:
    return _cfg("OWNER_BACKEND_URL", "http://{slug}-backend:8000").format(slug=c.slug) + path


async def fetch_stats(c: Client) -> dict | str:
    if not c.token:
        return "нет OWNER_TOKEN: выполните ./deploy/client.sh owner"
    try:
        async with httpx.AsyncClient(timeout=4, transport=transport) as http:
            r = await http.get(_url(c, "/api/owner/stats"), headers={"X-Owner-Token": c.token})
        if r.status_code == 200:
            return r.json()
        return f"ответ {r.status_code}"
    except httpx.HTTPError:
        return "не отвечает (остановлен?)"


async def put_subscription(c: Client, until: date | None) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=6, transport=transport) as http:
            r = await http.put(_url(c, "/api/owner/subscription"), headers={"X-Owner-Token": c.token},
                               json={"until": until.isoformat() if until else None})
        return None if r.status_code == 200 else f"ответ {r.status_code}"
    except httpx.HTTPError:
        return "клиент не отвечает"


async def call(c: Client, method: str, path: str, body: dict | None = None,
               params: dict | None = None) -> tuple[bool, dict | str]:
    """(ok, json) or (False, Russian error message from the client app)."""
    if not c.token:
        return False, "нет OWNER_TOKEN: выполните ./deploy/client.sh owner"
    try:
        async with httpx.AsyncClient(timeout=8, transport=transport) as http:
            r = await http.request(method, _url(c, path), headers={"X-Owner-Token": c.token}, json=body, params=params)
    except httpx.HTTPError:
        return False, "клиент не отвечает"
    try:
        data = r.json()
    except ValueError:
        data = {}
    if r.status_code < 300:
        return True, data
    detail = data.get("detail") if isinstance(data, dict) else None
    if isinstance(data, dict) and data.get("errors"):
        detail = "; ".join(e.get("message", "") for e in data["errors"]) or detail
    return False, detail if isinstance(detail, str) else f"ответ {r.status_code}"


# ---------- session ----------

def _sign(value: str) -> str:
    return hmac.new(_secret(), value.encode(), hashlib.sha256).hexdigest()


def make_session() -> str:
    expires = str(int(time.time()) + SESSION_HOURS * 3600)
    return f"{expires}.{_sign(expires)}"


def valid_session(cookie: str | None) -> bool:
    if not cookie or "." not in cookie:
        return False
    expires, sig = cookie.split(".", 1)
    return expires.isdigit() and int(expires) > time.time() and hmac.compare_digest(sig, _sign(expires))


def csrf_token(cookie: str) -> str:
    return _sign("csrf:" + cookie)[:32]


async def form(request: Request) -> dict[str, str]:
    body = (await request.body()).decode("utf-8", "replace")
    return {k: v[0] for k, v in parse_qs(body).items()}


def _ip(request: Request) -> str:
    return request.headers.get("x-real-ip") or (request.client.host if request.client else "?")


# ---------- dates ----------

def local_today() -> date:
    """The apiaries' calendar day (TIMEZONE, default Asia/Dushanbe) — this app has no database settings."""
    return datetime.now(ZoneInfo(_cfg("TIMEZONE", "Asia/Dushanbe"))).date()


def add_months(d: date, months: int) -> date:
    m = d.month - 1 + months
    y, m = d.year + m // 12, m % 12 + 1
    days = [31, 29 if y % 4 == 0 and (y % 100 or y % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1]
    return date(y, m, min(d.day, days))


def new_until(action: str, current: date | None, picked: str, today: date) -> tuple[bool, date | None]:
    """Returns (ok, date). Extending counts from the current end, or from today when it has passed."""
    base = current if current and current >= today else today
    if action == "month":
        return True, add_months(base, 1)
    if action == "year":
        return True, add_months(base, 12)
    if action == "block":
        return True, today - timedelta(days=1)
    if action == "unlimited":
        return True, None
    if action == "date":
        try:
            return True, date.fromisoformat(picked)
        except ValueError:
            return False, None
    return False, None


# ---------- pages ----------

CSS = """
:root{--bg:#15120c;--card:#201a11;--rim:#3d3222;--gold:#f4c23b;--text:#f6ecd6;--muted:#a8997d;--ok:#9cc56b;--bad:#e8664b;--warn:#ee8a1c}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
main{max-width:760px;margin:0 auto;padding:20px 16px 40px}h1{font-size:26px;margin:0 0 4px}p{margin:6px 0}
.muted{color:var(--muted)}.card{background:var(--card);border:1px solid var(--rim);border-radius:16px;padding:16px;margin:14px 0}
.head{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}.name{font-size:18px;font-weight:700}
.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px}
.badge{padding:3px 10px;border-radius:999px;font-size:13px;white-space:nowrap;border:1px solid var(--rim)}
.ok{color:var(--ok)}.bad{color:var(--bad)}.warn{color:var(--warn)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px;margin:12px 0}
.grid div{background:#2b2317;border-radius:12px;padding:8px 10px}.grid b{display:block;font-size:20px}
form.inline{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px;align-items:center}
button,input{font:inherit;border-radius:12px;border:1px solid var(--rim);background:#2b2317;color:var(--text);padding:9px 14px}
button{cursor:pointer}button.primary{background:var(--gold);color:#1b1406;border-color:var(--gold);font-weight:700}
button.danger{color:var(--bad)}.msg{padding:10px 14px;border-radius:12px;background:#2b2317;border:1px solid var(--rim)}
.top{display:flex;justify-content:space-between;align-items:center}a{color:var(--gold)}
select{font:inherit;border-radius:12px;border:1px solid var(--rim);background:#2b2317;color:var(--text);padding:9px 10px}
.row{border-top:1px solid var(--rim);margin-top:12px;padding-top:8px}.small{font-size:13px}
.secret{font:20px ui-monospace,Menlo,monospace;letter-spacing:1px;background:#2b2317;padding:10px 14px;border-radius:12px;display:inline-block}
label.check{display:flex;gap:6px;align-items:center}h2{font-size:19px;margin:22px 0 4px}
"""


def page(body: str, title: str = "Панель владельца") -> HTMLResponse:
    doc = (f"<!doctype html><html lang='ru'><head><meta charset='utf-8'><meta name='viewport' "
           f"content='width=device-width,initial-scale=1'><meta name='robots' content='noindex'><title>{title}</title>"
           f"<style>{CSS}</style></head><body><main>{body}</main></body></html>")
    return HTMLResponse(doc, headers={
        "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'",
        "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer", "Cache-Control": "no-store"})


def login_page(error: str = "") -> HTMLResponse:
    err = f"<p class='bad'>{html.escape(error)}</p>" if error else ""
    return page(f"""<h1>Панель владельца</h1><p class='muted'>Клиенты подписки на этом сервере.</p>
<div class='card'><form method='post' action='/login' class='inline'>
<input type='password' name='password' placeholder='Пароль' autocomplete='current-password' required autofocus>
<button class='primary'>Войти</button></form>{err}</div>""")


def _fmt_dt(v: str | None) -> str:
    if not v:
        return "—"
    try:
        moment = datetime.fromisoformat(v.replace("Z", "+00:00"))
        return moment.astimezone(ZoneInfo(_cfg("TIMEZONE", "Asia/Dushanbe"))).strftime("%d.%m.%Y %H:%M")
    except ValueError:
        return html.escape(v)


def _kg(v) -> str:
    """219.00 → «219», 12.5 → «12,5»."""
    try:
        return f"{float(v):,.1f}".replace(",", " ").replace(".", ",").removesuffix(",0")
    except (TypeError, ValueError):
        return "—"


def _fmt_date(v: str | None) -> str:
    return date.fromisoformat(v).strftime("%d.%m.%Y") if v else "без срока"


def client_card(c: Client, s: dict | str, csrf: str) -> str:
    e = html.escape
    link = f"<a href='https://{e(c.domain)}' target='_blank' rel='noreferrer'>{e(c.domain)}</a>" if c.domain else ""
    if isinstance(s, str):
        return (f"<div class='card'><div class='name'>{e(c.brand)}</div>"
                f"<p class='muted'>{e(c.slug)} · {link}</p><p class='bad'>{e(s)}</p></div>")
    sub = s["subscription"]
    left = sub.get("days_left")
    if not sub["active"]:
        badge, cls = "доступ закрыт", "bad"
    elif left is not None and left <= 7:
        badge, cls = f"осталось {left} дн.", "warn"
    else:
        badge, cls = "оплачено", "ok"
    colour = e(s["brand"]["color"])
    actions = "".join(
        f"<button name='action' value='{a}'{' class=primary' if a == 'year' else ''}{' class=danger' if a == 'block' else ''}>{t}</button>"
        for a, t in (("month", "+1 месяц"), ("year", "+1 год"), ("unlimited", "Без срока"), ("block", "Закрыть доступ")))
    return f"""<div class='card'>
<div class='head'><div><div class='name'><span class='dot' style='background:{colour}'></span>{e(s['brand']['name'])}</div>
<p class='muted'>{e(c.slug)} · {link}</p></div><span class='badge {cls}'>{badge}</span></div>
<p>Оплачено до: <b>{_fmt_date(sub.get('until'))}</b>{' <span class=muted>(из панели)</span>' if sub.get('source') == 'panel' else ''}</p>
<div class='grid'><div><b>{s['hives']}</b>ульев</div><div><b>{s['apiaries']}</b>пасек</div>
<div><b>{s['users']['active']}</b>пользователей</div><div><b>{_kg(s['honey_year_kg'])}</b>кг мёда в этом году</div></div>
<p class='muted'>Последний вход: {_fmt_dt(s.get('last_login'))} · последнее изменение: {_fmt_dt(s.get('last_change'))}</p>
{admin_row(c, s, csrf)}
<form method='post' action='/clients/{quote(c.slug)}/subscription' class='inline'>
<input type='hidden' name='csrf' value='{csrf}'>{actions}
<input type='date' name='date' aria-label='Дата'><button name='action' value='date'>До даты</button></form></div>"""


ROLES = {"ADMIN": "Администратор", "BEEKEEPER": "Пчеловод", "ASSISTANT": "Помощник", "VIEWER": "Наблюдатель"}


def admin_row(c: Client, s: dict, csrf: str) -> str:
    slug = quote(c.slug)
    in_app = s.get("admin_in_app", True)
    where = ("в приложении (администратор клиента)" if in_app else "<b>только здесь</b> — в приложении раздела нет")
    switch = ("Перенести сюда" if in_app else "Вернуть в приложение")
    return f"""<div class='row'><p>Пользователи и права: {where}</p>
<p><a href='/clients/{slug}/users'>Пользователи и доступ</a> · <a href='/clients/{slug}/log'>Журнал действий</a></p>
<form method='post' action='/clients/{slug}/settings' class='inline'><input type='hidden' name='csrf' value='{csrf}'>
<input type='hidden' name='admin_in_app' value='{'0' if in_app else '1'}'><button>{switch}</button></form></div>"""


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, msg: str = ""):
    cookie = request.cookies.get(SESSION_COOKIE)
    if not valid_session(cookie):
        return login_page()
    items = clients()
    stats = await asyncio.gather(*(fetch_stats(c) for c in items))
    csrf = csrf_token(cookie)
    closed = sum(1 for s in stats if isinstance(s, dict) and not s["subscription"]["active"])
    soon = sum(1 for s in stats if isinstance(s, dict) and s["subscription"]["active"]
               and s["subscription"].get("days_left") is not None and s["subscription"]["days_left"] <= 7)
    note = f"<p class='msg'>{html.escape(msg)}</p>" if msg else ""
    cards = "".join(client_card(c, s, csrf) for c, s in zip(items, stats)) or \
        "<div class='card'><p>Клиентов пока нет. Добавьте: <code>./deploy/client.sh add имя домен</code></p></div>"
    return page(f"""<div class='top'><h1>Клиенты</h1><form method='post' action='/logout'>
<input type='hidden' name='csrf' value='{csrf}'><button>Выйти</button></form></div>
<p class='muted'>Всего: {len(items)} · закрыто: {closed} · заканчивается в течение недели: {soon}</p>{note}{cards}""")


@app.post("/login")
async def login(request: Request):
    ip = _ip(request)
    fails, until = _fails.get(ip, (0, 0.0))
    if until > time.time():
        return login_page("Слишком много попыток. Подождите 15 минут.")
    password = (await form(request)).get("password", "")
    expected = _cfg("OWNER_PASSWORD")
    if not expected or not hmac.compare_digest(password.encode(), expected.encode()):
        fails += 1
        _fails[ip] = (0, time.time() + LOCK_SECONDS) if fails >= MAX_FAILS else (fails, 0.0)
        return login_page("Неверный пароль")
    _fails.pop(ip, None)
    r = RedirectResponse("/", status_code=303)
    r.set_cookie(SESSION_COOKIE, make_session(), max_age=SESSION_HOURS * 3600, httponly=True, samesite="strict",
                 secure=_cfg("OWNER_INSECURE_COOKIE") != "1")
    return r


def _checked(request: Request, data: dict[str, str]) -> bool:
    cookie = request.cookies.get(SESSION_COOKIE)
    return valid_session(cookie) and hmac.compare_digest(data.get("csrf", ""), csrf_token(cookie))


@app.post("/logout")
async def logout(request: Request):
    r = RedirectResponse("/", status_code=303)
    if _checked(request, await form(request)):
        r.delete_cookie(SESSION_COOKIE)
    return r


@app.post("/clients/{slug}/subscription")
async def change_subscription(slug: str, request: Request):
    data = await form(request)
    if not _checked(request, data):
        return RedirectResponse("/", status_code=303)
    c = next((x for x in clients() if x.slug == slug), None)
    if c is None or not c.token:
        return RedirectResponse("/?msg=" + quote("Клиент не найден или без OWNER_TOKEN"), status_code=303)
    stats = await fetch_stats(c)
    current = None
    if isinstance(stats, dict) and stats["subscription"].get("until"):
        current = date.fromisoformat(stats["subscription"]["until"])
    ok, until = new_until(data.get("action", ""), current, data.get("date", ""), local_today())
    if not ok:
        return RedirectResponse("/?msg=" + quote("Выберите дату"), status_code=303)
    error = await put_subscription(c, until)
    text = (f"{c.brand}: " + (error or ("без срока" if until is None else f"оплачено до {until:%d.%m.%Y}")))
    return RedirectResponse("/?msg=" + quote(text), status_code=303)


# ---------- users of one client ----------

def _client(slug: str) -> Client | None:
    return next((x for x in clients() if x.slug == slug), None)


def _back(slug: str, msg: str, page_: str = "users") -> RedirectResponse:
    return RedirectResponse(f"/clients/{quote(slug)}/{page_}?msg=" + quote(msg), status_code=303)


def _role_select(current: str = "BEEKEEPER", name: str = "role") -> str:
    return f"<select name='{name}' aria-label='Роль'>" + "".join(
        f"<option value='{k}'{' selected' if k == current else ''}>{v}</option>" for k, v in ROLES.items()) + "</select>"


def _who(u: dict) -> str:
    e = html.escape
    bits = []
    if u.get("username"):
        bits.append("@" + e(u["username"]))
    if u.get("telegram_id"):
        bits.append(f"Telegram ID {u['telegram_id']}")
    if u.get("login"):
        bits.append(f"логин {e(u['login'])}")
    return " · ".join(bits) or "—"


def user_card(slug: str, u: dict, csrf: str) -> str:
    e, uid = html.escape, quote(u["id"])
    state = "<span class='ok'>работает</span>" if u["is_active"] else "<span class='bad'>отключён</span>"
    login_field = "" if u.get("login") else \
        "<input name='login' placeholder='Логин для входа' required minlength='3' maxlength='64' autocomplete='off'>"
    return f"""<div class='card'><div class='head'><div><div class='name'>{e(u['display_name'])}</div>
<p class='muted small'>{_who(u)}</p></div><span class='badge'>{ROLES.get(u['role'], e(u['role']))}</span></div>
<p class='small'>{state} · последний вход: {_fmt_dt(u.get('last_seen_at'))}</p>
<form method='post' action='/clients/{quote(slug)}/users/{uid}' class='inline'><input type='hidden' name='csrf' value='{csrf}'>
{_role_select(u['role'])}<label class='check'><input type='checkbox' name='is_active' value='1'{' checked' if u['is_active'] else ''}> доступ открыт</label>
<button>Сохранить</button></form>
<form method='post' action='/clients/{quote(slug)}/users/{uid}/password' class='inline'><input type='hidden' name='csrf' value='{csrf}'>
{login_field}<button>Временный пароль</button></form></div>"""


def invite_line(slug: str, i: dict, csrf: str) -> str:
    e = html.escape
    who = ("@" + e(i["username"])) if i.get("username") else f"Telegram ID {i.get('telegram_id')}"
    return f"""<form method='post' action='/clients/{quote(slug)}/invites/{quote(i['id'])}/revoke' class='inline'>
<input type='hidden' name='csrf' value='{csrf}'><span>{who} — {ROLES.get(i['role'], e(i['role']))}{(' · ' + e(i['note'])) if i.get('note') else ''}
<span class='muted small'>до {_fmt_dt(i.get('expires_at'))}</span></span><button class='danger'>Отозвать</button></form>"""


def _session(request: Request) -> str | None:
    cookie = request.cookies.get(SESSION_COOKIE)
    return cookie if valid_session(cookie) else None


@app.get("/clients/{slug}/users", response_class=HTMLResponse)
async def users_page(slug: str, request: Request, msg: str = ""):
    cookie = _session(request)
    if not cookie:
        return login_page()
    c = _client(slug)
    if c is None:
        return RedirectResponse("/?msg=" + quote("Клиент не найден"), status_code=303)
    ok, data = await call(c, "GET", "/api/owner/users")
    csrf, e = csrf_token(cookie), html.escape
    note = f"<p class='msg'>{e(msg)}</p>" if msg else ""
    head = f"<p><a href='/'>← Клиенты</a></p><h1>{e(c.brand)}: пользователи</h1><p class='muted'>{e(c.domain)}</p>{note}"
    if not ok:
        return page(head + f"<div class='card'><p class='bad'>{e(data)}</p></div>")
    pending = [i for i in data["invites"] if i["status"] == "PENDING" and not i.get("expired")]
    people = "".join(user_card(slug, u, csrf) for u in data["users"]) or "<p class='muted'>Пока никого.</p>"
    invites = "".join(invite_line(slug, i, csrf) for i in pending) or "<p class='muted small'>Ожидающих приглашений нет.</p>"
    return page(head + f"""<h2>Добавить по Telegram</h2><div class='card'>
<p class='muted small'>Человек получит роль при первом входе через бота. Если он уже входил — роль изменится сразу.</p>
<form method='post' action='/clients/{quote(slug)}/invites' class='inline'><input type='hidden' name='csrf' value='{csrf}'>
<input name='who' placeholder='@username или Telegram ID' required maxlength='64' autocomplete='off'>{_role_select()}
<input name='note' placeholder='Кто это (необязательно)' maxlength='200'><button class='primary'>Пригласить</button></form>
<div class='row'>{invites}</div></div>
<h2>Вход по логину и паролю</h2><div class='card'><p class='muted small'>Для тех, у кого нет Telegram. Временный пароль
покажется один раз, при первом входе человек сменит его.</p>
<form method='post' action='/clients/{quote(slug)}/accounts' class='inline'><input type='hidden' name='csrf' value='{csrf}'>
<input name='first_name' placeholder='Имя' required maxlength='128'><input name='last_name' placeholder='Фамилия' maxlength='128'>
<input name='login' placeholder='Логин' required minlength='3' maxlength='64' autocomplete='off'>{_role_select()}
<button class='primary'>Создать</button></form></div>
<h2>Пользователи ({len(data['users'])})</h2>{people}""", f"{c.brand}: пользователи")


def credentials_page(c: Client, data: dict) -> HTMLResponse:
    e = html.escape
    return page(f"""<p><a href='/clients/{quote(c.slug)}/users'>← Пользователи</a></p><h1>Данные для входа</h1>
<div class='card'><p>{e(data['user']['display_name'])} · {e(c.domain)}</p><p>Логин: <span class='secret'>{e(data['login'])}</span></p>
<p>Временный пароль: <span class='secret'>{e(data['temporary_password'])}</span></p>
<p class='muted small'>Пароль показан один раз — передайте его человеку лично. При первом входе он задаст свой.
Все прежние входы этого человека закрыты.</p></div>""", "Данные для входа")


async def _owner_form(slug: str, request: Request) -> tuple[Client | None, dict | None]:
    data = await form(request)
    if not _checked(request, data):
        return None, None
    return _client(slug), data


def _uuid(v: str) -> str | None:
    try:
        return str(uuid.UUID(v))
    except ValueError:
        return None


@app.post("/clients/{slug}/settings")
async def change_settings(slug: str, request: Request):
    c, data = await _owner_form(slug, request)
    if c is None:
        return RedirectResponse("/", status_code=303)
    value = data.get("admin_in_app") == "1"
    ok, res = await call(c, "PUT", "/api/owner/settings", {"admin_in_app": value})
    text = f"{c.brand}: " + ((("пользователями управляет администратор в приложении" if value
                               else "пользователи и права — только в этой панели")) if ok else res)
    return RedirectResponse("/?msg=" + quote(text), status_code=303)


@app.post("/clients/{slug}/users/{user_id}")
async def change_user(slug: str, user_id: str, request: Request):
    c, data = await _owner_form(slug, request)
    uid = _uuid(user_id)
    if c is None or uid is None:
        return RedirectResponse("/", status_code=303)
    ok, res = await call(c, "PATCH", f"/api/owner/users/{uid}",
                         {"role": data.get("role"), "is_active": data.get("is_active") == "1"})
    return _back(slug, f"Сохранено: {res['display_name']}" if ok else res)


@app.post("/clients/{slug}/users/{user_id}/password", response_class=HTMLResponse)
async def user_password(slug: str, user_id: str, request: Request):
    c, data = await _owner_form(slug, request)
    uid = _uuid(user_id)
    if c is None or uid is None:
        return RedirectResponse("/", status_code=303)
    ok, res = await call(c, "POST", f"/api/owner/users/{uid}/password", {"login": data.get("login") or None})
    return credentials_page(c, res) if ok else _back(slug, res)


@app.post("/clients/{slug}/accounts", response_class=HTMLResponse)
async def new_account(slug: str, request: Request):
    c, data = await _owner_form(slug, request)
    if c is None:
        return RedirectResponse("/", status_code=303)
    ok, res = await call(c, "POST", "/api/owner/accounts", {
        "first_name": data.get("first_name", ""), "last_name": data.get("last_name") or None,
        "login": data.get("login", ""), "role": data.get("role", "")})
    return credentials_page(c, res) if ok else _back(slug, res)


@app.post("/clients/{slug}/invites")
async def new_invite(slug: str, request: Request):
    c, data = await _owner_form(slug, request)
    if c is None:
        return RedirectResponse("/", status_code=303)
    who = data.get("who", "").strip()
    body = {"role": data.get("role", ""), "note": data.get("note") or None}
    if who.isdigit():
        body["telegram_id"] = int(who)
    else:
        body["username"] = who
    ok, res = await call(c, "POST", "/api/owner/invites", body)
    if not ok:
        return _back(slug, res)
    if res.get("kind") == "updated":
        return _back(slug, f"{res['user']['display_name']} уже пользуется приложением — роль изменена")
    return _back(slug, f"Приглашение создано. Отправьте человеку ссылку: https://{c.domain}")


@app.post("/clients/{slug}/invites/{invite_id}/revoke")
async def revoke(slug: str, invite_id: str, request: Request):
    c, _ = await _owner_form(slug, request)
    iid = _uuid(invite_id)
    if c is None or iid is None:
        return RedirectResponse("/", status_code=303)
    ok, res = await call(c, "POST", f"/api/owner/invites/{iid}/revoke")
    return _back(slug, "Приглашение отозвано" if ok else res)


# ---------- activity log ----------

ENTITIES = {"user": "пользователь", "user_invite": "приглашение", "hive": "улей", "installation": "подписка",
            "sale": "продажа", "expense": "расход", "order": "заказ", "customer": "клиент", "payment": "оплата",
            "stock_item": "склад", "stock_movement": "склад", "queen": "матка", "family": "семья", "apiary": "пасека"}
ACTIONS = {"created": "создано", "updated": "изменено", "archived": "в архив", "cancelled": "отменено",
           "invited": "приглашён", "invite_revoked": "приглашение отозвано", "account_created": "вход по паролю создан",
           "password_reset": "временный пароль", "subscription_set": "срок оплаты", "admin_place_set": "где управлять пользователями",
           "device_login": "вход с телефона", "role_from_config": "администратор из настроек"}


def _short(v: dict | None) -> str:
    if not v:
        return ""
    parts = []
    for k, x in list(v.items())[:4]:
        x = ROLES.get(x, x) if isinstance(x, str) else x
        parts.append(f"{k}: {x}")
    return html.escape(", ".join(str(p) for p in parts))[:180]


@app.get("/clients/{slug}/log", response_class=HTMLResponse)
async def log_page(slug: str, request: Request, offset: int = 0, msg: str = ""):
    if not _session(request):
        return login_page()
    c = _client(slug)
    if c is None:
        return RedirectResponse("/", status_code=303)
    ok, data = await call(c, "GET", "/api/owner/audit", params={"offset": max(offset, 0), "limit": 50})
    e = html.escape
    head = f"<p><a href='/'>← Клиенты</a> · <a href='/clients/{quote(slug)}/users'>Пользователи</a></p><h1>{e(c.brand)}: журнал</h1>"
    if not ok:
        return page(head + f"<div class='card'><p class='bad'>{e(data)}</p></div>")
    rows = []
    for r in data["items"]:
        who = e(r.get("user_name") or r.get("comment") or "система")
        what = f"{ENTITIES.get(r['entity_type'], e(r['entity_type']))}: {ACTIONS.get(r['action'], e(r['action']))}"
        hive = f" · улей №{e(r['hive_number'])}" if r.get("hive_number") else ""
        rows.append(f"<div class='row small'><b>{_fmt_dt(r['created_at'])}</b> · {who}<br>{what}{hive}"
                    f"<br><span class='muted'>{_short(r.get('new_value'))}</span></div>")
    more = (f"<p><a href='/clients/{quote(slug)}/log?offset={data['next_offset']}'>Дальше →</a></p>"
            if data.get("next_offset") is not None else "")
    return page(head + f"<div class='card'>{''.join(rows) or '<p class=muted>Записей нет.</p>'}</div>{more}",
                f"{c.brand}: журнал")


@app.get("/health")
def health() -> Response:
    return Response("ok")
