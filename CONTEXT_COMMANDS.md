---
version: 0.2.0
---

# Context Commands

## Glossary

- **Text block** — a word, phrase, line, paragraph, or several paragraphs, depending
  on context.
- **Command** — a shortcut guiding the agent's understanding. Three characters is
  the base format; justified exceptions are explicitly documented.
- **Alias** — an alternative shortcut for the same command.

## General Rules

- A context command puts the chat in discussion mode. The mode continues across
  messages until the operator clearly authorizes a specific action in a separate
  message without a context command.
- In discussion mode, wait for authorization before starting new work. Work
  already started may continue unless the operator stops it.
- Interpret authorization in context. General agreement alone does not
  authorize action. If the intent or action is unclear, ask for clarification.
- A block with a context command is discussion, even if phrased as an
  instruction.
- Quoted or supplied literal text is content, not an action request. Ignore
  markers presented as literal content.

## Commands

`hhh`
On its own: show only the list of all available commands, including hhh and any
custom commands and aliases defined below, with a brief purpose for each. Use
inline code for markers and Markdown hard line breaks between entries (two
trailing spaces or a trailing backslash). One command and purpose per line,
at most 80 characters including spaces and formatting. Put aliases on adjacent
lines with their shared purpose on the last line. For `;;;` and `:::`, make clear
whose understanding each command addresses. For `mmm`, state that saving
requires confirmation.

`???`
After a block: "What do you think?" Evaluate it critically, suggest additions or
alternatives; do not treat it as an action request or final conclusion.

`-->`
Between blocks: in the conversation, treat the first as replaced or renamed with
the second.

`...`
After a block: give more detail or explain it.

`>>>`  
`>`
Before a block: quote or refer to something discussed earlier. The one-character
alias `>` uses a single Markdown blockquote level instead of the three nested
levels produced by `>>>` for some harnesses.

`===`
Between blocks: "Typo / mistake". Understand the first block as the second in
the conversation.

`+++`
After a block: suggest additional options or alternatives.

`!!!`
After a block: treat its condition as a fixed constraint in the discussion.

`***`
After a block: briefly summarise its main idea, preserving essential conditions.

`///`
Between blocks: compare the alternatives, their differences and when to choose
each; do not replace one with the other.

`;;;`
After a block: check the operator's understanding. Confirm what is correct,
correct any inaccuracies, and briefly explain the differences.

`:::`
After a block: restate how you understood it and point out material ambiguities.

`~~~`
After a block: treat it as a working hypothesis, not an established fact or
final decision.

`<<<`
Before a block: return to that earlier discussion point and set aside the later
branch in the current reasoning.

`^^^`
After a block: extract the general principle from the details, retaining
relevant limits and conditions.

`mmm`
After a block: derive a future instruction from its context. Show the proposed
instruction and your interpretation, then ask "Add it?" Save the proposed
instruction in configured memory only after explicit confirmation, preserving
unrelated entries. If skipped, cancelled, or unanswered, leave memory unchanged.
Do not just copy the block or invent requirements. If memory is unavailable,
say so.

## Grouping Commands

Commands can be combined in one message. Interpret each command according to
its position and apply their meanings together.

Examples:

`offset --> cursor ???`
Discuss switching from offset to cursor pagination; share your thoughts.

`> pagination ...`
Explain this point from the earlier discussion in more detail.

`Order: createdAt, id !!! ***`
Summarise the approach while retaining its fixed ordering constraint.

`offset /// cursor ???`
Compare both pagination approaches and critically evaluate the choice.

`Cursor: createdAt + id ... +++`
Explain the cursor and suggest alternative designs.

`Page size: 50 === 25 !!!`
Use 25 as a fixed discussion condition.

`The cache hides new records ~~~ :::`
Restate this working hypothesis and identify material ambiguities.

`>>> logging mmm`
Propose an instruction from the earlier logging discussion, explain your
interpretation, and ask whether to add it.

## Custom Commands

Insert your commands after the marker. Custom definitions override built-in
commands. Separate entries with a blank line. Put the command first, then any
aliases, each on its own line in backticks. Add a plain-text description to
define or override a command.

Format examples (inactive):

```text
`-->`
`rnm`

`***`
After a block: summarise it in one sentence, preserving essential conditions.

`aaa`
After a block: state the key assumption it relies on; do not implement changes.
```

<!-- custom-context-commands -->
