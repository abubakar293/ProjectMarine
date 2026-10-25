# Security policy

## Skills are executable instructions

An agent skill is Markdown that your agent *obeys*. A malicious or careless skill is a
prompt injection payload with a distribution channel (prompt-injection and supply-chain
risk apply to every skill repo, this one included). This repository treats that seriously:

- **No network calls.** No skill in this repo instructs an agent to fetch URLs, exfiltrate
  data, or install packages silently. The only install step is the documented
  `pip install numpy scipy navaltoolbox` in INSTALL.md, which you run yourself.
- **No credential access.** No skill reads env vars, dotfiles, git credentials or cloud
  configs. If you ever see one in a fork, treat it as hostile.
- **No `allowed-tools` pre-approvals.** We deliberately ship none, so your harness's normal
  tool-approval flow stays in charge.
- **Pinning.** Install from a pinned commit or tag, not a floating branch. Review diffs
  before updating — a skills repo is a supply chain.

## Engineering-safety disclaimer (read this twice)

This repository helps agents produce *engineering artefacts whose failure modes are
physical*. Ships kill people when they are wrong. Therefore:

1. **Nothing produced with these skills is approved for construction, classification, or
   operation by virtue of having been produced.** A licensed naval architect / engineer of
   record must review and sign; a classification society and flag administration must
   approve where applicable.
2. **Rule text must come from the rule documents in force**, never from model memory. The
   skills are built to *refuse* recalled constants (see `provenance-discipline` and the
   [defect log](docs/DEFECT-LOG.md) items #36–#42 — three separate mis-transcriptions of one
   rule formula, all caught by gates, none by reading).
3. **The reference implementation is a demonstration of method, not a certified tool.** Its
   own record ships with FAIL and OPEN items on purpose.

## Reporting a vulnerability

If you find a security issue in the skills, the reference implementation, or this policy's
claims (e.g. a skill that does instruct network access), open a private vulnerability report
via GitHub Security Advisories, or email the maintainers listed in CONTRIBUTING.md.
We aim to acknowledge within 72 hours.

## Scope of support

We will fix: injection-style instructions, credential access, silent network calls, code that
misrepresents verification status (e.g. marking an OPEN item PASS), CI bypasses.

We cannot fix: an agent harness that ignores its own gates, a user who skips human sign-off,
or physics.
