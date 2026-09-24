from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from pathlib import Path, PurePosixPath
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA = "sample-strategy-bundle/v1"
MAX_MANIFEST = 2 * 1024**2
MAX_FILE = 2 * 1024**3
MAX_TOTAL = 8 * 1024**3
Finite = Annotated[float, Field(allow_inf_nan=False)]
Nonnegative = Annotated[Finite, Field(ge=0)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Artifact(Contract):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    role: Literal["model", "normalizer", "training_metadata", "xai_trace", "xai_manifest", "xai_card", "ohlcv", "research"]
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size: int = Field(gt=0, le=MAX_FILE, strict=True)

    @model_validator(mode="after")
    def safe_path(self):
        parts = PurePosixPath(self.path).parts
        if (not parts or self.path.startswith("/") or "\\" in self.path
                or any(p in (".", "..", "") for p in self.path.split("/"))
                or any(ord(c) < 32 for c in self.path) or ":" in self.path):
            raise ValueError("artifact path must be a safe relative POSIX path")
        return self


class Provenance(Contract):
    repository: str = Field(min_length=1, max_length=500)
    revision: str = Field(min_length=1, max_length=128)
    runId: str = Field(min_length=1, max_length=128)
    modelRef: str = Field(min_length=1, max_length=128)
    seed: int = Field(ge=0, le=9007199254740991, strict=True)
    trainedAt: datetime
    evidence: Literal["ORIGINAL", "REPLAYED"]


class Model(Contract):
    algorithm: Literal["ppo", "a2c", "sac", "ddpg", "td3", "ars", "crossq", "tqc", "trpo", "recurrentppo"]
    symbols: list[str] = Field(min_length=1, max_length=500)
    features: list[str] = Field(min_length=1, max_length=1000)
    timesteps: int = Field(gt=0)
    normalization: Literal["none", "obs_rms"]
    observationSize: int = Field(gt=0)
    actionSize: int = Field(gt=0)
    libraryVersions: dict[str, str] = Field(min_length=1)
    envContract: dict[str, Any] = Field(min_length=1)

    @model_validator(mode="after")
    def ordered_contract(self):
        for key in ("symbols", "features"):
            values = getattr(self, key)
            if len(set(values)) != len(values) or any(not v.strip() for v in values):
                raise ValueError(f"{key} must be nonempty and unique; order is significant")
        if any(not re.fullmatch(r"[A-Z0-9._-]{1,20}", s) for s in self.symbols):
            raise ValueError("invalid symbol")
        if self.actionSize != len(self.symbols):
            raise ValueError("actionSize must match ordered symbols")
        return self


class Strategy(Contract):
    name: str = Field(min_length=1, max_length=180)
    description: str = Field(min_length=1, max_length=20000)
    config: dict[str, Any] = Field(min_length=1)
    riskLevel: Literal["LOW", "MEDIUM", "HIGH"]
    horizon: Literal["INTRADAY", "SWING", "POSITION"]
    universe: str = Field(min_length=1, max_length=200)
    authorLabel: str = Field(min_length=1, max_length=200)
    research: dict[str, Any] = Field(min_length=1)


class Nav(Contract):
    date: date
    balance: Nonnegative


class Trade(Contract):
    date: date
    symbol: str
    action: Literal["BUY", "SELL"]
    quantity: int = Field(gt=0, strict=True)
    price: Annotated[Finite, Field(gt=0)]
    fee: Nonnegative
    tax: Nonnegative
    slippageCost: Nonnegative
    pnl: Finite | None = None
    pnlNet: Finite | None = None
    pnlPercent: Finite | None = None
    priceClose: Finite | None = None
    grossValue: Finite | None = None
    netValue: Finite | None = None


class Action(Contract):
    date: date
    actions: list[Finite]


class Metrics(Contract):
    # Fraction units: 0.10 means 10%; never infer units from magnitude.
    totalReturn: Finite
    maxDrawdown: Annotated[Finite, Field(ge=0, le=1)]
    sharpeRatio: Finite | None
    winRate: Annotated[Finite, Field(ge=0, le=1)] | None
    totalTrades: int = Field(ge=0, strict=True)
    sortinoRatio: Finite | None = None
    cagr: Finite | None = None
    calmarRatio: Finite | None = None
    profitFactor: Nonnegative | None = None
    avgWin: Finite | None = None
    avgLoss: Finite | None = None
    profitableTrades: int | None = Field(default=None, ge=0)
    riskFreeRate: Finite | None = None
    closedTrades: int | None = Field(default=None, ge=0)
    nullReasons: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def explain_nulls(self):
        for key in ("sharpeRatio", "winRate"):
            if getattr(self, key) is None and not self.nullReasons.get(key):
                raise ValueError(f"nullReasons.{key} is required")
        return self


class Evaluation(Contract):
    role: Literal["train", "validation", "test"]
    ratioUnit: Literal["fraction"]
    startDate: date
    endDate: date
    initialCapital: Annotated[Finite, Field(gt=0)]
    transactionFee: Nonnegative
    taxRate: Nonnegative
    slippage: Nonnegative
    settlementDays: int = Field(ge=0)
    metrics: Metrics
    computedMetrics: dict[str, Finite] = Field(default_factory=dict)
    riskProfile: dict[str, Finite | str] = Field(default_factory=dict)
    realizedPnl: Finite | None = None
    unrealizedPnl: Finite | None = None
    dividendIncome: Finite | None = None
    resultFidelity: Literal["exact", "reconstructed"] | None = None
    executionTimeSec: Nonnegative | None = None
    nav: list[Nav] = Field(min_length=2, max_length=20000)
    trades: list[Trade] = Field(max_length=30000)
    actions: list[Action] = Field(min_length=1, max_length=20000)
    terminalPositions: dict[str, Any] = Field(min_length=1)
    baselines: dict[str, Any] = Field(min_length=1)

    @model_validator(mode="after")
    def consistent_evaluation(self):
        if self.endDate < self.startDate:
            raise ValueError("endDate precedes startDate")
        for key in ("nav", "actions"):
            rows = getattr(self, key)
            dates = [r.date for r in rows]
            if dates != sorted(set(dates)):
                raise ValueError(f"{key} dates must be unique and ascending")
        if any(not self.startDate <= r.date <= self.endDate for r in [*self.nav, *self.trades, *self.actions]):
            raise ValueError("evaluation rows outside declared window")
        if self.metrics.totalTrades != len(self.trades):
            raise ValueError("totalTrades must match execution rows")
        if self.metrics.closedTrades is not None:
            closed = [t for t in self.trades if t.action == "SELL" and t.pnlNet is not None]
            wins = sum(t.pnlNet > 0 for t in closed)
            if self.metrics.closedTrades != len(closed) or self.metrics.profitableTrades != wins:
                raise ValueError("Closed trade counts must match realized execution PnL")
            expected_win_rate = wins / len(closed) if closed else None
            if expected_win_rate is None:
                if self.metrics.winRate is not None:
                    raise ValueError("Win rate is undefined without closed trades")
            elif self.metrics.winRate is None or abs(self.metrics.winRate - expected_win_rate) > 1e-6:
                raise ValueError("Win rate must use closed trades as its denominator")
        actual_return = self.nav[-1].balance / self.initialCapital - 1
        if abs(actual_return - self.metrics.totalReturn) > 1e-6:
            raise ValueError("totalReturn does not match final NAV / initial capital")
        peak, drawdown = self.initialCapital, 0.0
        for row in self.nav:
            peak = max(peak, row.balance)
            drawdown = max(drawdown, 1 - row.balance / peak)
        if abs(drawdown - self.metrics.maxDrawdown) > 1e-6:
            raise ValueError("maxDrawdown does not match NAV")
        return self


class Bundle(Contract):
    schemaVersion: Literal[SCHEMA]
    provenance: Provenance
    strategy: Strategy
    model: Model
    evaluation: Evaluation
    inSample: Evaluation | None = None
    artifacts: list[Artifact] = Field(min_length=4, max_length=256)

    @model_validator(mode="after")
    def consistent_bundle(self):
        if sum(a.size for a in self.artifacts) > MAX_TOTAL:
            raise ValueError("bundle exceeds 8 GiB")
        for key in ("id", "path"):
            values = [getattr(a, key) for a in self.artifacts]
            if len(set(values)) != len(values):
                raise ValueError(f"duplicate artifact {key}")
        roles = [a.role for a in self.artifacts]
        required = ["model", "training_metadata", "xai_trace", "xai_card", "xai_manifest", "ohlcv"]
        if self.model.normalization == "obs_rms":
            required.append("normalizer")
        elif "normalizer" in roles:
            raise ValueError("normalizer supplied with normalization=none")
        for role in required:
            if roles.count(role) != 1:
                raise ValueError(f"exactly one {role} artifact is required")
        if self.evaluation.role == "train":
            raise ValueError("Primary evaluation must be validation or test")
        if self.inSample and (self.inSample.role != "train" or self.inSample.endDate >= self.evaluation.startDate):
            raise ValueError("In-sample evaluation must precede the primary evaluation")
        for evaluation in [self.evaluation, *([self.inSample] if self.inSample else [])]:
            if any(t.symbol not in self.model.symbols for t in evaluation.trades):
                raise ValueError("trade symbol outside model universe")
            if any(len(a.actions) != self.model.actionSize for a in evaluation.actions):
                raise ValueError("action vector length differs from actionSize")
        cfg = self.strategy.config
        if cfg.get("stocks") != self.model.symbols:
            raise ValueError("strategy.config.stocks must equal ordered model.symbols")
        # JSON cannot contain NaN/Infinity, including arbitrary config/research blocks.
        json.dumps(self.model_dump(mode="json"), allow_nan=False)
        return self


def load_bundle(path: Path) -> Bundle:
    if path.stat().st_size > MAX_MANIFEST:
        raise ValueError("manifest exceeds 2 MiB")
    return Bundle.model_validate_json(path.read_bytes())


def sha256_file(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def artifact_path(root: Path, relative: str) -> Path:
    root = root.resolve()
    path = root / relative
    if not path.resolve().is_relative_to(root):
        raise ValueError(f"artifact escapes bundle root: {relative}")
    if any(p.is_symlink() for p in [path, *path.parents] if p != root and p.is_relative_to(root)):
        raise ValueError(f"symlinks are not allowed: {relative}")
    if not path.is_file():
        raise ValueError(f"artifact missing: {relative}; run git lfs pull if needed")
    return path


def verify_bundle(root: Path) -> Bundle:
    bundle = load_bundle(root / "manifest.json")
    for artifact in bundle.artifacts:
        path = artifact_path(root, artifact.path)
        if path.stat().st_size != artifact.size or sha256_file(path) != artifact.sha256:
            raise ValueError(f"checksum/size mismatch: {artifact.path}; run git lfs pull if needed")
    return bundle


def fingerprint(bundle: Bundle) -> str:
    # Source layout is a locator, not model identity. Artifact ids remain stable.
    data = bundle.model_dump(mode="json")
    for artifact in data["artifacts"]:
        artifact.pop("path")
    encoded = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(encoded.encode()).hexdigest()
