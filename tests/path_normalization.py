"""Normalize exported run paths, including Windows spelling and file URIs."""

import json
import re
from urllib.parse import quote, unquote


def compile_path_replacements(replacements):
    patterns = []
    for path, replacement in sorted(replacements, key=lambda item: len(str(item[0])), reverse=True):
        variants = {str(path), path.as_posix()}
        if path.is_absolute():
            posix = path.as_posix()
            prefix = "file:" if path.drive and posix.startswith("//") else "file://" + ("/" if path.drive else "")
            uri = prefix + quote(posix, safe="/:")
            variants.update((uri, unquote(uri)))
        flags = re.IGNORECASE if path.drive else 0
        spellings = {spelling for variant in variants for spelling in
                     (variant, json.dumps(variant, ensure_ascii=True)[1:-1],
                      json.dumps(variant, ensure_ascii=False)[1:-1])}
        for spelling in sorted(spellings, key=len, reverse=True):
            # A sibling such as run-other must not match the run directory.
            boundary = r'''(?=$|[\\/\s"'\)\]\}?#])'''
            patterns.append((re.compile(re.escape(spelling) + boundary, flags), replacement))
    return patterns


def replace_paths(text, patterns):
    for pattern, replacement in patterns:
        text = pattern.sub(lambda match: replacement, text)
    return text
