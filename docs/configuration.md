# Configuration and commands

## Configuration

Two files, both plain text.

**`.env`** — credentials. Every variable documented inline with where to get it. The only required one is a mail provider; everything else is optional.

**`huntly.yaml`** — who Huntly is and who it sells to:

```yaml
persona:      { name, company, role, email, tone }
product:      { name, description, pricing, key_benefits, objection_responses, offer }
icp:          { industries, titles, company_size, geography, hiring_signals, geo_coordinates }
channels:
  email:      { provider: gmail | microsoft | smtp | instantly, max_daily_sends, per_inbox_daily_cap,
                require_approval, send_to_risky, min_write_score, max_bounce_rate, warmup, send_window, signature }
usage:        { max_daily_claude_percent, heartbeat_interval_minutes, quiet_hours }
brain:        { provider: claude | codex, model, reasoning_effort }   # optional; claude by default
writer:       { humanizer }   # optional; true adds one editing pass per batch using ~/.claude/skills/humanizer/SKILL.md
              # email_rules: your own markdown rules for the emails' shape (see The skills library)
```

`min_write_score` (0-100, default 0) is the lowest Scout fit score the writer
drafts for: a prospect below it keeps its deliverable address but gets no
sequence, so Claude calls and sends go to the best matches first.

`max_daily_claude_percent` caps whichever subscription `brain.provider` uses (the name predates Codex support).

If `huntly.local.yaml` exists it wins. It's gitignored, so a fork can carry real product configuration while the tracked `huntly.yaml` stays a template — nobody publishes their positioning and pricing by accident.

### Commands

```bash
huntly run                   # the heartbeat loop
huntly dashboard             # web UI at 127.0.0.1:5555 (--url: print the unlock link)
huntly signals               # review/confirm what to prospect against
huntly discover              # find businesses; --providers / --estimate
huntly profile               # read discovered companies' sites (free)
huntly train <url>           # learn a product from its website (--provider codex --model gpt-5.5)
huntly status                # pipeline summary
huntly usage                 # active provider's quota + per-agent tokens
huntly outbox                # review queued email
huntly export                # deliverable prospects → CSV
huntly precleared-key        # free key for the cold-email check, saved to .env
huntly companies             # company register → CSV: every company, fit, and why it wasn't contacted
huntly sending pause|resume  # kill switch
huntly suppressions [add|remove <value>]  # addresses and domains never emailed
huntly inboxes list|connect|test|pause|resume|cap|name|remove|use  # several sending inboxes
huntly mcp install [claude|codex]  # let your coding agent read Huntly and pause sending
huntly warmup [domain]       # is the sending domain ready? (SPF/DKIM/DMARC, age, blocklists, warmup)
huntly trulyinbox connect    # connect TrulyInbox so Huntly reads the mailbox's warmup
huntly retry-writes          # retry prospects the Writer gave up on
huntly gmail auth            # one-time Gmail OAuth
huntly microsoft auth|test  # one-time Microsoft 365 sign-in (docs/microsoft365.md)
```

Prospect CSV exports exclude opted-out contacts, including when using
`--status` or `--email-status` filters. `huntly export --all` is an unfiltered
raw-data export for inspection: it includes opted-out and unverified contacts
and should not be imported as an outreach list. The dashboard's prospect CSV
download follows the same policy; `?all=true` selects its raw export.

## Several sending inboxes

The main mailbox is the one `channels.email.provider` sets up. You can send
from more inboxes you already own, besides it:

```bash
huntly inboxes connect gmail --address two@yourdomain.co      # browser sign-in
huntly inboxes connect microsoft --address three@yourdomain.co
huntly inboxes connect smtp --address four@yourdomain.co --smtp-host smtp.example.com
huntly inboxes list                                           # each inbox and today's cold sends
```

- **Where sign-ins live.** In your system keychain (service `huntly`), never
  in the database or a file. A Gmail or Microsoft inbox keeps only its refresh
  token; an SMTP inbox's password is asked for at the prompt, never on the
  command line. Signing in as a different account than `--address` connects
  nothing. Docker and other headless machines have no keychain, so extra
  inboxes can't be connected there yet.
- **Which inbox sends what.** A prospect's first email goes from the inbox
  with the most room left today. Once anything in a thread has gone out, its
  follow-ups and Huntly's replies leave from that same inbox. A reply is
  answered from the inbox it arrived in.
- **Caps.** Each inbox, the main one included, sends up to
  `per_inbox_daily_cap` cold emails a day (default 30), or the number you set
  with `huntly inboxes cap <address> <n>`. An inbox connected with
  `--warmup-started YYYY-MM-DD` ramps up from that day like
  `channels.email.warmup` describes; the main mailbox ramps from
  `warmup.start_date`. `max_daily_sends` stays the ceiling on everything sent
  in a day, so raise it when you add inboxes.
- **Pausing and removing.** `huntly inboxes pause <address>` stops one inbox.
  Its unsent first emails move to the others, and threads it started wait for
  it. `remove` stops using it for good: threads it started end. Its sign-in
  stays in your keychain until you delete it there.
- **Choosing inboxes per campaign.** `huntly inboxes use <campaign>
  <address>...` limits a campaign's new threads to those inboxes (`main` is
  the main mailbox); with no addresses it uses every inbox again.
- Replies are read from every inbox each cycle. If one can't be read,
  nothing is sent that cycle, as with one inbox, and the Today page says
  which inbox.
- An extension can add another way to connect an inbox with
  `registry.add_mailbox_connection` ([docs/extensions.md](extensions.md)).

## Your coding agent (MCP)

`huntly mcp install` adds Huntly to Claude Code (`huntly mcp install codex`
for Codex). It shows the exact change to your agent's config first and applies it
only on a yes, touches only its own entry, and refuses if a Huntly entry it
didn't write is already there. `--print` shows the entry to add by hand to any
other MCP client; `huntly mcp uninstall` takes it out again.

Your agent then talks to the running dashboard (`huntly dashboard`) with its
own token, `data/agent-token`, never yours. With it the agent can read
everything Huntly knows (Today, campaigns, prospects, companies,
conversations, the Outbox, signals, usage, setup), estimate what a discovery
run would cost, and pause sending. It can't approve or send email, resume
sending, confirm signals, start discovery, change settings or keys, or delete
anything: the dashboard answers 403 to the agent's token for every route that
isn't on its short allowlist (`huntly/agent_policy.py`).

