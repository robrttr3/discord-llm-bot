# Validation record

Executed on 22 October 2026 in the supplied Linux cloud workspace, using Python 3.12.14. This is not a Windows validation or a live Discord/AI integration result.

## Passed

- Created the repository-local `.venv` and installed pinned packages from PyPI with TLS verification enabled.
- Re-ran installation from `requirements.lock`; every required version was already installed. Dependency checking reported `No broken requirements found.`
- Executed the complete reusable cloud install script, including the real automated test command.
- `python -m unittest discover -s tests -q`: **69 tests passed** after the Gemini request compatibility and diagnostic updates (the initial project had 64). This includes all emoji sequences in the installed emoji database in one test, common emoticons, moderation normalization, identity, safe sending, triggers, references, context expiry/reset, cooldowns, provider payloads, malformed/empty output, timeout, authentication errors, 429/quota pauses, and daily limits. New tests check that different Gemini model names do not inject guessed thinking settings, and that recognized 400 errors produce fixed diagnostic hints without logging keys or arbitrary provider text. Malformed error bodies use a safe generic hint. Further tests distinguish timeout, proxy, network and HTTP-status outage hints while checking that exception/response contents and keys remain unlogged. The cause of the operator's live immediate outage remains unconfirmed until a retest supplies that diagnostic.
- Instantiated the official `discord.Client` subclass and invoked its event handlers with simulated Discord messages. Verified reference fetching, mention removal, reply triggering, safe output, disallowed-channel silence, bot-loop prevention, minimum intents, disabled message cache, and cleanup-task lifecycle.
- Ran `main.py --config /tmp/orion-smoke.toml --check-config` with a temporary configuration containing harmless synthetic server/channel IDs. It printed `Configuration OK. Allowlists and output rules loaded. Credentials not tested.` No real channel was accessed.
- Confirmed shipped empty allowlists fail closed with a local configuration error. No user's real IDs were guessed or written into settings.
- Confirmed `DISCORD_BOT_TOKEN`, `ORION_AI_KEY`, `GEMINI_API_KEY`, and `GROQ_API_KEY` were absent by checking presence only. No credential values were printed or copied.

## Not run or not established

- Live AI authentication, model availability for a specific account, model output quality, end-to-end provider safety behavior and real quota enforcement: no AI key supplied.
- Live Discord login, Gateway connection, channel permissions and sending: no bot token or actual permitted server/channel IDs supplied.
- Windows and Python 3.13 execution: no Windows runtime available here.
- Exact current free allocation, payment/verification conditions, or regional provider data-use terms: official pricing/terms hosts were blocked by the network proxy. The default model name and API usage were verified against Google's official GitHub examples, not a live model request.
- Free always-on hosting and uptime guarantees: not verified; no deployment performed.
- Publication or restoration in a fresh cloud task: saving environment instructions does not publish or validate a restored snapshot.
- Absolute semantic identity/moderation correctness against all language, invented emoticons and future emoji: not claimed. See README limitations.

The project is prepared for local development and offline tests. Live operation remains conditional on the operator's credentials, free-tier confirmation, allowlists, Message Content Intent, channel permissions and network access.

## Saved cloud configuration

The environment draft save returned `status: saved` and `requires_publish: true`.

- `install_script`: repository-local virtual environment, installation from `requirements.lock`, dependency check and test suite. The same script was executed successfully in this workspace.
- `start_skill`: use the existing isolated checkout without creating worktrees; use the local Python, check prerequisites, run diagnostics, start the official bot only with usable credentials, and validate actual mentions/replies. It distinguishes retained dependencies from processes that must restart.
- `ORION_AI_KEY`: an additive proxy-secret requirement for `generativelanguage.googleapis.com`. No key value was saved or supplied.
- Custom network domains: `ai.google.dev`, `aistudio.google.com`, `generativelanguage.googleapis.com`, `support.discord.com`, `docs.discord.com`, `discord.com`, `gateway.discord.gg`, `console.groq.com`, `api.groq.com`, `openrouter.ai`, and `docs.mistral.ai`. The existing package-manager presets were preserved. The documentation destinations support the requested provider research; the runtime destinations support Gemini and Discord.

Saving did not apply the network rules, inject credentials, start the bot or publish the snapshot. Review and save these changes in environment settings, then publish the environment if retaining this cloud setup. A usable secure raw Discord bot-token binding remains a separate prerequisite because a proxy placeholder cannot authenticate inside Gateway WebSocket payloads. The Windows tutorial uses your private local `.env` instead.
