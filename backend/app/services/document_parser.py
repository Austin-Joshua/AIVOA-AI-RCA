import io
import re
import hashlib
from typing import Dict, Any, Tuple, List, Optional
import pypdf
import logging

logger = logging.getLogger(__name__)

class DocumentParserService:
    @staticmethod
    def compute_sha256(data: bytes) -> str:
        """Calculate SHA-256 checksum for audit and integrity verification."""
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def extract_text_from_pdf(file_bytes: bytes) -> Tuple[str, Dict[str, Any]]:
        """Extract text and metadata from a PDF file (backwards-compatible tuple format)."""
        try:
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            text_parts = []
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                text_parts.append(f"--- Page {i+1} ---\n{page_text}")
            
            full_text = "\n\n".join(text_parts)
            metadata = {
                "num_pages": len(reader.pages),
                "title": reader.metadata.title if reader.metadata else None,
                "author": reader.metadata.author if reader.metadata else None,
            }
            return full_text.strip(), metadata
        except Exception as e:
            logger.error(f"Error parsing PDF: {e}")
            raise ValueError(f"Failed to parse PDF document: {str(e)}")

    @classmethod
    def parse_pdf_structured(cls, file_bytes: bytes) -> Dict[str, Any]:
        """
        Extract page-level structured text, page numbers, and document metadata.
        Exposes:
        - pages: List of {'page_number': int, 'text': str, 'char_count': int}
        - full_text: complete concatenated text
        - page_count: total pages
        - file_size_bytes: length in bytes
        - file_hash_sha256: SHA-256 hex digest
        - metadata: document metadata dictionary
        """
        try:
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            pages: List[Dict[str, Any]] = []
            text_parts = []

            for i, page in enumerate(reader.pages):
                page_num = i + 1
                raw_page_text = page.extract_text() or ""
                cleaned_page_text = cls.clean_text(raw_page_text)
                pages.append({
                    "page_number": page_num,
                    "text": cleaned_page_text,
                    "char_count": len(cleaned_page_text)
                })
                text_parts.append(f"--- Page {page_num} ---\n{cleaned_page_text}")

            full_text = "\n\n".join(text_parts).strip()
            sha256_hash = cls.compute_sha256(file_bytes)

            return {
                "pages": pages,
                "full_text": full_text,
                "page_count": len(reader.pages),
                "file_size_bytes": len(file_bytes),
                "file_hash_sha256": sha256_hash,
                "metadata": {
                    "num_pages": len(reader.pages),
                    "title": reader.metadata.title if reader.metadata else None,
                    "author": reader.metadata.author if reader.metadata else None,
                }
            }
        except Exception as e:
            logger.error(f"Error parsing PDF structured: {e}")
            raise ValueError(f"Failed to parse PDF document: {str(e)}")

    @staticmethod
    def parse_email(raw_text: str) -> Dict[str, str]:
        """Extract header fields (Subject, From, Date, To) and body from email-formatted text."""
        headers = {}
        body = raw_text

        subject_match = re.search(r"Subject:\s*(.+)", raw_text, re.IGNORECASE)
        from_match = re.search(r"From:\s*(.+)", raw_text, re.IGNORECASE)
        date_match = re.search(r"Date:\s*(.+)", raw_text, re.IGNORECASE)
        to_match = re.search(r"To:\s*(.+)", raw_text, re.IGNORECASE)

        if subject_match:
            headers["subject"] = subject_match.group(1).strip()
        if from_match:
            headers["from"] = from_match.group(1).strip()
        if date_match:
            headers["date"] = date_match.group(1).strip()
        if to_match:
            headers["to"] = to_match.group(1).strip()

        # Split headers from body if possible
        header_delimiter_match = re.search(r"\n\s*\n", raw_text)
        if header_delimiter_match and (subject_match or from_match):
            body = raw_text[header_delimiter_match.end():].strip()

        return {
            "headers": headers,
            "body": body,
            "raw": raw_text
        }

    @staticmethod
    def clean_text(text: str) -> str:
        """Normalize line breaks and clean whitespace."""
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # Replace 3 or more consecutive newlines with 2
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @staticmethod
    def validate_source_citation(
        finding_or_excerpt: Any, 
        source_text: str, 
        pages_metadata: Optional[List[Dict[str, Any]]] = None,
        claimed_page: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Rigorous citation and factual grounding validator for pharmaceutical RCA evidence.
        Validates:
        - Exact substring matches for verbatim quotes
        - Normalized span matches for continuous text
        - Embedded quote integrity: disallows fabricating assertions around real quotes
        - Entity/numeric parameter integrity (temperatures, batch numbers, units)
        - Page-level source alignment across multi-page documents
        Only EXACT or NORMALIZED_SPAN matches qualify as valid citations (is_valid=True).
        Token overlap alone does NOT validate as a source fact.
        """
        if isinstance(finding_or_excerpt, dict):
            text_to_check = finding_or_excerpt.get("finding_text") or finding_or_excerpt.get("text", "")
            page_ref = finding_or_excerpt.get("page_number") or claimed_page
        else:
            text_to_check = str(finding_or_excerpt)
            page_ref = claimed_page

        if not text_to_check or not source_text:
            return {
                "is_valid": False,
                "match_type": "NONE",
                "page_verified": False,
                "confidence": 0.0,
                "explanation": "Empty finding text or empty source document."
            }

        text_clean = text_to_check.strip()
        source_clean = source_text.strip()
        
        # 1. Check for fabricated quotation or ungrounded claims surrounding quotes
        quote_matches = re.findall(r'["\']([^"\']{4,})["\']', text_clean)
        for quote in quote_matches:
            if quote.lower() not in source_clean.lower():
                return {
                    "is_valid": False,
                    "match_type": "NONE",
                    "page_verified": False,
                    "confidence": 0.0,
                    "explanation": f"Fabricated quotation detected: quoted excerpt '{quote}' does not exist in source text."
                }
        
        # If text contains quotes, inspect the surrounding prose outside quotes
        if quote_matches:
            outside_text = re.sub(r'["\'][^"\']+["\']', ' ', text_clean)
            outside_words = [
                w.lower() for w in re.findall(r"\b[A-Za-z0-9_-]{3,}\b", outside_text)
                if w.lower() not in {"the", "and", "for", "was", "with", "that", "from", "this", "were", "been", "page", "excerpt", "finding", "note", "ref", "label", "value"}
            ]
            missing_outside = [w for w in outside_words if w not in source_clean.lower()]
            if missing_outside:
                return {
                    "is_valid": False,
                    "match_type": "EMBEDDED_FABRICATION",
                    "page_verified": False,
                    "confidence": 0.3,
                    "explanation": f"Ungrounded interpretation surrounding quotation: words {missing_outside[:4]} do not appear in source document."
                }

        # 2. Extract key critical metrics (numbers with units, batch IDs, percentages)
        metrics = re.findall(r"\b\d+(?:\.\d+)?\s*(?:°?C|%|rpm|kg|g|L|ml|bar|psi|mins?|hours?)\b", text_clean, re.IGNORECASE)
        for m in metrics:
            m_clean = re.sub(r"\s+", "", m.lower())
            src_clean_nospace = re.sub(r"\s+", "", source_clean.lower())
            if m.lower() not in source_clean.lower() and m_clean not in src_clean_nospace:
                return {
                    "is_valid": False,
                    "match_type": "NONE",
                    "page_verified": False,
                    "confidence": 0.2,
                    "explanation": f"Numeric parameter mismatch: value '{m}' not grounded in source text."
                }

        # 3. Exact continuous substring check
        if text_clean.lower() in source_clean.lower():
            match_type = "EXACT"
            confidence = 1.0
            is_valid = True
            explanation = "Exact continuous substring match verified in source document."
        else:
            # 4. Normalized whitespace check
            norm_needle = re.sub(r"\s+", " ", text_clean).lower()
            norm_haystack = re.sub(r"\s+", " ", source_clean).lower()
            if norm_needle in norm_haystack:
                match_type = "NORMALIZED_SPAN"
                confidence = 0.95
                is_valid = True
                explanation = "Normalized continuous span match verified in source document."
            else:
                # 5. Non-continuous text / Token overlap: Token overlap does NOT qualify as verified source citation
                tokens = [t.lower() for t in re.findall(r"\b[A-Za-z0-9_-]{3,}\b", text_clean)]
                if not tokens:
                    return {
                        "is_valid": False,
                        "match_type": "NONE",
                        "page_verified": False,
                        "confidence": 0.0,
                        "explanation": "No significant alphanumeric tokens found in finding."
                    }
                matched_count = sum(1 for t in tokens if t in norm_haystack)
                ratio = matched_count / len(tokens)
                return {
                    "is_valid": False,
                    "match_type": "TOKEN_OVERLAP" if ratio >= 0.75 else "NONE",
                    "page_verified": False,
                    "confidence": round(ratio * 0.5, 2),
                    "explanation": f"Ungrounded citation: finding is not a continuous span or verbatim quote in source document (token overlap: {int(ratio*100)}%). Classify as AI_INFERENCE or investigator observation."
                }

        # 6. Page-level verification if page metadata is available
        page_verified = False
        if pages_metadata:
            target_page_idx = (int(page_ref) - 1) if page_ref else None
            # Check if text is on the claimed page
            if target_page_idx is not None and 0 <= target_page_idx < len(pages_metadata):
                page_text = pages_metadata[target_page_idx].get("text", "").lower()
                norm_page_text = re.sub(r"\s+", " ", page_text)
                if text_clean.lower() in page_text or re.sub(r"\s+", " ", text_clean).lower() in norm_page_text:
                    page_verified = True
                else:
                    # Search if it actually appears on a different page
                    actual_page = None
                    for p_idx, p_data in enumerate(pages_metadata):
                        p_t = p_data.get("text", "").lower()
                        if text_clean.lower() in p_t or re.sub(r"\s+", " ", text_clean).lower() in re.sub(r"\s+", " ", p_t):
                            actual_page = p_idx + 1
                            break
                    if actual_page is not None and actual_page != page_ref:
                        return {
                            "is_valid": False,
                            "match_type": match_type,
                            "page_verified": False,
                            "confidence": confidence,
                            "explanation": f"Page reference mismatch: citation claimed Page {page_ref}, but text is actually located on Page {actual_page}."
                        }
                    else:
                        page_verified = False
            elif target_page_idx is not None:
                return {
                    "is_valid": False,
                    "match_type": match_type,
                    "page_verified": False,
                    "confidence": confidence,
                    "explanation": f"Claimed page {page_ref} exceeds total document pages ({len(pages_metadata)})."
                }
        elif page_ref is not None:
            # Without pages_metadata, page cannot be strictly verified
            page_verified = False

        return {
            "is_valid": is_valid,
            "match_type": match_type,
            "page_verified": page_verified,
            "confidence": confidence,
            "explanation": explanation
        }

    @staticmethod
    def validate_source_reference(excerpt_or_reference: str, source_text: str) -> bool:
        """
        Validate whether an AI-generated source reference or excerpt genuinely appears
        in the actual source document text to prevent hallucinations.
        """
        res = DocumentParserService.validate_source_citation(excerpt_or_reference, source_text)
        return res["is_valid"]

document_parser = DocumentParserService()
