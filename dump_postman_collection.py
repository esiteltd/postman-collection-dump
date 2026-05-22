#!/usr/bin/env python3
"""
Dump Postman collections to local JSON files using the Postman API.

Works even when you're only a READ-ONLY viewer of someone else's workspace
(e.g., the workspace owner is on a locked/limited plan). Your own API key
inherits the visibility you already have in the Postman desktop/web UI, so
anything you can see there, this script can export.

IMPORTANT: Postman API keys are scoped to the TEAM they were generated in.
If you belong to multiple teams, one key only sees one team. The script
supports multi-key sessions for migration: paste keys one after another and
each team's collections land in its own subfolder.

Modes (per key):
  1) Single collection - paste a postman.co URL or a bare UID.
  2) Whole workspace  - paste a workspace URL or ID; dumps every collection
                        you can see in it.
  3) Everything       - lists every workspace this key can access and dumps
                        all collections from all of them.

Output is Postman Collection v2.1 JSON, which Bruno imports directly via
File -> Import Collection -> Postman Collection.

Generate an API key here (switch to the target team FIRST in the Postman
top-left team switcher, then generate):
  https://postman.com/settings/me/api-keys
"""

import json
import os
import re
import sys
from getpass import getpass
from pathlib import Path
from urllib.parse import urlparse, unquote, quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

POSTMAN_API_BASE = "https://api.getpostman.com"

COLLECTION_UID_RE = re.compile(
    r"(\d+-[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})"
)
UUID_RE = re.compile(
    r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})"
)


# ---------- input parsing -------------------------------------------------

def extract_collection_uid(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Empty collection URL/UID")
    if COLLECTION_UID_RE.fullmatch(value):
        return value
    parsed = urlparse(value)
    haystack = unquote(parsed.path + "?" + parsed.query)
    m = COLLECTION_UID_RE.search(haystack)
    if not m:
        raise ValueError(
            "Could not find a collection UID. Expected something like "
            "39131400-9241ca79-eca8-483e-b668-94dc153933f7"
        )
    return m.group(1)


def extract_workspace_id(value: str) -> str:
    """Workspace IDs are plain UUIDs. URLs look like:
       https://<tenant>.postman.co/workspace/<name>~<uuid>/...
    """
    value = value.strip()
    if not value:
        raise ValueError("Empty workspace URL/ID")
    if UUID_RE.fullmatch(value):
        return value
    parsed = urlparse(value)
    haystack = unquote(parsed.path + "?" + parsed.query)
    # The workspace UUID is typically right after a `~` or in a /workspace/<x>~<uuid> segment
    after_tilde = re.search(r"~(" + UUID_RE.pattern.strip("()") + r")", haystack)
    if after_tilde:
        return after_tilde.group(1)
    # Fallback: take the first UUID we find that ISN'T part of a collection UID
    for m in UUID_RE.finditer(haystack):
        start = m.start()
        # If preceded by "<digits>-" it's likely a collection UID, skip it
        if start >= 1 and haystack[start - 1] == "-" and haystack[max(0, start - 3):start - 1].isdigit():
            continue
        return m.group(1)
    raise ValueError("Could not find a workspace UUID in the input.")


# ---------- HTTP ----------------------------------------------------------

def api_get(path: str, api_key: str) -> dict:
    url = f"{POSTMAN_API_BASE}{path}"
    req = Request(url, headers={"X-Api-Key": api_key, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise SystemExit(
            f"\nPostman API returned HTTP {e.code} for GET {url}\n"
            f"Response body: {body}\n\n"
            "Common causes:\n"
            "  401 - API key invalid or revoked\n"
            "  403 - Your key can't read this resource (was the key made on the wrong account?)\n"
            "  404 - Wrong ID, or the resource isn't visible to this key\n"
            "  429 - Rate limit / monthly free-tier quota hit\n"
        )
    except URLError as e:
        raise SystemExit(f"Network error talking to Postman: {e.reason}")


def fetch_collection(uid: str, api_key: str) -> dict:
    return api_get(f"/collections/{quote(uid, safe='-')}", api_key)


def list_workspaces(api_key: str) -> list:
    return api_get("/workspaces", api_key).get("workspaces", [])


def fetch_workspace(ws_id: str, api_key: str) -> dict:
    return api_get(f"/workspaces/{quote(ws_id)}", api_key).get("workspace", {})


# ---------- file output ---------------------------------------------------

def safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^\w\-.]+", "_", name).strip("._")
    return cleaned or "collection"


def save_collection(payload: dict, out_dir: Path) -> Path:
    """Strip Postman's {'collection': {...}} envelope and write the inner v2.1 JSON."""
    collection = payload.get("collection")
    if not collection:
        raise RuntimeError(f"Unexpected response: {json.dumps(payload)[:300]}")
    name = collection.get("info", {}).get("name", "collection")
    out_path = out_dir / f"{safe_filename(name)}.postman_collection.json"
    # Avoid clobbering when two collections share a name
    counter = 2
    while out_path.exists():
        out_path = out_dir / f"{safe_filename(name)}_{counter}.postman_collection.json"
        counter += 1
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(collection, f, indent=2, ensure_ascii=False)
    return out_path


# ---------- workflows -----------------------------------------------------

def dump_single(api_key: str, raw: str, out_dir: Path) -> None:
    uid = extract_collection_uid(raw)
    print(f"  Fetching {uid} ...")
    path = save_collection(fetch_collection(uid, api_key), out_dir)
    print(f"  -> {path}")


def dump_workspace(api_key: str, raw: str, out_dir: Path) -> None:
    ws_id = extract_workspace_id(raw)
    ws = fetch_workspace(ws_id, api_key)
    ws_name = ws.get("name", ws_id)
    collections = ws.get("collections", []) or []
    if not collections:
        print(f"Workspace '{ws_name}' has no collections visible to this API key.")
        return
    ws_dir = out_dir / safe_filename(ws_name)
    ws_dir.mkdir(parents=True, exist_ok=True)
    print(f"Workspace '{ws_name}' - {len(collections)} collection(s):")
    for c in collections:
        uid = c.get("uid") or c.get("id")
        print(f"  Fetching {c.get('name', uid)} [{uid}] ...")
        try:
            path = save_collection(fetch_collection(uid, api_key), ws_dir)
            print(f"  -> {path}")
        except SystemExit as e:
            print(f"  ! Skipped: {e}", file=sys.stderr)


def dump_everything(api_key: str, out_dir: Path) -> None:
    workspaces = list_workspaces(api_key)
    if not workspaces:
        print("No workspaces visible to this API key.")
        return
    print(f"Found {len(workspaces)} workspace(s):")
    for ws in workspaces:
        print(f"  - {ws.get('name')} [{ws.get('id')}] ({ws.get('type')})")
    print()
    for ws in workspaces:
        dump_workspace(api_key, ws.get("id"), out_dir)


# ---------- entry point ---------------------------------------------------

def prompt_api_key(first: bool = True) -> str:
    if first:
        env_key = os.environ.get("POSTMAN_API_KEY")
        if env_key:
            print("Using POSTMAN_API_KEY from environment.")
            return env_key.strip()
    label = "Postman API key" if first else "Next team's Postman API key"
    return getpass(f"{label} (input hidden, blank to quit): ").strip()


def fetch_team_label(api_key: str) -> str:
    """Best-effort team name for the folder. /me returns user info; the team
    name itself isn't on /me, but the first workspace usually carries it.
    Falls back to a short hash of the key.
    """
    try:
        workspaces = list_workspaces(api_key)
        # Team workspaces have type == 'team'; grab the first one's name as a hint.
        for ws in workspaces:
            if ws.get("type") == "team":
                return ws.get("name", "team")
        if workspaces:
            return "personal"
    except SystemExit:
        pass
    import hashlib
    return "team_" + hashlib.sha1(api_key.encode()).hexdigest()[:6]


def prompt_mode() -> str:
    print()
    print("What do you want to dump?")
    print("  1) A single collection (URL or UID)")
    print("  2) An entire workspace (URL or workspace UUID)")
    print("  3) Everything my API key can see (all workspaces, all collections)")
    while True:
        choice = input("Choice [1/2/3]: ").strip()
        if choice in {"1", "2", "3"}:
            return choice
        print("Please enter 1, 2, or 3.")


def run_one_key(api_key: str, base_dir: Path) -> None:
    team_label = fetch_team_label(api_key)
    team_dir = base_dir / safe_filename(team_label)
    team_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nDumping into: {team_dir}")

    mode = prompt_mode()
    if mode == "1":
        raw = input("Collection URL or UID: ").strip()
        dump_single(api_key, raw, team_dir)
    elif mode == "2":
        raw = input("Workspace URL or UUID: ").strip()
        dump_workspace(api_key, raw, team_dir)
    else:
        dump_everything(api_key, team_dir)


def main() -> int:
    print("Postman Collection Dumper")
    print("-------------------------")
    print("Tip: API keys are scoped to one team. To dump from multiple teams,")
    print("switch teams in Postman, generate a new key, and paste it when asked.\n")

    base_dir = Path.cwd()
    first = True
    while True:
        key = prompt_api_key(first=first)
        if not key:
            if first:
                print("No API key provided.", file=sys.stderr)
                return 1
            break
        try:
            run_one_key(key, base_dir)
        except SystemExit as e:
            print(f"Aborted this key: {e}", file=sys.stderr)
        first = False
        again = input("\nAdd another team's API key? [y/N]: ").strip().lower()
        if again != "y":
            break

    print("\nDone. Import into Bruno: File -> Import Collection -> Postman Collection")
    return 0


if __name__ == "__main__":
    sys.exit(main())
