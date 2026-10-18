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
    for tool in ("docker", "certbot"):
        fake = bin_dir / tool
        fake.write_text(f'#!/bin/bash\necho "{tool} $*" >> "{log}"\nexit 0\n')
        fake.chmod(0o755)
    # CI runs as a normal user: /var/www/certbot cannot be created there
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "BEE_WEBROOT": str(tmp_path / "webroot")}

    def run(*args, ok=True):
        res = subprocess.run(["bash", str(root / "deploy" / "client.sh"), *args], env=env,
                             capture_output=True, text=True, cwd=root)
        if ok:
            assert res.returncode == 0, res.stdout + res.stderr
        return res

    run.root = root
    run.log = log
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
