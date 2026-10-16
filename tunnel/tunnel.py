"""Dev tunnel for testing the Mini App inside Telegram from a laptop.

Runs a free Cloudflare quick tunnel (https://xxxx.trycloudflare.com → the Vite dev server) and keeps it
usable without manual steps:

* every new tunnel address is set on the bot's menu button through the Bot API (setChatMenuButton),
  so there is no need to paste it into @BotFather;
* the address is checked every 30 s; quick tunnels die after some hours or after the laptop sleeps
  ("Tunnel not found", the name stops resolving) — after 4 failed checks cloudflared is restarted and
  the new address is set on the button.

Standard library only. Configuration (environment):
  TELEGRAM_BOT_TOKEN  bot token (the real one from .env; placeholders are ignored)
  TUNNEL_TARGET       what to expose, default http://frontend:5173
  MENU_BUTTON_TEXT    button title, default «Пасека»
  URL_FILE            optional file where the current address is written (the dev bot reads it)
"""
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

URL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
CHECK_EVERY = 30        # seconds between health checks
FIRST_CHECK_AFTER = 45  # DNS for a new quick tunnel needs a moment
MAX_FAILURES = 4        # 4 × 30 s ≈ 2 minutes of a dead address → new tunnel
WAIT_FOR_URL = 90       # cloudflared normally prints the address within seconds


def log(msg: str) -> None:
    print(f"[tunnel] {msg}", flush=True)


def find_url(line: str) -> str | None:
    """The tunnel address from a cloudflared log line (not Cloudflare's own api.trycloudflare.com)."""
    for m in URL_RE.finditer(line):
        if m.group(0) != "https://api.trycloudflare.com":
            return m.group(0)
    return None


def token_usable(token: str) -> bool:
    return bool(token) and ":" in token and not token.endswith("local-test-token")


def menu_button_payload(url: str, text: str) -> dict:
    return {"menu_button": {"type": "web_app", "text": text, "web_app": {"url": url}}}


def set_menu_button(token: str, url: str, text: str, opener=urllib.request.urlopen) -> bool:
    """Default menu button for every chat with the bot = the same thing as @BotFather → Menu Button."""
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/setChatMenuButton",
        data=json.dumps(menu_button_payload(url, text)).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with opener(req, timeout=15) as resp:
            ok = json.loads(resp.read().decode()).get("ok") is True
    except (urllib.error.URLError, ValueError, OSError) as exc:
        log(f"MENU BUTTON FAILED: {exc} (не удалось обновить кнопку в Telegram)")
        return False
    if not ok:
        log("MENU BUTTON FAILED: Telegram ответил ошибкой — проверьте TELEGRAM_BOT_TOKEN в .env")
    if ok:
        log(f"MENU BUTTON OK -> {url}  (кнопка «{text}» в боте теперь открывает этот адрес)")
    return ok


def write_url_file(path: str, url: str) -> None:
    """Share the current address with the dev bot (its «Открыть пасеку» button must open the live tunnel)."""
    if not path:
        return
    try:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(url)
        os.replace(tmp, path)
    except OSError as exc:
        log(f"не удалось записать адрес в {path}: {exc}")


def is_alive(url: str, opener=urllib.request.urlopen) -> bool:
    try:
        with opener(urllib.request.Request(url, method="GET"), timeout=10) as resp:
            return 200 <= resp.status < 500
    except urllib.error.HTTPError as exc:
        return exc.code < 500 and exc.code != 404  # 530/1033 etc. = tunnel gone
    except (urllib.error.URLError, OSError, ValueError):
        return False


class Supervisor:
    def __init__(self, target: str, token: str, text: str, url_file: str = ""):
        self.target, self.token, self.text, self.url_file = target, token, text, url_file
        self.proc: subprocess.Popen | None = None
        self.url: str | None = None
        self._found = threading.Event()

    def _read_output(self, proc: subprocess.Popen) -> None:
        for raw in proc.stdout:  # cloudflared logs to stderr; merged into stdout
            line = raw.rstrip()
            url = find_url(line)
            if url and not self._found.is_set():
                self.url = url
                self._found.set()
            if "ERR" in line or url:
                print(line, flush=True)

    def start(self) -> bool:
        self._found.clear()
        self.url = None
        self.proc = subprocess.Popen(
            ["cloudflared", "tunnel", "--no-autoupdate", "--url", self.target],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
        )
        threading.Thread(target=self._read_output, args=(self.proc,), daemon=True).start()
        if not self._found.wait(WAIT_FOR_URL):
            log("cloudflared не выдал адрес, перезапускаю…")
            self.stop()
            return False
        log("=" * 60)
        log(f"TUNNEL URL: {self.url}")
        log("=" * 60)
        write_url_file(self.url_file, self.url)
        if token_usable(self.token):
            set_menu_button(self.token, self.url, self.text)
        else:
            log("MENU BUTTON SKIPPED: TELEGRAM_BOT_TOKEN не задан в .env — вставьте адрес в @BotFather → Menu Button вручную")
        return True

    def stop(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(10)
            except subprocess.TimeoutExpired:
                self.proc.kill()

    def run_forever(self) -> None:
        while True:
            if not self.start():
                time.sleep(5)
                continue
            time.sleep(FIRST_CHECK_AFTER)
            failures = 0
            while True:
                if self.proc.poll() is not None:
                    log("cloudflared остановился — запускаю новый туннель")
                    break
                if is_alive(self.url):
                    failures = 0
                else:
                    failures += 1
                    log(f"адрес не отвечает ({failures}/{MAX_FAILURES})")
                    if failures >= MAX_FAILURES:
                        log("туннель умер — создаю новый адрес")
                        break
                time.sleep(CHECK_EVERY)
            self.stop()


def main() -> None:
    sup = Supervisor(
        target=os.environ.get("TUNNEL_TARGET", "http://frontend:5173"),
        token=os.environ.get("TELEGRAM_BOT_TOKEN", "").strip(),
        text=os.environ.get("MENU_BUTTON_TEXT", "Пасека"),
        url_file=os.environ.get("URL_FILE", ""),
    )
    try:
        sup.run_forever()
    except KeyboardInterrupt:
        sup.stop()
        sys.exit(0)


if __name__ == "__main__":
    main()
