"""Failure intelligence for test automation.

The implementation is deliberately transparent: rule-based root-cause heuristics
plus TF-IDF/K-Means clustering. It can later be swapped with an LLM/RAG backend.
"""
from __future__ import annotations

import hashlib
import re
from collections import Counter
from typing import Iterable

from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer

from .models import FailureAnalysis, FailureBatchReport, FailureCluster, FailureRecord

PATTERNS = [
    (
        "infrastructure",
        [r"connection refused", r"timed? out", r"host unreachable", r"dns", r"503", r"502", r"network"],
        "Infrastructure or network dependency is unavailable.",
        ["Check service health and network reachability.", "Retry only after dependency readiness is confirmed."],
        "retry_after_readiness_check",
        "medium",
    ),
    (
        "configuration",
        [r"keyerror", r"missing config", r"invalid config", r"schema", r"yaml", r"json decode", r"environment variable"],
        "Configuration or environment-definition defect.",
        ["Validate configuration against schema.", "Compare environment metadata with the last known-good version."],
        "repair_and_revalidate_configuration",
        "medium",
    ),
    (
        "dependency",
        [r"modulenotfounderror", r"importerror", r"version conflict", r"dependency", r"package not found", r"no module named"],
        "Missing or incompatible software dependency.",
        ["Recreate dependencies from a locked manifest.", "Verify package/module availability and version compatibility."],
        "reinstall_dependencies",
        "low",
    ),
    (
        "flaky_test",
        [r"intermittent", r"flaky", r"race condition", r"assert.*sometimes", r"rerun passed"],
        "Potential nondeterministic or flaky test behaviour.",
        ["Run repeated executions with identical seed/configuration.", "Inspect shared state, timing assumptions and race conditions."],
        "rerun_with_same_seed",
        "medium",
    ),
    (
        "resource",
        [r"out of memory", r"oom", r"disk full", r"no space left", r"cpu thrott", r"resource exhausted"],
        "Resource exhaustion or capacity constraint.",
        ["Inspect CPU, memory and disk metrics.", "Increase limits or reduce parallel test load."],
        "scale_resources",
        "high",
    ),
    (
        "application",
        [r"assertionerror", r"nullpointer", r"segmentation fault", r"traceback", r"exception", r"expected .* got"],
        "Application or test logic failure.",
        ["Inspect stack trace and failing assertion.", "Compare inputs and application state with a successful execution."],
        None,
        "high",
    ),
]

def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"0x[0-9a-f]+", "<hex>", text)
    text = re.sub(r"\b\d{2,}\b", "<num>", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def _signature(text: str) -> str:
    normalized = _normalize(text)
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:10]
    return f"sig-{digest}"

def analyze_failure(record: FailureRecord) -> FailureAnalysis:
    text = _normalize(record.log)
    best = None
    best_hits = 0

    for item in PATTERNS:
        category, patterns, cause, remediation, action, risk = item
        hits = sum(bool(re.search(p, text)) for p in patterns)
        if hits > best_hits:
            best_hits = hits
            best = item

    if best is None:
        category = "unknown"
        cause = "No known deterministic failure pattern matched the available log context."
        remediation = [
            "Collect a larger log window and environment metadata.",
            "Compare with historical failures and similar signatures.",
        ]
        action = None
        risk = "high"
        confidence = 0.25
    else:
        category, patterns, cause, remediation, action, risk = best
        confidence = min(0.95, 0.55 + 0.10 * best_hits)
        if record.retry_count > 0 and category == "infrastructure":
            confidence = min(0.98, confidence + 0.05)

    return FailureAnalysis(
        test_name=record.test_name,
        category=category,
        probable_root_cause=cause,
        confidence=round(confidence, 2),
        signature=_signature(record.log),
        remediation=remediation,
        self_heal_action=action,
        risk=risk,
    )

def cluster_failures(records: list[FailureRecord], max_clusters: int = 5) -> list[FailureCluster]:
    if not records:
        return []
    if len(records) == 1:
        return [FailureCluster(
            cluster_id=0, size=1, representative_terms=[], tests=[records[0].test_name]
        )]

    texts = [_normalize(r.log) for r in records]
    vectorizer = TfidfVectorizer(
        stop_words="english", max_features=500, ngram_range=(1, 2), min_df=1
    )
    X = vectorizer.fit_transform(texts)
    n_clusters = max(2, min(max_clusters, len(records)))
    if X.shape[0] < n_clusters:
        n_clusters = X.shape[0]

    model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = model.fit_predict(X)
    terms = vectorizer.get_feature_names_out()

    clusters = []
    for cid in sorted(set(labels)):
        idxs = [i for i, label in enumerate(labels) if label == cid]
        center = model.cluster_centers_[cid]
        top = center.argsort()[::-1][:6]
        rep_terms = [terms[i] for i in top if center[i] > 0]
        clusters.append(FailureCluster(
            cluster_id=int(cid),
            size=len(idxs),
            representative_terms=rep_terms,
            tests=[records[i].test_name for i in idxs],
        ))
    return clusters

def analyze_batch(records: list[FailureRecord]) -> FailureBatchReport:
    analyses = [analyze_failure(r) for r in records]
    clusters = cluster_failures(records)
    counts = dict(Counter(a.category for a in analyses))
    recurring = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    if recurring:
        top_cat, top_count = recurring[0]
        summary = (
            f"Analysed {len(records)} failures. Most frequent category: "
            f"{top_cat} ({top_count}). Generated {len(clusters)} similarity clusters."
        )
    else:
        summary = "No failures supplied."
    return FailureBatchReport(
        analyses=analyses,
        clusters=clusters,
        recurring_categories=counts,
        summary=summary,
    )

def self_heal_plan(analysis: FailureAnalysis) -> dict:
    safe_actions = {
        "retry_after_readiness_check": {
            "action": "readiness_then_retry",
            "automatic": True,
            "guardrail": "Retry only if dependency readiness checks pass.",
        },
        "repair_and_revalidate_configuration": {
            "action": "configuration_repair",
            "automatic": False,
            "guardrail": "Require validation and human approval before deployment.",
        },
        "reinstall_dependencies": {
            "action": "dependency_restore",
            "automatic": False,
            "guardrail": "Use only a trusted locked dependency manifest.",
        },
        "rerun_with_same_seed": {
            "action": "controlled_rerun",
            "automatic": True,
            "guardrail": "Limit retries and preserve identical test inputs.",
        },
        "scale_resources": {
            "action": "resource_adjustment",
            "automatic": False,
            "guardrail": "Require configured resource ceilings and approval.",
        },
    }
    if not analysis.self_heal_action:
        return {
            "supported": False,
            "reason": "No safe predefined self-healing action for this failure category.",
        }
    plan = safe_actions[analysis.self_heal_action]
    return {"supported": True, **plan}
