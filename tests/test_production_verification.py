from envguard.production_verification import (
    ProductionTestResult,
    RequirementSpec,
    match_requirement,
    verify_production_results,
)


def test_exact_and_similarity_matching():
    results = [
        ProductionTestResult(test_id="T1", parameter="output power", value=39.5, unit="dBm"),
        ProductionTestResult(test_id="T2", parameter="EVM RMS", value=2.1, unit="%"),
    ]
    req_exact = RequirementSpec(
        requirement_id="REQ-001",
        parameter="Output Power",
        operator="ge",
        expected=39.0,
        unit="dBm",
        source_document="RadioSpec-A",
    )
    req_similar = RequirementSpec(
        requirement_id="REQ-002",
        parameter="EVM RMS percent",
        operator="le",
        expected=3.0,
        unit="%",
        source_document="RadioSpec-A",
    )
    assert match_requirement(req_exact, results).match_method == "exact"
    assert match_requirement(req_similar, results, similarity_threshold=0.45).test_id == "T2"


def test_detects_known_deviation_and_traceability():
    requirements = [
        RequirementSpec(
            requirement_id="REQ-PWR-01",
            parameter="output power",
            operator="ge",
            expected=40.0,
            unit="dBm",
            source_document="Radio Production Spec",
            source_section="5.2 Tx Power",
        )
    ]
    results = [
        ProductionTestResult(
            test_id="TX-001",
            parameter="output power",
            value=38.4,
            unit="dBm",
        )
    ]
    report = verify_production_results(requirements, results)
    assert report.deviations == 1
    finding = report.findings[0]
    assert finding.result == "deviation"
    assert finding.requirement_id == "REQ-PWR-01"
    assert "5.2 Tx Power" in finding.traceability_ref


def test_detects_missing_and_unit_mismatch():
    requirements = [
        RequirementSpec(
            requirement_id="REQ-1",
            parameter="receiver sensitivity",
            operator="le",
            expected=-100,
            unit="dBm",
            source_document="Spec",
        ),
        RequirementSpec(
            requirement_id="REQ-2",
            parameter="temperature",
            operator="between",
            expected=[-10, 55],
            unit="C",
            source_document="Spec",
        ),
    ]
    results = [
        ProductionTestResult(
            test_id="TEMP-1",
            parameter="temperature",
            value=25,
            unit="F",
        )
    ]
    report = verify_production_results(requirements, results)
    assert report.missing_results == 1
    assert report.unit_mismatches == 1


def test_between_and_tolerance_pass():
    requirements = [
        RequirementSpec(
            requirement_id="REQ-EVM",
            parameter="evm",
            operator="eq",
            expected=2.0,
            tolerance=0.2,
            unit="%",
            source_document="Spec",
        )
    ]
    results = [
        ProductionTestResult(test_id="EVM-1", parameter="evm", value=2.15, unit="%")
    ]
    report = verify_production_results(requirements, results)
    assert report.passed == 1
