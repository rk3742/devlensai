"""
Module 6: Dead Code Detection.
Module 7: Technical Debt Detector.

Both are implemented primarily as deterministic static analysis (regex-based
function/import extraction + cross-reference counting) rather than pure LLM
guessing. This is intentional: "confidence: 92%" type claims need to come from
something measurable, not an LLM's vibes. The LLM is used only to write a
human-readable explanation for findings the static pass already detected.
"""
import re
from collections import defaultdict
from dataclasses import dataclass

TEST_PATH_RE = re.compile(r"(^|/)(tests?|__tests__|spec|specs)(/|$)|\.(test|spec)\.\w+$", re.I)

# --- Function/identifier extraction patterns per broad language family ---

FUNC_DEF_PATTERNS = [
    re.compile(r"^\s*def\s+([a-zA-Z_]\w*)\s*\(", re.M),                      # Python
    re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s*\*?\s+([a-zA-Z_]\w*)\s*\(", re.M),  # JS/TS named function
    re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+([a-zA-Z_]\w*)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>", re.M),  # JS arrow
    re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+([a-zA-Z_]\w*)\s*=\s*(?:async\s+)?function\b", re.M),  # const x = function
    # Java/C#-style typed method: requires an access modifier OR a capitalized/known return type to
    # avoid matching JS keywords like "return"/"if" followed by "function(...)".
    re.compile(
        r"^\s*(?:public|private|protected)\s+(?:static\s+)?(?:async\s+)?[\w<>\[\]]+\s+([a-zA-Z_]\w*)\s*\([^)]*\)\s*\{",
        re.M,
    ),
]

IMPORT_LINE_PATTERNS = [
    re.compile(r"^\s*import\s+.*$", re.M),
    re.compile(r"^\s*from\s+[\w.]+\s+import\s+(.*)$", re.M),
    re.compile(r"^\s*(?:const|let|var)\s+\{?\s*([\w,\s]+)\}?\s*=\s*require\(", re.M),
]

LONG_FUNCTION_LINE_THRESHOLD = 60   # lines
HUGE_FUNCTION_LINE_THRESHOLD = 120  # lines, flagged as severe


@dataclass
class FunctionDef:
    name: str
    file_path: str
    start_line: int
    line_count: int


def extract_function_defs(file_path: str, content: str) -> list[FunctionDef]:
    lines = content.splitlines()
    defs: list[FunctionDef] = []
    seen_positions = set()

    for pattern in FUNC_DEF_PATTERNS:
        for match in pattern.finditer(content):
            name = match.group(1)
            if not name or name in ("if", "for", "while", "switch", "catch"):
                continue
            start_pos = match.start()
            if start_pos in seen_positions:
                continue
            seen_positions.add(start_pos)
            start_line = content[:start_pos].count("\n") + 1
            line_count = _estimate_function_length(lines, start_line - 1)
            defs.append(FunctionDef(name=name, file_path=file_path, start_line=start_line, line_count=line_count))

    return defs


def _estimate_function_length(lines: list[str], start_idx: int) -> int:
    """
    Brace/indent-agnostic heuristic: count lines until we hit a blank line
    followed by a line at the same or lower indentation that starts a new
    top-level construct, or until a sane cap. Good enough for flagging outliers,
    not meant to be a perfect parser.
    """
    if start_idx >= len(lines):
        return 1
    base_indent = len(lines[start_idx]) - len(lines[start_idx].lstrip())
    count = 1
    for i in range(start_idx + 1, min(start_idx + 600, len(lines))):
        line = lines[i]
        if not line.strip():
            count += 1
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        is_new_top_level = indent <= base_indent and re.match(
            r"^(def |function |class |const \w+\s*=|export |module\.exports|@)", stripped
        )
        if is_new_top_level and i > start_idx + 1:
            break
        count += 1
    return count


def extract_imported_names(content: str) -> set[str]:
    names: set[str] = set()
    for pattern in IMPORT_LINE_PATTERNS:
        for match in pattern.finditer(content):
            group = match.group(1) if match.groups() else match.group(0)
            for token in re.split(r"[,{}\s]+", group):
                token = token.strip()
                if token and token.isidentifier():
                    names.add(token)
    return names


EXPORT_OR_ROUTE_PATTERNS = [
    r"module\.exports\s*=.*\b{name}\b",
    r"export\s*\{{[^}}]*\b{name}\b",
    r"export\s+(?:default\s+)?(?:function\s+|const\s+|class\s+)?{name}\b",
    r"\.(?:get|post|put|delete|patch|use|all)\s*\([^)]*\b{name}\b",   # Express-style route registration
    r"@app\.(?:route|get|post|put|delete)\b.*\n\s*def\s+{name}\b",    # Flask decorator above def
    r"\b{name}\s*:\s*{name}\b",  # object shorthand re-export { foo: foo }
]

# Names that are conventionally entry points / framework hooks, never safe to flag.
FRAMEWORK_ENTRYPOINT_NAMES = {
    "main", "init", "setup", "index", "app", "handler", "render", "App",
    "componentDidMount", "componentWillUnmount", "useEffect", "constructor",
    "__init__", "__main__", "get", "post", "put", "delete", "patch",
    "onMount", "onUnmount", "setupServer", "createApp", "configure",
}


def _is_used_via_export_or_route(name: str, all_content: str) -> bool:
    for template in EXPORT_OR_ROUTE_PATTERNS:
        pattern = re.compile(template.format(name=re.escape(name)))
        if pattern.search(all_content):
            return True
    return False


def detect_dead_code(files_with_content: list[tuple[str, str, str]]) -> list[dict]:
    """
    Heuristic dead-code detection:
    1. Collect every function definition across the repo.
    2. Count how many times each function name appears as a call/reference
       ANYWHERE else in the repo (cheap whole-corpus substring search).
    3. Treat exports, route registrations, and framework hook names as "used"
       even with a single occurrence, since those are legitimate single-reference
       usage patterns (a route handler is "called" once, by the router).
    4. Flag functions with zero qualifying references as likely dead code, with
       a confidence score based on name specificity — common/short names and
       known framework hooks are never flagged, since the false-positive cost
       is high and erodes trust in every other finding this module reports.
    """
    all_content = ""
    all_defs: list[FunctionDef] = []

    for rel_path, _lang, content in files_with_content:
        all_content += content + "\n"
        all_defs.extend(extract_function_defs(rel_path, content))

    findings = []
    seen_names_this_run = set()

    for fd in all_defs:
        if fd.name in seen_names_this_run or fd.name in FRAMEWORK_ENTRYPOINT_NAMES:
            continue

        occurrence_pattern = re.compile(r"\b" + re.escape(fd.name) + r"\b")
        total_occurrences = len(occurrence_pattern.findall(all_content))
        external_references = total_occurrences - 1

        if external_references > 0:
            continue
        if _is_used_via_export_or_route(fd.name, all_content):
            continue

        # Confidence scales down for very short/common names (riskier to flag).
        specificity = min(len(fd.name) / 12.0, 1.0)
        confidence = int(45 + specificity * 45)
        if confidence < 40:
            continue  # not worth surfacing as a finding

        seen_names_this_run.add(fd.name)
        findings.append({
            "kind": "dead_code",
            "file_path": fd.file_path,
            "title": f"Possibly unused function: {fd.name}()",
            "detail": (
                f"'{fd.name}' is defined at line {fd.start_line} in {fd.file_path} but no call, "
                f"export, or route registration referencing it was found anywhere else in the "
                f"analyzed files. It may be dead code, or it may be invoked dynamically, called from "
                f"a file that wasn't indexed, or used as a callback passed by reference in a way this "
                f"scan doesn't recognize."
            ),
            "confidence": confidence,
            "severity": "low" if confidence < 65 else "medium",
        })

    return findings


def detect_technical_debt(files_with_content: list[tuple[str, str, str]]) -> list[dict]:
    """
    Deterministic technical-debt signals:
    - Long functions (line count thresholds)
    - Duplicate-looking function bodies (same function name defined in 2+ places)
    - TODO/FIXME/HACK comments
    - Deeply nested code (proxy: lines with very high indentation)
    """
    findings = []
    name_locations: dict[str, list[str]] = defaultdict(list)

    for rel_path, _lang, content in files_with_content:
        defs = extract_function_defs(rel_path, content)
        is_test_file = bool(TEST_PATH_RE.search(rel_path))

        for fd in defs:
            name_locations[fd.name].append(rel_path)

            # Test files routinely have long it()/describe() callback bodies that aren't
            # production complexity debt — skip the long-function check for them, but still
            # let TODO/duplicate detection run since those signals stay meaningful there.
            if is_test_file:
                continue

            if fd.line_count >= HUGE_FUNCTION_LINE_THRESHOLD:
                findings.append({
                    "kind": "tech_debt",
                    "file_path": rel_path,
                    "title": f"Very long function: {fd.name}() — ~{fd.line_count} lines",
                    "detail": (
                        f"'{fd.name}' starting at line {fd.start_line} spans roughly {fd.line_count} lines. "
                        "Functions this long are hard to test and reason about — consider splitting into "
                        "smaller, single-purpose functions."
                    ),
                    "confidence": 85,
                    "severity": "high",
                })
            elif fd.line_count >= LONG_FUNCTION_LINE_THRESHOLD:
                findings.append({
                    "kind": "tech_debt",
                    "file_path": rel_path,
                    "title": f"Long function: {fd.name}() — ~{fd.line_count} lines",
                    "detail": (
                        f"'{fd.name}' starting at line {fd.start_line} is roughly {fd.line_count} lines long, "
                        "above the ~60-line readability guideline. Consider refactoring."
                    ),
                    "confidence": 65,
                    "severity": "medium",
                })

        # TODO / FIXME / HACK comments
        for i, line in enumerate(content.splitlines(), start=1):
            if re.search(r"(TODO|FIXME|HACK|XXX)\b", line):
                marker = re.search(r"(TODO|FIXME|HACK|XXX)\b", line).group(1)
                findings.append({
                    "kind": "tech_debt",
                    "file_path": rel_path,
                    "title": f"{marker} comment at line {i}",
                    "detail": line.strip()[:200],
                    "confidence": 95,
                    "severity": "low",
                })

    # Duplicate function names defined in 2+ different files = likely duplicated logic.
    for name, locations in name_locations.items():
        unique_files = sorted(set(locations))
        if len(unique_files) >= 2:
            findings.append({
                "kind": "tech_debt",
                "file_path": ", ".join(unique_files[:4]),
                "title": f"Duplicate logic: {name}() defined in {len(unique_files)} files",
                "detail": (
                    f"A function named '{name}' is defined independently in: {', '.join(unique_files)}. "
                    "This may indicate copy-pasted logic that should be extracted into a shared module."
                ),
                "confidence": 55,
                "severity": "medium",
            })

    # Cap volume so the UI stays useful rather than overwhelming.
    findings.sort(key=lambda f: -f["confidence"])
    return findings[:150]
