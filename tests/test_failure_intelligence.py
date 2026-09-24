from envguard.failure_intelligence import (
    analyze_batch,
    analyze_failure,
    cluster_failures,
    self_heal_plan,
)
from envguard.models import FailureRecord

def test_connection_failure_is_classified():
    record = FailureRecord(
        test_name="api",
        log="Connection refused while calling service after timeout",
        retry_count=1,
    )
    result = analyze_failure(record)
    assert result.category == "infrastructure"
    assert result.confidence >= 0.6
    assert result.self_heal_action == "retry_after_readiness_check"

def test_configuration_failure_is_classified():
    record = FailureRecord(
        test_name="config",
        log="ValidationError: missing config field in YAML schema",
    )
    result = analyze_failure(record)
    assert result.category == "configuration"

def test_self_heal_plan_has_guardrail():
    record = FailureRecord(
        test_name="api",
        log="Connection refused to service",
    )
    analysis = analyze_failure(record)
    plan = self_heal_plan(analysis)
    assert plan["supported"] is True
    assert "guardrail" in plan

def test_batch_clustering_and_summary():
    records = [
        FailureRecord(test_name="a", log="connection refused to api"),
        FailureRecord(test_name="b", log="timeout connecting to api"),
        FailureRecord(test_name="c", log="ModuleNotFoundError: No module named x"),
    ]
    report = analyze_batch(records)
    assert len(report.analyses) == 3
    assert report.clusters
    assert "infrastructure" in report.recurring_categories
