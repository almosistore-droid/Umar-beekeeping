"""Stage 8: every few minutes asks the backend to send the reminders that are due (one message each).

The backend decides what is due, who gets it and keeps the log, so a restart never sends anything twice;
outside 7:00–21:00 (apiary time) it simply sends nothing.
"""
import asyncio
import logging
import os

import backend_client

log = logging.getLogger(__name__)
EVERY = max(60, int(os.environ.get("NOTIFY_EVERY_SECONDS", "300")))


async def run_forever() -> None:
    await asyncio.sleep(20)  # let the backend start first
    while True:
        status, body = await backend_client.post("/api/notifications/dispatch", {})
        if status == 200:
            if body.get("sent") or body.get("failed"):
                log.info("reminders: sent %s, failed %s, left %s", body.get("sent"), body.get("failed"), body.get("left"))
        else:
            log.warning("reminders: backend answered %s %s", status, body.get("detail", ""))
        await asyncio.sleep(EVERY)
