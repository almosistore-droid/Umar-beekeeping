"""Stage 5: permanent hive QR codes, scanner resolution, printable labels, registration by QR."""
import base64
import uuid

import pytest

from app.config import get_settings
from app.services import qr_service, telegram_bot


@pytest.fixture
def apiary(client, beekeeper):
    return client.post("/api/apiaries", json={"name": "Пасека №1"}, headers=beekeeper).json()


@pytest.fixture
def apiary2(client, beekeeper):
    return client.post("/api/apiaries", json={"name": "Горная"}, headers=beekeeper).json()


@pytest.fixture
def bot_configured(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "telegram_bot_username", "umar_bee_bot")
    monkeypatch.setattr(s, "telegram_webapp_short_name", "app")
    return s


def hive(client, headers, apiary_id, number, **kw):
    r = client.post("/api/hives", json={"apiary_id": apiary_id, "hive_number": number,
                                        "family": {"strength": "MEDIUM"}, **kw}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def qr(client, headers, hive_id):
    r = client.get(f"/api/hives/{hive_id}/qr", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


# ---------- US1 permanent QR ----------

def test_new_hive_gets_qr_with_deep_link(client, beekeeper, apiary, bot_configured):
    h = hive(client, beekeeper, apiary["id"], "27")
    body = qr(client, beekeeper, h["id"])
    assert body["code"] == f"hive_{h['id']}"
    assert body["deep_link"] == f"https://t.me/umar_bee_bot/app?startapp=hive_{h['id']}"
    assert body["content"] == body["deep_link"] and body["deep_link_ready"] is True
    assert body["svg_data_uri"].startswith("data:image/svg+xml;base64,")
    svg = base64.b64decode(body["svg_data_uri"].split(",", 1)[1]).decode()
    # standalone SVG: without xmlns an <img src="data:…"> shows nothing
    assert svg.startswith('<svg xmlns="http://www.w3.org/2000/svg"')
    assert body["hive_number"] == "27" and body["apiary_name"] == "Пасека №1" and body["print_count"] == 0


def test_deep_link_variants(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "telegram_bot_username", "")
    monkeypatch.setattr(s, "telegram_webapp_short_name", "")
    assert qr_service.deep_link("hive_x") is None and qr_service.qr_content("hive_x") == "hive_x"
    monkeypatch.setattr(s, "telegram_bot_username", "@umar_bee_bot")
    assert qr_service.deep_link("hive_x") == "https://t.me/umar_bee_bot?startapp=hive_x"
    # Telegram limits start_param to 64 chars of [A-Za-z0-9_-]
    code = qr_service.payload(uuid.uuid4())
    assert len(code) <= 64 and all(c.isalnum() or c in "_-" for c in code)


def test_qr_without_bot_is_flagged(client, beekeeper, apiary, monkeypatch):
    monkeypatch.setattr(get_settings(), "telegram_bot_username", "")
    h = hive(client, beekeeper, apiary["id"], "1")
    body = qr(client, beekeeper, h["id"])
    assert body["deep_link"] is None and body["deep_link_ready"] is False and body["content"] == body["code"]


def test_qr_never_changes(client, beekeeper, apiary, apiary2):
    h = hive(client, beekeeper, apiary["id"], "5")
    code = qr(client, beekeeper, h["id"])["code"]
    # number, queen, strength, health, apiary, family
    r = client.put(f"/api/hives/{h['id']}", json={"hive_number": "55", "version": h["version"]}, headers=beekeeper)
    assert r.status_code == 200, r.text
    client.post("/api/queens", json={"queen_code": "M-1", "hive_id": h["id"]}, headers=beekeeper)
    client.patch(f"/api/hives/{h['id']}/family", json={"strength": "STRONG"}, headers=beekeeper)
    client.post(f"/api/hives/{h['id']}/move", json={"to_apiary_id": apiary2["id"]}, headers=beekeeper)
    client.post(f"/api/hives/{h['id']}/families", json={"strength": "WEAK"}, headers=beekeeper)
    after = qr(client, beekeeper, h["id"])
    assert after["code"] == code and after["hive_number"] == "55" and after["apiary_name"] == "Горная"
    # POST is idempotent and keeps the code
    r = client.post(f"/api/hives/{h['id']}/qr", headers=beekeeper)
    assert r.status_code == 200 and r.json()["code"] == code


def test_split_hive_gets_qr(client, beekeeper, apiary):
    src = hive(client, beekeeper, apiary["id"], "10")
    new = client.post(f"/api/hives/{src['id']}/split", json={"new_hive_number": "11"}, headers=beekeeper).json()["new_hive"]
    assert qr(client, beekeeper, new["id"])["code"] == f"hive_{new['id']}"


def test_viewer_reads_but_cannot_change_qr(client, beekeeper, apiary, as_role):
    h = hive(client, beekeeper, apiary["id"], "3")
    viewer = as_role("VIEWER")
    assert client.get(f"/api/hives/{h['id']}/qr", headers=viewer).status_code == 200
    assert client.post(f"/api/hives/{h['id']}/qr", headers=viewer).status_code == 403
    assert client.get(f"/api/hives/{uuid.uuid4()}/qr", headers=viewer).status_code == 404


# ---------- US3 scanner ----------

@pytest.mark.parametrize("fmt", [
    "https://t.me/umar_bee_bot/app?startapp=hive_{id}",
    "https://t.me/umar_bee_bot?startapp=hive_{id}",
    "https://bee.example.com/?tgWebAppStartParam=hive_{id}",
    "hive_{id}",
    "  HIVE_{ID}  ",
    "{id}",
    "https://bee.example.com/hives/{id}",
    "https://bee.example.com/hives/{id}/edit",
])
def test_resolve_formats(client, beekeeper, apiary, fmt):
    h = hive(client, beekeeper, apiary["id"], "8")
    code = fmt.format(id=h["id"], ID=h["id"].upper())
    r = client.get("/api/qr/resolve", params={"code": code}, headers=beekeeper)
    assert r.status_code == 200, r.text
    assert r.json() == {"status": "found", "hive_id": h["id"], "hive_number": "8", "apiary_name": "Пасека №1",
                        "is_archived": False, "can_register": False}


@pytest.mark.parametrize("code", ["", "https://example.com", "hello", "hive_123", "hive_" + "z" * 36])
def test_resolve_invalid(client, beekeeper, code):
    r = client.get("/api/qr/resolve", params={"code": code}, headers=beekeeper)
    assert r.json()["status"] == "invalid" and r.json()["hive_id"] is None


def test_resolve_unknown_offers_registration_to_managers(client, beekeeper, as_role):
    new_id = str(uuid.uuid4())
    r = client.get("/api/qr/resolve", params={"code": f"hive_{new_id}"}, headers=beekeeper).json()
    assert r["status"] == "unknown" and r["hive_id"] == new_id and r["can_register"] is True
    r = client.get("/api/qr/resolve", params={"code": f"hive_{new_id}"}, headers=as_role("ASSISTANT")).json()
    assert r["status"] == "unknown" and r["can_register"] is False


def test_resolve_archived_hive(client, beekeeper, apiary):
    h = hive(client, beekeeper, apiary["id"], "4")
    client.put(f"/api/hives/{h['id']}", json={"status": "SOLD", "version": h["version"]}, headers=beekeeper)
    r = client.get("/api/qr/resolve", params={"code": f"hive_{h['id']}"}, headers=beekeeper).json()
    assert r["status"] == "found" and r["is_archived"] is True


def test_resolve_requires_login(client):
    assert client.get("/api/qr/resolve", params={"code": "x"}).status_code == 401


# ---------- US5 registration ----------

def test_register_hive_from_blank_label(client, beekeeper, apiary):
    new_id = str(uuid.uuid4())
    h = hive(client, beekeeper, apiary["id"], "40", id=new_id)
    assert h["id"] == new_id
    assert qr(client, beekeeper, new_id)["code"] == f"hive_{new_id}"
    history = client.get(f"/api/hives/{new_id}/history", headers=beekeeper).json()
    assert history[-1]["action"] == "created" and "QR" in history[-1]["comment"]
    r = client.post("/api/hives", json={"id": new_id, "apiary_id": apiary["id"], "hive_number": "41"}, headers=beekeeper)
    assert r.status_code == 409 and "уже привязан к улью №40" in r.json()["detail"]


# ---------- US2 labels ----------

def pdf_pages(data: bytes) -> int:
    return data.count(b"/Type /Page\n") or data.count(b"/Type /Page ") or data.count(b"/Type /Page>")


def test_labels_pdf_for_apiary_with_blanks(client, beekeeper, apiary, apiary2):
    hs = [hive(client, beekeeper, apiary["id"], n) for n in ("2", "10", "1")]
    hive(client, beekeeper, apiary2["id"], "99")
    r = client.post("/api/qr/labels", json={"apiary_id": apiary["id"], "blank_count": 11}, headers=beekeeper)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    assert "attachment" in r.headers["content-disposition"]
    assert r.content.startswith(b"%PDF")
    # 3 hives + 11 blanks = 14 labels → 2 pages of 12
    assert b"/Count 2" in r.content
    for h in hs:
        body = qr(client, beekeeper, h["id"])
        assert body["print_count"] == 1 and body["last_printed_at"]
        events = client.get(f"/api/hives/{h['id']}/history", headers=beekeeper).json()
        assert events[0]["action"] == "qr_printed"


def test_labels_refusals(client, beekeeper, apiary, as_role):
    r = client.post("/api/qr/labels", json={}, headers=beekeeper)
    assert r.status_code == 422 and "Выберите ульи" in r.json()["detail"]
    r = client.post("/api/qr/labels", json={"blank_count": 61}, headers=beekeeper)
    assert r.status_code == 422
    r = client.post("/api/qr/labels", json={"apiary_id": apiary["id"]}, headers=beekeeper)
    assert r.status_code == 422 and "нет ульев" in r.json()["detail"]
    r = client.post("/api/qr/labels", json={"hive_ids": [str(uuid.uuid4())]}, headers=beekeeper)
    assert r.status_code == 404
    assert client.post("/api/qr/labels", json={"blank_count": 1}, headers=as_role("VIEWER")).status_code == 403
    assert client.post("/api/qr/labels", json={"blank_count": 1}, headers=as_role("ASSISTANT")).status_code == 200


def test_labels_sent_by_bot_to_own_chat(client, beekeeper, apiary, monkeypatch):
    h = hive(client, beekeeper, apiary["id"], "7")
    sent = {}

    def fake_send(chat_id, filename, content, caption=None):
        sent.update(chat_id=chat_id, filename=filename, pdf=content[:4], caption=caption)
    monkeypatch.setattr(telegram_bot, "send_document", fake_send)
    r = client.post("/api/qr/labels", json={"hive_ids": [h["id"]], "blank_count": 1, "delivery": "telegram"}, headers=beekeeper)
    assert r.status_code == 200, r.text
    assert r.json() == {"sent": True, "labels": 2}
    assert sent["chat_id"] == 3000 and sent["pdf"] == b"%PDF" and sent["filename"].endswith(".pdf")
    assert "2 наклейки" in sent["caption"]
    assert qr(client, beekeeper, h["id"])["print_count"] == 1


def test_labels_bot_failure_marks_nothing(client, beekeeper, apiary, monkeypatch):
    h = hive(client, beekeeper, apiary["id"], "7")

    def failing(*_a, **_k):
        raise telegram_bot.TelegramUnavailable("Telegram не принял файл")
    monkeypatch.setattr(telegram_bot, "send_document", failing)
    r = client.post("/api/qr/labels", json={"hive_ids": [h["id"]], "delivery": "telegram"}, headers=beekeeper)
    assert r.status_code == 502 and "Telegram" in r.json()["detail"]
    assert qr(client, beekeeper, h["id"])["print_count"] == 0


def test_send_document_without_token(monkeypatch):
    monkeypatch.setattr(get_settings(), "telegram_bot_token", "")
    with pytest.raises(Exception) as exc:
        telegram_bot.send_document(1, "a.pdf", b"%PDF")
    assert "Бот не настроен" in str(exc.value)


def test_qr_status(client, beekeeper, monkeypatch):
    monkeypatch.setattr(get_settings(), "telegram_bot_username", "")
    assert client.get("/api/qr/status", headers=beekeeper).json() == {"deep_link_ready": False, "example_link": None}
    monkeypatch.setattr(get_settings(), "telegram_bot_username", "umar_bee_bot")
    monkeypatch.setattr(get_settings(), "telegram_webapp_short_name", "")
    body = client.get("/api/qr/status", headers=beekeeper).json()
    assert body["deep_link_ready"] is True and body["example_link"].startswith("https://t.me/umar_bee_bot?startapp=")
