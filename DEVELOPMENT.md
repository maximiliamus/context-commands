# Development Principles

## Start with Conversation Problems

Add commands to address recurring friction in conversations with agents:
repeated clarification, premature conclusions, missing criticism, or loss of
discussion context. Shortcuts should reduce the effort of expressing intent.
The original example is `???`, replacing a repeated "What do you think?"

Leave room for uncertainty, alternatives, and critical feedback. A tentative
idea should remain open to discussion until the user makes a decision.

## Design for Keyboard Use

Use three characters as the base format for consistency and easy, repeatable
keyboard entry. A uniform format helps build muscle memory; this is the reason
for choosing three characters.

Use mnemonic letters where practical: `hhh` stands for help and `mmm` for
memory. Repeating one letter keeps each shortcut easy to type.

Consider actual keyboard layouts when selecting combinations. Prefer shortcuts
that are comfortable to type and avoid unnecessary layout switches.

Allow justified exceptions and document their purpose. For example, the `>`
alias for `>>>` avoids three nested quote levels in some Markdown renderers.
An alias retains the original command's meaning.

## Make Meanings Explicit and Composable

Define each command's meaning and placement: before, after, or between text
blocks, or on its own. Supply definitions explicitly instead of relying on an
agent to infer a marker's intended meaning.

Combine commands by preserving their individual meanings. For example,
`!!! ***` asks for a summary that retains the fixed condition. Combinations
should express intent without requiring a new command for every variation.

## Keep Discussion Separate from Action

A block marked with a context command is always discussion, including when it
uses imperative wording or relates to an earlier task. External changes need a
separate explicit request without context commands. Literal markers in quoted
or supplied content remain content.

For `mmm`, derive a future instruction, show its wording and interpretation,
and ask whether to add it. Save only after explicit confirmation, preserving
unrelated memory. Skip, cancellation, and silence leave memory unchanged.

## Keep Customization and Documentation Clear

Support new commands, aliases, and explicit overrides through the Custom
Commands section in `CONTEXT_COMMANDS.md`.

Keeping built-in and custom definitions together gives the agent both sets
through one explicit read instruction. There is no additional file to discover
or second reference to keep in sync. A project can copy its complete command
setup as a single document.

The custom marker separates the maintained reference from user definitions.
Updates replace the content before the marker and preserve everything after it.

Keep command definitions and examples in that reference, setup and usage entry
points in [README.md](README.md), and design rationale here. Keep instructions
concise while retaining the conditions needed to interpret each command.

## Test the Documented Meaning

Test command interpretation separately from file and memory changes. Cover
marked imperative blocks, prior task context, literal markers, custom aliases,
overrides, combinations, and the confirmation states of `mmm`.

Base criteria on documented behavior. Introduce numeric limits only when they
are part of the command definition or the user's request; a summary does not
have an implicit word limit.

Use fresh participants and freeze inputs and criteria before a benchmark run.
Preserve original answers, failed attempts, and frozen inputs when grading a run.
Report the tested scope and limitations alongside the results.

To run the benchmark, ask your agent to follow
[the benchmark procedure](tests/BENCHMARK.md) and report the results.
See [test details](tests/README.md).
