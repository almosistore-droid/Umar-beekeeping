"""deploy/client.sh: clients of the subscription on one server (run with a fake docker/certbot)."""
import os
import shutil
import subprocess
from datetime import date, timedelta
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "deploy" / "client.sh"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None or shutil.which("openssl") is None,
                                reason="needs bash and openssl")


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    (root / "deploy").mkdir(parents=True)
    shutil.copytree(REPO / "deploy", root / "deploy", dirs_exist_ok=True)
    (root / "nginx").mkdir()
    shutil.copy(REPO / "nginx" / "proxy_params_bee", root / "nginx")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "calls.log"
    for tool in ("docker", "certbot", "curl"):
        fake = bin_dir / tool
        fake.write_text(f"""#!/bin/bash
echo "{tool} $*" >> "{log}"
case "$*" in
  *pg_dump*) echo "-- dump of the client database" ;;
  *urllib*) echo 200 ;;
  *psql*) cat >> "{tmp_path}/restored.sql" ;;
  *api.telegram.org*) echo '{{"ok":true}}' ;;
esac
exit 0
""")
        fake.chmod(0o755)
    # CI runs as a normal user: /var/www/certbot cannot be created there
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "BEE_WEBROOT": str(tmp_path / "webroot"),
           "BEE_CERTS": str(tmp_path / "bee-certs"), "BEE_LETSENCRYPT": str(tmp_path / "letsencrypt")}

    def run(*args, ok=True):
        res = subprocess.run(["bash", str(root / "deploy" / "client.sh"), *args], env=env,
                             capture_output=True, text=True, cwd=root)
        if ok:
            assert res.returncode == 0, res.stdout + res.stderr
        return res

    run.root = root
    run.log = log
    run.tmp = tmp_path
    run.env = env
    return run


def read_env(path: Path) -> dict:
    return dict(line.split("=", 1) for line in path.read_text().splitlines() if line and not line.startswith("#"))


def test_add_creates_private_env_with_generated_secrets(repo):
    repo("add", "asal", "asal.tj")
    env_file = repo.root / "clients" / "asal.env"
    env = read_env(env_file)
    assert env["SLUG"] == "asal" and env["DOMAIN"] == "asal.tj"
    assert env["POSTGRES_PASSWORD"].isalnum() and len(env["POSTGRES_PASSWORD"]) == 32
    assert len(env["JWT_SECRET"]) == 64
    assert env["SUBSCRIPTION_UNTIL"] == (date.today() + timedelta(days=30)).isoformat()
    assert env["UVICORN_WORKERS"] == "1"
    assert len(env["OWNER_TOKEN"]) == 64
    assert oct(env_file.stat().st_mode & 0o777) == "0o600"
    assert "__" not in env_file.read_text()


def test_add_refuses_bad_names_duplicates_and_taken_domains(repo):
    repo("add", "asal", "asal.tj")
    assert repo("add", "asal", "other.tj", ok=False).returncode != 0
    assert "уже у клиента" in repo("add", "honey", "asal.tj", ok=False).stderr
    assert repo("add", "Bad-Name", "x.tj", ok=False).returncode != 0
    assert repo("add", "ok", "not a domain", ok=False).returncode != 0
    assert not (repo.root / "clients" / "honey").exists()


def test_extend_and_block_change_the_paid_date(repo):
    repo("add", "asal", "asal.tj")
    env_file = repo.root / "clients" / "asal.env"
    until = date.fromisoformat(read_env(env_file)["SUBSCRIPTION_UNTIL"])
    repo("extend", "asal", "+1year")
    assert read_env(env_file)["SUBSCRIPTION_UNTIL"] == until.replace(year=until.year + 1).isoformat()
    repo("extend", "asal", "2030-01-31")
    assert read_env(env_file)["SUBSCRIPTION_UNTIL"] == "2030-01-31"
    repo("block", "asal")
    assert read_env(env_file)["SUBSCRIPTION_UNTIL"] == (date.today() - timedelta(days=1)).isoformat()
    # after a block the new period starts today, not from the past date
    repo("extend", "asal", "+30days")
    assert read_env(env_file)["SUBSCRIPTION_UNTIL"] == (date.today() + timedelta(days=30)).isoformat()
    # the date goes into the client's database (it wins over the .env)
    assert "exec -T backend python -m app.utils.subscription set " + read_env(env_file)["SUBSCRIPTION_UNTIL"] \
        in repo.log.read_text()
    repo("extend", "asal", "none")
    assert read_env(env_file)["SUBSCRIPTION_UNTIL"] == ""
    assert "subscription set none" in repo.log.read_text()


def test_start_writes_the_site_and_runs_the_bot_only_with_a_token(repo):
    repo("add", "asal", "asal.tj")
    repo("start", "asal")
    site = (repo.root / "deploy" / "edge" / "sites" / "asal.conf").read_text()
    assert "server_name asal.tj;" in site
    assert "http://asal-backend:8000" in site and "http://asal-frontend:80" in site
    assert "/etc/letsencrypt/live/asal.tj/fullchain.pem" in site
    calls = repo.log.read_text()
    assert "-p bee-asal" in calls and "--profile bot" not in calls
    assert f"certbot certonly --webroot -w {repo.root.parent / 'webroot'} -d asal.tj" in calls

    env_file = repo.root / "clients" / "asal.env"
    env_file.write_text(env_file.read_text().replace("TELEGRAM_BOT_TOKEN=\n", "TELEGRAM_BOT_TOKEN=1:abc\n"))
    repo("update", "asal")
    assert "--profile bot up -d --force-recreate" in repo.log.read_text()


def test_adopt_keeps_the_old_docker_project_and_its_data(repo):
    (repo.root / ".env").write_text("DOMAIN=fayziumar.tj\nPOSTGRES_USER=bee\nPOSTGRES_PASSWORD=abc\n"
                                    "POSTGRES_DB=beekeeping\nUVICORN_WORKERS=2\n")
    repo("adopt", "fayzi")
    env = read_env(repo.root / "clients" / "fayzi.env")
    assert env["COMPOSE_PROJECT"] == "beekeeping"  # → volumes beekeeping_pgdata / beekeeping_uploads
    assert env["UVICORN_WORKERS"] == "1" and env["BRAND_NAME"] == "Fayzi Umar"
    assert len(env["OWNER_TOKEN"]) == 64
    assert (repo.root / ".env.moved").exists() and not (repo.root / ".env").exists()
    calls = repo.log.read_text()
    assert calls.index("docker-compose.yml down") < calls.index("-p beekeeping")


def test_logo_must_be_png(repo):
    repo("add", "asal", "asal.tj")
    bad = repo.root / "x.txt"
    bad.write_text("hello")
    assert "PNG" in repo("logo", "asal", str(bad), ok=False).stderr
    png = REPO / "backend" / "app" / "assets" / "brand" / "logo.png"
    repo("logo", "asal", str(png))
    assert (repo.root / "clients" / "asal" / "logo.png").read_bytes() == png.read_bytes()


def test_edge_site_keeps_the_rate_limits_of_the_single_install():
    single = (REPO / "nginx" / "templates" / "default.conf.template").read_text()
    site = (REPO / "deploy" / "edge" / "site.conf.template").read_text()
    for line in ("location = /api/auth/telegram", "location ~ ^/api/auth/(login-codes|device|password)$",
                 "limit_req zone=auth burst=10 nodelay;", "limit_req zone=api burst=40 nodelay;",
                 'add_header Content-Security-Policy', 'add_header Permissions-Policy'):
        assert line in single and line in site, line


def test_owner_panel_setup(repo):
    repo("add", "asal", "asal.tj")
    old = repo.root / "clients" / "old.env"
    old.write_text("SLUG=old\nDOMAIN=old.tj\nPOSTGRES_USER=bee\nPOSTGRES_DB=beekeeping\n")
    r = repo("owner", "admin.fayzi.tj")
    owner_env = read_env(repo.root / "deploy" / "owner.env")
    assert owner_env["DOMAIN"] == "admin.fayzi.tj" and len(owner_env["OWNER_SECRET"]) == 64
    assert owner_env["OWNER_PASSWORD"] in r.stdout
    assert oct((repo.root / "deploy" / "owner.env").stat().st_mode & 0o777) == "0o600"
    assert len(read_env(old)["OWNER_TOKEN"]) == 64       # the client without a key got one
    site = (repo.root / "deploy" / "edge" / "sites" / "_owner.conf").read_text()
    assert "server_name admin.fayzi.tj;" in site and "http://bee-owner:8000" in site
    calls = repo.log.read_text()
    assert "-p bee-old" in calls and "owner.yml" in calls
    # again: the password stays, a new one only on request
    again = repo("owner", "admin.fayzi.tj")
    assert owner_env["OWNER_PASSWORD"] not in again.stdout
    r = repo("owner-password")
    assert read_env(repo.root / "deploy" / "owner.env")["OWNER_PASSWORD"] in r.stdout


def test_public_sites_hide_the_owner_api():
    site = (REPO / "deploy" / "edge" / "site.conf.template").read_text()
    assert "location /api/owner/ { return 404; }" in site


@pytest.mark.parametrize("has_key", [False, True])
def test_harden_never_locks_out_without_a_key(tmp_path, has_key):
    keys = tmp_path / "authorized_keys"
    if has_key:
        keys.write_text("ssh-ed25519 AAAA test")
    env = {**os.environ, "DRY_RUN": "1", "HARDEN_KEYS": str(keys), "HARDEN_ETC": str(tmp_path / "etc")}
    res = subprocess.run(["bash", str(REPO / "deploy" / "harden.sh"), "--ssh-keys-only"], env=env,
                         capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    assert "ufw allow 443/tcp" in res.stdout and "ufw --force enable" in res.stdout
    assert ("90-bee.conf" in res.stdout) is has_key
    if not has_key:
        assert "пароли НЕ отключаю" in res.stdout


def test_backup_encrypted_to_telegram_and_decrypt(repo, tmp_path):
    repo("add", "asal", "asal.tj")
    (repo.root / "deploy" / "backup.env").write_text("BACKUP_BOT_TOKEN=123456:" + "a" * 30 +
                                                     "\nBACKUP_CHAT_ID=1324431208\nBACKUP_PASSWORD=secret-pass-1\n")
    r = repo("backup", "all", "--send")
    assert "отправлена в Telegram" in r.stdout
    calls = repo.log.read_text()
    assert "sendDocument" in calls and "chat_id=1324431208" in calls
    assert "secret-pass-1" not in calls                      # the password is never on a command line
    dumps = list((repo.root / "backups").glob("asal-*.sql.gz"))
    assert len(dumps) == 1 and not list((repo.root / "backups").glob("*.enc"))   # encrypted copy not kept
    assert oct(dumps[0].stat().st_mode & 0o777) == "0o600"

    # the file that went to Telegram opens with the password
    enc = tmp_path / "copy.sql.gz.enc"
    subprocess.run(["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-iter", "200000", "-salt", "-pass", "pass:secret-pass-1",
                    "-in", str(dumps[0]), "-out", str(enc)], check=True)
    repo("decrypt", str(enc))
    assert (tmp_path / "copy.sql.gz").read_bytes() == dumps[0].read_bytes()


def test_restore_makes_a_safety_copy_first(repo, tmp_path):
    import gzip
    repo("add", "asal", "asal.tj")
    dump = tmp_path / "old.sql.gz"
    dump.write_bytes(gzip.compress(b"CREATE TABLE hives (id int);\n"))
    env = dict(os.environ)
    res = subprocess.run(["bash", str(repo.root / "deploy" / "client.sh"), "restore", "asal", str(dump)],
                         input="wrong\n", capture_output=True, text=True, cwd=repo.root,
                         env={**env, "PATH": f"{tmp_path / 'bin'}:{env['PATH']}"})
    assert res.returncode != 0 and "отменено" in res.stderr   # needs the client's name typed
    res = subprocess.run(["bash", str(repo.root / "deploy" / "client.sh"), "restore", "asal", str(dump)],
                         input="asal\n", capture_output=True, text=True, cwd=repo.root,
                         env={**env, "PATH": f"{tmp_path / 'bin'}:{env['PATH']}", "BEE_WEBROOT": str(tmp_path / "w")})
    assert res.returncode == 0, res.stderr
    calls = repo.log.read_text()
    assert calls.index("pg_dump") < calls.index("DROP SCHEMA public CASCADE")   # copy before replacing
    assert "CREATE TABLE hives" in (tmp_path / "restored.sql").read_text()


def test_update_backs_up_first_and_rollback(repo):
    repo("add", "asal", "asal.tj")
    repo("update", "all")
    calls = repo.log.read_text()
    assert calls.index("pg_dump") < calls.index("up -d --force-recreate")
    r = repo("rollback")
    assert "предыдущая версия" in r.stdout.lower() or "Возвращена" in r.stdout
    assert "tag beekeeping-backend:previous beekeeping-backend:latest" in repo.log.read_text()


def test_check_and_cron(repo, tmp_path):
    repo("add", "asal", "asal.tj")
    r = repo("check")
    assert "Всё в порядке" in r.stdout
    cron = tmp_path / "cron"
    import os as _os
    res = subprocess.run(["bash", str(repo.root / "deploy" / "client.sh"), "cron"], capture_output=True, text=True,
                         env={**_os.environ, "BEE_CRON_FILE": str(cron)})
    assert res.returncode == 0, res.stderr
    text = cron.read_text()
    assert "backup all --send" in text and "renew" in text and "check --alert" in text


def make_cert(dir: Path, name: str, *hosts: str) -> tuple[Path, Path]:
    cert, key = dir / f"{name}.pem", dir / f"{name}.key"
    san = ",".join(f"DNS:{h}" for h in hosts)
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "5475",
                    "-subj", f"/CN={hosts[0]}", "-addext", f"subjectAltName={san}",
                    "-keyout", str(key), "-out", str(cert)], check=True, capture_output=True)
    return cert, key


def test_own_certificate_replaces_lets_encrypt(repo):
    """Cloudflare Origin certificate: no port 80, no renewal; sites point to /etc/bee-certs."""
    repo("add", "asal", "asal.tj")
    repo("owner", "admin.asal.tj")
    cert, key = make_cert(repo.tmp, "origin", "asal.tj", "*.asal.tj")
    _, other_key = make_cert(repo.tmp, "other", "other.tj")

    assert "не подходит" in repo("cert-files", str(cert), str(other_key), ok=False).stderr
    foreign, foreign_key = make_cert(repo.tmp, "foreign", "foreign.tj")
    assert "ни к одному домену" in repo("cert-files", str(foreign), str(foreign_key), ok=False).stderr

    r = repo("cert-files", str(cert), str(key))
    assert "asal.tj: свой сертификат" in r.stdout and "admin.asal.tj: свой сертификат" in r.stdout
    stored = repo.tmp / "bee-certs" / "asal.tj" / "privkey.pem"
    assert stored.read_bytes() == key.read_bytes()
    assert oct(stored.stat().st_mode & 0o777) == "0o600"
    for name, domain in (("asal", "asal.tj"), ("_owner", "admin.asal.tj")):
        site = (repo.root / "deploy" / "edge" / "sites" / f"{name}.conf").read_text()
        assert f"ssl_certificate     /etc/bee-certs/{domain}/fullchain.pem;" in site
        assert f"ssl_certificate_key /etc/bee-certs/{domain}/privkey.pem;" in site
        assert "__CERT__" not in site and "letsencrypt" not in site

    # starting again asks Let's Encrypt for nothing
    repo.log.write_text("")
    repo("start", "asal")
    assert "certbot" not in repo.log.read_text()
    assert "/etc/bee-certs/asal.tj/" in (repo.root / "deploy" / "edge" / "sites" / "asal.conf").read_text()
    # the expiry check reads the own certificate (valid 15 years → no warning)
    assert "истекает" not in repo("check", "asal").stdout
    # renewal skips own certificates, still renews the Let's Encrypt ones
    renewal = repo.tmp / "letsencrypt" / "renewal"
    renewal.mkdir(parents=True)
    (renewal / "asal.tj.conf").write_text("")
    (renewal / "old.tj.conf").write_text("")
    repo.log.write_text("")
    repo("renew")
    calls = repo.log.read_text()
    assert "--cert-name old.tj" in calls and "--cert-name asal.tj" not in calls


def test_edge_mounts_own_certificates_and_trusts_only_cloudflare_for_real_ip():
    compose = (REPO / "deploy" / "edge" / "docker-compose.yml").read_text()
    assert "/etc/bee-certs:/etc/bee-certs:ro" in compose
    cf = (REPO / "deploy" / "edge" / "conf.d" / "10-cloudflare.conf").read_text()
    assert "real_ip_header CF-Connecting-IP;" in cf
    assert "set_real_ip_from 0.0.0.0/0" not in cf and cf.count("set_real_ip_from") >= 15


def test_build_retries_when_docker_hub_is_slow(repo):
    fake = repo.tmp / "bin" / "docker"
    count = repo.tmp / "builds"
    fake.write_text(f"""#!/bin/bash
echo "docker $*" >> "{repo.log}"
if [[ "$1" == build ]]; then
  n=$(cat "{count}" 2>/dev/null || echo 0); echo $((n + 1)) > "{count}"
  [[ $n -lt 2 ]] && exit 1   # the first two builds time out
fi
exit 0
""")
    repo.env["BEE_RETRY_SLEEP"] = "0"
    r = repo("build")
    assert "попытка 2 из 3" in r.stdout and "попытка 3 из 3" in r.stdout and "собрана" in r.stdout
    count.write_text("-10")  # every build fails now
    r = repo("build", ok=False)
    assert r.returncode != 0 and "сборка backend не удалась" in r.stderr
