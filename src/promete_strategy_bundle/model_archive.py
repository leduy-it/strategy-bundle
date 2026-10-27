"""SB3 checkpoint as the import API accepts it: the policy, not the state a trainer resumes from.

A saved model also carries rollout state (pickled arrays and deques), replay-buffer and
train-frequency objects and per-network optimizers. The server refuses all of them without
decoding them, so the exporter drops them and `verify` applies the same envelope rules
locally. The server remains the authority (policy kwargs, dimensions, sizes).
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

POLICY_MEMBERS = frozenset({
    "data", "policy.pth", "pytorch_variables.pth", "policy.optimizer.pth",
    "_stable_baselines3_version", "system_info.txt",
})
# Serialized SB3 fields the server accepts as inert metadata (type checked, never decoded).
INERT_SERIALIZED = frozenset({
    "policy_class", "observation_space", "action_space",
    "rollout_buffer_class", "lr_schedule", "clip_range",
})
_ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)


def _serialized(value) -> bool:
    return isinstance(value, dict) and ":serialized:" in value


def write_policy_archive(source: Path, target: Path) -> dict:
    """Write `target` with only the policy members and plain/inert metadata of `source`.

    Output bytes depend only on the input, so a re-export reproduces the same hash.
    Returns what was dropped, for the bundle's provenance.
    """
    dropped_members, dropped_keys = [], []
    with zipfile.ZipFile(source) as src, zipfile.ZipFile(target, "w", zipfile.ZIP_STORED) as dst:
        for name in src.namelist():
            if name not in POLICY_MEMBERS:
                dropped_members.append(name)
                continue
            payload = src.read(name)
            if name == "data":
                data = json.loads(payload)
                dropped_keys = [k for k, v in data.items() if _serialized(v) and k not in INERT_SERIALIZED]
                payload = json.dumps({k: v for k, v in data.items() if k not in dropped_keys}).encode()
            info = zipfile.ZipInfo(name, date_time=_ZIP_EPOCH)
            info.external_attr = 0o644 << 16
            dst.writestr(info, payload)
    return {"droppedMembers": dropped_members, "droppedDataKeys": dropped_keys}


def check_policy_archive(path: Path) -> None:
    """Raise if the archive still holds members or serialized fields the server refuses."""
    with zipfile.ZipFile(path) as archive:
        extra = sorted(set(archive.namelist()) - POLICY_MEMBERS)
        if extra:
            raise ValueError(f"model archive has training-only members {extra}; re-export the bundle")
        data = json.loads(archive.read("data"))
    extra = sorted(k for k, v in data.items() if _serialized(v) and k not in INERT_SERIALIZED)
    if extra:
        raise ValueError(f"model data has serialized training state {extra}; re-export the bundle")
