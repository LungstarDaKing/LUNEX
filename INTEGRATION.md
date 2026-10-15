# Connecting LUNEX to LSDKChat

LUNEX appears as a chat called **LUNEX** at the top of the chat list (like "Notes to myself"). The conversation is kept in the
user's own browser, so you do not need new database tables.

## 1. Host LUNEX and note its address
See README.md. You need an address like `https://lunex-xxxx.onrender.com`. Check `https://YOUR-ADDRESS/health` shows `"ai_ready": true`.

## 2. Add the client file
Copy `client/lunex.js` to `LSDKChat/src/lib/lunex.js`.

## 3. Add the address to `src/config.js`
```js
lunexUrl: 'https://lunex-xxxx.onrender.com',   // leave '' to switch LUNEX off
```

## 4. Allow it in the security policy (`vite.config.js`) - IMPORTANT
The app only lets the page contact addresses it lists, so without this the browser silently blocks LUNEX.
Next to the `turn` line add:
```js
const lunex = CONFIG.lunexUrl ? ` ${new URL(CONFIG.lunexUrl).origin}` : ''
```
and change the `connect-src` line to end with `${turn}${lunex}`.

## 5. Use it in the app
```js
// src/lib/lunex.js is the client. Create it once (for example in chat.js init()):
import { LunexClient, chatContext } from '../lib/lunex.js'
import { supabase } from '../lib/supabase.js'
import { CONFIG } from '../config.js'
this.lunex = CONFIG.lunexUrl ? new LunexClient({ baseUrl: CONFIG.lunexUrl,
  getToken: async () => (await supabase.auth.getSession()).data.session?.access_token }) : null

// Send a message to LUNEX and show the answer as it arrives:
const bubble = addBubble('assistant', '')                       // your own function that adds a message bubble
try {
  const r = await this.lunex.ask(text, {
    history: this.lunexTurns,                                   // [{role:'user'|'assistant', content}]
    onStatus: (t) => showStatus(t),                             // "Searching the web…"
    onDelta: (t) => { bubble.textContent += t },                // IMPORTANT: textContent, never innerHTML
  })
  this.lunexTurns.push({ role: 'user', content: text }, { role: 'assistant', content: r.reply })
  // r.sources = [{ title, url? }] -> show as small links (use rel="noopener noreferrer")
} catch (e) { toast(e.message, 'error') }                       // e.message is already friendly (limits, sign-in, offline)

// "Summarize this chat" (only sends the messages the user chose to share):
await this.lunex.ask('/summarize', { skill: 'summarize', context: chatContext(this.messages, (id) => this.nameOf(id)) })
```
Keep the LUNEX conversation in `localStorage` under a key that includes the user id (cap it at ~100 messages) and add a "Clear" button.

## 6. Tell users (required)
Everything a user sends to LUNEX (and any chat they ask it to summarize) leaves your database and goes to LUNEX and the AI
provider you configured. Update Terms/Privacy in `src/pages/legal.js` to say so, name the providers, tell users not to send passwords or
secrets, and bump `termsVersion` so everyone accepts again. Some free AI tiers may use prompts to improve their models: check
each provider's terms, and consider showing a short "this chat will be sent to LUNEX" confirmation before "Summarize this chat".

## 7. Test
1. Ask "how do I make a group call?" -> answer from the help guide.
2. `/research best free VPN` -> "Searching the web…", then an answer with source links.
3. Open a group chat -> Summarize this chat.
4. Sign out -> LUNEX should refuse (sign-in message). Send 7 messages in a minute -> friendly "too fast" message.
