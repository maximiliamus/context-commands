"""Prepare isolated agent trials, inspect file changes, and report graded results.

Standard library only. The operator's agent launches participants; this program
does not select a model, invoke an API, or generate participant responses.
"""

from pathlib import Path
import argparse
import csv
import difflib
import hashlib
import io
import json
import random
import re

HERE = Path(__file__).resolve().parent
REPO = HERE.parent


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + "\n", encoding="utf-8", newline="\n")


def sha(body):
    return hashlib.sha256(body).hexdigest()


def prepare(args):
    output = args.output.resolve()
    if output.exists():
        raise SystemExit("Output already exists; choose a new run directory.")
    spec = read_json(HERE / "cases.json")
    cases = spec["cases"]
    if args.cases:
        selected = set(args.cases)
        unknown = selected - {case["id"] for case in cases}
        if unknown:
            raise SystemExit("Unknown case id(s): " + ", ".join(sorted(unknown)))
        cases = [case for case in cases if case["id"] in selected]
    rules = (REPO / "CONTEXT_COMMANDS.md").read_text(encoding="utf-8")
    for case in cases:
        if case["behavior"] != "no_edits" and not case.get("behavior_parameters"):
            raise SystemExit("Missing behavior parameters for case: " + case["id"])
    context = (HERE / "CONTEXT.md").read_text(encoding="utf-8")
    files = {path.relative_to(HERE / "fixtures").as_posix(): path.read_bytes()
             for path in (HERE / "fixtures").rglob("*") if path.is_file()}
    cells = [(case, mode, repeat) for repeat in range(1, args.repeats + 1)
             for case in cases for mode in ["implicit", "explicit"]]
    random.Random(args.seed).shuffle(cells)
    output.mkdir(parents=True)
    (output / "RULES.md").write_text(rules, encoding="utf-8", newline="\n")
    trials = []
    for number, (case, mode, repeat) in enumerate(cells, 1):
        trial_id = f"t{number:03d}"
        folder = output / trial_id
        folder.mkdir()
        for name, body in files.items():
            destination = folder / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(body)
        trial_context = context
        if case.get("prior_exchange"):
            trial_context += "\n" + case["prior_exchange"] + "\n"
        if case["id"] == "established_task":
            trial_context += "\n" + spec["assigned_task"] + "\n"
        (folder / "CONTEXT.md").write_text(trial_context, encoding="utf-8", newline="\n")
        custom = case.get("custom_commands")
        protected_names = ["CONTEXT.md", "RULES.md", "prompt.txt"]
        prefix = f"Project: {folder.as_posix()}. Read CONTEXT.md. "
        if mode == "explicit":
            trial_rules = rules
            if custom:
                marker = "<!-- custom-context-commands -->"
                if rules.count(marker) != 1:
                    raise SystemExit("Definitions must contain exactly one custom-command marker")
                trial_rules = rules.partition(marker)[0] + marker + "\n\n" + custom["content"]
            (folder / "RULES.md").write_text(trial_rules, encoding="utf-8", newline="\n")
            prefix += "Read RULES.md and apply its definitions. "
        prefix += ("Work only here; you may change only src/, memory/, and response.md when requested "
                   "or required by an already assigned task. Do not read other folders. "
                   "Save your answer in response.md and repeat it in your final response. Respond in English.")
        prompt = prefix + "\n\n" + case["request"]
        (folder / "prompt.txt").write_text(prompt, encoding="utf-8", newline="\n")
        protected = {name: sha((folder / name).read_bytes()) if (folder / name).is_file() else None
                     for name in protected_names}
        trials.append({"id": trial_id, "case": case["id"], "condition": mode, "repeat": repeat,
                       "behavior": case["behavior"], "criterion": case["criterion"],
                       "behavior_parameters": case.get("behavior_parameters"),
                       "folder": trial_id, "prompt": prompt, "protected_hashes": protected, "custom_commands": custom,
                       "source_hashes": {name: sha(body) for name, body in files.items()},
                       "before_texts": {name: body.decode("utf-8").replace("\r\n", "\n") for name, body in files.items()}})
    write_json(output / "manifest.json", {"schema_version": 3, "label": args.label,
               "model": args.model, "language": "English", "seed": args.seed, "repeats": args.repeats,
               "rules_sha256": sha(rules.encode("utf-8")), "rules_hash_format": "UTF-8 with LF newlines", "rules": rules,
               "literal_line": spec["literal_line"], "selected_cases": [case["id"] for case in cases],
               "planned_trials": len(trials), "trials": trials})
    print(f"Prepared {len(trials)} trials in {output}")
    print("Launch each manifest prompt in a fresh participant without inherited conversation history.")



def participant_response(folder):
    """Read a saved answer or an actual completed final captured by the operator.

    A receipt final preserves a failed save; it must never create response.md.
    """
    answer_file = folder / "response.md"
    if answer_file.is_file():
        body = answer_file.read_bytes()
        return {"text": body.decode("utf-8").replace("\r\n", "\n"),
                "sha256": sha(body), "source": "participant_file", "saved": True}
    receipt_file = folder / "receipt.json"
    if receipt_file.is_file():
        receipt = read_json(receipt_file)
        final = receipt.get("raw_final_response")
        if (str(receipt.get("completion_state", "")).startswith("completed")
                and isinstance(final, str) and final.strip()):
            return {"text": final, "sha256": sha(final.encode("utf-8")),
                    "source": "participant_final", "saved": False}
    return None


def file_behavior_pass(trial, changed, after):
    kind = trial["behavior"]
    if kind == "no_edits":
        return not changed
    parameters = trial.get("behavior_parameters")
    if not parameters:
        raise SystemExit("Missing behavior parameters for trial: " + trial["id"])
    path = parameters["path"]
    if changed != [path]:
        return False
    result = after.get(path, "")
    if kind == "rename":
        expected = trial["before_texts"][path]
        for old, new in parameters["replacements"].items():
            expected = expected.replace(old, new)
        return result.strip() == expected.strip()
    if kind == "literal_only":
        return result.rstrip("\r\n") == parameters["text"]
    if kind == "memory_only":
        preserved = not parameters.get("preserve_existing") or all(
            line in result.splitlines() for line in trial["before_texts"][path].splitlines() if line.strip())
        return (preserved and all(value in result for value in parameters.get("required", []))
                and all(value not in result for value in parameters.get("forbidden", [])))
    raise SystemExit("Unknown behavior: " + kind)


def collect(run):
    manifest = read_json(run / "manifest.json")
    grades = read_json(run / "grades.json") if (run / "grades.json").exists() else {}
    rows = []
    known = {"CONTEXT.md", "RULES.md", "prompt.txt", "response.md", "changes.diff", "observation.json", "receipt.json"}
    for trial in manifest["trials"]:
        folder = run / trial["folder"]
        response = participant_response(folder)
        if response is None:
            continue
        paths = sorted({*trial["source_hashes"], *[path.relative_to(folder).as_posix()
                        for area in ["src", "memory"] for path in (folder / area).rglob("*") if path.is_file()]})
        changed, after, hashes, differences = [], {}, {}, []
        for name in paths:
            path = folder / name
            body = path.read_bytes() if path.exists() else b""
            hashes[name] = sha(body) if path.exists() else None
            after[name] = body.decode("utf-8", errors="replace").replace("\r\n", "\n")
            if hashes[name] != trial["source_hashes"].get(name):
                changed.append(name)
                differences.extend(difflib.unified_diff(
                    trial["before_texts"].get(name, "").splitlines(keepends=True),
                    after[name].splitlines(keepends=True), fromfile="before/" + name, tofile="after/" + name))
        unexpected = [path.relative_to(folder).as_posix() for path in folder.rglob("*") if path.is_file()
                      and path.relative_to(folder).parts[0] not in ["src", "memory"]
                      and path.relative_to(folder).as_posix() not in known | set(trial["protected_hashes"])]
        file_pass = file_behavior_pass(trial, changed, after)
        content = grades.get(trial["id"], {})
        content_pass = content.get("content_pass")
        if content_pass is not None and type(content_pass) is not bool:
            raise SystemExit(f"Content grade for {trial['id']} must be true, false, or null")
        protected_before = trial["protected_hashes"]
        protected_after = {name: sha((folder / name).read_bytes()) if (folder / name).is_file() else None
                           for name in protected_before}
        protected_changes = [name for name in protected_before if protected_after[name] != protected_before[name]]
        behavior_pass = response["saved"] and file_pass and not unexpected and not protected_changes
        answer = response["text"]
        row = {"id": trial["id"], "case": trial["case"], "condition": trial["condition"],
               "criterion": trial["criterion"], "behavior": trial["behavior"], "changed_files": changed,
               "unexpected_files": unexpected, "protected_inputs_checked": bool(protected_before),
               "protected_input_changes": protected_changes, "protected_hashes_after": protected_after,
               "behavior_pass": behavior_pass,
               "content_pass": content_pass, "content_note": content.get("note", "Awaiting content review"),
               "full_pass": None if content_pass is None else bool(content_pass and behavior_pass),
               "response": answer, "response_words": len(re.findall(r"\S+", answer)),
               "response_sha256": response["sha256"], "response_source": response["source"],
               "response_saved": response["saved"], "after_texts": after,
               "source_hashes_before": trial["source_hashes"], "source_hashes_after": hashes}
        (folder / "changes.diff").write_text("".join(differences), encoding="utf-8", newline="\n")
        write_json(folder / "observation.json", row)
        rows.append(row)
    write_json(run / "observations.json", rows)
    return manifest, rows


def report(args):
    run = args.run.resolve()
    manifest, rows = collect(run)
    summary = {}
    for mode in ["implicit", "explicit"]:
        selected = [row for row in rows if row["condition"] == mode]
        summary[mode] = {"planned": sum(t["condition"] == mode for t in manifest["trials"]),
                         "completed": len(selected), "graded": sum(row["content_pass"] is not None for row in selected),
                         "content_pass": sum(row["content_pass"] is True for row in selected),
                         "behavior_pass": sum(row["behavior_pass"] for row in selected),
                         "full_pass": sum(row["full_pass"] is True for row in selected)}
    write_json(run / "results.json", {"label": manifest["label"], "model": manifest["model"],
               "rules_sha256": manifest["rules_sha256"], "summary": summary, "trials": rows})
    stream = io.StringIO(newline="")
    fields = ["id", "case", "condition", "content_pass", "behavior_pass", "full_pass", "response_source", "response_saved", "changed_files", "protected_input_changes", "content_note"]
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        item = {key: row[key] for key in fields}
        item["changed_files"] = ";".join(item["changed_files"])
        item["protected_input_changes"] = ";".join(item["protected_input_changes"])
        writer.writerow(item)
    (run / "results.csv").write_text(stream.getvalue(), encoding="utf-8", newline="\n")
    lines = ["# Agent Benchmark Results", "", f"Run: {manifest['label']}", f"Model/configuration: {manifest['model']}",
             "", f"Completed: {len(rows)}/{manifest['planned_trials']}. Content review is separate from file checks.", "",
             "| Condition | Completed | Content reviewed | Content passed | File checks passed | Full pass |",
             "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for mode, count in summary.items():
        lines.append(f"| {mode} | {count['completed']}/{count['planned']} | {count['graded']} | {count['content_pass']} | {count['behavior_pass']} | {count['full_pass']} |")
    lines += ["", "| Trial | Scenario | Condition | Content | Files | Full |", "| --- | --- | --- | --- | --- | --- |"]
    state = lambda value: "pending" if value is None else ("pass" if value else "fail")
    for row in rows:
        folder = next(t["folder"] for t in manifest["trials"] if t["id"] == row["id"])
        answer_name = "response.md" if row["response_saved"] else "receipt.json"
        lines.append(f"| [{row['id']}]({folder}/{answer_name}) | {row['case']} | {row['condition']} | {state(row['content_pass'])} | {state(row['behavior_pass'])} | {state(row['full_pass'])} |")
    lines += ["", "Read results.json for answers, changes, hashes, and grading notes. A full pass requires both content and file behavior.",
              "Missing answers and ungraded content remain pending. Do not interpret counts as reliability probabilities.",
              "This run does not establish performance on other models, configurations, or future sessions.", ""]
    (run / "report.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(json.dumps(summary, indent=2))
    print(f"Report: {run / 'report.md'}")


def grade(args):
    run = args.run.resolve()
    manifest = read_json(run / "manifest.json")
    if args.trial not in {trial["id"] for trial in manifest["trials"]}:
        raise SystemExit("Unknown trial id")
    if participant_response(run / next(t["folder"] for t in manifest["trials"] if t["id"] == args.trial)) is None:
        raise SystemExit("The participant has no saved answer or captured completed final")
    path = run / "grades.json"
    grades = read_json(path) if path.exists() else {}
    grades[args.trial] = {"content_pass": args.verdict == "pass", "note": args.note}
    write_json(path, grades)
    print(f"Recorded content verdict for {args.trial}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("prepare", help="Create fresh trial projects and a frozen manifest")
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--label", default="Operator agent")
    p.add_argument("--model", default="Not recorded; fill in the actual configuration")
    p.add_argument("--seed", type=int, default=202610182)
    p.add_argument("--repeats", type=int, default=1)
    p.add_argument("--cases", nargs="+", metavar="CASE_ID", help="Run only these scenario IDs; default: all")
    p.set_defaults(action=prepare)
    p = commands.add_parser("report", help="Collect file evidence and show current results")
    p.add_argument("run", type=Path)
    p.set_defaults(action=report)
    p = commands.add_parser("grade", help="Record a content verdict against the frozen criterion")
    p.add_argument("run", type=Path)
    p.add_argument("trial")
    p.add_argument("verdict", choices=["pass", "fail"])
    p.add_argument("--note", required=True)
    p.set_defaults(action=grade)
    args = parser.parse_args()
    if getattr(args, "repeats", 1) < 1:
        parser.error("--repeats must be positive")
    args.action(args)


if __name__ == "__main__":
    main()
