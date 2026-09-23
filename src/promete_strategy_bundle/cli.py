"""Installable CLI. Tokens only come from environment or a private file."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from . import __version__
from .contract import Bundle, artifact_path, fingerprint, load_bundle, verify_bundle


def api_url(base: str) -> str:
    parsed = urlsplit(base)
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("API URL must not contain credentials, query or fragment")
    if parsed.scheme != "https" and not (parsed.scheme == "http" and parsed.hostname in ("localhost", "127.0.0.1", "::1")):
        raise ValueError("HTTPS required except for localhost development")
    return base.rstrip("/") + "/api/admin/sample-strategy-imports"


def call(client: httpx.Client, method: str, url: str, **kwargs):
    response = client.request(method, url, **kwargs)
    if response.is_error:
        # The server's structured validation errors are useful; never print request headers.
        raise ValueError(f"HTTP {response.status_code}: {response.text[:4000]}")
    return response.json()


def import_bundle(client: httpx.Client, base: str, root: Path, commit: bool = True) -> dict:
    bundle = verify_bundle(root)
    result = call(client, "POST", base, json=bundle.model_dump(mode="json"),
                  headers={"Idempotency-Key": fingerprint(bundle)})
    import_id = result["id"]
    if result["status"] == "COMPLETED":
        return result
    if result["status"] in ("UPLOADING", "INVALID"):
        for artifact in bundle.artifacts:
            with artifact_path(root, artifact.path).open("rb") as stream:
                call(client, "PUT", f"{base}/{import_id}/artifacts/{artifact.id}",
                     content=stream, headers={"Content-Type": "application/octet-stream", "Content-Length": str(artifact.size)})
        result = call(client, "POST", f"{base}/{import_id}/validate")
    if result["status"] != "VALIDATED" and result["status"] != "FAILED":
        raise ValueError(f"Import {import_id}: {result['status']}: {result.get('validation', '')}")
    if commit:
        result = call(client, "POST", f"{base}/{import_id}/commit")
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Verify and import complete strategy bundles (admin JWT required).")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("schema", help="Print the versioned JSON Schema")
    for name in ("inspect", "verify"):
        p = sub.add_parser(name)
        p.add_argument("bundle", type=Path)
    p = sub.add_parser("import", help="Upload, validate and commit a bundle as a hidden sample")
    p.add_argument("bundle", type=Path)
    p.add_argument("--validate-only", action="store_true")
    for name in ("status", "commit", "cancel"):
        p = sub.add_parser(name)
        p.add_argument("id")
    for name in ("import", "status", "commit", "cancel"):
        p = sub.choices[name]
        p.add_argument("--api", required=True, help="Backend origin, e.g. https://app.profinai.vn")
        p.add_argument("--token-file", type=Path, help="JWT file; otherwise STRATEGY_BUNDLE_TOKEN")
    args = parser.parse_args(argv)
    try:
        if args.command == "schema":
            result = Bundle.model_json_schema()
        elif args.command in ("inspect", "verify"):
            bundle = verify_bundle(args.bundle) if args.command == "verify" else load_bundle(args.bundle / "manifest.json")
            result = {"name": bundle.strategy.name, "modelRef": bundle.provenance.modelRef,
                      "algorithm": bundle.model.algorithm, "fingerprint": fingerprint(bundle),
                      "artifacts": len(bundle.artifacts), "verified": args.command == "verify"}
        else:
            base = api_url(args.api)
            if args.token_file:
                if args.token_file.stat().st_mode & 0o077:
                    raise ValueError("token file must be private (chmod 600)")
                token = args.token_file.read_text().strip()
            else:
                token = os.environ.get("STRATEGY_BUNDLE_TOKEN", "").strip()
            if not token:
                raise ValueError("Set STRATEGY_BUNDLE_TOKEN or --token-file to an admin access token")
            with httpx.Client(headers={"Authorization": f"Bearer {token}"}, timeout=300, follow_redirects=False) as client:
                if args.command == "import":
                    result = import_bundle(client, base, args.bundle, not args.validate_only)
                else:
                    if not all(c in "0123456789abcdef-" for c in args.id) or len(args.id) != 36:
                        raise ValueError("id must be a UUID")
                    method = {"status": "GET", "commit": "POST", "cancel": "DELETE"}[args.command]
                    suffix = "/commit" if args.command == "commit" else ""
                    result = call(client, method, f"{base}/{args.id}{suffix}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, httpx.HTTPError) as exc:
        print(f"strategy-bundle: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
