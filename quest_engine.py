import asyncio
import random
import logging
import aiohttp

log = logging.getLogger("quest_engine")

API_BASE = "https://discord.com/api/v9"


class QuestEngine:
    def __init__(self, token: str, user_id: int, notify):
        self.token = token
        self.user_id = user_id
        self.notify = notify
        self.headers = {
            "Authorization": token,
            "Content-Type": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        }
        self._running = False

    async def start(self):
        self._running = True
        async with aiohttp.ClientSession(headers=self.headers) as session:
            await self._run(session)

    def stop(self):
        self._running = False

    async def _run(self, session):
        try:
            quests = await self._fetch(session)
        except Exception as e:
            await self.notify(f"❌ Failed to fetch quests: {e}")
            return

        if not quests:
            await self.notify("✅ No active quests found.")
            return

        await self.notify(f"🎯 Found **{len(quests)}** quests. Starting...")

        for quest in quests:
            if not self._running:
                break
            try:
                await self._complete(session, quest)
            except Exception as e:
                log.exception("Quest failed")
                await self.notify(f"❌ Quest error: {e}")

        if self._running:
            await self.notify("✅ All quests processed.")

    async def _fetch(self, session):
        async with session.get(f"{API_BASE}/users/@me/quests") as r:
            if r.status != 200:
                raise RuntimeError(f"HTTP {r.status}")
            data = await r.json()
            return data.get("quests", [])

    async def _complete(self, session, quest):
        qid = quest["id"]
        name = (
            quest.get("config", {})
            .get("messages", {})
            .get("quest_name", "Unknown Quest")
        )

        async with session.post(f"{API_BASE}/quests/{qid}/accept") as r:
            if r.status not in (200, 204):
                log.warning(f"Accept failed for {name}: {r.status}")

        task_config = quest.get("config", {}).get("taskConfigV2", {})
        tasks = task_config.get("tasks", {})

        for task_id, task_data in tasks.items():
            if not self._running:
                return
            target = task_data.get("target", 0)
            if target <= 0:
                continue

            await self.notify(f"⏳ **{name}** — `{task_id}` — 0/{target}")

            current = task_data.get("current", 0)
            interval = 5 if "VIDEO" in task_id else random.randint(25, 35)

            while current < target and self._running:
                await asyncio.sleep(interval)
                payload = {
                    "task_id": task_id,
                    "progress": min(current + interval, target),
                }
                try:
                    async with session.post(
                        f"{API_BASE}/quests/{qid}/heartbeat", json=payload
                    ) as r:
                        if r.status == 200:
                            resp = await r.json()
                            current = resp.get("progress", payload["progress"])
                            pct = int((current / target) * 100)
                            await self.notify(
                                f"⏳ **{name}** — `{task_id}` — "
                                f"{current}/{target} ({pct}%)"
                            )
                        else:
                            log.warning(f"Heartbeat {r.status} for {name}")
                            break
                except Exception as e:
                    log.error(f"Heartbeat error: {e}")
                    break

            await self.notify(f"✅ **{name}** — `{task_id}` — done.")

        try:
            async with session.post(f"{API_BASE}/quests/{qid}/claim") as r:
                if r.status == 200:
                    await self.notify(f"🎁 **{name}** — reward claimed.")
        except Exception as e:
            log.error(f"Claim error: {e}")
