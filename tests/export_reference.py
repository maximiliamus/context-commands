"""Bundle a completed real run, normalizing local project paths for portability."""

from pathlib import Path
import argparse
import hashlib
import json
import re

from benchmark import participant_response
from path_normalization import compile_path_replacements, replace_paths

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("source", type=Path)
parser.add_argument("destination", type=Path)
args = parser.parse_args()
source, destination = args.source.resolve(), args.destination.resolve()
if destination.exists():
    raise SystemExit("Destination exists; reference bundles are never overwritten")
manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
results = json.loads((source / "results.json").read_text(encoding="utf-8"))
planned_ids = [trial["id"] for trial in manifest["trials"]]
result_ids = [row["id"] for row in results["trials"]]
if (len(set(planned_ids)) != manifest["planned_trials"] or len(set(result_ids)) != len(result_ids)
        or set(result_ids) != set(planned_ids)
        or any(type(row.get("full_pass")) is not bool or type(row.get("content_pass")) is not bool
               for row in results["trials"])):
    raise SystemExit("Only a completed, content-graded real run can be exported")
current = Path(__file__).resolve().parent.parent / "CONTEXT_COMMANDS.md"
rules_hash = hashlib.sha256(current.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
if rules_hash != manifest["rules_sha256"]:
    raise SystemExit("Definitions changed since this run; do not label it as the current reference")
if (hashlib.sha256(manifest["rules"].encode("utf-8")).hexdigest() != manifest["rules_sha256"]
        or results["rules_sha256"] != manifest["rules_sha256"]):
    raise SystemExit("Definition snapshots and reported hashes do not match")
for row in results["trials"]:
    trial = next(trial for trial in manifest["trials"] if trial["id"] == row["id"])
    folder = source / trial["folder"]
    response = participant_response(folder, prefer_final=manifest.get("response_recording") == "final")
    if (response is None or response["sha256"] != row["response_sha256"]
            or response["source"] != row["response_source"]
            or response["saved"] != row["response_saved"]):
        raise SystemExit(f"Response changed after the report: {row['id']}")
    if (not response["saved"] and manifest.get("response_recording") != "final"
            and (row["behavior_pass"] or row["full_pass"])):
        raise SystemExit(f"Missing response file cannot pass file checks: {row['id']}")
    for name, expected in {**row["source_hashes_after"], **row["protected_hashes_after"]}.items():
        path = folder / name
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        if actual != expected:
            raise SystemExit(f"Trial input or output changed after the report: {row['id']}/{name}")
    reported_files = {name for name, digest in row["source_hashes_after"].items() if digest is not None}
    actual_files = {path.relative_to(folder).as_posix() for area in ["src", "memory"]
                    for path in (folder / area).rglob("*") if path.is_file()}
    known = {"CONTEXT.md", "RULES.md", "prompt.txt", "response.md", "changes.diff", "observation.json", "receipt.json"}
    unexpected = {path.relative_to(folder).as_posix() for path in folder.rglob("*") if path.is_file()
                  and path.relative_to(folder).parts[0] not in ["src", "memory"]
                  and path.relative_to(folder).as_posix() not in known | set(trial["protected_hashes"])}
    if actual_files != reported_files or unexpected != set(row["unexpected_files"]):
        raise SystemExit(f"Trial file inventory changed after the report: {row['id']}")

replacements = []
for trial in manifest["trials"]:
    path = source / trial["folder"]
    replacements.append((path, f"<RUN_DIRECTORY>/{trial['folder']}"))
replacements.append((source, "<RUN_DIRECTORY>"))
patterns = compile_path_replacements(replacements)
provenance = {
    "kind": "Real completed reference run; no generated example responses",
    "model": manifest["model"], "rules_sha256": manifest["rules_sha256"],
    "path_normalization": "Absolute local run/trial paths are replaced with <RUN_DIRECTORY>. Original observation/result hashes refer to the original run; this inventory records both original and bundled bytes.",
    "artifacts": {},
}
pending = []
for path in sorted(source.rglob("*")):
    if not path.is_file() or path.name == "run-status.json":
        continue
    relative = path.relative_to(source)
    original = path.read_bytes()
    text = original.decode("utf-8")
    text = replace_paths(text, patterns)
    decoded = json.dumps(json.loads(text), ensure_ascii=False) if path.suffix == ".json" else text
    if re.search(r"[\u0400-\u04ff]", text + decoded):
        raise SystemExit(f"Non-English Cyrillic text remains in {relative}")
    bundled = text.encode("utf-8")
    pending.append((relative, bundled))
    provenance["artifacts"][relative.as_posix()] = {
        "original_sha256": hashlib.sha256(original).hexdigest(),
        "bundled_sha256": hashlib.sha256(bundled).hexdigest(),
        "path_normalized": original != bundled,
    }
destination.mkdir(parents=True)
for relative, bundled in pending:
    target = destination / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(bundled)
(destination / "provenance.json").write_text(json.dumps(provenance, ensure_ascii=True, indent=2) + "\n", encoding="utf-8", newline="\n")
print(f"Exported {len(results['trials'])} real trials to {destination}")
