# Build Orion on Windows

Orion is an official Discord AI bot created by Rontgen. This project includes the complete Python application, configuration, tests, and a beginner walkthrough. The latest supplied specification uses **Orion** and **Rontgen**, with this capitalization.

## 1. Discord account feasibility and policy limitations

Use a **bot account** created in the [Discord Developer Portal](https://discord.com/developers/applications). Discord prohibits automating ordinary user accounts, often called self-bots, outside its bot API. See [Discord's official self-bot policy](https://support.discord.com/hc/en-us/articles/115002192352-Automated-User-Accounts-Self-Bots).

Orion has its own application identity and visible bot/app designation. It does not send as your personal account and cannot hide that distinction. It can still respond to mentions, respond to replies, and read permitted recent channel history. No personal user token, modified client, or self-bot is used.

The standalone support-policy page was blocked by this environment's network proxy during preparation. Discord's [official OAuth2 documentation source](https://github.com/discord/discord-api-docs/blob/main/developers/topics/oauth2.mdx#bot-vs-standard-user-accounts), which was reachable, explicitly says developers must refrain from automating standard accounts outside the OAuth2/bot API. Its bot section confirms bots are separate automation accounts. The [Gateway documentation source](https://github.com/discord/discord-api-docs/blob/main/developers/events/gateway.mdx#message-content-intent) was also checked for the content-intent requirement.

## 2. Comparison of suitable AI models and inference providers

Research date: **22 October 2026**. This is an evidence-limited comparison, not an independent conversation-quality benchmark. Official GitHub sources were readable. Google pricing, quota, terms, Groq console, OpenRouter, and Mistral documentation hosts returned proxy 403 errors. Exact current free quotas, signup requirements, privacy terms, and account availability could therefore **not** be verified. No live model was tested because no AI key was supplied.

| Candidate | Conversation and instruction-following considerations | Free access, limits, and setup | Privacy and reliability considerations | Decision |
| --- | --- | --- | --- | --- |
| Google Gemini `gemini-3.8-flash` through Gemini API | Google's current quickstart default; a practical general chat candidate with system instructions, thinking controls, and provider safety settings. Quality against these alternatives was not benchmarked. | Google account and AI Studio API key. Exact free eligibility, RPM, TPM, RPD, concurrency, verification, and whether payment details are required for your region must be checked in AI Studio. Do not enable billing. | Hosted messages leave your PC. Read unpaid-service data-use terms before sending community conversations. No free-service uptime or continued-free guarantee established. | Selected practical default, conditional on your account confirming its free tier. |
| Gemini `gemini-4-argon` / `gemini-3.1-pro-preview` | Google's official examples describe these as stronger reasoning options. This does not establish better casual-chat quality. | The current official quickstart explicitly states neither has a free tier. | Hosted; payment and data terms apply. | Excluded from the free requirement, despite potential quality. |
| Groq, GPT-OSS 120B candidate | Serious open-weight reasoning/chat alternative. Groq's official cookbook includes a GPT-OSS 120B integration; its Python SDK documents chat completions. No direct quality comparison was run. | Official cookbook advertises an API key obtainable for free. That alone does not verify this specific model's current free allocation. Exact model ID, quotas, concurrency, payment/card and verification requirements need console confirmation. | Low-latency service is its intended use; latency and retention were not measured or verified here. | Supported via the OpenAI-compatible adapter, but not silently substituted. |
| OpenRouter free models | Quality depends on the selected model and upstream provider. Router-selected models complicate consistent behavior. | Free catalog and quotas are dynamic; current model availability, credit/purchase conditions and card requirements were not verified. | Additional routing parties may see content. Read each provider's policy. | Not selected without verified free access to a specific strong model. |
| Mistral experimental/free API access | A plausible hosted alternative; no current model quality comparison was performed. | Current free experiment terms, model catalog, verification and quotas could not be verified. | Evaluation tiers may differ from production availability and data terms. | Insufficient current evidence to choose it. |
| Ollama with a suitably sized local model | Quality and instruction adherence depend heavily on the model and quantization. A small model is not assumed equivalent to a strong hosted model. | No local per-request inference service fee, but hardware, electricity and model downloads cost resources. Your hardware is unknown. RAM/VRAM and latency must be evaluated for the exact model. The official Ollama README currently demonstrates Gemma 4; no size or RAM requirement is invented here. | Local inference avoids sending text to an AI host when genuinely run locally. Discord still stores channel messages. PC must stay on. | Supported as a deliberate alternative, not the beginner default. |

Primary sources actually read:

- [Google's official model quickstart](https://github.com/google-gemini/cookbook/blob/main/quickstarts/Get_started.ipynb), including exact model names and explicit lack of a free tier for Argon and Pro.
- [Google's official generateContent examples](https://github.com/google-gemini/cookbook/blob/main/quickstarts/Get_started_Generate_Content.ipynb), showing `gemini-3.8-flash`, system instructions and safety settings.
- [Google's official authentication notebook](https://github.com/google-gemini/cookbook/blob/main/quickstarts/Authentication.ipynb).
- [Groq's official cookbook](https://github.com/groq/groq-api-cookbook) and [Python SDK](https://github.com/groq/groq-python).
- [Ollama's official repository](https://github.com/ollama/ollama).

Current terms you must verify before hosted use:

- [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing), [rate limits](https://ai.google.dev/gemini-api/docs/rate-limits), [terms](https://ai.google.dev/gemini-api/terms), and [available regions](https://ai.google.dev/gemini-api/docs/available-regions).
- [Groq models](https://console.groq.com/docs/models), [limits](https://console.groq.com/docs/rate-limits), [data controls](https://console.groq.com/docs/your-data).
- [OpenRouter limits](https://openrouter.ai/docs/api-reference/limits) and [privacy](https://openrouter.ai/privacy).
- [Mistral documentation](https://docs.mistral.ai/) and [Ollama model library](https://ollama.com/library).

## 3. Chosen model and reasoning

**Use Gemini API with `gemini-3.8-flash`, after confirming free access in your own AI Studio project.** This is the best-supported practical choice from the primary evidence available here: Google's current recommended starting model, straightforward API-key setup, separate system instructions, and configurable hate/harassment safeguards. Model-specific safety support still needs the live diagnostic below. I cannot honestly establish that it is the globally best free model, verify its current free contract from inaccessible pricing pages, or claim any measured quality/latency advantage.

Do not select Argon or Pro as a supposedly free upgrade. Google's current examples explicitly exclude them from the free tier. A consumer Gemini subscription is not proof of free API entitlement. Do not enable billing, enter a card to upgrade, or use a paid project to make this tutorial work. If your account shows no free allocation for the selected model, stop before the first AI request and recheck official alternatives. This limitation is a prerequisite, not a promise of free access.

The bot calls the documented `generateContent` API and never changes its model automatically. A 429 response pauses API calls for the server's Retry-After interval, at least 60 seconds; without a usable header it waits one hour. A daily allocation can take longer to reset, so later attempts may still fail. There is no infinite retry loop. It does not manufacture a conversational answer when the provider fails.

An additional **100-request UTC-day cap** and **one simultaneous AI request** are local protective defaults, not provider quotas. A rejected generated reply can use one additional request. These counters and outage timers are in memory and reset on restart. They cannot guarantee zero charges on a billing-enabled account.

## 4. How the system works

1. Discord delivers a server message to the official bot connection.
2. The bot checks server/channel allowlists and ignores itself and other bots.
3. A direct mention or reply to Orion can trigger a response. Ordinary channel messages remain silent and may enter the small permitted-channel context buffer.
4. Cooldowns, duplicate protection, input-length limits and input moderation run before AI work.
5. Common requests to repeat, echo or output a participant-supplied phrase are refused locally without an AI request.
6. Common identity and creator questions, help and reset commands are handled locally without an AI request.
7. The context builder gathers permitted nearby messages and a same-channel referenced message. Every item is moderated, bounded and marked as untrusted data. Attachment files, embeds and linked pages are never downloaded.
8. The provider adapter sends the immutable identity/rules as system instructions, separate from a JSON object containing user data. For Gemini, hate and harassment safety settings remain enabled.
9. Output checks reject configured slurs and common wrong-identity claims, remove emoji/emoticons and em dashes, and apply Discord's length bound at the last complete sentence when possible. A rejected response can be regenerated once, without repeating the rejected text. A second failure yields a checked neutral fallback.
10. The single `SafeSender` path checks even errors, quota notices and fallback messages immediately before sending. Mentions and link embeds are disabled. If operator filters also prohibit the fallback, the bot stays silent.

History is **RAM only**, with no database or chat logs. Defaults: eight nearby messages, ten-minute context window, 6,000 nearby-context characters, and at most 100 active channel buffers. The current message and optional referenced message are separately bounded at 3,000 characters each. Expired text is excluded immediately on use and pruned from idle buffers at most 30 seconds later. Discord.py's extra message cache is disabled. A provider request temporarily holds its bounded payload until that request finishes.

`@Orion reset` clears this channel's context for everyone. Any permitted user may use it. It does not erase messages from Discord or a provider. Restarting Orion clears all buffers, cooldowns and counters; messages before that restart are not re-imported. Deleted/edited Discord messages already buffered can remain until reset/expiry. There is no persistent memory about individual users.

**Limits of the guards:** direct recognized identity questions have deterministic answers; common self-attribution patterns are blocked. Arbitrary natural-language paraphrases, all possible prompt injections, semantic hate without keywords, new Unicode emoji, every invented emoticon, and all multilingual attacks cannot be proven absent. The fixed identity prompt, encoded keyword rules, normalization, Gemini safety settings, output checks and tests provide several layers, not a mathematical guarantee. Unicode symbol category `So` is also removed to catch decorative symbols and kaomoji fragments; that intentionally removes some non-emoji symbols. Letters, ordinary punctuation, math operators and digits are preserved. Keyword boundaries reduce innocent-substring matches, but ambiguous homonyms and obfuscations can still cause mistakes. Educational discussion of racism is allowed without repeating prohibited terms. Provider changes can weaken semantic moderation and require fresh evaluation.

## 5. Complete project folder structure

All files below belong inside the same `Orion` folder. The ready-to-use archive already places them correctly.

```text
Orion/
  main.py                  Official Discord connection, safe sending, diagnostics
  config.py                Validated settings and private credential loading
  identity.py              Permanent Orion/Rontgen identity and system rules
  moderation.py            Configurable normalized keyword moderation
  output.py                Shared outgoing-message validation
  ai_provider.py           Gemini, OpenAI-compatible and local Ollama adapters
  conversation.py          Triggers, context, cooldowns, reset and retry policy
  settings.toml            Non-secret settings you can edit
  requirements.txt         Pinned direct dependencies
  requirements.lock        Tested complete dependency version set
  .env.example             Credential placeholders only
  .gitignore               Keeps real credentials and local files out of Git
  README.md                This walkthrough
  docs/PROJECT_FILES.md    Full source listings for every project source file
  docs/VALIDATION.md       Exact executed checks and remaining live checks
  tests/test_rules.py      Identity, moderation, Unicode and output tests
  tests/test_provider.py   Simulated provider success and failure tests
  tests/test_conversation.py  Simulated message/context/send behavior
  tests/test_config.py     Invalid-configuration and safe-default checks
  tests/test_discord_adapter.py  Official-client event adapter tests
```

`.env` and `.venv` are created locally and must not be shared. Python creates `__pycache__` automatically; it is not source code.

## 6. Full code for every file

The project files in the repository are the complete implementation, not snippets. [PROJECT_FILES.md](docs/PROJECT_FILES.md) contains their full contents, exact filenames, placement and purpose in one document. The supplied ZIP includes the actual files as well. Nothing essential is left as pseudocode. The only required personal values are your bot token, AI key, server ID and channel ID; your account must also confirm the selected model's free eligibility.

If copying manually, create the files using the exact names in that document. Do not paste Python code into PowerShell. Section 7 explains how to save files without accidental `.txt` extensions.

## 7. Windows installation and configuration tutorial

### 1. Install Python

Open [python.org/downloads/windows](https://www.python.org/downloads/windows/). Install an official **64-bit Python 3.13** release. This code requires Python 3.11 or later and was executed on Python 3.12 in Linux; a Windows/Python 3.13 run has not been performed here. Do not download an unofficial Python bundle.

For the traditional installer, select **Add python.exe to PATH** and keep the Python launcher enabled. If the current website offers the Python install manager instead, follow its official installation instructions to install Python 3.13. The website may change its labels; use the [official Windows guide](https://docs.python.org/3/using/windows.html), not an advertisement.

Open Start, type **PowerShell**, and open Windows PowerShell. This is the terminal, where commands run. Type the following command and press Enter:

```powershell
py -3.13 --version
```

Success: `Python 3.13.x`. If `py` is not found, close and reopen PowerShell, then repair the official installation and enable the launcher. Do not type the `PS C:\...>` prompt itself.

### 2. Make your project folder

In PowerShell, type:

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\Orion"
Set-Location "$env:USERPROFILE\Orion"
```

Success: the first command lists a folder and the prompt ends in `\Orion>`. With the ZIP, right-click it in File Explorer, select **Extract All**, and put its **contents** in this folder. Avoid nesting `Orion\Orion`; `main.py` must be directly in your selected project folder.

In File Explorer enable **View > Show > File name extensions** (wording differs slightly by Windows version). You should see `main.py`, not `main.py.txt`.

If creating a file manually, open Notepad, paste that file's complete contents from `docs/PROJECT_FILES.md`, choose **File > Save As**, set **Save as type: All files**, choose **UTF-8**, and enter the exact filename. Create a `tests` subfolder for the test files. A file beginning with a dot, such as `.env`, is valid on Windows. Ready-to-use files are easier and avoid copying mistakes.

In the same PowerShell window, run:

```powershell
Get-ChildItem
```

Success: `main.py`, `settings.toml`, `requirements.lock`, and `tests` are listed. This command only shows filenames.

### 3. Create a private Python environment and install libraries

A virtual environment is a folder holding this project's Python packages separately from other programs. In PowerShell, inside your Orion folder, run each command:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pip check
```

Success: the first command usually prints nothing and creates `.venv`; the second downloads and installs packages; the last says `No broken requirements found.` We call the environment's Python directly, so PowerShell activation and execution-policy changes are unnecessary. The lock file pins transitive packages too. Normal TLS and package verification stay enabled. Never add `--trusted-host` to hide a certificate problem.

### 4. Create an official Discord application and bot

Open [Discord Developer Portal > Applications](https://discord.com/developers/applications), sign in, and choose **New Application**. Name it **Orion**, agree to the terms, and create it. In this application's **Bot** settings, create the bot if one was not created automatically. The exact creation button can vary. Set its public name/icon as desired; the bot/app designation remains visible.

In **Bot**, find **Privileged Gateway Intents** and enable **Message Content Intent**. Save the change if prompted. Do not enable Server Members or Presence intents for this project. Message Content Intent lets an authorized bot receive ordinary message content, needed for nearby context and replies without a fresh mention. Larger/verified applications can need Discord approval. See [official Gateway intents](https://docs.discord.com/developers/events/gateway#gateway-intents) and [Discord.py intents guidance](https://discordpy.readthedocs.io/en/stable/intents.html).

Under **Bot**, use **Reset Token** or the token controls to obtain a **bot token**. A token is a password for that bot. Copy it only into the private `.env` file in step 7. Never retrieve or paste your personal Discord user token. Do not post the bot token in chat, screenshots, source code or GitHub.

### 5. Invite Orion with minimum permissions

In the application, open **OAuth2 > URL Generator** if offered, or the equivalent **Installation** settings. Select the `bot` scope. This bot does not use slash commands and does not require the `applications.commands` scope. Select only:

- **View Channels**
- **Send Messages**
- **Read Message History**

These permissions total **68608**. Do not grant Administrator, Manage Messages, Mention Everyone, members access or unrelated permissions. Copy the generated installation URL, open it in your browser, choose a test server you manage, and authorize the bot. You need permission to install applications in that server. See [official OAuth2 documentation](https://docs.discord.com/developers/topics/oauth2) and [permissions](https://docs.discord.com/developers/topics/permissions).

This initial setup targets ordinary text channels. Threads need their own channel ID in the allowlist, visibility and **Send Messages in Threads** permission; private threads also require membership. You can configure threads later. Forum containers are not ordinary sendable text channels.

### 6. Copy your server and channel IDs

In Discord's user settings, open **Advanced** and enable **Developer Mode**. Right-click your test server and choose **Copy Server ID**. Right-click the ordinary text channel where Orion should talk and choose **Copy Channel ID**. These are public numeric identifiers, not passwords.

Open `settings.toml` in Notepad. Replace the two empty lists at the top with your actual numbers, for example:

```toml
allowed_guild_ids = [123456789012345678]
allowed_channel_ids = [234567890123456789]
```

Those numbers are examples, not working IDs. Keep the square brackets. Do not add quotation marks. Multiple allowed IDs are separated by commas. Empty lists deny all access and cause a useful startup error. Channel permission overrides must allow Orion to view, read history and send there; seeing the bot in the server alone is insufficient.

### 7. Obtain a Gemini key and protect `.env`

Open [Google AI Studio API keys](https://aistudio.google.com/apikey). Sign in and follow its current **Create API key** workflow. A key is a password for the AI service. You may need to create or select a Google Cloud project and meet regional/age/account verification requirements. Exact current prompts were not accessible in this environment.

Before making any API request, open [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing) and AI Studio's usage/rate-limit view. Confirm **`gemini-3.8-flash`** is available to your project with a free allocation and confirm the data-use terms. Do not enable billing or enter payment details to continue this free setup. If access requires payment or no free quota is shown, pause live AI setup. The project and offline tests remain usable; free access cannot be guaranteed by this code.

In PowerShell, inside the Orion folder:

```powershell
Copy-Item .env.example .env
notepad .env
```

Success: Notepad opens the copied file. Replace `replace_with_your_bot_token` with the bot token, and `replace_with_your_ai_studio_key` with the AI Studio key. Preserve the variable names and `=` signs. Do not surround values with angle brackets. Save and close Notepad. Never run `Get-Content .env` when sharing terminal output. `.gitignore` excludes this file from normal Git adds, but cannot protect a file deliberately force-added or previously tracked.

On a shared PC, use your private Windows user account, restrict the folder's Security permissions to yourself, and avoid cloud-sync/shared folders. A plaintext `.env` is a convenience, not encrypted storage. Environment variables already set in PowerShell take precedence over `.env`; remove stale bindings privately if changing keys seems ineffective.

### 8. Validate setup without starting the bot

In PowerShell in your Orion folder, run:

```powershell
.\.venv\Scripts\python.exe main.py --check-config
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Success: `Configuration OK...` and a nonzero test count ending in `OK`. Tests simulate APIs and never contact Discord or an AI provider. Tests work before you have real keys; the configuration check needs your server/channel IDs.

After confirming free model access, run these separately:

```powershell
.\.venv\Scripts\python.exe main.py --check-ai
.\.venv\Scripts\python.exe main.py --check-discord
```

Success: `AI request and output validation OK...` and `Discord bot authentication OK...`. The first makes **one AI request**, using your free quota if your account supplies it. The second makes a read-only bot authentication request; it does not post to a channel. Neither prints credentials or raw service responses. The Discord check does not prove Gateway connectivity, intents, or channel permissions.

### 9. Start Orion

In the same PowerShell window:

```powershell
.\.venv\Scripts\python.exe main.py
```

Success: `INFO Orion connected. Listening only in configured server and channel IDs.` Keep this window open. The bot uses an outgoing connection to Discord; do not open router ports. In the allowed channel, type `@Orion hello` using Discord's real mention picker, not plain text that merely looks like a mention. Wait at least 15 seconds before a second test from the same user. Right-click Orion's message and choose **Reply**; a reply should work without another mention.

Stop with **Ctrl+C**. Run the same command to restart. Identity and configuration persist in files; conversation memory does not. To clear just the current channel while running, mention Orion and say `reset`. You do not need to delete files or reinstall packages.

### 10. Change safe behavior settings

Stop Orion, edit `settings.toml`, save, run `--check-config`, and restart. This file controls IDs, `reply_to_mentions`/`reply_to_replies`, personality, context length/expiry, cooldowns, input/output size, API timeout and request budget. `history_messages=0` disables nearby-history collection; a directly referenced message can still be used. Identity facts remain in `identity.py` and are not ordinary personality options.

`max_response_characters` is both an instruction to the model and a final safety limit. If a model still exceeds it, Orion keeps the last complete sentence that fits; a response with no completed sentence is shortened with an ellipsis.
`max_output_tokens` is the provider's generation budget. Keep it high enough for the model to finish, such as 256 or 512, and use `max_response_characters` to control the visible reply length. If a provider reports that it exhausted the token budget, Orion removes the unfinished trailing fragment.

For an intentional provider change, set `provider`, `model`, and (for OpenAI-compatible or Ollama) `base_url`. Use `ORION_AI_KEY` for the selected hosted provider. Verify its current exact model ID and free access first. An OpenAI-compatible service needs a `/v1`-style base URL without the `/chat/completions` suffix; the adapter appends that suffix. Ollama uses `http://127.0.0.1:11434` with `provider="ollama"` and an already-downloaded model name from your local model list. No AI key is transmitted to Ollama. Never point a hosted key at an untrusted endpoint. No model downloads, local GPU requirements or provider changes happen automatically.

### 11. Keeping Orion online when your Windows PC is off

Your PC must be on, awake and connected while running this copy. Closing PowerShell, sleeping Windows or turning the PC off disconnects Orion. A separate always-on computer can run it instead. Do not run two copies with the same bot token; they can produce duplicate replies because deduplication is process-local.

No genuinely free, reliable, always-on hosted VM was verified here. [Oracle Cloud Free Tier](https://www.oracle.com/cloud/free/) is a candidate to investigate, **not** a promise: verify card/identity requirements, availability, regional capacity, idle-reclamation rules and chargeable resources before creating anything. Web hosting plans that sleep or require incoming HTTP traffic are a poor fit for a persistent Discord Gateway connection. Do not run artificial keep-alive traffic to defeat hosting rules or assume GitHub Actions is free continuous bot hosting.

If using a host, install the same Python dependencies, add credentials through its secret manager, set allowlists, and run the same entry point under its supported process manager. Check its data location and free terms first. This project does not deploy, create billing accounts or configure paid hosting for you.

## 8. Testing the finished project

The offline command is `.\.venv\Scripts\python.exe -m unittest discover -s tests -v` from PowerShell in the Orion folder. It exercises actual application code with simulated Discord/provider objects. [VALIDATION.md](docs/VALIDATION.md) distinguishes executed checks from unrun live checks.

For live tests, run Orion and allow 15 seconds between attempts from the same user. Test in a private server with consenting participants. Do not type real slurs to test it. Temporarily add `"blockedexample"` to `extra_blocked_terms` in `settings.toml`, restart, and use that harmless placeholder. Remove the extra term after testing if desired.

| Test | Expected result |
| --- | --- |
| Mention Orion normally | One relevant reply; nearby permitted context may help. |
| Reply to Orion without pinging again | One reply; the referenced message is fetched if not cached and used only within the context window. |
| Ordinary message without a mention or Orion reply | Silence. |
| Mention in a channel/server outside the allowlists | Silence; no AI call or history retrieval for that channel. |
| Another bot mentions Orion, or Orion receives its own sent message | Silence; no feedback loop. |
| Repeat delivery of one message ID | At most one response attempt in the process's bounded one-hour dedup window. |
| Mention twice rapidly | Later message ignored during cooldown, rather than queued. |
| Mention `blockedexample`, `b l o c k e d e x a m p l e`, or `bl0ck3d3x@mpl3` | Neutral checked notice, no AI request containing the term. |
| Discuss discrimination without prohibited words | Ordinary respectful discussion allowed; semantic provider safety can still refuse some requests. |
| Ask `What's your name?` | Exact local answer: `I'm Orion, an AI chat bot.` |
| Ask `Who created you?` | Exact local answer: `I'm Orion. Rontgen created me.` |
| Ask Orion to say, repeat, echo, or output a supplied phrase | Fixed local refusal; no AI request is made. |
| Ask it to rename itself or change its creator | Recognized identity requests produce a local fixed response; tests also reject common bad model attributions. General attacks still require monitoring. |
| Ask whether it is human | It says it is an AI chat bot. |
| Ask for biography of Rontgen | It states only the known creator fact and that it lacks personal information. |
| Ask for emoji, a custom Discord emoji, an emoticon or an em dash | Prompt tells the model not to use them; tests verify removal even when a simulated model ignores that instruction. |
| Generated prohibited term or wrong creator | Tests verify one safe regeneration attempt, then checked neutral fallback. Rejected text is not reused or logged. |
| Empty or malformed AI reply | Unavailability notice, then short circuit pause. No fake AI answer. |
| Very long input | Shorten-message notice, no AI call. Large generated text is capped at the last complete sentence when possible. |
| Simulated API timeout/5xx | One failed request, 60-second pause; notices throttled separately. |
| Simulated 429/exhausted quota | Quota notice, no model substitution, API calls paused. Repeated calls during the pause do not issue HTTP requests. |
| Missing AI key | Startup/diagnostic error naming the missing variable, no secret value. |
| Invalid AI key or forbidden access | Operator-attention notice; one-hour AI pause. Some 403s are regional/network authorization failures, not bad keys. |
| Daily local request cap | Quota notice; no additional AI requests until the UTC day changes or the process restarts. Do not use restarting to evade provider quotas. |
| `@Orion reset` | This channel's RAM context clears; old messages are not reimported in this process. |
| Stop and restart Orion | Identity/configuration survive; previous conversation context, counters and cooldowns clear. |
| Reset or TTL expiry | Does not delete Discord messages or data already sent to the provider. |

You do not need to deliberately break real keys, exhaust your account's quota, or send offensive content to test these paths. The automated tests cover them with harmless inputs and mock HTTP responses.

## 9. Troubleshooting and common mistakes

| Symptom | What to do |
| --- | --- |
| `py` not found | Reopen PowerShell; install/repair official Python and its launcher. |
| Python file opens Notepad instead of running | Run the exact terminal command; check that the file is not `main.py.txt`. |
| `No module named discord` or another package | Run the install command with `.\.venv\Scripts\python.exe`, then use the same Python to start. |
| Cannot read settings / unknown key | Keep TOML quotes, commas and brackets valid. Use the shipped key names. No credentials belong in TOML. |
| `Set allowed_...` error | Replace empty lists with real numeric IDs. Empty does not mean all. |
| Missing `DISCORD_BOT_TOKEN` / `ORION_AI_KEY` | Make `.env` beside `main.py`, replace placeholders, save. Existing process environment values override this file. |
| Bot login failed | Confirm it is a bot token from this application's Bot page; reset it there and update `.env`. Never use a user token. |
| Message Content Intent required / Gateway closes | Enable it in Bot settings, save, restart; check Discord's approval rules if your bot is verified/large. |
| Connected, but no reply | Check both allowlists, true mention/reply, channel overrides, cooldowns, bot-author exclusion and a second running process. |
| Reference/history unavailable | Grant Read Message History and View Channel; deleted/unavailable references cannot be recovered. Context is bounded and excludes pre-start/pre-reset text. |
| `auth` / operator-attention notice | Key invalid, project/region access denied, or proxy rejected access. Check account settings and endpoint connectivity; do not blindly create more keys. Restart only after correcting the prerequisite to clear the local pause. |
| `configuration` | Verify exact model name, API availability, endpoint format and support for the model's generation options. A missing model or unsupported thinking option needs a configuration/provider update. No weaker model is auto-selected. |
| `400 Bad Request` | This is a rejected request, not a quota response. Update Orion: it no longer guesses `thinkingLevel="minimal"` support from a Gemini model's name. Run `--check-ai` after restarting; the updated adapter prints fixed, credential-safe hints for recognized key, region, account, thinking and output-token errors. It never prints Google's raw error body. If the hint is generic, share the detailed AI Studio error with credentials and personal content removed. A 400 alone does not establish the cause. Restart after correcting the issue to clear Orion's one-hour pause. |
| `quota` | Check AI Studio usage limits and free allocation. Wait for the documented account-specific reset. Local notices are throttled; repeated mentions do not clear the pause. |
| `outage` | The updated adapter prints a safe preceding warning distinguishing a timeout, proxy failure, general network/TLS failure, or the exact unsuccessful HTTP status. An immediate error does not establish a timeout or a provider-wide outage. For HTTP 5xx, check provider status and retry later. For network/proxy errors, check the indicated connection prerequisites. Only if it actually reports a timeout, try `request_timeout_seconds = 120` and restart. A request can time out before the total deadline due to transport limits. Requests pause for 60 seconds after failure. Do not disable TLS verification. |
| `empty` | Provider returned no usable text or an unexpected response shape; it could have hit a token/thinking limit. Check the model's current output settings and diagnostics before changing the token cap. |
| One odd response is suppressed | Conservative identity/keyword checks can reject innocent phrasing. Review harmless regression cases; do not disable all moderation to make a single response pass. |
| No message even for an error | Cooldown/notice suppression, missing send permissions, or custom filters prohibiting the fallback can intentionally cause silence. |
| Certificate error | Update a trusted Python/certificate installation or configure your organization's trusted CA through supported HTTP-client settings. Never use `verify=False`. |
| Windows package install fails | Use a supported 64-bit Python and current official pip/wheels. Check the first error and network policy before retrying. Linux validation does not prove all future Windows wheel availability. |

For ordinary settings edits, stop and restart. For token exposure, rotate immediately, then update the private file and restart. Never paste tokens or complete `.env` contents into a bug report.

## 10. Security, privacy and maintenance

- Tell channel participants that Orion is an AI bot and sends limited selected messages to your AI provider. Only install it where you have authority and consent. Reading history does not mean it should read every server channel.
- Keep the allowlists narrow. Threads need separate IDs and permissions. Direct messages are disabled. The bot never downloads attachments or executes model code, tools, shell commands or linked content.
- A hostile message can still influence a model. Role separation and deterministic guards reduce risk but do not eliminate every injection or identity paraphrase. Do not grant the bot administrative powers or connect secret-reading tools.
- Keep bot tokens and API keys out of Git, screenshots and shared logs. Application logging contains status categories, not messages, user names, provider response bodies or secrets. Third-party logs are filtered at the configured console handler. Do not enable raw HTTP or Discord debug logs with real traffic.
- Reset a leaked bot token in Developer Portal > Bot. Revoke/replace a leaked AI key in AI Studio. Update private credentials and restart. Removing a leaked token from the latest commit does not remove it from Git history; rotation comes first.
- `.env` is local plaintext. On Linux use owner-only file access; on Windows restrict the folder's Security ACL. A hosting secret manager is preferable for a shared host. Never put credentials into the supplied source listings or environment setup scripts.
- In a Codex cloud environment, a proxy-injected placeholder may work for the AI HTTPS request but is **not a usable raw Discord token inside the Gateway WebSocket Identify payload**. Do not copy a placeholder into `.env` or assume a saved proxy binding enables Discord login. Live cloud startup requires a supported secure raw-runtime bot-token mechanism and permitted WebSocket egress; otherwise run the bot on Windows. No real secrets were supplied or live channels contacted during development.
- Hosting/domain needs: `pypi.org` and `files.pythonhosted.org` for package installation; `generativelanguage.googleapis.com` for Gemini; `discord.com` for REST; the Gateway endpoint returned by Discord, normally `gateway.discord.gg`, for WebSockets. Use HTTPS/WSS and trusted certificates. No inbound port is required. Provider alternatives need their explicitly configured destinations.
- Ten-minute RAM expiry and reset apply only to this process. Discord and hosted providers have their own storage/retention policies; the bot cannot erase those copies. Free-service training/data-use rules can differ by region and account. Do not send confidential information until those terms are verified. Local Ollama avoids the separate AI host, while Discord still stores conversations.
- Recheck model pricing, free eligibility, quota dashboards, region availability and data terms regularly. Free programs can shrink or disappear. No provider's continued free access, SLA or future model availability is guaranteed.
- Dependencies are pinned. To update, work on a copy, review release notes and security advisories, update version pins deliberately, reinstall with verification enabled, run all tests, and perform a private live smoke test before replacing a working bot. Keep the tested source, configuration and dependency pins together. Never share `.env` in a backup or ZIP.
