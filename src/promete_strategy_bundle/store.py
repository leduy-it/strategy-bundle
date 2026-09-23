"""Durable staging primitives for the server adapter; never unpickle uploads.

The configured root must be a shared persistent POSIX volume with flock support.
An import is locked across uploads, validation and registration; sealed files
are never overwritten. Receipt writes are atomic and survive process restarts.
"""
from __future__ import annotations

import fcntl
import json
import os
import uuid
import zipfile
from contextlib import contextmanager
from pathlib import Path

from .contract import Bundle, MAX_MANIFEST, fingerprint, sha256_file


class BusyError(ValueError):
    pass


class BundleStore:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)

    def directory(self, import_id: str) -> Path:
        if str(uuid.UUID(import_id)) != import_id:
            raise ValueError("invalid import UUID")
        return self.root / import_id

    @contextmanager
    def locked(self, import_id: str):
        folder = self.directory(import_id)
        folder.mkdir(mode=0o700, exist_ok=True)
        with (folder / ".lock").open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise BusyError("import operation in progress; retry later") from exc
            try:
                yield folder
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    @staticmethod
    def write_json(path: Path, data):
        temp = path.with_suffix(f".{uuid.uuid4().hex}.tmp")
        with temp.open("x", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)

    def initialize(self, import_id: str, data: dict) -> Bundle:
        raw = json.dumps(data, allow_nan=False).encode()
        if len(raw) > MAX_MANIFEST:
            raise ValueError("manifest exceeds 2 MiB")
        bundle = Bundle.model_validate(data)
        with self.locked(import_id) as folder:
            manifest = folder / "manifest.json"
            if manifest.exists() and fingerprint(Bundle.model_validate_json(manifest.read_bytes())) != fingerprint(bundle):
                raise ValueError("manifest is immutable; create a new import")
            if not manifest.exists():
                self.write_json(manifest, bundle.model_dump(mode="json"))
        return bundle

    def load(self, import_id: str) -> Bundle:
        return Bundle.model_validate_json((self.directory(import_id) / "manifest.json").read_bytes())

    def artifact(self, import_id: str, artifact_id: str):
        bundle = self.load(import_id)
        found = next((a for a in bundle.artifacts if a.id == artifact_id), None)
        if found is None:
            raise ValueError("artifact is not in manifest")
        return found

    def validate(self, import_id: str) -> dict:
        bundle = self.load(import_id)
        folder = self.directory(import_id)
        paths = {}
        for artifact in bundle.artifacts:
            path = folder / artifact.id
            if path.is_symlink() or not path.is_file() or path.stat().st_size != artifact.size:
                raise ValueError(f"missing or wrong-size artifact: {artifact.id}")
            if sha256_file(path) != artifact.sha256:
                raise ValueError(f"checksum mismatch: {artifact.id}")
            paths[artifact.role] = path
        # Bound decompression without executing any serialized Python object.
        with zipfile.ZipFile(paths["model"]) as archive:
            items = archive.infolist()
            if len(items) > 512 or sum(i.file_size for i in items) > 4 * 1024**3:
                raise ValueError("model archive exceeds expansion limit")
            if any(i.filename.startswith("/") or ".." in i.filename.split("/") or "\\" in i.filename for i in items):
                raise ValueError("unsafe model archive path")
            if not {"data", "policy.pth"}.issubset(archive.namelist()):
                raise ValueError("expected Stable Baselines model archive")
            data_info = archive.getinfo("data")
            if data_info.file_size > MAX_MANIFEST:
                raise ValueError("oversized model metadata")
            json.loads(archive.read("data"))
        for role in ("training_metadata", "xai_card", "xai_manifest", "ohlcv"):
            if paths[role].stat().st_size > 32 * 1024**2:
                raise ValueError(f"{role} exceeds 32 MiB")
        metadata = json.loads(paths["training_metadata"].read_bytes())
        portfolio = metadata.get("data", {})
        features = metadata.get("features", {})
        if portfolio.get("symbols") != bundle.model.symbols:
            raise ValueError("training metadata symbols differ from manifest")
        if features.get("feature_list") != bundle.model.features:
            raise ValueError("training metadata features differ from manifest")
        if metadata.get("hyperparameters", {}).get("algorithm", "").lower() != bundle.model.algorithm:
            raise ValueError("training metadata algorithm differs from manifest")
        env = metadata.get("env_config", {})
        if env != bundle.model.envContract:
            raise ValueError("training metadata env_config differs from manifest envContract")
        if env.get("state_space") != bundle.model.observationSize or env.get("action_space") != bundle.model.actionSize:
            raise ValueError("runtime observation/action dimensions differ from manifest")
        if metadata.get("hyperparameters", {}).get("normalize_env") is not (bundle.model.normalization != "none"):
            raise ValueError("normalization flag differs from manifest")
        if bundle.model.symbols != sorted(bundle.model.symbols):
            raise ValueError("current serving runtime requires alphabetically ordered symbols; do not reorder a trained model")
        if "normalizer" in paths:
            import math
            if paths["normalizer"].stat().st_size > MAX_MANIFEST:
                raise ValueError("normalizer exceeds JSON limit")
            normalizer = json.loads(paths["normalizer"].read_bytes())
            for key in ("mean", "var"):
                values = normalizer.get(key, [])
                if len(values) != bundle.model.observationSize or any(not isinstance(v, (float, int)) or not math.isfinite(v) for v in values):
                    raise ValueError("normalizer mean/var dimensions or values are invalid")
            if any(v < 0 for v in normalizer["var"]) or normalizer.get("count", 0) <= 0:
                raise ValueError("normalizer variance/count is invalid")
        xmanifest = json.loads(paths["xai_manifest"].read_bytes())
        config = xmanifest.get("config", {})
        if config.get("universe") != bundle.model.symbols:
            raise ValueError("XAI universe differs from ordered model universe")
        card = json.loads(paths["xai_card"].read_bytes())
        if card.get("run_id") != bundle.provenance.runId:
            raise ValueError("XAI card must identify the source run")
        nav = {str(n.date): n.balance for n in bundle.evaluation.nav}
        actions = {str(a.date): a.actions for a in bundle.evaluation.actions}
        dates = []
        with paths["xai_trace"].open() as stream:
            for count, line in enumerate(stream):
                if count >= 20000 or len(line) > MAX_MANIFEST:
                    raise ValueError("trace exceeds row limit")
                row = json.loads(line)
                day = row.get("date")
                if day not in nav or abs(float(row.get("port_value", -1)) - nav[day]) > 0.01:
                    raise ValueError("XAI trace NAV differs from evaluation")
                if row.get("action_executed") != actions.get(day):
                    raise ValueError("XAI executed actions differ from evaluation")
                dates.append(day)
        if dates != list(actions):
            raise ValueError("XAI trace must cover every action date in order")
        ohlcv = json.loads(paths["ohlcv"].read_bytes())
        if not isinstance(ohlcv, list) or not ohlcv:
            raise ValueError("OHLCV snapshot must be a nonempty array")
        if set(row.get("symbol") for row in ohlcv) != set(bundle.model.symbols):
            raise ValueError("OHLCV snapshot must cover the exact model universe")
        return {"valid": True, "fingerprint": fingerprint(bundle), "artifactCount": len(bundle.artifacts),
                "modelExecution": "not_executed", "researchCertification": False}
