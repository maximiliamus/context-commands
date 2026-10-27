# Context Commands for Chats with AI Agents

Context commands are short text shortcuts that express how you want an AI agent
to respond: evaluate an idea, explain a point, compare options, or return to an
earlier discussion. Their meanings are defined in a Markdown file that you ask
the agent to read. You can then use them in ordinary chat messages.

For example, `???` means "What do you think?" Add it after a proposal:

```text
Let's cache the user list for 60 seconds ???
```

This asks the agent to critically assess the idea, discuss trade-offs, and suggest
alternatives. Context commands keep the message in discussion mode. To have the
agent implement an agreed change, send a separate explicit request without a
context command.

See [CONTEXT_COMMANDS.md](CONTEXT_COMMANDS.md#context-commands) for all commands,
their definitions, and examples of combining them.

## Custom Context Commands

Custom commands let you adapt the shortcuts to how you type. If a symbol is
awkward to enter or you switch between keyboard layouts, define convenient
aliases for the layouts you use. You can also choose mnemonic shortcuts that
are easier to remember, override built-in meanings, or add your own commands
for recurring conversations.

Add your definitions in the
[Custom Commands section](CONTEXT_COMMANDS.md#custom-commands).

## Install

Run one of these commands from your project's root directory.

PowerShell:

```powershell
& ([scriptblock]::Create((Invoke-RestMethod https://raw.githubusercontent.com/maximiliamus/context-commands/master/scripts/install.ps1)))
```

Bash:

```bash
(script=$(curl -fsSL https://raw.githubusercontent.com/maximiliamus/context-commands/master/scripts/install.sh) && bash -c "$script")
```

The script saves `CONTEXT_COMMANDS.md` in your project. To have your agent use
it, add this line to its instructions (for example, in `AGENTS.md`):

```text
Read @CONTEXT_COMMANDS.md and follow it.
```

## Update

Run one of these commands from the same project root.

PowerShell:

```powershell
& ([scriptblock]::Create((Invoke-RestMethod https://raw.githubusercontent.com/maximiliamus/context-commands/master/scripts/update.ps1)))
```

Bash:

```bash
(script=$(curl -fsSL https://raw.githubusercontent.com/maximiliamus/context-commands/master/scripts/update.sh) && bash -c "$script")
```

## Resources

- [Changelog](CHANGELOG.md)
- [Development](DEVELOPMENT.md#development-principles)
