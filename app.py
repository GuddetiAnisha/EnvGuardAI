import json
from pathlib import Path
import yaml
import streamlit as st

from envguard.validator import validate_environment
from envguard.repair import repair_environment
from envguard.orchestrator import orchestrate
from envguard.failure_intelligence import analyze_batch, analyze_failure, self_heal_plan
from envguard.models import FailureRecord

st.set_page_config(page_title="EnvGuardAI", layout="wide")
st.title("EnvGuardAI")
st.caption(
    "Data-quality validation, test-environment orchestration, "
    "failure analysis and guarded self-healing recommendations."
)

tab1, tab2 = st.tabs(["Environment Orchestration", "Failure Intelligence"])

with tab1:
    default_path = Path("configs/invalid_environment.yaml")
    default_text = default_path.read_text(encoding="utf-8") if default_path.exists() else "services: []"

    text = st.text_area("Environment definition (YAML)", default_text, height=420)
    live_checks = st.checkbox("Run live network readiness checks", value=False)

    c1, c2, c3 = st.columns(3)
    try:
        payload = yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        st.error(f"Invalid YAML syntax: {exc}")
        st.stop()

    with c1:
        if st.button("Validate", use_container_width=True):
            result = validate_environment(payload)
            st.session_state["result"] = {"mode": "validate", "data": result.model_dump()}

    with c2:
        if st.button("Repair", use_container_width=True):
            repaired, actions = repair_environment(payload)
            st.session_state["result"] = {
                "mode": "repair",
                "data": {"repaired": repaired, "actions": actions},
            }

    with c3:
        if st.button("Orchestrate", use_container_width=True):
            report = orchestrate(payload, live_checks=live_checks, auto_repair=True)
            st.session_state["result"] = {"mode": "orchestrate", "data": report.model_dump()}

    if "result" in st.session_state:
        data = st.session_state["result"]["data"]
        st.subheader(st.session_state["result"]["mode"].title())
        if isinstance(data, dict) and "validation" in data:
            v = data["validation"]
            a, b = st.columns(2)
            a.metric("Data quality score", f"{v['quality_score']:.1f}/100")
            ready = data.get("readiness", {})
            b.metric("Readiness score", f"{ready.get('score', 0):.1f}/100" if ready else "N/A")
            if v.get("issues"):
                st.subheader("Validation issues")
                st.dataframe(v["issues"], use_container_width=True)
            if ready:
                st.subheader("Readiness checks")
                st.dataframe(ready["checks"], use_container_width=True)
            st.info(data["recommendation"])
        st.json(data)

with tab2:
    sample_path = Path("configs/sample_failures.json")
    default_failures = sample_path.read_text(encoding="utf-8") if sample_path.exists() else "[]"
    raw = st.text_area("Failed test executions (JSON)", default_failures, height=360)

    try:
        failure_payload = json.loads(raw)
        records = [FailureRecord.model_validate(x) for x in failure_payload]
    except Exception as exc:
        st.error(f"Invalid failure dataset: {exc}")
        records = []

    left, right = st.columns(2)

    with left:
        if st.button("Analyse Failures", use_container_width=True, disabled=not records):
            report = analyze_batch(records)
            st.session_state["failure_report"] = report.model_dump()

    with right:
        selected = st.selectbox(
            "Inspect one test",
            [r.test_name for r in records] if records else ["No failures loaded"],
        )

    if records and selected != "No failures loaded":
        rec = next(r for r in records if r.test_name == selected)
        analysis = analyze_failure(rec)
        plan = self_heal_plan(analysis)

        a, b, c = st.columns(3)
        a.metric("Category", analysis.category)
        b.metric("Confidence", f"{analysis.confidence:.0%}")
        c.metric("Risk", analysis.risk.upper())
        st.write("**Probable root cause:**", analysis.probable_root_cause)
        st.write("**Failure signature:**", analysis.signature)
        st.write("**Recommended remediation:**")
        for item in analysis.remediation:
            st.write(f"- {item}")
        st.write("**Self-healing plan:**")
        st.json(plan)

    if "failure_report" in st.session_state:
        report = st.session_state["failure_report"]
        st.subheader("Batch Summary")
        st.info(report["summary"])
        st.subheader("Failure Categories")
        st.bar_chart(report["recurring_categories"])
        st.subheader("Failure Analyses")
        st.dataframe(report["analyses"], use_container_width=True)
        st.subheader("Similarity Clusters")
        st.dataframe(report["clusters"], use_container_width=True)
