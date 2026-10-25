"""Validate every SKILL.md against the Agent Skills specification (agentskills.io).

Checks: frontmatter present and parseable; name matches directory, lowercase-hyphen, <=64
chars, no leading/trailing/double hyphens; description non-empty <=1024 chars; body length
<=500 lines (spec recommendation); no TODO/FIXME markers; referenced local files exist.
Exit code 1 on any error (used by CI).
"""
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SKILLS = os.path.join(ROOT, "skills")
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

errors, warns = [], []


def frontmatter(text, path):
    if not text.startswith("---"):
        errors.append(f"{path}: missing YAML frontmatter")
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        errors.append(f"{path}: unterminated frontmatter")
        return {}
    fm = {}
    for line in text[3:end].strip().splitlines():
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if m:
            fm[m.group(1)] = m.group(2).strip()
    return fm


def main():
    n = 0
    for d in sorted(os.listdir(SKILLS)):
        p = os.path.join(SKILLS, d)
        skill_md = os.path.join(p, "SKILL.md")
        if not os.path.isdir(p):
            continue
        n += 1
        if not os.path.exists(skill_md):
            errors.append(f"{d}: no SKILL.md")
            continue
        text = open(skill_md, encoding="utf-8").read()
        fm = frontmatter(text, d)
        name = fm.get("name", "")
        if name != d:
            errors.append(f"{d}: name '{name}' must equal directory name")
        if not NAME_RE.match(name) or len(name) > 64:
            errors.append(f"{d}: invalid name '{name}' (lowercase-hyphen, <=64)")
        desc = fm.get("description", "")
        if not desc:
            errors.append(f"{d}: missing description")
        elif len(desc) > 1024:
            errors.append(f"{d}: description {len(desc)} chars > 1024")
        elif not re.search(r"\b(Use|Start here)\b", desc):
            warns.append(f"{d}: description has no 'Use when...' trigger phrase")
        body_lines = len(text.splitlines())
        if body_lines > 500:
            errors.append(f"{d}: SKILL.md is {body_lines} lines (spec recommends <=500)")
        if re.search(r"\bTODO\b|\bFIXME\b|lorem ipsum", text, re.I):
            errors.append(f"{d}: unfinished marker (TODO/FIXME) present")
        # local file references must exist (relative markdown links / scripts paths)
        for ref in re.findall(r"\]\((?!https?:)([^)#][^)]*)\)", text):
            if not os.path.exists(os.path.join(p, ref)):
                errors.append(f"{d}: referenced file missing: {ref}")
        for sec in re.findall(r"(?:scripts|references|assets)/[\w./-]+", text):
            if not os.path.exists(os.path.join(p, sec)):
                errors.append(f"{d}: referenced path missing: {sec}")
    print(f"linted {n} skills: {len(errors)} error(s), {len(warns)} warning(s)")
    for e in errors:
        print("  ERROR:", e)
    for w in warns:
        print("  warn :", w)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
