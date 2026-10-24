# Orion Privacy Policy

**Effective date:** October 24, 2026

**Last updated:** October 24, 2026

This Privacy Policy explains how the official Orion Discord application and bot (**Orion**) processes personal data. Orion is operated by Rontgen, GitHub user [robrttr3](https://github.com/robrttr3) (the **Operator**, **we**, **us**, or **our**).

This policy applies to the official Orion application. A person who independently hosts, modifies, or operates a copy of Orion controls that deployment and must provide an accurate privacy policy for it.

## 1. Scope and summary

Orion processes limited Discord message and identifier data to decide whether to respond, build short-lived conversational context, prevent duplicate or excessive requests, moderate content, and obtain an AI-generated response. Orion does not maintain a user-profile database, sell personal data, serve advertising, or download attachments.

The Operator does not use Discord messages to train or fine-tune an AI model. A hosted AI provider may process submitted text under that provider's own terms, privacy policy, account settings, and data controls.

Selected message text can be sent to the AI provider configured for the deployment. Discord and that AI provider process data under their own privacy terms.

## 2. Data Orion processes

Depending on how Orion is configured and used, it processes:

- **Discord identifiers:** server, channel, message, and user IDs needed for allowlists, routing, reply handling, deduplication, cooldowns, and context reset;
- **message information:** message text, creation time, whether the author is a bot, whether Orion was mentioned, and whether the message replies to Orion;
- **limited conversational context:** a bounded number of recent messages from an allowed channel and, when applicable, the same-channel message being replied to;
- **configuration and operational state:** allowed server and channel IDs, cooldown timestamps, request counts, outage state, context reset timestamps, and configured model/provider information; and
- **diagnostic categories:** locally authored status such as authentication, quota, configuration, timeout, or outage categories.

Discord may deliver an event before Orion applies its allowlists. Orion immediately ignores messages outside configured servers and channels and does not add them to its context.

Orion strips its own mention from the current message before processing. AI requests use generic speaker labels rather than deliberately adding Discord usernames or user IDs. Message text itself can still contain names, mentions, IDs, links, or other information supplied by participants.

Orion does **not** intentionally:

- access direct messages;
- download or inspect attachment files, embeds, or linked pages;
- collect payment data, address books, precise location, or Discord passwords;
- log message content, usernames, API responses, bot tokens, or AI keys; or
- create persistent behavioral or advertising profiles.

Do not send secrets or sensitive personal data to Orion. If users place such data in a processed message, it may be included in temporary context and in an AI-provider request.

## 3. How Orion uses data

Orion uses the data described above to:

- verify that a message comes from an allowed server and channel;
- respond to a direct mention or a reply to Orion;
- maintain limited short-term context so replies can remain relevant;
- enforce cooldowns, deduplicate message events, limit requests, and prevent bot loops;
- apply input and output moderation, language, identity, and length rules;
- send a bounded prompt to the configured AI provider and deliver the checked response through Discord;
- diagnose availability, authentication, quota, and configuration failures without recording message text; and
- protect Orion, participants, Discord, and providers from abuse or security threats.

Where a legal basis is required, processing is based on performance of the requested service, the Operator's legitimate interests in operating and securing Orion, consent where applicable, and compliance with legal obligations. Server owners and administrators are responsible for any additional notice or consent required for their community and configuration.

## 4. When data is sent to an AI provider

When an eligible message triggers an AI response, Orion sends the configured provider:

- permanent system instructions;
- the current message text;
- an eligible same-channel referenced message, if present; and
- bounded recent context from the allowed channel.

The payload uses generic labels such as **participant** and **Orion** rather than deliberately including usernames or user IDs. Content written by users can nevertheless contain identifying information.

The deployment may use [Google Gemini](https://policies.google.com/privacy), an OpenAI-compatible provider such as [Groq](https://console.groq.com/docs/your-data), or a local [Ollama](https://ollama.com/) instance. The active provider is selected by the Operator and is not changed automatically. Hosted providers receive the selected text over an encrypted connection and may process or retain it according to their own terms, account settings, and legal obligations. Local Ollama processing avoids a separate hosted AI recipient, but Discord still processes Discord messages.

Before enabling Orion in a community, the server operator should identify the active provider and review that provider's current privacy and data-use terms.

## 5. Other disclosures

Personal data may also be processed or disclosed to:

- **Discord**, which delivers and stores Discord messages and bot interactions under the [Discord Privacy Policy](https://discord.com/privacy);
- **hosting and network providers**, to operate the process and transmit requests, subject to their own contracts and logs;
- **service maintainers**, when necessary to investigate a security or reliability problem and only with access appropriate to that task; and
- **authorities or other parties**, when reasonably necessary to comply with law, protect rights and safety, investigate abuse, or respond to valid legal process.

Orion does not sell personal data, share it for cross-context behavioral advertising, or use it to build advertising profiles.

## 6. Retention and deletion

Orion is designed around volatile memory rather than a conversation database:

- Message context is stored only in process memory. The default context window is 10 minutes and the configured maximum permitted by the application is 60 minutes. Expired messages are excluded when context is used and are pruned from inactive channel buffers. A restart clears all context.
- A message edited or deleted in Discord can remain in Orion's in-memory context until reset, expiry, eviction, or restart because Discord changes are not used to rewrite an existing context buffer.
- `@Orion reset` clears Orion's context for that channel in the running process. It does not delete Discord messages or data already sent to an AI provider.
- Message IDs used for duplicate detection become ineffective after approximately one hour and are pruned during later traffic. Bounded user and channel identifiers, cooldown timestamps, counters, and reset markers remain only in process memory until eviction or restart.
- An AI request temporarily holds its bounded payload until the request completes. The application does not write the payload to a database or application log.
- Application logs contain status categories rather than message content, usernames, Discord IDs, credentials, or raw provider responses. A host may retain those status-only logs under its own operational policy.
- Allowed server and channel IDs and other non-secret deployment settings remain in configuration until the Operator changes them.

Discord and hosted AI providers control their own copies and retention. Orion's reset command and process restart cannot erase those third-party copies. Requests concerning data held by Discord or an AI provider may need to be directed to that service.

## 7. Your choices and controls

You can limit Orion's processing by not mentioning or replying to Orion and by avoiding messages in channels where Orion is configured to collect nearby context. You can ask a server administrator which channels are enabled, request that Orion's permissions be removed, or ask that the bot be removed from the server.

Any permitted user can mention Orion and send `reset` to clear the current channel's in-memory conversation context. Because this affects the shared channel context, other participants should be considered before using it.

Server administrators can restrict Orion to specific channels, disable its access to message history, remove the bot, or revoke its permissions. Disabling history access can reduce functionality but does not alter data already held by Discord or a provider.

## 8. Privacy rights

Depending on where you live, you may have rights to access, correct, delete, restrict, or object to processing of personal data, obtain a portable copy, withdraw consent, or complain to a data-protection authority. These rights can be subject to legal exceptions.

Orion has no persistent user-profile or conversation database, so the Operator may have little or no stored data that can be linked to a requester. The Operator may request reasonable information to verify identity, server membership, authority, and the scope of a request. We will not ask for a password, bot token, or AI key.

To begin a request, open an issue titled **Privacy request** in the [Orion support repository](https://github.com/robrttr3/orion-discord-bot/issues) without posting personal data or message content. The Operator will provide next steps and, when necessary, arrange a non-public method for verification. You may also contact Discord or the active AI provider directly regarding data they control.

## 9. Security

Orion uses bounded in-memory context, server and channel allowlists, encrypted provider connections, minimal Discord intents, credential separation, disabled message-content logging, rate limits, and output validation. No system can guarantee absolute security. Server administrators should grant only the permissions Orion needs, keep credentials secret, install updates, and promptly report suspected misuse.

Do not put bot tokens, AI keys, private messages, or sensitive personal data in a public support issue. If a credential is exposed, revoke and replace it through the service that issued it.

## 10. International processing

Discord, an AI provider, and hosting or network providers may process data in countries other than your own. Those countries may have different data-protection laws. Where required, the responsible provider or Operator will rely on an applicable legal transfer mechanism. Review the active provider's policy for details about its locations and safeguards.

## 11. Children

Orion is not directed to children who are below the minimum age required to use Discord in their country. The Operator does not knowingly create profiles about children. If you believe a child has provided personal data contrary to applicable requirements, submit a privacy request so the matter can be reviewed.

## 12. Changes to this policy

We may update this policy to reflect changes to Orion, providers, Discord requirements, or law. The date at the top will be updated when changes are published. Material changes may also be announced through the repository, the Discord application profile, or an appropriate server notice.

## 13. Contact

For privacy questions or requests, open an issue titled **Privacy request** in the [Orion support repository](https://github.com/robrttr3/orion-discord-bot/issues) without including personal data. For general support, use the same issue tracker and do not post credentials or private message content.
