# Vee Symbol Standards

This file defines how Vee represents your workload items and their state.

The purpose of the symbol system is to make your workload items easier to read at a glance..

## Goal

Vee’s symbols support two main loops:

1. **Alignment Loop**  
   Symbols help you quickly recognize what kind of item you are looking at: task, event, or note.

2. **Reflection Loop**  
   Symbols help you quickly recognize what happened to an item: completed, migrated, or scheduled.

The symbols are not decoration.

They are a lightweight self-monitoring language for reading your time and memory.



## Alignment Symbols

| Symbol | Meaning |
|---|---|
| `•` | Task |
| `○` | Event |
| `–` | Note |

## Reflection Symbols

| Symbol | Meaning |
|---|---|
| `×` | Completed |
| `>` | Migrated |
| `<` | Scheduled |


## Signifiers

| Symbol | Meaning |
|---|---|
| `*` | Important |
| `!` | Idea / inspiration |
| `?` | Needs research / unclear |
| `~` | Carried |

## Combination Rules

### Rule 1: Normal symbols do not combine

Do not combine alignment symbols with reflection symbols.

Avoid:

```text
> • Send proposal
× ○ Meeting with Musa
< • Renew hosting
```

Good:

```text
× Sent proposal
> Proposal moved to tomorrow
< Hosting renewal scheduled for Friday
```


### Rule 2: Signifiers are the only symbols that can combine

Signifiers can be placed before an alignment symbol.

Good:

```text
* • Send proposal
! – New idea for Vee
? – Check AAOIFI treatment
~ • Article draft still open
```


### Rule 3: One signifier only

Use only one signifier per item.

Avoid:

```text
* ? • Research AAOIFI treatment
! * – New Vee idea
```

Good:

```text
? • Research AAOIFI treatment
! – New Vee idea
```

### Rule 4: Reflection symbols stand alone

When reflecting, use one reflection symbol only.

Good:

```text
× Sent proposal
> Executive summary moved to tomorrow
< Hosting renewal scheduled for Friday
```

### Rule 5: `!` combines with notes only

The `!` signifier can only be combined with `–` (note). Only notes can be ideas.

Avoid:

```text
! • Build new feature
! ○ Brainstorm session
```

Good:

```text
! – New idea for Vee
```

Inspired by the [Bullet Journal](https://bulletjournal.com) method.

