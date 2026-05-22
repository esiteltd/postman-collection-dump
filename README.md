# 📮 Postman Collection Dump

> 🚀 A zero-dependency Python script to bulk-export Postman collections to local JSON files — perfect for migrating to **Bruno**, archiving your work, or backing up collections you can only *view*.

[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![No Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen.svg)](#-prerequisites)
[![Postman API v2.1](https://img.shields.io/badge/Postman-Collection%20v2.1-orange.svg)](https://schema.postman.com/)

---

## ✨ Why this exists

Postman's free tier limits how many collections, requests, and runs you can store before things get locked behind a paywall. If you're stuck as a **read-only viewer** of someone else's workspace (because the owner is on a locked/limited plan), the UI offers no convenient way to bulk-export everything.

This script side-steps that limitation by talking directly to the **Postman API**. Your API key inherits the same visibility you have in the Postman desktop/web UI — so if you can *see* it, this script can *dump* it. 🎯

Common use cases:
- 🐂 **Migrating to [Bruno](https://www.usebruno.com/)** (open-source, offline-first, git-friendly)
- 💾 **Backing up** collections before a plan downgrade or team migration
- 📦 **Archiving** historical API definitions
- 🔄 **Multi-team migrations** when you belong to several Postman teams

---

## 🌟 Features

- 🪶 **Zero dependencies** — only the Python 3 standard library
- 🔑 **Multi-key sessions** — paste keys from multiple teams in one run; each team lands in its own subfolder
- 🎚️ **Three export modes** — single collection, whole workspace, or everything visible
- 🛡️ **Read-only friendly** — works even when you're just a viewer
- 📄 **Bruno-compatible output** — Postman Collection v2.1 JSON, imports cleanly into Bruno
- 🤐 **No secrets on disk** — API keys are taken from `getpass` (hidden input) or env vars; nothing is cached
- 🧼 **Safe filenames** — collection names are sanitized; collisions get auto-suffixed (`_2`, `_3`, …)

---

## 📋 Prerequisites

- 🐍 **Python 3.8+** (uses only stdlib — no `pip install` needed)
- 🔐 A **Postman API key** for each team you want to export from

That's it. No virtualenv, no requirements.txt, no extras.

---

## 🔑 Getting a Postman API key

> ⚠️ **Important:** Postman API keys are scoped to **one team**. If you belong to multiple teams, one key only sees one team's data.

1. In Postman, use the **team switcher** (top-left) to select the team you want to export from
2. Go to 👉 [https://postman.com/settings/me/api-keys](https://postman.com/settings/me/api-keys)
3. Click **Generate API Key**, name it something memorable (e.g. `bulk-dump-acme`)
4. Copy the key — you'll paste it into the script

🔁 Repeat for each team if you're migrating from multiple teams.

---

## 📥 Installation

Just clone and run:

```bash
git clone https://github.com/esiteltd/postman-collection-dump.git
cd postman-collection-dump
python3 dump_postman_collection.py
```

Or grab the single file directly:

```bash
curl -O https://raw.githubusercontent.com/esiteltd/postman-collection-dump/main/dump_postman_collection.py
python3 dump_postman_collection.py
```

---

## 🚀 Usage

Run the script and follow the interactive prompts:

```bash
python3 dump_postman_collection.py
```

You'll be asked to pick a mode:

### 1️⃣ Single Collection
Paste a Postman collection URL **or** a bare UID:

```
Collection URL or UID: https://www.postman.co/workspace/Team-Workspace~abc.../collection/39131400-9241ca79-eca8-483e-b668-94dc153933f7
```

✅ Exports just that one collection.

### 2️⃣ Whole Workspace
Paste a workspace URL **or** UUID:

```
Workspace URL or UUID: https://www.postman.co/workspace/Team-Workspace~e1234567-89ab-cdef-0123-456789abcdef
```

✅ Exports every collection in that workspace that your key can see.

### 3️⃣ Everything 🌍
No input needed — the script lists every workspace your key can access and dumps **all collections from all workspaces**.

```
Choice [1/2/3]: 3
Found 7 workspace(s):
  - My Workspace [abc...] (personal)
  - Acme Team [def...] (team)
  - ...
```

---

## 🔐 Using an environment variable (skip the prompt)

For automation, set `POSTMAN_API_KEY` and the first prompt is skipped:

```bash
export POSTMAN_API_KEY="PMAK-xxxxxxxxxxxxxxxxxxxxxxxx"
python3 dump_postman_collection.py
```

> 🧠 Only the **first** key is read from the env var. Subsequent keys (multi-team mode) are still prompted via hidden input.

---

## 👥 Multi-team workflow

After the first key finishes, you'll be asked:

```
Add another team's API key? [y/N]: y
Next team's Postman API key (input hidden, blank to quit):
```

Each team's collections land in their **own subfolder**, named after the team:

```
.
├── Acme_Team/
│   ├── Public_API.postman_collection.json
│   └── Internal_Tools.postman_collection.json
├── Side_Project_Org/
│   └── Webhooks.postman_collection.json
└── personal/
    └── Scratchpad.postman_collection.json
```

---

## 📂 Output structure

Files are written into the **current working directory**. Each file is named after the collection (sanitized) with the `.postman_collection.json` suffix:

```
<cwd>/
└── <team_label>/
    ├── <Collection Name>.postman_collection.json
    └── <Workspace Name>/                       ← only in mode 2 & 3
        ├── <Collection A>.postman_collection.json
        └── <Collection B>.postman_collection.json
```

The JSON is **Postman Collection v2.1**, with the outer `{"collection": ...}` envelope stripped — exactly the format Bruno expects.

---

## 🐂 Importing into Bruno

1. Open **Bruno**
2. **File → Import Collection → Postman Collection**
3. Select any `.postman_collection.json` file produced by this script
4. ✨ Done

Repeat for each file, or use Bruno's bulk-import if available in your version.

---

## 🩺 Troubleshooting

| HTTP code | What it usually means | Fix |
|-----------|----------------------|-----|
| **401** 🚫 | API key invalid or revoked | Re-generate the key in Postman settings |
| **403** 🛑 | Key can't read this resource | The key was made on the wrong account/team — switch teams first, regenerate |
| **404** 🔍 | Wrong ID, or resource not visible to this key | Double-check the URL/UID; confirm you can see it in the Postman UI |
| **429** ⏱️ | Rate-limited (monthly free-tier quota) | Wait a bit, or upgrade the Postman plan |

Other tips:

- 🧭 **"Could not find a collection UID"** — the URL you pasted didn't contain a recognizable UID. Try copying the URL from the collection's **Share → Get public link** dialog, or use the bare UID (e.g. `39131400-9241ca79-eca8-483e-b668-94dc153933f7`)
- 🪟 **Workspace not found** — workspace UUIDs sit after a `~` in URLs: `…/workspace/My-Workspace~e1234567-89ab-cdef-0123-456789abcdef`
- 🧪 **Empty workspace** — your key might be scoped to a different team than the workspace; switch teams in Postman, regenerate the key, retry

---

## 🤝 Contributing

PRs welcome! 🎉 Keep it dependency-free and stdlib-only — that's the whole point of this script.

Ideas that would be nice:
- 📜 Optional environment-variable export
- 🗃️ Mock servers / monitors export
- 🏷️ Filter by collection name regex
- 📈 Progress bar for large workspaces

---

## ⚖️ License

Released under the **MIT License** — do what you want with it. 🪄

---

## 🙏 Acknowledgements

- Built for everyone migrating away from Postman's freemium walls
- Bruno team for building a sane open-source alternative 🐂
- The Postman API team for keeping `/collections/{uid}` and `/workspaces` accessible to viewers

---

<p align="center">
  Made with ☕ and a strong dislike of vendor lock-in.
</p>
