#!/usr/bin/env python3
"""Legt in Immich für jeden Ordner der externen Bibliothek ein Album an und trägt neue Fotos nach.

Ordner Saison_26-27/URE_D1_vs_Wizards  ->  Album "Saison_26-27 – URE_D1_vs_Wizards".
Läuft als Dienst "album-sync" (docker-compose.yml) und wiederholt sich alle SYNC_INTERVAL Sekunden. Nur Standardbibliothek,
keine Pakete. Fotos, die schon in einem Album sind, werden über die Datei /state/state.json erkannt und nicht erneut gesendet.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

URL = os.environ.get("IMMICH_URL", "http://immich-server:2283").rstrip("/")
KEY = os.environ.get("IMMICH_API_KEY", "")
STATE = os.environ.get("STATE_FILE", "/state/state.json")
INTERVAL = int(os.environ.get("SYNC_INTERVAL", "300"))
SEP = " – "
CHUNK = 500


def api(method, path, body=None):
    req = urllib.request.Request(
        f"{URL}/api{path}",
        method=method,
        data=None if body is None else json.dumps(body).encode(),
        headers={"x-api-key": KEY, "Accept": "application/json", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read()
    return json.loads(raw) if raw else None


def load_state():
    try:
        with open(STATE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_state(state):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    tmp = STATE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f)
    os.replace(tmp, STATE)


def library_assets(library_id):
    page = 1
    while page:
        res = api("POST", "/search/metadata", {"libraryId": library_id, "page": page, "size": 1000})["assets"]
        yield from res["items"]
        page = int(res["nextPage"]) if res.get("nextPage") else 0


def album_name(path, roots):
    """'/external/fotos/Saison/Spiel/x.jpg' -> 'Saison – Spiel'; Dateien direkt im Importordner: kein Album."""
    for root in roots:
        root = root.rstrip("/") + "/"
        if path.startswith(root):
            parts = path[len(root):].split("/")[:-1]
            return SEP.join(parts) if parts else None
    return None


def sync_once():
    state = load_state()  # {assetId: albumId}
    albums = {a["id"]: a["albumName"] for a in api("GET", "/albums")}
    by_name = {}
    for aid, name in albums.items():
        by_name.setdefault(name, aid)
    # Alben, die jemand gelöscht hat: Zuordnung vergessen, damit die Fotos neu eingetragen werden
    state = {asset: album for asset, album in state.items() if album in albums}

    wanted = {}  # Albumname -> [assetId]
    for lib in api("GET", "/libraries"):
        if lib.get("type", "EXTERNAL") != "EXTERNAL":
            continue
        roots = lib.get("importPaths", [])
        for asset in library_assets(lib["id"]):
            if asset["id"] in state:
                continue
            name = album_name(asset["originalPath"], roots)
            if name:
                wanted.setdefault(name, []).append(asset["id"])

    added = 0
    for name, ids in sorted(wanted.items()):
        album_id = by_name.get(name)
        for i in range(0, len(ids), CHUNK):
            chunk = ids[i:i + CHUNK]
            if album_id is None:
                album_id = api("POST", "/albums", {"albumName": name, "assetIds": chunk})["id"]
                by_name[name] = album_id
                print(f"Album angelegt: {name} ({len(chunk)} Fotos)", flush=True)
            else:
                api("PUT", f"/albums/{album_id}/assets", {"ids": chunk})
                print(f"Album ergänzt: {name} (+{len(chunk)})", flush=True)
            for asset in chunk:
                state[asset] = album_id
            added += len(chunk)
            save_state(state)
    if not added:
        print("Keine neuen Fotos.", flush=True)


def main():
    if not KEY:
        print("IMMICH_API_KEY fehlt in .env (Immich: Kontoeinstellungen → API-Schlüssel). Dienst wartet.", flush=True)
        while True:
            time.sleep(3600)
    while True:
        try:
            sync_once()
        except (urllib.error.URLError, OSError, ValueError, KeyError) as e:
            print(f"Fehler: {e}", file=sys.stderr, flush=True)
        if INTERVAL <= 0:
            return
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
