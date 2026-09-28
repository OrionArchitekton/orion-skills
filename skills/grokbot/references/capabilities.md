# Grok Bot capability reference (xAI + Cursor docs, read 2026-09-27)

Sources: 20 docs.x.ai/grok-bot pages (full sitemap set) and 17 cursor.com Grok Bot doc/help pages, pages last updated Aug 11 to Sep 21 2026. The "Meet grok-4.7" string on docs.x.ai is a site-wide header banner. It does not say which model Grok Bot uses.

## 1. What a bot is
- A durable AI teammate with a name, label, description (its standing rules), avatar, its own conversation, and context that builds up over time. The desktop app runs on macOS, Windows and Linux; the mobile app runs on iOS/iPadOS 18+ and Android 9+. https://docs.x.ai/grok-bot/bots
- Access requires a Cursor account. Grok Bot is billed and metered through Cursor, not the Grok app, and Cursor calls them "two different apps". https://cursor.com/help/grok-bot/faqs
- Memory holds stable preferences, important facts and summaries of past work, kept separately for each Bot. Docs say memory is "not a substitute for an authoritative source". Duplicating a Bot does not copy its memory or history. https://docs.x.ai/grok-bot/bots
- There is no documented way to view, edit or clear a Bot's memory. Auto Review does not check memory writes. https://docs.x.ai/grok-bot/security
- Computer: one persistent cloud computer per USER, not per Bot. It is a Firecracker microVM with its own kernel, and user-to-user isolation happens at the hardware level. https://docs.x.ai/grok-bot/teams-and-enterprises
- The computer runs Linux (Debian-based) in Cursor's cloud. It is not enrolled in MDM and runs in the US today. https://cursor.com/docs/grok-bot/deployment
- All of a user's Bots share the browser cookies and logins, the files, and the command-line credentials. Each Bot gets its own screen, but screens "are separate work surfaces, not separate security boundaries". https://docs.x.ai/grok-bot/computer-and-apps
- Durable files live in `/workspace`. Files, browser state and logins survive Update and Recover. Temp directories and installed apps/packages are removed by Update, Recover and Reset. https://cursor.com/help/grok-bot/computer-recovery
- Idle computers hibernate. Conversations are stored outside the computer, so they survive a Reset. A "Disk Saver" Bot proposes cleanup and deletes nothing without your confirmation. https://cursor.com/help/grok-bot/computer-recovery
- Work continues when your laptop or phone is closed. You can watch the computer live ("Agent Computer") and take control yourself. https://docs.x.ai/grok-bot/overview
- A Bot has no identity of its own: it acts as the signed-in member and never holds more access than that member. The one exception is team-managed connectors, which can use service accounts. https://docs.x.ai/grok-bot/security
- Per-Bot Secrets: an env-var name, a description (the Bot can see this) and a value (the Bot and model never see it). Values are write-only and can be "filled into the page". https://cursor.com/help/grok-bot/secrets

## 2. What bots can do
- Apps: connectors are plugins installed from Marketplace. Plugins are account-wide, so every Bot can use every installed plugin. OAuth tokens stay on Cursor's backend and never reach the computer. https://cursor.com/docs/grok-bot/work
- Where no plugin exists, Bots use the computer's browser (computer use). https://docs.x.ai/grok-bot/computer-and-apps
- Named plugins: Gmail (search, read, draft, send, label; ONE mailbox at a time), Google Calendar, Drive, Sheets, Docs, Slides, Slack (posts as you, not as a bot user), Notion (supports multiple accounts) and Zoom (currently broken with error 4700). https://cursor.com/help/grok-bot/connect-plugins
- Google sees the OAuth app as "Grok", so Workspace admins must trust it. Plugins cannot raise your access or change sharing settings. https://cursor.com/help/grok-bot/connect-plugins
- MCP: the team's Cursor MCP/connector policy applies in full. The MCP allowlist is Enterprise only. Admins can block plugins but cannot push them to members. Individual plugin tools can be switched on or off. https://docs.x.ai/grok-bot/teams-and-enterprises
- Adding your own custom MCP server URL as an individual is not documented. https://docs.x.ai/grok-bot/settings-and-notifications
- Skills: reusable instructions (steps, decision rules, output format, what needs approval). One private skill library is shared by all your Bots. Marketplace also offers "packaged skills". Use `/` to reference a skill. https://docs.x.ai/grok-bot/skills-routines-and-automations
- "Teach a task": record a browser workflow (up to 10 minutes, no microphone audio) and the Bot turns it into a draft skill. It is rolling out gradually and is desktop-only. https://docs.x.ai/grok-bot/skills-routines-and-automations
- Email inboxes for Bots: not documented. There is no per-Bot email address. Email works through the Gmail plugin (your own mailbox), and email drafts appear as cards with Send or Discard. https://docs.x.ai/grok-bot/chat-and-collaboration
- Group chats hold 2 to 6 Bots. Use `@` to target one Bot and `@everyone` to address all of them. Handoffs from a Bot to the group are text-only, and voice chat does not work in groups. https://docs.x.ai/grok-bot/chat-and-collaboration
- Bots can message each other asynchronously (the receiving Bot wakes up). There is no switch to turn this off. Every Bot reply, including Bot-to-Bot replies, counts toward usage. https://cursor.com/help/grok-bot/group-chats
- Bots can create "helper Bots", which appear in your sidebar. https://cursor.com/help/grok-bot/how-to
- Bots can hand coding tasks to Cursor Cloud Agents, which run on separate VMs. This is on by default and admins can turn it off. https://docs.x.ai/grok-bot/teams-and-enterprises
- Voice: dictation, live voice chat (one at a time) and voice memos sent by a Bot. https://cursor.com/help/grok-bot/voice-chat
- Templates: sharing a Bot via "Create template" (public or team-only link) shares its identity, description, skills and routines, but not its computer, logins or history. Adding someone else's template accepts third-party bot terms. https://docs.x.ai/grok-bot/bots
- Routines: one routine = one Bot + an instruction + a "when". You create and edit them by chatting with the Bot. They run in the cloud. Limits are 50 routines per Bot, with the 20 most recent run records kept. https://docs.x.ai/grok-bot/skills-routines-and-automations
- Schedule trigger: written in plain words ("every 2 hours"), using Settings > Bot > Timezone. A new routine waits for its next slot. "Test" does real work and spends usage. https://cursor.com/help/grok-bot/routines
- Slack trigger: part of the routine, not the Slack plugin, and needs Slack connected on the Cursor account that owns the Bot. It fires on a Bot mention, a phrase, your reaction, or any message, in one channel or all of Slack, and only for new activity. https://cursor.com/help/grok-bot/routines
- GitHub, Linear, Sentry, PagerDuty and email triggers are only named as event sources. Their setup, filters and payload are not documented. These are "Cursor account integrations" and are separate from plugins. https://cursor.com/help/grok-bot/routines
- **Webhook contract (the complete documented contract):** HTTP `POST` to the routine's "POST to" URL, with header `Authorization: Bearer <key>` and an optional JSON body. The Bot receives the body together with the routine instruction. https://cursor.com/help/grok-bot/routines
- Webhook response: `200` means the call was accepted and a run started, not that the run finished. Any other response means no run started. Results appear in the Bot's chat, not in a callback. https://cursor.com/help/grok-bot/routines
- Not documented for webhooks: key rotation, rate limits, body size limit, retries or idempotency, a response body, or payload/event schemas for the other triggers. https://cursor.com/help/grok-bot/routines

## 3. Local computer access
- What it allows: run commands, read files, and move files between the cloud computer and your machine, through the desktop app. It is a separate control from Auto Review (which covers the cloud computer). https://docs.x.ai/grok-bot/security
- The three settings are Ask every time (the default), Always allow and Never allow. They live under Settings > General > Bot > Execution on Local Computer, or per machine under Settings > Computer > Computers ("Execution on this computer"). https://docs.x.ai/grok-bot/approvals-security-and-privacy
- Per-command approval: the card shows the exact command. The first request offers Always allow / Allow once / Never / Deny once (Esc). "Always allow" and "Never" apply to ALL Bots. https://docs.x.ai/grok-bot/approvals-security-and-privacy
- A team admin can cap the setting. The team ceiling defaults to "Always allow", which leaves the choice to each member, and the stricter of team and member settings wins. The docs recommend Never allow. https://docs.x.ai/grok-bot/teams-and-enterprises
- Related local features: "Route egress through this desktop" (sites see your IP and the Bot can reach your networks) and a hardware security key passed through from your desktop, which asks for approval on every use and does not work on Linux. https://docs.x.ai/grok-bot/settings-and-notifications

## 4. Approvals and safety model
- Approval cards show the proposed operation and its inputs, with Allow once / Always allow (saves a rule) / Deny. An approval does not undo work already done, and "Stop now" does not undo completed actions. https://docs.x.ai/grok-bot/approvals-security-and-privacy
- Auto Review is a separate review model that checks shell commands, plugin calls, computer use, automation writes (routines and triggers) and Cloud Agent/subagent launches. It can allow, ask or deny. It does NOT check memory writes or most settings changes. https://docs.x.ai/grok-bot/security
- Rules come in two kinds: "Ask first" and "Allow automatically"; when both match, Ask first wins. Enforcement and team rules are Enterprise-only. Whether Auto Review is on by default for individuals is not documented. https://docs.x.ai/grok-bot/approvals-security-and-privacy
- Approvals triggered by unattended work (a routine, a trigger or another Bot) expire after about 10 minutes, and the action then does not run. https://cursor.com/help/grok-bot/how-to
- Always handed to the human, never typed by the Bot: passwords, passkeys, 2FA, CAPTCHAs, payment and identity checks. The Bot does not see what you type during takeover. https://cursor.com/docs/grok-bot/work
- Laptop passkeys and Face ID/Windows Hello do not work on the Bot's computer. https://cursor.com/help/grok-bot/how-to
- Sending, publishing, purchases, deletes, permission changes, production changes and legal terms are only RECOMMENDED "Ask first" boundaries. The docs list no hard-coded set of actions that always require approval: it depends on "the tool, the risk of the action, and... your Auto-review rules". https://docs.x.ai/grok-bot/faq
- Prompt injection: outside content is marked as untrusted, and the docs say the defenses "reduce, but do not eliminate" the risk. https://docs.x.ai/grok-bot/security

## 5. Limits, pricing, weaknesses
- Access is included with Cursor Pro, Pro+, Ultra and self-serve Teams, or by linking an individual SuperGrok / Plus / Heavy or X Premium+ subscription. Lite, SuperGrok Team and SuperGrok Enterprise are excluded. Enterprise access goes through your account team. https://cursor.com/help/grok-bot/plans
- Usage is a WEEKLY allowance tiered by plan (Ultra > Pro+ > Pro), and no numbers are published. Plans do not stack, and a SuperGrok link is permanent. On-demand usage past the allowance is billed from model and token cost. https://cursor.com/help/grok-bot/plans
- The monthly on-demand cap is not a hard stop mid-run. There is no separate Grok Bot spend cap for teams. https://docs.x.ai/grok-bot/teams-and-enterprises
- The trial is a usage credit (metered by agent steps and tokens) with a 7-day window. One large task can use all of it, and used credit is not restored. An hourly routine or a busy Slack trigger "can use a week of usage in a day". https://cursor.com/help/grok-bot/routines
- Concurrency: Bots run in parallel, but each Bot runs only one computer-use task at a time on its screen. A maximum number of Bots or parallel runs is not documented. https://docs.x.ai/grok-bot/computer-and-apps
- Run length: no maximum turn or run duration is documented. The only duration limits are the 10-minute Teach-a-task recording and the 30-minute timeout on Team Setup scripts. https://docs.x.ai/grok-bot/private-networks
- Attachments: 6 per message on desktop, 25 MB for documents, images and audio, 200 MB for video. Android sharing accepts text only. https://docs.x.ai/grok-bot/files-and-results
- No model picker: "Cursor manages model selection", the model mix can change, and no fixed vendor is guaranteed. The Enterprise model allowlist "may not" be followed. https://docs.x.ai/grok-bot/security
- Not available: on-prem or bring-your-own image, dedicated egress IPs (shared datacenter IPs get blocked by some sites), DLP hooks, an EDR feed, a per-org retention policy, or point-in-time restore for a computer. https://docs.x.ai/grok-bot/security
- Separate Bots are not a security boundary. For separate credentials, use a separate Cursor user. https://docs.x.ai/grok-bot/security-faq
- Weak spots the docs admit: sites that block automation or expire sessions; the Calendar plugin cannot change Meet settings or add Zoom links; installed packages are lost on Update; editing and testing routines is desktop-only. https://cursor.com/help/grok-bot/connect-plugins
- Routines may be paused after "a long period away" if you do not respond. The app must be updated when it is more than 14 days old. Legacy Privacy Mode blocks Grok Bot entirely. https://cursor.com/help/grok-bot/how-to

## 6. Open questions (not documented)
- Per-plan weekly usage numbers, and the cost per run or step. https://cursor.com/help/grok-bot/plans
- Setup, filters and payload for GitHub, Linear, Sentry, PagerDuty and email triggers; which mailbox the email trigger watches; webhook rate limits, rotation and retries. https://cursor.com/help/grok-bot/routines
- Whether users can add their own custom or remote MCP servers outside the team Marketplace. https://docs.x.ai/grok-bot/computer-and-apps
- Maximum Bots per account, maximum concurrent Bots, maximum run length, and computer CPU, RAM and disk specs. https://docs.x.ai/grok-bot/overview
- Whether Auto Review is on by default for individuals and self-serve Teams, and how to inspect or delete a Bot's memory. https://docs.x.ai/grok-bot/approvals-security-and-privacy
- Which models serve Bots. The only answer is "Cursor manages model selection". https://cursor.com/help/grok-bot/faqs
- Any API or SDK for driving Bots programmatically, other than routine webhooks and the admin-only Admin API. https://docs.x.ai/grok-bot/teams-and-enterprises
- Places where the two doc sites disagree: (a) x.ai says Auto-review rules sync to the account and apply on every desktop, while cursor.com/docs/grok-bot/settings says they are stored per desktop; (b) x.ai says setup scripts cannot hold secrets, while cursor.com teams documents Enterprise Team Secrets (100 per team, 32 KB each, 96 KB total); (c) x.ai omits X Premium+ from its list of plans that can link. https://cursor.com/docs/grok-bot/teams
