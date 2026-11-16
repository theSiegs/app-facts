# App Facts: shared app categories and values for Glint and Hearth

A small public, signed dataset of facts about apps: what kind of app each Android package is, keys for
the same app on Xbox, Microsoft Store, Windows, Steam and Switch, the values table (each category and
detail, with Hearth's default pool), the apps that are only system screens, and Glint's starter list of
notifications it hides. The Glint launcher and Hearth (Home Assistant) read it.

Tile recipes (the "tile exchange") are no longer published here (2026-11-16): the index's `apps` is
empty, and `revoked.txt` lists every recipe id it once published so phones drop their cached copies.

## What's here

| Path | What it is |
|---|---|
| `categories.json` | App categories: one line per Android package, written by the intake's nightly classifier (below). |
| `categories-overrides.json` | Hand corrections to the categories; they always win. |
| `catalog/` | The cross-platform app catalog: `keys.json` (Xbox, Microsoft Store, Windows, Steam, Switch and web keys), `apps.json` (app slugs), `overrides.json`, `values.json` (the values table), `evidence/` (the reviewer agent's records) and `normalize-vectors.json` (see "App catalog"). |
| `hidden.json` | Glint's starter list of notifications it hides (see "Hidden notifications"). |
| `revoked.txt` | Recipe ids withdrawn: one `id` or `id@rev` per line. |
| `keys/exchange-1.pub`, `keys/exchange-2.pub` | The publishing public keys (base64 of the raw 32-byte Ed25519 key). |
| `tools/build_index.py` | Builds and signs the published site (Python, standard library only). |
| `tools/check_categories.py` | Checks the two categories files and merges them for publishing (and `tools/test_check_categories.py`). |
| `tools/check_hidden.py` | Checks `hidden.json` (and `tools/test_check_hidden.py`). |
| `tools/check_catalog.py` | Checks the app catalog, computes each entry's state and builds its shards (and `tools/test_check_catalog.py`). |

## How a change gets in

1. A pull request changes the categories files (see "App categories"), `hidden.json` (see "Hidden
   notifications") or `catalog/`.
2. `check.yml` runs the checks below.
3. When they pass and the pull request comes from a branch of this repo and touches nothing else, it
   is merged automatically (main fast-forwards to its commits, so the pull request must be on top of
   main), except the cases named in "App categories", "Hidden notifications" and "Values", which wait
   for the owner's merge.
4. `publish.yml` then checks again, builds the index, signs it, verifies the signature against the
   committed public key and publishes the site.

Run the same steps locally (Python 3):

```sh
python tools/check_categories.py                                       # the categories files
python tools/check_hidden.py                                           # the notifications Glint hides
python tools/check_catalog.py                                          # the app catalog (add --base <old tree> for the caps)
python -m unittest discover -s tools                                   # the tests
python tools/build_index.py --out site                                 # unsigned dry run
python tools/build_index.py --out site --key test.pem --verify test.pub
```

## App categories

`categories.json` says what kind of app a package is: `game`, `video`, `audio`, `image`, `social`,
`news`, `maps`, `productivity`, `accessibility` or `messaging` (Hearth HA's app categories; the values
table, below, lists them), `interface` (not an app: System UI, launchers, Android's own screens, setup
wizards, permission controllers, package installers, keyboards, Family Link's lock and downtime screens;
only ever set by an override, see "Values"), or `unknown`. Glint uses it for an app's glyph when nothing else says what the app is, and passes it to
Hearth HA's screen time as `catalog_categories` (Hearth prefers the category the app declares itself).

```json
"com.roblox.client": {"category": "game", "name": "Roblox", "source": "play:GAME_ADVENTURE", "checked": "2026-11-05"},
"com.example.gallery": {"category": "image", "name": "Gallery", "glance": "photos", "source": "play:PHOTOGRAPHY", "checked": "2026-11-09"},
```

An entry may also say which of Glint's glances the app's tile borrows when nothing is waiting on it
(`glance`, optional):

| `glance` | The app's tile shows |
|---|---|
| `photos` | the photos glance (galleries and cameras) |
| `music` | the Music glance (players, podcasts) |
| `calendar` | the next event |
| `clock` | the Clock glance |
| `weather` | the forecast |
| `car` | reserved for a car glance Glint doesn't have yet (car makers' apps); Glint guesses as without one |
| `none` | the app's own glance, never a borrowed one |

Without one, Glint guesses on the phone (galleries it knows, what the app handles, its category). The
catalog's word wins over the guess while the tile exchange is on. Older Glint ignores the key, and Glint
skips a value it doesn't know, so new values can come later.

An entry may also say what kind of app it is (`kind`, optional), which Glint's kind recipes and Car
tile key on instead of hand lists of packages: `charging` (a charger network's app, such as
Electrify America or ChargePoint: its charging session joins the Car tile's when it matches the car's
own), `assistant` (an AI assistant or bot app, such as Claude or ChatGPT: its replies come as chat
notifications, but no person writes in it, so Glint never treats it as people talking), `car`,
`airline`, `delivery` or `ride`. An app has one kind at most. An app can have both a `glance` and a `kind` (Tesla's app
is a car app and a Supercharger app: `{"glance": "car", "kind": "charging"}`). Older Glint ignores the
key, and Glint skips a value it doesn't know.

The intake's nightly classifier writes it: Google Play's own genre for the app, mapped by a fixed rule;
an AI only for genres too broad to map (Entertainment, Lifestyle, Education...) and apps not on Play,
and `unknown` when it isn't sure. It writes a `glance` only where Play's genre says it cleanly
(Photography: `photos`, Music & Audio: `music`, Weather: `weather`, Auto & Vehicles: `car`). `name` is the app's Play title (left out if it might hold an email
address, link or phone number), `source` says where the category came from, `checked` when. About 40
new apps a night, plus a re-check of entries older than 90 days. Its pull requests from a
`categories/*` branch **merge on their own** when `tools/check_categories.py` passes: the schema,
categories, glances and kinds from the lists above, Android package names, no personal data (a name is one
short line; every other value has a fixed form), and at most 60 apps added, removed or changed
(category, glance or kind) per pull request.

### Changing a category

Never edit `categories.json` by hand (the classifier owns it). Put the fix in
**`categories-overrides.json`**, which always wins:

```json
{
  "format": "glint.categories-overrides/1",
  "apps": {
    "com.example.player": "video",
    "com.example.notagame": "unknown",
    "com.example.maps": {"category": "maps", "name": "Example Maps"},
    "com.example.gallery": {"glance": "photos"},
    "com.example.charger": {"kind": "charging"}
  }
}
```

A value is a category, `unknown` (publish no category for that app), or an object with a `category`, a
`name`, a `glance`, a `kind`, a `detail` and/or an `app` slug (each overrides only that key; see "App catalog"
for `detail` and `app`). The classifier leaves an app alone when its
override sets the category; one that only names the app or its glance still gets its category from
the classifier. Either commit to `main` (the push
publishes) or open a one-line pull request from a branch of this repo: it is checked and merged on its
own, and the merge publishes. Phones pick it up at their next update check with the tile exchange on.

## Hidden notifications

`hidden.json` is Glint's starter list of notifications it hides (format `glint.hidden/1`, Glint's
`docs/contracts/hidden-notifications.md`): reminders and promotions that aren't news, which every phone
gets marked "from glint" and can turn off one by one. Glint also ships a copy, used until it has fetched
this one.

```json
{
  "format": "glint.hidden/1",
  "rules": [
    {"id": "messages-device-pairing", "pkg": "com.google.android.apps.messaging",
     "titlePattern": "Device pairing", "action": "hide_and_clear", "why": "Not a message."}
  ]
}
```

A rule names the app (`pkg`) and a notification `channel`, a `titlePattern` (the whole title, ignoring
case; `*` is one or more characters, `\*` a literal star) or both, never a whole app. `action` is `hide`
(the default) or `hide_and_clear` (also clear it from the shade). `id` is stable: a phone keeps its "turned
off" choice by id, so never reuse one for another notification. `why` is for people reading the file.

The build publishes it as `c/<hash>.json` and names it in the signed index as `hidden` (path, SHA-256 and
rule count), as it does the categories; an index without it leaves phones on their bundled copy.
`tools/check_hidden.py` refuses anything Glint's parser would skip (a bad id or a repeated one, a package
that isn't an Android package name, a pattern that is only stars or over 200 characters, an unknown
action, more than 500 rules) and any email address, link or phone number in its text. A pull request
that changes it merges on its own when the check passes, except from a bot's branch (`categories/*`),
which waits for the owner.

## App catalog

The app categories above grow into a catalog of app facts across platforms, for Glint and for Hearth HA's
screen time (which fetches it itself). Glint's catalog owns, writes and signs it; Hearth only reads it. The
published URL, `glint.exchange/1` and `glint.catalog/1` are stable for both.

### Keys

Every key is `<namespace>:<id>`. One app has many keys; each key carries the app's **slug** (`app`), listed in
`catalog/apps.json`, so keys that share a slug are the same app.

| Namespace | Id | Example |
|---|---|---|
| `android` | package (in `categories.json`, without the prefix) | `android:com.example.player` |
| `msstore` | Microsoft Store product id, 12 characters, upper case: the Microsoft anchor | `msstore:9NBLGGH2JHXJ` |
| `xbox` | Xbox title id, decimal (the Store's `XboxTitleId`) | `xbox:1828326430` |
| `pfn` | Windows package family name, lower case | `pfn:microsoft.minecraftuwp_8wekyb3d8bbwe` |
| `steam` | Steam appid | `steam:1172470` |
| `switch` | Nintendo application id, 16 hex, upper case | `switch:0100152000022000` |
| `web` | registrable domain (curated only) | `web:example.com` |
| `name` | `name:<xbox\|msstore\|switch\|steam>:<normalized title>`, built from the entries' names | `name:switch:example kart` |
| `fs` | Family Safety's own id; **not accepted yet** (not known to be the same across accounts) | |

The name normalizer: drop the trademark, registered and copyright signs; Unicode NFKD without combining marks;
lower case; one trailing " for nintendo switch", " nintendo switch edition", " - nintendo switch", " standard
edition" or " edition" removed; every run of other characters than a-z and 0-9 becomes one space; trimmed.
`catalog/normalize-vectors.json` pins it, and Hearth's matches it. A name two apps share is left out.

### Fields

| Field | Values |
|---|---|
| `category` | The eleven above, from the values table (below). Add-only; a new one only when Android adds a category, or for a need as basic as messaging. Older Glint and Hearth drop a value they don't know (Other in Hearth: never looser). |
| `detail` | `youtube`, `streaming` (both under `video`), `education`, `companion`, `system` (under `productivity` or no category), `browser` (web browsers; no category). From the values table, add-only. Educational games are `game` with no detail. |
| `app`, `name` | The slug and the app's title. |
| `state` | `confirmed` or `suggested`, **computed when publishing, never written in a source file**. |
| `source` | `override`, `play`, `store`, `steam`, `platform`, `ai`, `match` or `review`. |
| `checked` | When the facts were last read. |

**When an entry is confirmed:** an override (`categories-overrides.json`, `catalog/overrides.json`, by key or by
`app:<slug>`; a key's beats its app's); a store rule (Play's genre in the classifier's fixed map, for the category
that map gives; the Microsoft Store's `ProductKind` Game, Steam's type game with no software genre and every Switch
title, each for `game` only); or a review whose evidence record passes the rule below. Anything else (an AI answer,
a match by name, a Store application, Steam software) is `suggested`. A `detail` shows on a confirmed entry only
when an override or a passing review gave it; on a suggested entry it shows as suggested. Glint and Hearth never
let a suggested value loosen a limit.

**Loose values.** The values the table marks `loose`: a detail of `education`, `companion` or `system`, and the categories `messaging` (Hearth counts
chat outside screen time) and `accessibility` (Hearth never pauses it), can lift a limit. No store rule confirms
them: only an override or a passing review. Play's Communication genre holds web browsers and hearing tools as
well as messengers, so a messenger the classifier filed from it stays suggested until one of those confirms it.

**Overrides-only values.** The values the table marks `overrides_only` (the category `interface`: System UI,
launchers, Android's own screens, keyboards; counted nowhere and never held or paused) are set only by an
override (`categories-overrides.json`, `catalog/overrides.json`) or a device's built-in list. The classifier may
not write one (the check refuses it in `categories.json` and `catalog/keys.json`), no store rule or review
confirms one, and the intake's classifier, reviewer and relay never offer one. A game filed there by mistake would
be free time, so nothing automatic can put it there.

**The evidence rule** (`catalog/evidence/<id>.json`, `glint.catalog-evidence/1`, written by the intake's reviewer
agent). A record confirms its key's proposed category and detail only when its verdict is `approve`, two judges
with different prompts both answered exactly that, at least one fact is a store or web page on
`displaycatalog.mp.microsoft.com`, `play.google.com`, `store.steampowered.com`, `www.nintendo.com`,
`ec.nintendo.com` or `en.wikipedia.org`, and no game signal stands against a value that isn't a game. The check
enforces it on every pull request and publish, so nothing loosens a limit without a recorded, passing review.

**Changes.** `check.yml` runs `tools/check_catalog.py --base` on pull requests: at most 60 keys added, removed or
changed, and no confirmed game stops being one without an override or a review. The classifier's pull requests
(`categories/*`) merge on their own. The reviewer agent's escalations come as a weekly `escalate/<date>` pull
request that waits for the owner: merging it accepts its overrides, closing it rejects them. A pull request from
a bot's branch (`categories/*`) that touches an overrides file waits for the owner too.

### Values

`catalog/values.json` (`glint.values/1`) is the one list of every category and detail. The checkers here, the
intake's classifier and reviewer, and the relay all read it; nobody keeps a copy of their own.

```json
{"format": "glint.values/1",
 "categories": {"messaging": {"label": "Messaging", "pool": "messaging", "outside_all": true, "loose": true}},
 "details": {"browser": {"label": "Web browsers", "parents": [null], "pool": "other"}}}
```

Each value has a short `label` and Hearth's default `pool` (`games`, `social`, `messaging` or `other`), and may
have `pool_names` (a household's own pool of that name takes it, else `pool`), `loose` (it can lift a limit, so
only an override or a passing review confirms it) and `outside_all` (Hearth counts it outside All screen time).
A value with `"counted": false` is counted nowhere and never held or paused, so it has no `pool`, `pool_names` or
`outside_all`; one with `"overrides_only": true` is set only by an override (above), never with `loose`.
A detail also has `parents`, the categories it may sit under (`null`: no category). `tools/values.py` checks it.
The build publishes it as `c/<hash>.json` and names it in the signed index as `values` (path, SHA-256 and count),
so readers get labels for new values without a release.

**How it grows: add-only, the owner decides, one step.**
1. Values are only added. None is removed or renamed in place, none stops being loose or overrides-only, and
   none uncounted becomes counted:
   `tools/check_catalog.py --base` refuses that against the base. A needed rename is a one-step migration
   (overrides first, then the Glint and Hearth releases).
2. The owner decides each new value, never the classifier, the reviewer or a model. A pull request that changes
   `catalog/values.json` never merges on its own. A proposal names the decision it changes, Hearth's default,
   what Glint does with it, the apps (about five, or one safety case), and why a `kind`, `glance` or flag won't do.
3. New values default to Other in Hearth. One that would take time out of All screen time or out of a pool is
   `loose`.
4. Gaps wait in `unknown`: published as nothing, Other in Hearth, the phone's own guess in Glint.
5. Growth goes into `detail`; a category is added only when Android adds one, or for a need as basic as messaging.

### Published (`glint.catalog/1`)

The index gains `"catalog": {"format": "glint.catalog/1", "shards": {"<platform>": {"path":
"k/<platform>.<first 16 hex of sha256>.json", "sha256": "...", "count": n}}}`, one shard per platform that has
keys. A shard is `{"format": "glint.catalog/1", "platform": "xbox", "keys": {"xbox:1828326430": {"app":
"minecraft", "name": "Minecraft", "category": "game", "state": "confirmed", "source": "store", "checked":
"2026-11-13"}}}`, trusted only when its SHA-256 equals the signed index's entry. The categories file
(`c/<hash>.json`) also gains each entry's `detail`, `state` and `source`; older Glint ignores them, and Glint
still reads only that file, never the shards. Readers ignore unknown keys and skip values and namespaces they
don't know; a change that can't be made that way gets a new format published beside this one for a year.

## Published format (`glint.exchange/1`)

Base URL `https://thesiegs.github.io/app-facts/` (Glint reads a saved old `.../glint-recipes/` address as this one):

- `index.json`: UTF-8 JSON

  ```
  {"format":"glint.exchange/1","seq":<int, increases every publish>,"issued":"<ISO-8601 UTC>",
   "apps":{}, "revoked":["<recipe id>" | "<recipe id>@<rev>", ...],
   "categories":{"path":"c/<first 16 hex of sha256>.json","sha256":"<lowercase hex of the file bytes>","count":<int>},
   "hidden":{"path":"c/...json","sha256":"...","count":<rules>},
   "values":{"path":"c/<first 16 hex of sha256>.json","sha256":"...","count":<categories plus details>},
   "catalog":{"format":"glint.catalog/1","shards":{"<platform>":{"path":"k/<platform>.<hash>.json","sha256":"...","count":<int>}}}}
  ```

  `apps` stays (empty) and `revoked` lists the recipe ids once published, so older Glint reads the index
  and drops any cached recipe. `seq` is the Unix time of the publish run in seconds, so it only grows.
  Unknown keys are ignored.
- `c/<hash>.json`: the app categories, `{"format":"glint.categories/1","apps":{"<package>":{"category":"game","name":"Roblox"}}}`,
  with the overrides applied and `unknown` left out (an app may have only a `name`, a `glance` or a `kind`);
  also the hidden starter list and the values table. Each is named by its content, so it never changes
  under a cached index, and trusted only if its SHA-256 equals the index's entry.
- `k/<platform>.<hash>.json`: the app catalog's shards (see "App catalog").
- `index.json.sig`: base64 (standard, no line breaks) of the raw 64-byte **Ed25519** signature over
  the exact bytes of `index.json`.

Readers ship one or two public keys and accept an index signed by any of them, and reject an index
whose `seq` is lower than the one they have cached (no rollback).

## Keys and rotation

The private keys exist only as the repository secrets `EXCHANGE_SIGNING_KEY` (signs today, public
half `keys/exchange-1.pub`) and `EXCHANGE_SIGNING_KEY_NEXT` (unused until a rotation, public half
`keys/exchange-2.pub`). Glint ships both public keys. To rotate:

1. Make sure the Glint release **and the Hearth release** in people's hands carry both public keys (Hearth HA
   pins them to verify the app catalog; see "App catalog").
2. Put the next key into `EXCHANGE_SIGNING_KEY` and set `EXCHANGE_PUBLIC_KEY` in `publish.yml` to
   `keys/exchange-2.pub`; publish.
3. Generate a new next key, commit its public half as `keys/exchange-3.pub`, set it as
   `EXCHANGE_SIGNING_KEY_NEXT`, and ship a Glint release that trusts keys 2 and 3. Then remove key 1.

A key that may have leaked is rotated the same way, at once. Never commit a private key.

## Privacy

Everything published here is about apps, never about people: app names, store ids and categories.

- **Glint** downloads the signed index and the files it names with its usual update check (on by
  default, and its "tile exchange" switch still controls it until a later Glint release builds these
  lists in). Like any website, the site sees the phone's internet address; nothing else is sent, and
  which apps are on the phone is never sent. Glint no longer shares notification layouts or tile edits.
- **Hearth** (Home Assistant) reads the same signed files and sends nothing to fetch them. With its own
  setting turned on by an HA administrator, it may send the store ids and store titles of public apps
  the catalog lacks, and corrections an adult chooses to share: no household, person or device id, no
  usage and no times. The intake only looks them up at their store; they never set a value here by themselves.

This notice describes how the software works; it is not legal advice.

## License

Everything in this repository is dedicated to the public domain under
[CC0 1.0 Universal](LICENSE).
