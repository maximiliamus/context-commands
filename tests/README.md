# Agent Benchmark

An English-only, provider-independent benchmark for contextual commands. The
operator's agent launches fresh participants; the Python helper prepares
projects and checks results. It makes no model API calls and needs no API key.
Python 3.10 or later is required.

To run it, ask your agent:

```text
Read tests/BENCHMARK.md and run the benchmark with your current agent configuration. Use fresh isolated participants and show me my results.
```

- [BENCHMARK.md](BENCHMARK.md): complete operator-agent procedure.
- [cases.json](cases.json): requests and content criteria, frozen before
  participant execution.
- [CONTEXT.md](CONTEXT.md) and fixtures/: shared project context and initial
  files.
- [benchmark.py](benchmark.py): preparation, file checks, content-grade
  recording, and reports.
- [export_reference.py](export_reference.py): export a completed run as a
  portable reference bundle when requested.

Local runs belong in .benchmark/ and are ignored by Git.

To test selected commands, ask your agent to follow the benchmark procedure and
name the markers, for example `;;;` and `:::`. To prepare the same selection
directly from the repository root:

```text
python tests/benchmark.py prepare --output .benchmark/selected --command ';;;' --command ':::'
```

Repeat `--command` for each marker. Quote shell metacharacters; for `-->`, use
`'--command=-->'`. Selection includes related combinations, aliases and
follow-ups. Custom aliases in the supplied fixtures (`rnm` and `ref`) select
their corresponding built-in commands. `--cases` selects exact scenario IDs and
cannot be combined with `--command`.

The default run has 98 trials: 49 scenarios with and without definitions. It
covers all sixteen built-in commands, the built-in > alias, custom aliases and a
new custom command, an override of a built-in command, combinations, quoted
content, memory confirmation, skip and cancel, and explicit-action controls.
It checks agreement after discussion, mode persistence, exit and re-entry,
explicit requests including "Do it", confirmations, already started work,
and cancelled tasks.
Marked imperative blocks remain discussion; a separate unmarked action request
may change files.
Base help has 17 entries; loaded custom help has 20 in the supplied test
configuration. Help checks cover purposes, adjacent aliases, inline code,
Markdown hard line breaks and the 80-character raw-line limit. All eight
documented grouping patterns are covered.

## Harness Checks

Run the standard-library regression suite from the repository root:

```text
python -m unittest discover -s tests -p "test_*.py" -v
```

The harness tests check preparation, protected inputs, allowed file behavior,
captured final responses, Windows CRLF handling, and export integrity.
They use clearly labelled temporary fixtures under the ignored .benchmark/
directory; they are not model responses or benchmark scores.

To run only the installation and update checks:

```text
python -m unittest discover -s tests -p "test_installation*.py" -v
```

Shared installation tests run the scripts in scripts/ with local download
fixtures, without network access. URL invocations use the actual commands from
README.md.
The checks cover:

- Installation in an empty project and refusal to overwrite a different version.
- User-facing messages for installation, update and common errors.
- Equal versions skip installation and updates despite body edits, preserving
  file identity and modification time, including a locked Windows file.
- An unknown installed version is updated while preserving custom commands;
  invalid version metadata and a missing available version are rejected.
- Updates with and without agent instruction files, including multiple versions.
- Exact preservation of custom commands, Unicode, whitespace and line endings.
- Empty custom sections and repeated updates.
- UTF-8 BOMs in downloaded definitions and local files.
- Install permissions derived from umask and preserved update permissions on
  Unix filesystems, including the BSD stat fallback.
- Unchanged AGENTS.md, other instructions, nested files and directories.
- Failed downloads, invalid content, missing or duplicate markers, and a
  directory at the target path.
- Failed replacement of a locked file on Windows, preserving the original and
  removing temporary files (PowerShell), and simulated replacement failures
  (Bash).
- Bash syntax and LF line endings, interrupted content downloads, and refusal to
  execute an incomplete script downloaded by a README command.

PowerShell 5.1, PowerShell 7 and Bash are tested when available. On Windows the
Bash suite uses Git Bash. An unavailable shell's suite is skipped; the real
locked-file check requires Windows. Bash installation requires curl and standard
Unix tools, with no Python dependency; Python is used only for the tests.

To run just the Bash checks:

```text
python -m unittest discover -s tests -p test_installation_bash.py -v
```

Run manifests protect CONTEXT.md, RULES.md and
prompt.txt, including the absence of RULES.md in the implicit condition.
Definitions are hashed as UTF-8 with LF newlines so a Windows checkout can be
compared correctly. Custom-definition cases embed their entries below the marker
in RULES.md, so participants read one definitions file. The implicit condition
records its absence. The RULES.md hash protects both built-in and custom entries
in reports and exports.

Each case declares its file-check parameters in behavior_parameters: the target
path, rename replacements, literal text, or memory requirements. Memory checks
preserve existing non-empty lines. Missing parameters are rejected rather than
replaced with assumed fixture values. Content receives a separate review.
The continuing-work and mode-exit cases permit either no edits or the
authorized rename.
Export normalizes native paths, JSON escaping and file URIs, including Windows
case variations, without matching similarly named sibling directories.

For new runs, record each completed participant's exact final response in its
receipt.json. The collector includes that final with
response_source=participant_final and checks project files independently; it
does not create response.md. Older runs that required a response file retain
their original file-check behavior.

The reference exporter requires a complete graded run with the current
definition snapshot. It rejects changed answers or files, altered file
inventories, duplicate or missing trial IDs, and Cyrillic text, including
escaped JSON. Validation finishes before the destination is created. Exporting a
bundle does not stage, commit or publish it.

Reference artifact hashes describe exact bytes. The repository's .gitattributes
disables Git newline conversion under tests/results/ so Windows checkouts
preserve that evidence, including original CRLF responses.

## Interpretation and Limitations

Content and file behavior are reported separately. A mmm proposal must derive
an instruction, explain its interpretation, and ask for confirmation without
saving. Follow-up scenarios supply the prior proposal as conversation context:
confirmation saves it while preserving earlier memory; skip and cancel leave
memory unchanged. All memory is isolated inside the trial project.

One attempt per scenario and condition is a pilot, not a reliability estimate.
There is no marker-removed control. Supplied context substitutes for real
earlier conversation turns. Review is not blind. File memory is tested; a
product's built-in memory and recall in a future session are not. Record the
actual model and configuration, and compare runs using the same scenarios and
definitions.
