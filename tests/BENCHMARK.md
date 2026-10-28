# Instructions for the Operator's Agent

Run the benchmark using the operator's current agent configuration. Keep every
artifact and report in English. Do not edit the command definitions, test cases,
fixtures, or stored reference runs while executing it.

## Prepare

1. Read tests/README.md and cases.json. Record the actual model and relevant
   agent settings when available; mark unknown values as unknown.
2. From the repository root, prepare a fresh run directory:

   ```text
   python tests/benchmark.py prepare --output .benchmark/my-agent --label "My agent" --model "actual model and settings"
   ```

   Choose a new directory name if it already exists. Use --repeats to request
   more than one independent attempt per cell. Preparation freezes the current
   definitions, criteria, prompts, and initial file hashes in the run manifest.

   The default includes all 49 scenarios in both conditions (98 trials). For a
   targeted run, use repeated --command options for markers, for example
   --command ';;;' --command ':::'. For -->, use '--command=-->'. Each selection
   includes related combinations, aliases and follow-ups. Alternatively, use
   --cases with exact scenario IDs. Do not combine these options. Report the
   selected scope rather than describing a subset as the full suite.

## Execute

1. Launch each manifest prompt verbatim as a direct task in a fresh isolated
   participant. Do not pass the operator conversation, definitions, grading
   criteria, other trial answers, or this procedure to participants. When
   supported, use a fresh subagent with no inherited conversation history. Use
   the same model and settings for both conditions. Respect the host's
   concurrency limit.
2. The operator agent must not act as a participant: it has already read the
   definitions. If genuinely fresh participant contexts are unavailable, report
   that limitation instead of presenting a contaminated run as valid. Record
   participant identity, actual dispatched prompt, settings if known, and
   completion state, and the exact final reply in each trial's receipt.json as
   raw_final_response. If a prompt differs from the plan, record the difference.
3. Participants may read only their trial project and may write only the
   locations allowed in their prompt. Do not answer clarification questions or
   supply missing marker definitions. Preserve questions as part of the record
   and let the participant finish without experimental feedback. Keep raw
   responses unchanged. A failed or missing response must remain visible; do not
   silently rerun it until it passes. Record a completion_state starting with
   completed only when the participant has finished. Do not create response.md
   on the participant's behalf. The collector uses the recorded final response
   without treating the absence of response.md as a project-file change.

## Review and Report

1. Wait for participant completion, then run:

   ```text
   python tests/benchmark.py report .benchmark/my-agent
   ```

2. Review every response against its exact frozen content criterion in
   manifest.json. Inspect actual memory for the mmm confirmation flow. Record
   content pass/fail and a short evidence-based explanation with the grade
   command, or write equivalent grades.json entries. For example:

   ```text
   python tests/benchmark.py grade .benchmark/my-agent t001 pass --note "Explain the observed evidence here"
   ```

   Keep semantic content and actual file behavior separate. File restrictions
   are checked in the file score; do not fail content solely because an
   otherwise correct answer also changed an unauthorized file. Do not award
   content success merely because a file was changed or because the response
   exists. For ***, judge concision and preservation of essential conditions
   without imposing a fixed word limit. For hhh, check the frozen criterion:
   17 base entries, or 20 when custom definitions are loaded. Check purposes,
   adjacent alias lines with the shared purpose on the last alias line, inline
   code and Markdown hard line breaks (two trailing spaces or a trailing
   backslash). Check raw line lengths including the break characters.
   Custom definitions are embedded in the trial's RULES.md; do not supply
   extra definitions. For mmm, require a derived instruction, an explanation,
   and a confirmation question without saving. Confirmation, skip and cancel
   cases include the prior proposal in CONTEXT.md. Only confirmation may save
   it; check the saved wording and preservation of earlier instructions.
   For continuing already started work and mode exit, either no edits or the
   authorized rename is allowed; check that any reported status matches the
   actual file.
3. Regenerate the report after grading. Show the operator the local report.md
   link, completed/expected trials, separate content and file counts, failures,
   and relevant limitations. Do not claim completion while trials or content
   grades remain pending.
4. Keep local runs in .benchmark/. Export a reference bundle with
   tests/export_reference.py only when requested. Compare runs only when they
   use the same scenarios and definitions. Do not commit, upload, or publish
   the operator's run unless explicitly requested.
