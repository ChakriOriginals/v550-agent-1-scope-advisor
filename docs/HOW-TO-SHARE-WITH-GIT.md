# How to share Agent 1 with Git

This guide publishes the prepared local repository to a private Git host and gives teaching staff a repeatable test workflow.

## Prerequisites

- Access to a private GitHub, IU GitHub Enterprise, or private GitLab project.
- Permission to invite the teaching staff who should see instructor source material.
- A successful `python3 tools/verify_package.py` run.
- No real student work, deployment properties, credentials, or private test results in the working tree.

## Create the private remote

Create an empty private repository in your approved Git service. A suitable name is:

```text
v550-agent-1-scope-advisor
```

Do not initialize the remote with a README, license, or `.gitignore`; this package already has them.

## Connect and push

From this package folder:

```bash
git remote add origin PRIVATE_REPOSITORY_URL
git push -u origin main
```

The local repository already has an initial verified commit. Replace `PRIVATE_REPOSITORY_URL` with the HTTPS or SSH URL supplied by your Git host.

## Invite teaching staff

Give staff the least privilege they need:

- read access for testers who only clone and file issues;
- write or triage access for staff who maintain fixtures or resolve defects;
- administrator access only for the repository owner and designated technical maintainer.

Keep forking and repository visibility private. Do not publish the instructor-only evidence folder in a public fork.

## Clone and verify

Each staff member runs:

```bash
git clone PRIVATE_REPOSITORY_URL
cd v550-agent-1-scope-advisor
python3 tools/verify_package.py
```

Staff should stop if canonical verification, source-map equality, or any automated test fails.

## Work on a test or fix

Use one branch per change:

```bash
git switch -c staff-test/SHORT-DESCRIPTION
```

After editing, run:

```bash
python3 tools/verify_package.py
git status --short
```

Stage only the intended paths, commit, and push:

```bash
git add PATH_ONE PATH_TWO
git commit -m "test: describe the Agent 1 case"
git push -u origin staff-test/SHORT-DESCRIPTION
```

Open a pull request for review. Do not push directly to `main` after staff testing begins.

## Binary course files

The current package is about 36 MB and its largest file is below GitHub's 100 MB per-file limit. Plain Git can share this snapshot.

PowerPoint, Word, and PDF files do not diff well. If those files will change frequently, install Git LFS before the first remote push and track them:

```bash
git lfs install
git lfs track "*.pptx" "*.docx" "*.pdf"
git add .gitattributes
git commit -m "chore: track course binaries with Git LFS"
```

Do not add LFS after many binary revisions without planning the history migration. The build machine that created this package did not have Git LFS installed, so the initial local commit uses ordinary Git objects.

## Privacy and secret checks

Before every push:

1. Run `python3 tools/verify_package.py`.
2. Review `git diff --cached` and `git status --short`.
3. Confirm no `.env`, key, Script Properties export, student key, roster file, transcript, or private report was added.
4. Keep the repository private and collaborators current.
5. Rotate any credential immediately if it was ever committed; deleting the latest file does not remove it from Git history.

## Troubleshooting

### The remote rejects a large file

Do not split or compress source files arbitrarily. Install Git LFS, track the affected binary types, recommit before the first shared push, and retry.

### Staff cannot run schema tests

Use Python 3.11+ with the `jsonschema` package available. A missing dependency is an environment problem, not permission to skip the schema tests.

### A canonical file changed

Edit only the canonical source under `skills/v550-scope-advisor/references/`, then run:

```bash
python3 skills/v550-scope-advisor/scripts/sync_runtime_knowledge.py
python3 skills/v550-scope-advisor/scripts/verify_canonical_knowledge.py
python3 tools/verify_package.py
```

Never hand-edit the generated runtime or acceptance-fixture copies.

### A credential was committed

Make the repository temporarily inaccessible, rotate the credential first, notify the repository owner, and clean Git history using the Git host's approved incident procedure. A normal revert is not sufficient because the credential remains in earlier commits.
