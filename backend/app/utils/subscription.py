"""Server command for the paid-until date of this installation (used by deploy/client.sh extend / block / list).

    python -m app.utils.subscription show            → 2027-10-18 | none
    python -m app.utils.subscription set 2027-10-18
    python -m app.utils.subscription set none        (no limit)
"""
import sys
from datetime import date

from app.config import get_settings
from app.database import SessionLocal
from app.services import subscription_service


def main(argv: list[str]) -> int:
    settings = get_settings()
    if len(argv) >= 1 and argv[0] == "show":
        until = subscription_service.effective_until(settings)
        print(until.isoformat() if until else "none")
        return 0
    if len(argv) == 2 and argv[0] == "set":
        until = None if argv[1] == "none" else date.fromisoformat(argv[1])
        with SessionLocal() as db:
            subscription_service.set_until(db, until, "server")
        print(until.isoformat() if until else "none")
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
