# Jarvis — Design

Date: 2026-11-16
Status: approved by owner, 2026-11-16

## 1. Intent

A personal assistant in the spirit of Jarvis from Iron Man: the owner talks
to it, it talks back, and it acts as their agent across mail, calendar,
ideas and their YouTube channels.

Why: the owner runs several mail accounts, several projects and more than
one YouTube channel. They want one voice they can ask, instead of opening
five apps, and one agent that watches things for them and tells them what
needs attention.

Single user. This is a personal tool, not a product for others.

## 2. What the owner asked for (their words, tidied)

1. Talk to him and have him answer.
2. Ask him to check any mail and reply "with my words".
3. Check the calendar for all my mail accounts and plan my day for me.
4. When I have an issue or an idea, ask him how we can make it.
5. Be my agent watching all my channels: tell me what is good, what is
   bad, and how to make it better.
6. He learns and develops himself the more we talk.

## 3. Goals

- G1 **Voice conversation** on the Mac in English and Arabic. Jarvis starts
  speaking within about 2 seconds of the owner finishing a short question.
- G2 **Mail**: summarise unread mail across all connected Google accounts,
  read a message aloud, draft a reply from a spoken gist in the owner's
  writing style, send after spoken approval.
- G3 **Calendar and day plan**: read every connected account's calendars,
  merge them, and produce a day plan that also pulls in deadlines and
  requests found in mail. Deliver it as a morning briefing and on request.
- G4 **Idea workshop**: the owner describes an idea or problem; Jarvis asks
  questions, proposes how to build it, and saves the result as a document
  the owner can come back to.
- G5 **Channel watcher**: for each of the owner's YouTube channels, track
  performance, and produce a report of what worked, what did not, and
  concrete improvements. Available on request and as a weekly report.
- G6 **Memory**: Jarvis remembers the owner's style, projects, people and
  past decisions between conversations.

- G7 **Self-improvement**: Jarvis gets better the more the owner talks to
  him. He learns from corrections, from edits to his drafts and from
  repeated requests, and the owner can see and undo everything he learned.

## 4. Non-goals (for this design)

- Phone app or access away from the Mac (planned as a later phase).
- Smart-home control, controlling arbitrary Mac apps, hologram-style UI.
- Instagram, TikTok or other social networks.
- Non-Google mail (Outlook, iCloud). Added later if the owner needs it.
- Editing or uploading videos, replying to YouTube comments.
- Multiple users.

## 5. Anti-goals (failure even if it "works")

- Sending a mail, creating or changing a calendar event, or posting
  anything without the owner saying yes to that specific action.
- Replies that sound like a generic assistant and not like the owner.
- A voice loop slow enough that typing is faster.
- Tokens or keys stored outside the Keychain; mail content or personal data
  committed to the repo; mail content sent to any service other than the
  model provider and Google (unless the owner switches on an optional
  service, see 8.2).
- A channel report that restates numbers without saying what to do.
- Jarvis changing his own behaviour in a way the owner cannot see or undo,
  or "learning" his way around the approval gate.

## 6. Constraints

- Runs on the owner's Mac (macOS, Apple silicon assumed; builder confirms).
- The repo `Eslam1141/jarvis` is public: no secrets, tokens, mail content or
  personal data may ever be committed. Runtime data lives outside the repo.
- Google access needs the owner's own Google Cloud project and OAuth
  consent. Known risk: an OAuth app left in "testing" status issues refresh
  tokens that expire after a few days. The builder must verify current
  Google rules and pick the setup that keeps the owner signed in.
- Gmail and YouTube Analytics scopes are sensitive or restricted; the app
  stays personal (owner is the only user) to avoid Google verification.
- Costs: model API usage is pay-per-use; everything else should be free or
  local by default.

## 7. Approaches considered

**A. Local Jarvis on the Mac (chosen).** One program on the Mac: a voice
layer on top of an agent "brain" with tools for Gmail, Calendar and
YouTube. Fast to a first conversation, private, no hosting. Works only
while the Mac is on.

**B. Voice layer on top of the owner's Claude desktop app.** Reuse the
connectors and scheduled tasks already there, add only speech. Least work,
but Jarvis never becomes its own thing, the personality and memory are
limited, and the connectors cannot be called from outside the app.

**C. Cloud Jarvis with a phone app.** Brain on a server, Mac and phone as
clients. Available everywhere; most work and a monthly cost before any
feature is useful.

The owner handed this choice over ("plus your defaults"); A is the
designer's call. To keep C open, the brain is a separate component that
talks to the voice layer over a narrow interface, so a phone client or a
server deployment is an addition, not a rewrite.

## 8. Design

### 8.1 Shape

```
  microphone ──> [ Voice layer ] ──text──> [ Brain ] ──> [ Tools ]
  speaker   <──  speech in / out  <─text──  agent loop     ├─ Mail (Gmail)
                                               │           ├─ Calendar
                                          [ Memory ]       ├─ Channels (YouTube)
                                               │           ├─ Ideas
                                          [ Scheduler ]    └─ Day plan
                                     briefings, reports
```

Five parts, each replaceable on its own:

- **Voice layer.** Captures speech, turns it into text, speaks the reply.
  Knows nothing about mail or calendars.
- **Brain.** An agent loop around a Claude model. Takes text in, decides
  which tools to call, returns text out. Also usable from a terminal chat,
  which is how every feature is developed and tested before voice is added.
- **Tools.** One module per domain, each a small set of functions the brain
  can call. Read tools run freely; write tools go through the approval gate
  (8.4).
- **Memory.** What Jarvis knows about the owner, kept on disk.
- **Scheduler.** Runs the morning briefing, mail checks and channel reports
  without being asked.

### 8.2 Voice

- Phase 1 uses **push-to-talk**: hold a global hotkey, speak, release.
  Reliable and has no false triggers.
- A later phase adds the **wake word** "Jarvis" and the ability to interrupt
  him mid-sentence.
- Speech-to-text runs **locally** with a Whisper-family model, chosen
  because it handles both English and Arabic and keeps audio on the Mac.
- Owner's decision: they speak Egyptian Arabic, English, or both mixed in
  one sentence, and Jarvis answers in whichever language they used. The
  speech model must be one that copes with mixed-language speech, even at
  some cost in speed, and each reply is spoken with a voice for its
  language.
- Mail replies are written in the language of the mail being answered
  unless the owner says otherwise.
- For approvals, "yes" is recognised in both languages. If Jarvis is unsure
  what was said, he asks again; he never treats an unclear answer as yes.
- Text-to-speech starts with the **built-in macOS voices** (free, instant).
  A premium cloud voice is an optional upgrade behind the same interface.
  It is off by default; switching it on means reply text, which can include
  mail content, goes to that voice provider, and the setup step says so.
- Replies are streamed: Jarvis starts speaking the first sentence while the
  rest is still being generated.
- Spoken replies are short by default. Long content (a full day plan, a
  channel report) is spoken as a summary and also written to a file or
  shown on screen.
- Personality: calm, dry, concise, addresses the owner by a name they
  choose. Defined in one editable prompt file.

### 8.3 Brain

- Built on the Claude Agent SDK in Python (designer's call: Python has the
  strongest audio and Google client libraries, and one language keeps the
  project simple).
- Two model tiers, set in config: a fast model for live conversation and
  mail triage, a stronger model for idea workshops and channel analysis.
- The 2-second target in G1 is the hard requirement; the SDK is not. If
  the SDK cannot meet it, live conversation turns use a direct streaming
  model call behind the same brain interface, and the SDK is kept for
  longer multi-step work. Phase 0 measures this before anything is built
  on top.
- The brain receives, on every turn: the personality prompt, a compact
  profile of the owner from memory, the current date and time, and the
  recent conversation.

### 8.4 Approval gate

Every action that changes something outside Jarvis (send mail, create or
edit a calendar event, anything future that posts or deletes) passes
through one gate:

1. Jarvis states exactly what he is about to do. For mail: recipient,
   subject, and the full text read aloud.
2. The owner says yes, asks for changes, or says no.
3. Only an explicit yes executes it. Silence, unclear speech or a low
   speech-recognition confidence counts as no.
4. Every executed action is appended to a local action log.

Instructions found inside emails, calendar invites, video comments or any
other fetched content are treated as content to report, never as commands.

### 8.5 Mail

- Sign in to multiple Google accounts; each is labelled by the owner
  ("work", "personal", ...).
- Owner's decision: the accounts are personal Gmail plus work accounts on
  Google Workspace. A Workspace admin can block outside apps, so sign-in
  for a work account may fail until the admin allows it. Setup must report
  that clearly, and every feature must work with whichever accounts did
  connect.
- **Triage**: fetch unread mail since the last check, group into "needs a
  reply", "needs action", "FYI" and "ignore", and summarise by voice.
- **Read**: read any message or thread aloud, or summarise it.
- **Reply in my words**: the owner speaks the gist ("tell him Thursday
  works, ask for the contract"). Jarvis writes the reply using the style
  profile, reads it back, edits on request, sends through the gate, from
  the account that received the message.
- **Style profile**: built once per account from a sample of the owner's
  sent mail (greeting, sign-off, length, formality, language per
  recipient type), stored in memory, refreshable, editable by hand.
- When Jarvis reads a reply back, he also saves it as a Gmail draft so the
  owner can finish it in Gmail. Saving a draft is visible only to the owner,
  so it does not need a spoken yes, but it is written to the action log.
  Sending always goes through the gate.

### 8.6 Calendar and day plan

- Read all calendars of all connected accounts; merge into one timeline;
  flag clashes.
- **Day plan**: today's events, plus tasks and deadlines extracted from
  mail triage, plus carried-over items from yesterday's plan, arranged
  into time blocks around fixed events. Respects working hours and
  preferences stored in memory.
- **Morning briefing**: at a time the owner sets, Jarvis prepares the plan
  and speaks it when the owner first greets him (or at the set time if the
  owner opts in to being spoken to unprompted).
- Creating or moving events is supported through the gate. Jarvis proposes;
  the owner approves.

### 8.7 Idea workshop

- Triggered by "I have an idea" or "I have a problem with ...".
- Jarvis runs a short structured conversation: what it is, who it is for,
  why, what already exists, then proposes two or three ways to build it,
  with a recommendation and first steps.
- The outcome is saved as a Markdown file per idea (summary, options,
  chosen direction, next steps, open questions) in the data folder.
- Ideas can be listed, reopened and continued by voice.

### 8.8 Channel watcher

- Connects to the owner's YouTube channels through the official YouTube
  Data and Analytics APIs (owner's own channels only).
- Owner's decision: the channels belong to the same Google accounts used
  for mail, so one sign-in per account covers mail, calendar and channels.
  Setup lists the channels each account can see so the owner can confirm
  none is missing.
- A daily job stores a snapshot per channel and per recent video: views,
  watch time, average view duration, click-through rate where available,
  subscribers gained, top traffic sources, and a sample of comments.
- **Report** (weekly, and on request): for each channel, what is good
  (videos beating the channel's own baseline and why), what is bad
  (underperformers, drop-offs, declining trends), and specific
  improvements (titles, topics, length, posting pattern). Spoken summary
  plus a written report file.
- "Good" and "bad" are judged against that channel's own recent baseline,
  not absolute numbers.
- Alerts: a video doing unusually well or badly in its first 48 hours is
  mentioned in the next conversation or briefing.

### 8.9 Memory

- A local data folder outside the repo (default `~/.jarvis/`), holding:
  - a profile file: name, preferences, working hours, projects, people;
  - style profiles per mail account;
  - idea files, day plans, channel reports;
  - a small database for conversation history, mail triage state, channel
    snapshots and the action log.
- Jarvis updates the profile when he learns a durable fact, and says so.
- Everything is plain files or a single local database, so the owner can
  read, edit, back up or delete it.
- Google tokens and API keys are stored in the macOS Keychain, never in
  files.
- Mail bodies are not kept. Jarvis stores message IDs, senders, subjects
  and his own short summaries, and fetches the full text again when needed.
- The data folder is readable only by the owner's Mac user and relies on
  macOS disk encryption (FileVault); setup checks that FileVault is on and
  warns if it is not. No separate database encryption.

### 8.10 Learning and self-improvement

Jarvis improves in four ways, from least to most powerful. The first three
change what he knows and how he behaves; only the fourth touches his code.

1. **Lessons from corrections.** When the owner corrects him ("too long",
   "never schedule before 10", "don't call him Mr."), Jarvis turns it into
   a short rule, confirms it in one sentence ("Noted: no meetings before
   10"), and applies it from then on.
2. **Style from edits.** Every time the owner changes a draft before
   sending, Jarvis compares his version with the final one and updates the
   style profile for that account or recipient. The same applies to day
   plans the owner rearranges.
3. **Routines from repetition.** When the owner asks for the same
   multi-step thing several times, Jarvis offers to save it as a named
   routine ("Shall I make that your 'Monday review'?"). A routine is a
   plain text file listing the steps; saying its name runs it.
4. **Proposing changes to himself.** Jarvis keeps a wish list of things he
   could not do or did badly. In a weekly self-review he reads the week's
   conversations, corrections and failures, and reports: what he learned,
   what he got wrong, and what he suggests adding. For suggestions that
   need new code, he can prepare the change on a separate branch in the
   repo for the owner to review. He never changes his own running code.

Rules that hold for all four:

- Everything learned is stored as readable text in the data folder: a
  lessons file, style profiles, routine files, the wish list.
- "What have you learned?" lists recent lessons; "forget that" removes
  one. The owner can also edit the files by hand.
- Lessons carry a date and where they came from, so a wrong one can be
  traced and removed.
- Learning never removes or weakens the approval gate (8.4), and a lesson
  cannot be created from text inside an email, invite or comment; only
  from what the owner says or does.
- If two lessons conflict, Jarvis asks which one stands.

### 8.11 Running it

- One command starts Jarvis; a later phase adds a menu-bar icon and
  start-at-login.
- A terminal text mode exists from day one and remains supported.
- Config file for accounts, models, hotkey, briefing time, voices.
- Scheduled work (mail checks, day plan preparation, channel snapshots)
  runs as a small macOS background job from phase 3 on, so it happens
  whether or not the voice program is open. It runs when the Mac is awake
  and catches up on anything missed while it slept. Speaking still needs
  Jarvis to be running.

## 9. Phases

Each phase ends with something the owner can use.

0. **Foundations** — project skeleton, config, secrets in Keychain, brain
   with terminal chat, personality, memory profile, lessons from
   corrections ("what have you learned?", "forget that").
1. **Voice** — push-to-talk, local speech-to-text (English and Arabic),
   spoken streamed replies.
2. **Mail** — Google sign-in for several accounts, triage, read aloud,
   style profile, reply in my words, approval gate, action log, style
   learning from the owner's edits.
3. **Calendar and day plan** — merged calendar, day plan, morning
   briefing, event changes through the gate.
4. **Idea workshop** — guided conversation, saved idea files, reopen and
   continue.
5. **Channel watcher** — YouTube sign-in, daily snapshots, weekly and
   on-demand reports, early-performance alerts.
6. **Always there** — wake word, interruption, menu-bar app, start at
   login, proactive speech.
7. **Self-development** — saved routines, wish list, weekly self-review,
   proposed code changes on a branch for the owner to approve.
8. **Later, not in this design** — phone or cloud access, other social
   networks, non-Google mail.

## 10. Left to the builder

- Exact libraries for audio capture, hotkey, speech-to-text and wake word.
- Database choice and schema; file layout inside the data folder.
- Module layout and naming inside the repo; test framework.
- Prompt wording for personality, triage, style extraction and reports.
- Exact Google OAuth configuration, within the constraints in section 6.
- Model IDs per tier (current Claude models at build time).
- Baseline formula for "good" and "bad" videos.

## 11. Designer's calls the owner should check

- "Channels" means YouTube channels only.
- Mail means Google accounts only, for now.
- Push-to-talk first; wake word later.
- Local speech recognition; built-in Mac voice first.
- Python, local data in `~/.jarvis/`.
- Every send or calendar change needs a spoken yes.
- Jarvis speaks unprompted only if the owner opts in.
- "Develops himself" means he learns rules, style and routines on his own,
  but changes to his code are proposals the owner approves; he never
  rewrites himself while running.
