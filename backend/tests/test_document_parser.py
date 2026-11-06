import pytest
import io
import pypdf
from app.services.document_parser import document_parser

def test_parse_email():
    email_sample = """Subject: URGENT: Deviation in Batch B2026-API-044 at Crystallization
From: production.lead@pharma-plant.com
Date: Wed, 04 Nov 2026 14:30:00 +0000
To: qa.investigations@pharma-plant.com

Dear QA Team,
During crystallization of Atorvastatin batch B2026-API-044 in reactor RX-301, the temperature spiked to 38.4C.
Target temperature was 22.0C. The cooling valve CV-04 failed to stroke open.
We have isolated the batch and require immediate RCA support.
"""
    result = document_parser.parse_email(email_sample)
    assert "headers" in result
    assert result["headers"]["subject"] == "URGENT: Deviation in Batch B2026-API-044 at Crystallization"
    assert result["headers"]["from"] == "production.lead@pharma-plant.com"
    assert "Atorvastatin" in result["body"]

def test_clean_text():
    raw = "Line 1\r\n\r\n\r\n\r\nLine 2   \r\n"
    cleaned = document_parser.clean_text(raw)
    assert "Line 1\n\nLine 2" == cleaned

def test_parse_pdf():
    # Create an in-memory PDF using pypdf writer
    writer = pypdf.PdfWriter()
    page = writer.add_blank_page(width=200, height=200)
    
    stream = io.BytesIO()
    writer.write(stream)
    pdf_bytes = stream.getvalue()
    
    text, meta = document_parser.extract_text_from_pdf(pdf_bytes)
    assert meta["num_pages"] == 1

