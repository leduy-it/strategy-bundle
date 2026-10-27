# Portable strategy-sample-report snapshot

Read `strategy-sample-report/SKILL.md` and its three references first. Its content,
renderer, examples, logo, Lexend fonts/license and feature rationale are exact
copies, identified by `manifest.json` SHA-256 entries. The evidence policy sibling
`strategy-dossier-editor/` is also included unchanged. This file is an adapter
guide, not another authoring prompt or renderer.

Codex, Claude Code and OpenCode all use the same exported SKILL file and CLI.
Explicitly tell the selected harness to read `<export>/strategy-sample-report/SKILL.md`;
do not assume automatic discovery. No harness-specific SDK, API key, or runner is
required for these offline commands. Harness execution itself is a separate test.

The original instructions retain historical checkout paths (`$PY`, `.agents/skills`,
`docs/`, `weights/`, `research-rl`). Those identify research inputs, not files
silently obtained by installing this package. Replace the historical interpreter
with the active Python. Supply your actual verified research inputs. The original
DOCX renderer is runnable as `python <export>/strategy-sample-report/scripts/build_report.py`.
The package facade below provides containment, receipt and packet checks around it.

```sh
strategy-bundle report prepare ./authored-report --output ./prepared
strategy-bundle report validate ./prepared/report.json
strategy-bundle report render ./prepared/report.json --output ./rendered
strategy-bundle report pack ./prepared ./rendered --output ./packet
strategy-bundle report check ./packet --expected-subject ./canonical-subject.json
```

`prepare` copies existing content and any supplied facts/source manifest. It does
not invent content or metrics and returns a draft. When authoring from scratch,
write the JSON according to the existing skill and its layout specification first.
There is no universal adapter from a single checkpoint to the skill's multi-seed
and multi-year evidence. Missing evidence must stay missing.

Default asset references must stay inside the source spec directory. Only an
explicit `--source-root <trusted-research-root>` allows legacy relative paths
outside that directory; files must remain inside that root and cannot be symlinks.
Absolute asset paths are forbidden. Preparation copies consumed CSV/images and
all source-manifest files, records hashes, and rebases paths into the prepared
packet. The original source bytes are never modified.

For a complete packet, put `facts.json` and `source-manifest.json` beside the source
`report.json`. Source manifest format:

```json
{
  "schemaVersion": "strategy-report-source/v1",
  "subject": {
    "repository": "your-source-repository",
    "revision": "exact-source-revision-or-snapshot",
    "runId": "actual-run-id",
    "modelRef": "actual-checkpoint-id",
    "seed": 3,
    "evaluationFingerprint": "<64 lowercase hex chars, computed from canonical evaluation>"
  },
  "files": [{"path": "relative/source.json", "size": 123, "sha256": "<actual SHA-256>"}]
}
```

Source paths are relative to `--source-root` when supplied, otherwise the spec
directory. Do not fabricate identity, hashes or evaluation bindings to pass a
check. `facts.identity.model_id/seed`, when present, must match the subject.
For legacy migration, build a new source manifest beside a copied report spec and
point it at explicitly trusted original evidence. Keep the source checkout read-only.

`validate` checks structure, contained files and the original renderer's editorial
lint. Font glyph checking runs only when fonttools is installed. It does not
verify numerical claims against arbitrary prose. `render` requires the `report`
Python extra plus LibreOffice (`soffice`), poppler-utils (`pdfinfo`, `pdftotext`,
`pdffonts`) and fontconfig (`fc-list`, `fc-cache`). The upstream renderer may install
bundled fonts under the current user's `~/.local/share/fonts/promete-lexend`.

`render.json` binds the exact input hashes, skill snapshot and PDF/DOCX output
hashes. Content/facts/source changes require another render. The original renderer
and fonts are pinned; PDF and DOCX timestamps/toolchain versions mean outputs are
not guaranteed byte-identical across runs. Inspect all PDF pages and compare facts
before publication, as required by the original skill.

`pack`/`check` require PDF, DOCX, facts, content, source manifest and matching render
receipt. The packet is `strategy-report-package/v1`, separate from the old model
bundle contract. Its `packageDigest` is SHA-256 of canonical UTF-8 manifest JSON
(sorted keys, compact separators, no NaN), excluding `packageDigest` itself.
`importReady` means offline file-integrity eligibility; human review and canonical
backend subject/ACL checks remain required. Receipts are hashes, not signatures or
proof that the writer is trusted. No offline command uploads or publishes anything.

Exit codes: 0 success; 2 invalid input/incomplete packet; 3 missing optional/system
dependency; 4 renderer failure; 5 packaged skill integrity failure. Successful
results use JSON stdout; report operation failures use JSON stderr. CLI argument
usage errors retain argparse's standard diagnostics.

## Bind and attach to the platform

The new model-plus-report workflow requires a rendered packet BEFORE model upload:

```sh
strategy-bundle report bind ./packet --bundle ./model-bundle --output ./bound-report
strategy-bundle import ./model-bundle --with-reports ./bound-report --api https://app.profinai.vn
strategy-bundle report attach ./bound-report --import-id <completed-import-uuid> --api https://app.profinai.vn
```

The `binding` object is separate from `subject`: `{bundleFingerprint, modelSha256,
evaluationFingerprint, provenance}`. It is included in `packageDigest`. Its evaluation
fingerprint is SHA-256 of the Pydantic-normalized bundle evaluation serialized as
UTF-8 JSON with sorted keys, compact separators, ensure_ascii=False, allow_nan=False,
including default/null fields. Model SHA identifies the normalized import artifact;
source `subject.modelSha256` identifies the original checkpoint.

For Strategy Lab source mapping, require the normalized bundle's canonical
`source-evidence.json` research artifact and sourceHashes. The packet declares exact
original metadata/performance JSON bytes; metadata identity/model hash/window and
performance values must agree with the canonical imported evidence and evaluation.
`subject.evaluationFingerprint` identifies the declared raw performance file SHA.
For sources without that mapping, require exact source provenance/model SHA and
canonical evaluation fingerprint. Binding adds transport metadata; it never changes
the source spec/facts/identity or turns incomplete evidence into verified claims.

Attach transport is raw application/zip to
`POST /api/admin/sample-strategy-imports/{importId}/report`, rooted at manifest.json,
32MiB compressed/128MiB expanded, admin JWT, Idempotency-Key=packageDigest. Server
derives sample/model/backtest from that completed import and rechecks binding and
source evidence. SDK verifies returned binding/identity/digests, then authenticated
metadata and PDF readback pinned with `?reportId=<id>`, PDF SHA, quoted ETag,
X-Report-Id and Cache-Control private,no-store. No bearer token is put in a URL.
Only then is workflowStatus COMPLETE. Model-only legacy import remains compatible;
its status COMPLETED alone is not completion of the new report workflow.
