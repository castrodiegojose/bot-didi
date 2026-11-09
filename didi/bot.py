import json
import os
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from didi.handle import handle_message, mark_checked
from didi.store import Store, default_store_path

COMMANDS = [
    {"command": "lista", "description": "Ver la lista del super"},
    {"command": "agregar", "description": "Agregar productos"},
    {"command": "comprar", "description": "Agregar productos a la lista"},
    {"command": "sacar", "description": "Sacar productos"},
    {"command": "compre", "description": "Marcar como comprado"},
    {"command": "limpiar", "description": "Borrar lo ya comprado"},
    {"command": "ayuda", "description": "Ver cómo se usa"},
]


def load_env(path=".env"):
    file = Path(path)
    if not file.exists():
        return
    for line in file.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        os.environ.setdefault(key.strip(), value)


class Telegram:
    def __init__(self, token):
        self.token = token

    def call(self, method, payload=None, timeout=65):
        data = None
        headers = {}
        if payload is not None:
            data = json.dumps(payload).encode()
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            f"https://api.telegram.org/bot{self.token}/{method}",
            data=data,
            headers=headers,
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = json.loads(response.read().decode())
        except urllib.error.HTTPError as error:
            detail = error.read().decode(errors="replace")
            raise RuntimeError(f"Telegram respondió {error.code}: {detail}") from None
        if not body.get("ok"):
            raise RuntimeError(f"Telegram rechazó {method}")
        return body.get("result")


def keyboard(count):
    rows = []
    row = []
    for index in range(count):
        row.append({"text": str(index + 1), "callback_data": f"r:{index}"})
        if len(row) == 5:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return {"inline_keyboard": rows}


def markup(result):
    suggestions = result.get("suggestions") or []
    if suggestions:
        return keyboard(len(suggestions))
    checks = result.get("checks") or []
    if checks:
        return {"inline_keyboard": [[{"text": item["text"], "callback_data": item["data"]}] for item in checks]}
    return {"inline_keyboard": []}


def _user(sender):
    return {
        "id": sender["id"],
        "name": sender.get("first_name") or sender.get("username") or "Alguien",
    }


def _send(api, chat_id, result):
    if not result or result.get("silent") or not result.get("html"):
        return
    payload = {
        "chat_id": chat_id,
        "text": result["html"],
        "parse_mode": "HTML",
    }
    if result.get("suggestions") or result.get("checks"):
        payload["reply_markup"] = markup(result)
    api.call("sendMessage", payload)
    followup = result.get("followup")
    if followup:
        _send(api, chat_id, followup)


def _edit(api, chat_id, message_id, result):
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": result["html"],
        "parse_mode": "HTML",
        "reply_markup": markup(result),
    }
    api.call("editMessageText", payload)


def _dispatch(api, store, update):
    message = update.get("message")
    if message and message.get("text") and message.get("from"):
        result = handle_message(
            store,
            _user(message["from"]),
            message["text"],
            chat_type=message.get("chat", {}).get("type"),
        )
        _send(api, message["chat"]["id"], result)
        return

    callback = update.get("callback_query")
    if not callback or not callback.get("from") or not callback.get("message"):
        return
    data = callback.get("data") or ""
    if data.startswith("c:"):
        result = mark_checked(store, _user(callback["from"]), data[2:])
        api.call(
            "answerCallbackQuery",
            {"callback_query_id": callback["id"], "text": result.get("toast") or "Listo"},
        )
        chat_id = callback["message"]["chat"]["id"]
        message_id = callback["message"]["message_id"]
        try:
            _edit(api, chat_id, message_id, result)
        except RuntimeError as error:
            print(f"No pude actualizar la lista: {error}", flush=True)
            try:
                api.call("deleteMessage", {"chat_id": chat_id, "message_id": message_id})
            except RuntimeError:
                pass
            _send(api, chat_id, result)
        else:
            if result.get("followup"):
                _send(api, chat_id, result["followup"])
        return
    if not data.startswith("r:"):
        return
    number = int(data.split(":", 1)[1]) + 1
    result = handle_message(
        store,
        _user(callback["from"]),
        str(number),
        chat_type=callback["message"].get("chat", {}).get("type"),
    )
    api.call("answerCallbackQuery", {"callback_query_id": callback["id"]})
    _send(api, callback["message"]["chat"]["id"], result)


def webhook_url(external):
    return external.rstrip("/") + "/telegram"


def listen_for_healthcheck():
    port = os.environ.get("PORT")
    if not port:
        return
    _serve(int(port), _handler(None, None))
    print(f"Salud en el puerto {port}", flush=True)


def _handler(api, store):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self._text(200, b"ok")

        def do_HEAD(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()

        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b""
            if self.path.split("?", 1)[0] != "/telegram" or api is None:
                self._text(404, b"no")
                return
            try:
                _dispatch(api, store, json.loads(raw.decode() or "{}"))
            except Exception as error:
                print(f"Falló un mensaje: {error}", flush=True)
                self._text(500, b"error")
                return
            self._text(200, b"ok")

        def _text(self, status, body):
            self.send_response(status)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            return

    return Handler


def _serve(port, handler):
    server = ThreadingHTTPServer(("0.0.0.0", port), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def run(token, store):
    api = Telegram(token)
    external = os.environ.get("RENDER_EXTERNAL_URL", "").strip()
    port = os.environ.get("PORT", "").strip()
    if port:
        _serve(int(port), _handler(api, store))
        print(f"Salud en el puerto {port}", flush=True)
    me = api.call("getMe", timeout=20)
    api.call("setMyCommands", {"commands": COMMANDS}, timeout=20)
    print(f"Didi está escuchando como @{me.get('username')}", flush=True)
    if external and port:
        api.call(
            "setWebhook",
            {
                "url": webhook_url(external),
                "allowed_updates": ["message", "callback_query"],
                "drop_pending_updates": False,
            },
        )
        print(f"Webhook en {webhook_url(external)}", flush=True)
        threading.Event().wait()
        return
    offset = None
    while True:
        payload = {"timeout": 50, "allowed_updates": ["message", "callback_query"]}
        if offset is not None:
            payload["offset"] = offset
        try:
            updates = api.call("getUpdates", payload)
        except Exception as error:
            print(f"Se cortó la conexión: {error}", flush=True)
            continue
        for update in updates:
            offset = update["update_id"] + 1
            try:
                _dispatch(api, store, update)
            except Exception as error:
                print(f"Falló un mensaje: {error}", flush=True)


def main():
    load_env()
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token or "pegá-acá" in token:
        print("Falta TELEGRAM_BOT_TOKEN.")
        print("1. En Telegram, hablá con @BotFather y creá un bot con /newbot.")
        print("2. Copiá .env.example a .env y pegá el token.")
        print("3. Corré de nuevo: python3 main.py")
        raise SystemExit(1)
    store = Store(os.environ.get("STORE_PATH") or default_store_path())
    try:
        run(token, store)
    except RuntimeError as error:
        print("No pude conectar con Telegram. Revisá TELEGRAM_BOT_TOKEN.")
        print(error)
        raise SystemExit(1) from None
