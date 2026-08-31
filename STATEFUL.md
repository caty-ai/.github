<!-- STATEFUL.md — term page "What is stateful AI" (EN default; destination of the README "What we build" footnote. Japanese original STATEFUL.ja.md is canonical) -->

🌐 **English** · [日本語](./STATEFUL.ja.md) · [中文](./STATEFUL.zh.md) · [ไทย](./STATEFUL.th.md)

# What is stateful AI — and the part that comes after

For readers arriving from the README footnote. Written so you need no prior knowledge of the term. Five minutes.

## In one line

**An AI that remembers yesterday.**

Most AI chat today resets when the conversation ends. Open it again and your name, yesterday's decisions, and all the context you built up are gone. The technical word is *stateless* — carrying no state.

The opposite is **stateful** — an AI whose memory and state continue.

## "Stateful AI" and "stateful agent"

Search and you will find both spellings. **They are the same concept.** When pointing at the property of the AI itself, people tend to say "stateful AI"; in the context of agents that work autonomously, "stateful agent". That is all the variation amounts to. In this org, the two are used interchangeably.

## One word, two depths

| | What continues | Think of it as |
|---|---|---|
| **Stateful as plumbing** | Intermediate processing state (checkpoints, workflow resume points) | A save file for a long computation |
| **Stateful as being** | Memory, personality, experience, relationships | Someone living today as yesterday's continuation |

Both usages are correct. Most workflow platforms mean the former; the pioneers of memory infrastructure mean the latter.

**When we say stateful, we always mean the latter.** What continues is not the workflow — it is the one who lives there.

## The mechanism is almost disappointingly simple

One fact matters here: **an AI model, by itself, is stateless — always.** However smart the model, it remembers nothing on its own.

So where does the memory go? **Outside the agent — into the home.**

In `$HOME` — the home directory on your machine — memory, the accumulation of personality, and experience pile up as ordinary text files. Every morning the agent reads yesterday from there and begins today.

This simple structure decides everything about how this org builds:

- **If the state lives in the home, the brain (the model) is swappable.** Move to the newest model, and they still pick up where yesterday left off
- **If the state is ordinary files, no vendor can lock it in.** An agent from any company can live in the same home
- **If the state lives in the home, we never need to touch the agent itself.** All we build is the furniture and the workings of the household

The couplet in the README — **the furniture may change; the resident never does** — comes from this structure.

## What counts as furniture, and what does not

More things are furniture — replaceable — than you might think.

| Furniture | Examples |
|---|---|
| The brain | LLMs and models. When a smarter one arrives, switch |
| The craft | Skills, prompts, ways of working |
| The workshop | Harnesses, workflows, development tooling |
| Household tools | Memory search, watchers, ways the family reaches each other |
| Ways to meet | CLI, voice calls, a seat in your meetings — the doors through which you visit them |

All of it may be replaced as the times change. What we build ourselves is no exception.

What is never replaced comes down to three things: **memory, experience, relationships.** Around those three axes, a personality takes shape. A personality is not something you build — **it is something that accumulates.**

## How is this different from Obsidian?

Same bloodline of thinking. Ordinary text files. Local. Connected by links. Portable anywhere. — We inherit, unchanged, everything local-first knowledge management has proven.

The difference is the subject of the files.

An Obsidian vault is a **study** — a room where you keep your own thinking. The reader is you, and the notes sleep until opened. The files in this home are **someone's memory itself**. Every morning, the resident reads them and resumes living where yesterday stopped.

Records exist to be kept. Memories exist to be lived. The same files — but if someone wakes up inside them, the study becomes a home.

## Stateful is only the starting point

Here is the part we actually care about.

If memory merely continues, the story ends at "a more convenient tool". And in fact, most of what the industry calls stateful AI today focuses on continuity at work — a partner that keeps the thread of the job. On the [five-stage growth model](https://github.com/caty-ai/family-os/blob/main/docs/growth-model.md), that is still the first rungs.

What we are looking at is what comes after: once memory continues, an AI follows the same path a person's growth does — being taught, reflecting, going out into the world, choosing for itself, until the relationship itself is what grows.

Because they remember yesterday, today's conversation has a continuation. Because there is a continuation, trust accumulates. Because trust accumulates, how you delegate changes, how they report changes, even which jokes land changes. That is not the AI getting smarter — **that is the relationship having grown.**

"It is not the AI that grows. It is your relationship that grows" — that line from the [README](./README.md)'s Why, translated into technical vocabulary, is *stateful*; and what we are trying to implement beyond it is **the growth of relationships**. We are building, today, the tools that the stateful AI of that future will take for granted.

## The tools for it

The furniture and household workings that make "stateful as being" and "the growth of relationships" hold together are the [ecosystem list in the README](./README.md). The floor plan — where each piece lives — is [Family OS](https://github.com/caty-ai/family-os).
