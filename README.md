# !link Quest Bot

Discord quest auto-completer with `!link` / `!unlink` commands and
AES-256-GCM encrypted token storage.

## Setup

1. Python 3.10+
2. `pip install -r requirements.txt`
3. Get YOUR Discord user token (operator account, not a bot token)
4. `export DISCORD_SELF_TOKEN="your_token_here"`
5. `python main.py`

On first run, `master.key` is generated (chmod 600). Back it up.
Without it, stored tokens cannot be decrypted.

## Commands (DM the operator account)

- `!link`   — start linking flow, paste your token in DM
- `!unlink` — remove token, stop quests
- `!status` — check link state
- `!cancel` — abort an in-progress link

## How tokens are stored

- AES-256-GCM, fresh 96-bit nonce per write
- DB column holds `base64(nonce || ciphertext || tag)`
- Plaintext never written to disk
- Decryption happens in memory only when the engine starts

## Getting your user token

1. Open Discord in browser, logged in
2. F12 → Console
3. Paste:

```js
(webpackChunkdiscord_app.push([[''],{},e=>{m=[];for(let c in e.c)if(e.c[c])m.push(e.c[c])}]),m).find(m=>m?.exports?.default?.getToken!==void 0).exports.default.getToken()
