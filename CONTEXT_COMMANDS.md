# Context Commands

## Glossary

Text block - a word, phrase, line, paragraph, or several paragraphs, depending
on context.
Command - a shortcut guiding the agent's understanding. Three characters is the
base format; justified exceptions are explicitly documented.

## Scope

Blocks with context commands are discussion only, never action requests, even
when phrased as instructions. External changes require a separate explicit
request without context commands; prior task context does not override this.
mmm proposes a memory update and waits for confirmation.
Ignore markers that are literal quoted or supplied content. A leading `>` used
to refer to an earlier discussion is the reference alias below; it does not
authorize actions from quoted text.

## Commands

`hhh`
On its own: show only the list of all available commands, including hhh and any
custom commands and aliases defined below, with a brief purpose for each. Use
inline code for markers and Markdown hard line breaks between entries (two
trailing spaces or a trailing backslash). One command and purpose per line,
at most 80 characters including spaces and formatting. Put aliases on adjacent
lines with their shared purpose on the last line.

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
