import re
from pathlib import Path
from pydriller import Repository
from pydriller.domain.commit import ModificationType


INPUT_FILE = Path("./input.txt")

def collect_inputs():
    lines = [ln.strip() for ln in INPUT_FILE.read_text().splitlines() if ln.strip()]

    # len of lines must be 2
    if len(lines) < 2:
        raise ValueError(
            f"inputs.txt must contain exactly 2 lines.\n"
            f"  Line 1: comma-separated issue IDs\n"
            f"  Line 2: GitHub repository URL\n"
            f"  Found only {len(lines)} non-empty line(s)."
        )

    issue_ids = [token.strip().lower() for token in lines[0].split(",") if token.strip()]
    repo_url  = lines[1]

    return issue_ids, repo_url

def build_pattern(issue_ids):
    escaped = [re.escape(i) for i in issue_ids]
    pattern = r"\b(" + "|".join(escaped) + r")\b"
    return re.compile(pattern, re.IGNORECASE)


TRACKED_TYPES = {ModificationType.ADD, ModificationType.MODIFY, ModificationType.DELETE}

def get_unique_files(commit):
    paths = set()
    for mod in commit.modified_files:
        if mod.change_type not in TRACKED_TYPES:
            continue
        path = mod.new_path if mod.change_type != ModificationType.DELETE else mod.old_path
        if path:
            paths.add(path)
    return paths

def get_dmm_score(commit):
    scores = [
        commit.dmm_unit_size,
        commit.dmm_unit_complexity,
        commit.dmm_unit_interfacing,
    ]
    valid = [s for s in scores if s is not None]
    return sum(valid) / len(valid) if valid else 0.0

def analyze(issue_ids, repo_url):
    pattern             = build_pattern(issue_ids)
    seen_hashes         = set()
    unique_files_global = set()
    dmm_total           = 0.0
    total_commits       = 0

    for commit in Repository(repo_url).traverse_commits():
        # ── does this commit reference any of our issue IDs? ──────────────
        if not pattern.search(commit.msg):
            continue
        # ── deduplicate by commit hash ────────────────────────────────────
        if commit.hash in seen_hashes:
            continue
        seen_hashes.add(commit.hash)

        total_commits += 1
        # ── accumulate global unique files ────────────────────────────────
        unique_files_global |= get_unique_files(commit)
        # ── accumulate DMM score ──────────────────────────────────────────
        dmm_total += get_dmm_score(commit)

    # ── final averages ────────────────────────────────────────────────────
    if total_commits == 0:
        return 0, 0.0, 0.0

    avg_files_changed = len(unique_files_global) / total_commits
    avg_dmm           = dmm_total / total_commits

    return total_commits, avg_files_changed, avg_dmm

def main():
    issue_ids, repo_url = collect_inputs()

    total_commits, avg_files, avg_dmm = analyze(issue_ids, repo_url)

    print(f"Total commits analyzed: {total_commits}")
    print(f"Average number of files changed: {round(avg_files, 2)}")
    print(f"Average DMM metrics: {round(avg_dmm, 4)}")


if __name__ == "__main__":
    main()