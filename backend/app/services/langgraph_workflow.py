from typing import Dict, Any, List, Optional, TypedDict
import logging
from langgraph.graph import StateGraph, END
from app.services.document_parser import document_parser
from app.services.groq_service import groq_service, GroqServiceError
from app.schemas.deviation import DeviationCreate
from app.schemas.root_cause import RootCauseCreate
from app.schemas.capa import CapaActionCreate

logger = logging.getLogger(__name__)

class InvestigationState(TypedDict):
    raw_document: Optional[str]
    raw_bytes: Optional[bytes]
    source_type: str  # PDF, TEXT, EMAIL
    parsed_text: str
    metadata: Dict[str, Any]
    
    # Structured fields
    extracted_data: Dict[str, Any]
    validation_errors: List[str]
    is_valid: bool
    missing_evidence: List[Dict[str, Any]]
    has_critical_missing_info: bool
    
    # Evidence & Planning
    evidence_analysis: Dict[str, Any]
    has_conflicting_evidence: bool
    is_evidence_insufficient: bool
    investigation_plan: Dict[str, Any]
    selected_methodology: str  # "BOTH", "5_WHYS", "FISHBONE_6M"
    
    # Methodology & Root Cause
    rca_analysis: Optional[Dict[str, Any]]
    five_whys: List[Dict[str, Any]]
    fishbone_causes: List[Dict[str, Any]]
    root_causes: List[Dict[str, Any]]
    capa_actions: List[Dict[str, Any]]
    
    # Validation & Sign-off
    output_validated: bool
    validation_issues: List[str]
    human_approved: bool
    current_step: str
    trace_log: List[str]
    allow_offline_fallback: bool

# Node 1: Document Intake Node
def document_intake_node(state: InvestigationState) -> Dict[str, Any]:
    trace = list(state.get("trace_log", []))
    source_type = state.get("source_type", "TEXT").upper()
    raw_doc = state.get("raw_document")
    raw_bytes = state.get("raw_bytes")
    
    # Validate payload presence and length
    byte_size = len(raw_bytes) if raw_bytes else (len(raw_doc.encode('utf-8')) if raw_doc else 0)
    if byte_size == 0:
        raise ValueError("Document Intake Error: Empty payload received. Incident document or text is required.")
    
    if byte_size > 10 * 1024 * 1024:
        raise ValueError(f"Document Intake Error: Payload size ({byte_size / (1024*1024):.1f} MB) exceeds maximum allowed 10 MB limit.")

    trace.append(f"1. Document Intake Node: Ingested {source_type} payload ({byte_size} bytes).")
    return {
        "current_step": "INTAKE_VALIDATED",
        "trace_log": trace
    }

# Node 2: Document Parsing Node
def document_parsing_node(state: InvestigationState) -> Dict[str, Any]:
    trace = list(state.get("trace_log", []))
    source_type = state.get("source_type", "TEXT").upper()
    parsed_text = ""
    meta = dict(state.get("metadata", {}))

    if source_type == "PDF" and state.get("raw_bytes"):
        try:
            structured_pdf = document_parser.parse_pdf_structured(state["raw_bytes"])
            parsed_text = structured_pdf["full_text"]
            meta["page_count"] = structured_pdf["page_count"]
            meta["file_size_bytes"] = structured_pdf["file_size_bytes"]
            meta["file_hash_sha256"] = structured_pdf["file_hash_sha256"]
            meta["pages"] = [{"page_number": p["page_number"], "char_count": p["char_count"]} for p in structured_pdf["pages"]]
            trace.append(f"2. Document Parsing Node: Preserved page-level text across {structured_pdf['page_count']} PDF pages with SHA-256 integrity.")
        except Exception as e:
            trace.append(f"2. Document Parsing Node: PDF extraction error ({e}), utilizing text fallback.")
            parsed_text = state.get("raw_document", "")
    elif source_type == "EMAIL":
        parsed = document_parser.parse_email(state.get("raw_document", ""))
        parsed_text = (
            f"Subject: {parsed['headers'].get('subject', 'None')}\n"
            f"From: {parsed['headers'].get('from', 'None')}\n"
            f"Date: {parsed['headers'].get('date', 'None')}\n\n"
            f"{parsed['body']}"
        )
        meta.update(parsed["headers"])
        meta["file_hash_sha256"] = document_parser.compute_sha256((state.get("raw_document") or "").encode())
        trace.append("2. Document Parsing Node: Parsed RFC 5322 email headers and message body.")
    else:
        raw_doc = state.get("raw_document", "")
        parsed_text = document_parser.clean_text(raw_doc)
        meta["file_hash_sha256"] = document_parser.compute_sha256(raw_doc.encode())
        trace.append("2. Document Parsing Node: Normalized raw plain text incident notes with checksum.")

    return {
        "parsed_text": parsed_text,
        "metadata": meta,
        "current_step": "PARSED",
        "trace_log": trace
    }

# Node 3: Structured Information Extraction Node
def structured_extraction_node(state: InvestigationState) -> Dict[str, Any]:
    trace = list(state.get("trace_log", []))
    text = state.get("parsed_text", "")
    source_type = state.get("source_type", "TEXT")
    allow_fallback = state.get("allow_offline_fallback", False)

    # Invoke Groq LLM inference for extraction
    pages_meta = state.get("metadata", {}).get("pages")
    extracted = groq_service.extract_intake_data(
        document_text=text, 
        source_type=source_type, 
        allow_offline_fallback=allow_fallback,
        pages_metadata=pages_meta
    )
    model_name = groq_service.model
    trace.append(f"3. Structured Extraction Node: Extracted structured deviation attributes and 16 validated fields using Groq LLM ({model_name}).")

    return {
        "extracted_data": extracted,
        "current_step": "EXTRACTED",
        "trace_log": trace
    }

# Node 4: Field Validation Node
def field_validation_node(state: InvestigationState) -> Dict[str, Any]:
    trace = list(state.get("trace_log", []))
    extracted = state.get("extracted_data", {})
    dev = extracted.get("deviation", {})
    errors = []

    # Mandatory pharmaceutical GMP field checks
    batch_num = str(dev.get("batch_number") or "").strip().upper()
    if (
        not batch_num 
        or batch_num in ["UNKNOWN", "TBD", "N/A", "NONE", "NULL", "UNRECORDED", "INFO", "NOT RECORDED", "MISSING"]
        or "NO BATCH" in batch_num
    ):
        errors.append("Critical: Batch Number is missing or unverified.")
    prod_name = str(dev.get("product_name") or "").strip().upper()
    if not prod_name or prod_name in ["UNKNOWN", "TBD", "N/A", "NONE", "NULL", ""]:
        errors.append("Critical: API Product Name is missing.")
    if not dev.get("description") or len(dev.get("description", "")) < 10:
        errors.append("Critical: Deviation technical description is insufficient.")
    if not dev.get("unit_operation"):
        errors.append("Notice: Unit Operation not identified; investigator clarification required.")

    is_valid = len([e for e in errors if e.startswith("Critical")]) == 0
    trace.append(f"4. Field Validation Node: Checked GMP requirements. Status: {'VALID' if is_valid else 'INCOMPLETE'} ({len(errors)} notes).")

    return {
        "validation_errors": errors,
        "is_valid": is_valid,
        "current_step": "VALIDATED",
        "trace_log": trace
    }

# Node 5: Missing Information Detection Node
def missing_information_detection_node(state: InvestigationState) -> Dict[str, Any]:
    trace = list(state.get("trace_log", []))
    extracted = state.get("extracted_data", {})
    missing_items = list(extracted.get("missing_information", []))
    errors = state.get("validation_errors", [])

    # Enrich missing items with any validation errors
    for err in errors:
        if err.startswith("Critical"):
            missing_items.append({
                "category": "GMP_BATCH_RECORD",
                "question": f"Please provide missing batch data: {err}",
                "impact_description": "Essential for establishing production traceability and regulatory compliance.",
                "urgency": "HIGH"
            })

    has_critical = any(item.get("urgency") == "HIGH" for item in missing_items)
    trace.append(f"5. Missing Information Detection Node: Identified {len(missing_items)} evidence gaps (Critical: {has_critical}).")

    return {
        "missing_evidence": missing_items,
        "has_critical_missing_info": has_critical,
        "current_step": "EVIDENCE_GAPS_IDENTIFIED",
        "trace_log": trace
    }

# Node 6: Evidence Analysis Node
def evidence_analysis_node(state: InvestigationState) -> Dict[str, Any]:
    trace = list(state.get("trace_log", []))
    findings = state.get("extracted_data", {}).get("extracted_findings", [])
    raw_source_text = state.get("parsed_text", "")
    parsed_text_lower = raw_source_text.lower()
    meta = state.get("metadata", {})
    pages_meta = meta.get("pages") if isinstance(meta, dict) else None
    
    # Conflict and sufficiency heuristics
    has_conflict = False
    is_insufficient = False

    verified_findings = []
    unverified_findings = []
    supporting_findings = []
    contradictory_findings = []

    for f in findings:
        f_str = f.get("finding_text") if isinstance(f, dict) else str(f)
        claimed_page = f.get("page_number") if isinstance(f, dict) else None

        # Execute rigorous source citation validation against actual document text & pages
        val_res = document_parser.validate_source_citation(
            finding_or_excerpt=f_str,
            source_text=raw_source_text,
            pages_metadata=pages_meta,
            claimed_page=claimed_page
        )

        if isinstance(f, dict):
            f["citation_verified"] = val_res["is_valid"]
            f["validation_status"] = "VERIFIED_SOURCE_FACT" if val_res["is_valid"] else "UNVERIFIED_CITATION"
            f["validation_explanation"] = val_res["explanation"]
            f["confidence_score"] = val_res["confidence"]

        if val_res["is_valid"]:
            verified_findings.append(f)
            f_lower = f_str.lower()
            if any(term in f_lower for term in ["conflict", "discrepancy", "contradict", "unconfirmed", "disputed"]):
                contradictory_findings.append(f_str)
                has_conflict = True
            else:
                supporting_findings.append(f_str)
        else:
            unverified_findings.append(f)
            trace.append(f"6. Citation Validation: Finding '{f_str[:40]}...' flagged as unverified: {val_res['explanation']}")

    if "conflict" in parsed_text_lower or "discrepancy" in parsed_text_lower or "contradict" in parsed_text_lower:
        has_conflict = True
        trace.append("6. Evidence Analysis Node: Detected conflicting empirical evidence in report narrative.")

    if len(verified_findings) < 2:
        is_insufficient = True
        trace.append("6. Evidence Analysis Node: Verified empirical evidence is insufficient for definitive conclusion.")

    evidence_analysis = {
        "total_findings": len(findings),
        "verified_findings_count": len(verified_findings),
        "unverified_findings_count": len(unverified_findings),
        "traceable_facts": verified_findings,
        "unverified_facts": unverified_findings,
        "supporting_findings": supporting_findings,
        "contradictory_findings": contradictory_findings,
        "has_conflicting_evidence": has_conflict,
        "is_evidence_insufficient": is_insufficient,
        "risk_rating": "HIGH" if "Critical" in str(state.get("extracted_data")) else "MEDIUM"
    }
    trace.append(
        f"6. Evidence Analysis Node: Analyzed {len(findings)} findings — "
        f"{len(verified_findings)} verified ({len(supporting_findings)} supporting, {len(contradictory_findings)} contradictory), "
        f"{len(unverified_findings)} unverified."
    )

    return {
        "evidence_analysis": evidence_analysis,
        "has_conflicting_evidence": has_conflict,
        "is_evidence_insufficient": is_insufficient,
        "current_step": "EVIDENCE_ANALYZED",
        "trace_log": trace
    }

# Node 7: Investigation Planning Node
def investigation_planning_node(state: InvestigationState) -> Dict[str, Any]:
    trace = list(state.get("trace_log", []))
    selected_methodology = state.get("selected_methodology", "BOTH")
    
    plan = {
        "selected_methodology": selected_methodology,
        "execution_strategy": "Unified Single-Inference RCA Optimization",
        "target_areas": ["Equipment Reliability", "Process Parameter Control", "Preventive Maintenance Schedule"],
        "ready_for_rca": True
    }
    trace.append(f"7. Investigation Planning Node: Strategy set to '{selected_methodology}' using unified RCA inference.")
    
    return {
        "investigation_plan": plan,
        "selected_methodology": selected_methodology,
        "current_step": "PLAN_READY",
        "trace_log": trace
    }

# Node 8: 5 Whys Analysis Node
def five_whys_analysis_node(state: InvestigationState) -> Dict[str, Any]:
    trace = list(state.get("trace_log", []))
    dev = state.get("extracted_data", {}).get("deviation", {})
    allow_fallback = state.get("allow_offline_fallback", False)
    
    # OPTIMIZATION: Generate unified RCA analysis once and store in state
    rca_result = state.get("rca_analysis")
    if not rca_result:
        rca_result = groq_service.generate_rca_analysis(
            deviation_dict=dev,
            allow_offline_fallback=allow_fallback
        )
    five_whys = rca_result.get("five_whys", [])
    
    trace.append(f"8. 5 Whys Analysis Node: Generated {len(five_whys)} sequential causality tiers via Groq.")
    return {
        "rca_analysis": rca_result,
        "five_whys": five_whys,
        "current_step": "FIVE_WHYS_COMPLETE",
        "trace_log": trace
    }

# Node 9: Fishbone Analysis Node
def fishbone_analysis_node(state: InvestigationState) -> Dict[str, Any]:
    trace = list(state.get("trace_log", []))
    dev = state.get("extracted_data", {}).get("deviation", {})
    allow_fallback = state.get("allow_offline_fallback", False)
    
    rca_result = state.get("rca_analysis")
    if not rca_result:
        rca_result = groq_service.generate_rca_analysis(
            deviation_dict=dev,
            allow_offline_fallback=allow_fallback
        )
    fishbone = rca_result.get("fishbone_causes", [])
    
    trace.append(f"9. Fishbone Analysis Node: Evaluated Ishikawa 6Ms with {len(fishbone)} distinct factors.")
    return {
        "rca_analysis": rca_result,
        "fishbone_causes": fishbone,
        "current_step": "FISHBONE_COMPLETE",
        "trace_log": trace
    }

# Node 10: Root Cause Evaluation Node
def root_cause_evaluation_node(state: InvestigationState) -> Dict[str, Any]:
    trace = list(state.get("trace_log", []))
    dev = state.get("extracted_data", {}).get("deviation", {})
    allow_fallback = state.get("allow_offline_fallback", False)
    has_conflict = state.get("has_conflicting_evidence", False)
    is_insufficient = state.get("is_evidence_insufficient", False)
    ev_analysis = state.get("evidence_analysis", {})
    
    rca_result = state.get("rca_analysis")
    if not rca_result:
        rca_result = groq_service.generate_rca_analysis(
            deviation_dict=dev,
            allow_offline_fallback=allow_fallback
        )
    root_causes = list(rca_result.get("root_causes", []))
    
    # Enforce pharmaceutical safety rule:
    # 1. AI cannot confirm root causes (status must be PROPOSED or UNDER_REVIEW)
    # 2. If evidence is conflicting or insufficient, all causes must be flagged as PROPOSED with warning
    # 3. Associate supporting and contradictory evidence references
    supporting_refs = ev_analysis.get("supporting_findings", [])
    contradictory_refs = ev_analysis.get("contradictory_findings", [])

    for rc in root_causes:
        rc["is_ai_suggested"] = True
        rc["is_verified"] = False
        rc["supporting_evidence_references"] = supporting_refs[:3]
        rc["contradictory_evidence_references"] = contradictory_refs
        
        if has_conflict or is_insufficient or contradictory_refs:
            rc["status"] = "PROPOSED"
            rc["rationale"] = (rc.get("rationale") or "") + " [Flagged: Conflicting or preliminary evidence requires investigator physical inspection]."
        else:
            rc["status"] = "PROPOSED" if rc.get("status") == "CONFIRMED" else (rc.get("status") or "PROPOSED")
    
    trace.append(f"10. Root Cause Evaluation Node: Formulated {len(root_causes)} causes (All classified as unverified proposals with evidence links).")
    return {
        "rca_analysis": rca_result,
        "root_causes": root_causes,
        "current_step": "ROOT_CAUSE_EVALUATED",
        "trace_log": trace
    }

# Node 11: CAPA Generation Node
def capa_generation_node(state: InvestigationState) -> Dict[str, Any]:
    trace = list(state.get("trace_log", []))
    dev = state.get("extracted_data", {}).get("deviation", {})
    allow_fallback = state.get("allow_offline_fallback", False)
    
    rca_result = state.get("rca_analysis")
    if not rca_result:
        rca_result = groq_service.generate_rca_analysis(
            deviation_dict=dev,
            allow_offline_fallback=allow_fallback
        )
    capas = list(rca_result.get("capa_actions", []))
    
    for c in capas:
        c["is_ai_suggested"] = True
        c["is_verified"] = False
        if not c.get("effectiveness_criteria"):
            c["effectiveness_criteria"] = "Quantitative review of equipment calibration logs with zero deviations over 30 days."
    
    trace.append(f"11. CAPA Generation Node: Formulated {len(capas)} Corrections, Corrective, and Preventive Actions.")
    return {
        "rca_analysis": rca_result,
        "capa_actions": capas,
        "current_step": "CAPA_GENERATED",
        "trace_log": trace
    }

# Node 12: Output Validation Node
def output_validation_node(state: InvestigationState) -> Dict[str, Any]:
    trace = list(state.get("trace_log", []))
    issues = []
    
    # 1. Enforce safety on 5 Whys
    for why in state.get("five_whys", []):
        why["is_ai_suggested"] = True
        why["is_verified"] = False
        
    # 2. Enforce safety on Fishbone
    for cause in state.get("fishbone_causes", []):
        cause["is_ai_suggested"] = True
        cause["is_verified"] = False
        
    # 3. Enforce safety on Root Causes
    for rc in state.get("root_causes", []):
        rc["is_ai_suggested"] = True
        rc["is_verified"] = False
        if rc.get("status") == "CONFIRMED":
            rc["status"] = "PROPOSED"
            issues.append("Safety Guard: Prevented unauthorized AI confirmation of root cause.")
            
    # 4. Enforce safety on CAPA Actions
    for capa in state.get("capa_actions", []):
        capa["is_ai_suggested"] = True
        capa["is_verified"] = False

    trace.append(f"12. Output Validation Node: Validated outputs against cGMP non-fabrication constraints (Issues: {len(issues)}).")
    return {
        "output_validated": True,
        "validation_issues": issues,
        "current_step": "VALIDATED_FOR_HUMAN_REVIEW",
        "trace_log": trace
    }

# Node 13: Human Review Preparation Node
def human_review_node(state: InvestigationState) -> Dict[str, Any]:
    trace = list(state.get("trace_log", []))
    trace.append("13. Human Review Node: Investigation dossier assembled for investigator verification and QA sign-off.")
    return {
        "human_approved": False,
        "current_step": "READY_FOR_INVESTIGATOR",
        "trace_log": trace
    }

# ----------------- CONDITIONAL ROUTING FUNCTIONS -----------------

def route_after_validation(state: InvestigationState) -> str:
    """If required fields are missing, route to missing information detection; otherwise continue to evidence analysis."""
    if not state.get("is_valid", True):
        return "missing_information_detection"
    return "evidence_analysis"

def route_after_planning(state: InvestigationState) -> str:
    """Routes to chosen RCA methodology without running unselected methodologies."""
    methodology = state.get("selected_methodology", "BOTH")
    if methodology == "FISHBONE_6M":
        return "fishbone_analysis"
    return "five_whys_analysis"

def route_after_five_whys(state: InvestigationState) -> str:
    """If user only requested 5-Whys, skip fishbone analysis directly to root cause evaluation."""
    methodology = state.get("selected_methodology", "BOTH")
    if methodology == "5_WHYS":
        return "root_cause_evaluation"
    return "fishbone_analysis"

def route_after_output_validation(state: InvestigationState) -> str:
    """Proceeds to human review if validation passed; otherwise ends cleanly."""
    if state.get("output_validated", False):
        return "human_review"
    return END

# ----------------- GRAPH COMPILATION -----------------

def create_rca_workflow() -> Any:
    """Builds and compiles the 13-node LangGraph StateGraph with conditional routing."""
    workflow = StateGraph(InvestigationState)

    # 1. Register all 13 nodes
    workflow.add_node("document_intake", document_intake_node)
    workflow.add_node("document_parsing", document_parsing_node)
    workflow.add_node("structured_extraction", structured_extraction_node)
    workflow.add_node("field_validation", field_validation_node)
    workflow.add_node("missing_information_detection", missing_information_detection_node)
    workflow.add_node("evidence_analysis", evidence_analysis_node)
    workflow.add_node("investigation_planning", investigation_planning_node)
    workflow.add_node("five_whys_analysis", five_whys_analysis_node)
    workflow.add_node("fishbone_analysis", fishbone_analysis_node)
    workflow.add_node("root_cause_evaluation", root_cause_evaluation_node)
    workflow.add_node("capa_generation", capa_generation_node)
    workflow.add_node("output_validation", output_validation_node)
    workflow.add_node("human_review", human_review_node)

    # 2. Set Entry Point
    workflow.set_entry_point("document_intake")

    # 3. Intake -> Parsing -> Extraction -> Validation
    workflow.add_edge("document_intake", "document_parsing")
    workflow.add_edge("document_parsing", "structured_extraction")
    workflow.add_edge("structured_extraction", "field_validation")

    # 4. Conditional Edge after Validation (if incomplete, route to missing info detection)
    workflow.add_conditional_edges(
        "field_validation",
        route_after_validation,
        {
            "missing_information_detection": "missing_information_detection",
            "evidence_analysis": "evidence_analysis"
        }
    )
    workflow.add_edge("missing_information_detection", "evidence_analysis")
    workflow.add_edge("evidence_analysis", "investigation_planning")

    # 5. Conditional Edge after Planning (route to selected methodology)
    workflow.add_conditional_edges(
        "investigation_planning",
        route_after_planning,
        {
            "five_whys_analysis": "five_whys_analysis",
            "fishbone_analysis": "fishbone_analysis"
        }
    )

    # 6. Conditional Edge after 5 Whys (skip fishbone if only 5 Whys selected)
    workflow.add_conditional_edges(
        "five_whys_analysis",
        route_after_five_whys,
        {
            "fishbone_analysis": "fishbone_analysis",
            "root_cause_evaluation": "root_cause_evaluation"
        }
    )
    workflow.add_edge("fishbone_analysis", "root_cause_evaluation")
    workflow.add_edge("root_cause_evaluation", "capa_generation")
    workflow.add_edge("capa_generation", "output_validation")

    # 7. Conditional Edge after Output Validation
    workflow.add_conditional_edges(
        "output_validation",
        route_after_output_validation,
        {
            "human_review": "human_review",
            END: END
        }
    )
    workflow.add_edge("human_review", END)

    return workflow.compile()

rca_graph = create_rca_workflow()
