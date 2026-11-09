import json
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from didi.food import clean_name, is_edible, keywords, pretty

MAX_MEMBERS = 2
MAX_BOUGHT = 50


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def default_store_path():
    return Path.cwd() / "data" / "household.json"


def _empty():
    return {"members": [], "items": [], "sessions": {}, "picked": [], "shop_done": False}


def _item(name, user, status):
    display = pretty(name)
    return {
        "id": str(uuid4()),
        "name": display,
        "norm": clean_name(display),
        "keywords": keywords(display),
        "edible": is_edible(display),
        "status": status,
        "addedBy": user["name"],
        "addedAt": now_iso(),
        "boughtAt": now_iso() if status == "bought" else None,
    }


class Store:
    def __init__(self, file_path):
        self.path = Path(file_path)
        self.state = _empty()
        self._load()

    def _load(self):
        if not self.path.exists():
            self.state = _empty()
            return
        raw = self.path.read_text(encoding="utf-8").strip()
        if not raw:
            self.state = _empty()
            return
        parsed = json.loads(raw)
        self.state = {
            "members": parsed.get("members") or [],
            "items": parsed.get("items") or [],
            "sessions": parsed.get("sessions") or {},
            "picked": parsed.get("picked") or [],
            "shop_done": bool(parsed.get("shop_done")),
        }

    def _save(self):
        bought = [item for item in self.state["items"] if item["status"] == "bought"]
        pending = [item for item in self.state["items"] if item["status"] == "pending"]
        bought.sort(key=lambda item: item.get("boughtAt") or "", reverse=True)
        self.state["items"] = pending + bought[:MAX_BOUGHT]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, self.path)

    def _match_pending(self, query):
        wanted = clean_name(query)
        keys = keywords(query)
        pending = [item for item in self.state["items"] if item["status"] == "pending"]
        exact = [item for item in pending if item["norm"] == wanted]
        if exact:
            return exact
        if keys:
            by_key = [item for item in pending if any(key in keys for key in item["keywords"])]
            if by_key:
                return by_key
        if not wanted:
            return []
        return [item for item in pending if wanted in item["norm"] or item["norm"] in wanted]

    def authorize(self, user):
        user_id = str(user["id"])
        name = str(user.get("name") or "Alguien")[:40]
        existing = next((member for member in self.state["members"] if member["id"] == user_id), None)
        if existing:
            existing["name"] = name
            self._save()
            return {"ok": True, "joined": False}
        if len(self.state["members"]) >= MAX_MEMBERS:
            return {"ok": False, "joined": False}
        self.state["members"].append({"id": user_id, "name": name, "joinedAt": now_iso()})
        self._save()
        return {"ok": True, "joined": True}

    def leave(self, user_id):
        user_id = str(user_id)
        before = len(self.state["members"])
        self.state["members"] = [member for member in self.state["members"] if member["id"] != user_id]
        self.state["sessions"].pop(user_id, None)
        self._save()
        return before != len(self.state["members"])

    def members(self):
        return [dict(member) for member in self.state["members"]]

    def items(self):
        copied = []
        for item in self.state["items"]:
            clone = dict(item)
            clone["keywords"] = list(item["keywords"])
            copied.append(clone)
        return copied

    def add_items(self, names, user):
        added = []
        duplicates = []
        for name in names:
            display = pretty(name)
            norm_name = clean_name(display)
            if not display or not norm_name:
                continue
            exists = any(
                item["status"] == "pending" and item["norm"] == norm_name for item in self.state["items"]
            )
            if exists:
                duplicates.append(display)
                continue
            item = _item(display, user, "pending")
            self.state["items"].append(item)
            added.append(item)
        if added:
            self.state["shop_done"] = False
            self._save()
        return {"added": added, "duplicates": duplicates}

    def _pending_sorted(self):
        pending = [item for item in self.state["items"] if item["status"] == "pending"]
        pending.sort(key=lambda item: item["addedAt"])
        return pending

    def remove_items(self, names):
        removed = []
        missing = []
        removed_ids = set()
        pending = self._pending_sorted()
        for name in names:
            token = str(name).strip()
            if token.isdigit():
                position = int(token)
                if 1 <= position <= len(pending) and pending[position - 1]["id"] not in removed_ids:
                    item = pending[position - 1]
                    removed_ids.add(item["id"])
                    removed.append(item)
                else:
                    missing.append(token)
                continue
            hits = [hit for hit in self._match_pending(name) if hit["id"] not in removed_ids]
            if not hits:
                missing.append(pretty(name))
                continue
            for hit in hits:
                removed_ids.add(hit["id"])
                removed.append(hit)
        if removed_ids:
            self.state["items"] = [item for item in self.state["items"] if item["id"] not in removed_ids]
            self.state["shop_done"] = False
            self._save()
        return {"removed": removed, "missing": missing}

    def buy_items(self, names, user):
        bought = []
        seen = set()
        for name in names:
            hits = self._match_pending(name)
            if not hits:
                display = pretty(name)
                norm_name = clean_name(display)
                if not norm_name or any(item["norm"] == norm_name for item in bought):
                    continue
                created = _item(display, user, "bought")
                bought.append(created)
                continue
            for hit in hits:
                if hit["id"] in seen:
                    continue
                seen.add(hit["id"])
                bought.append(hit)
        if not bought:
            return {"bought": []}
        self.state["items"] = [item for item in self.state["items"] if item["id"] not in seen]
        self.state.setdefault("picked", []).extend(
            {"name": item["name"], "keywords": list(item["keywords"]), "edible": item["edible"]}
            for item in bought
        )
        self._refresh_shop_done()
        self._save()
        return {"bought": bought}

    def _refresh_shop_done(self):
        pending = any(item["status"] == "pending" for item in self.state["items"])
        self.state["shop_done"] = not pending

    def take_id(self, item_id):
        found = None
        kept = []
        for item in self.state["items"]:
            if item["id"] == item_id:
                found = item
            else:
                kept.append(item)
        if not found:
            return None
        self.state["items"] = kept
        self.state.setdefault("picked", []).append(
            {"name": found["name"], "keywords": list(found["keywords"]), "edible": found["edible"]}
        )
        self._refresh_shop_done()
        self._save()
        return found

    def take_picked(self):
        picked = list(self.state.get("picked") or [])
        self.state["picked"] = []
        self._save()
        return picked

    def buy_all(self, user):
        pending = [item for item in self.state["items"] if item["status"] == "pending"]
        if not pending:
            return {"bought": []}
        ids = {item["id"] for item in pending}
        self.state["items"] = [item for item in self.state["items"] if item["id"] not in ids]
        self.state.setdefault("picked", []).extend(
            {"name": item["name"], "keywords": list(item["keywords"]), "edible": item["edible"]}
            for item in pending
        )
        self._refresh_shop_done()
        self._save()
        return {"bought": pending}

    def clear_bought(self):
        before = len(self.state["items"])
        self.state["items"] = [item for item in self.state["items"] if item["status"] != "bought"]
        removed = before - len(self.state["items"])
        if removed:
            self._save()
        return removed

    def clear_pending(self):
        before = len(self.state["items"])
        self.state["items"] = [item for item in self.state["items"] if item["status"] != "pending"]
        self.state["picked"] = []
        self.state["shop_done"] = False
        removed = before - len(self.state["items"])
        if removed:
            self._save()
        return removed

    def set_session(self, user_id, slugs):
        self.state["sessions"][str(user_id)] = slugs
        self._save()

    def session(self, user_id):
        return list(self.state["sessions"].get(str(user_id), []))

    def shop_done(self):
        return bool(self.state.get("shop_done"))
