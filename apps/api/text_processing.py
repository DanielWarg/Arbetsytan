"""
Text extraction and masking utilities.
Fail-closed: raises exceptions on errors.
"""
import re
import os
from typing import Tuple, List


class PiiGateError(Exception):
    """Raised when PII is detected after masking (fail-closed)"""
    def __init__(self, reasons: List[str]):
        self.reasons = reasons
        super().__init__(f"PII detected after masking: {', '.join(reasons)}")


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text from PDF file.
    Raises exception on failure (fail-closed).
    """
    try:
        import pypdf
    except ImportError:
        raise ImportError("pypdf is required for PDF extraction. Install with: pip install pypdf")
    
    try:
        text_parts = []
        with open(file_path, 'rb') as f:
            pdf_reader = pypdf.PdfReader(f)
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
        
        if not text_parts:
            raise ValueError("PDF contains no extractable text")
        
        return '\n\n'.join(text_parts)
    except Exception as e:
        raise ValueError(f"Failed to extract text from PDF: {str(e)}")


def extract_text_from_txt(file_path: str) -> str:
    """
    Extract text from TXT file.
    Tries UTF-8 first, falls back to latin-1.
    Raises exception on failure (fail-closed).
    """
    try:
        # Try UTF-8 first
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            # Fallback to latin-1
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()
        except Exception as e:
            raise ValueError(f"Failed to extract text from TXT file: {str(e)}")
    except Exception as e:
        raise ValueError(f"Failed to read TXT file: {str(e)}")


def normalize_text(text: str) -> str:
    """
    Basic text normalization:
    - Remove excessive whitespace
    - Normalize line breaks
    """
    # Normalize line breaks
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # Remove excessive blank lines (max 2 consecutive)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove trailing whitespace from lines
    lines = [line.rstrip() for line in text.split('\n')]
    text = '\n'.join(lines)
    
    return text.strip()


def mask_text(text: str, level: str = "normal") -> str:
    """
    Progressive text masking with three levels:
    - normal: Standard PII masking (email, phone, personnummer)
    - strict: Normal + aggressive numeric masking (5+ digits, spaced/hyphenated)
    - paranoid: Replace all digits, emails/urls, mask names after labels
    
    This is proof-of-concept level, not production-grade.
    """
    if level == "paranoid":
        return mask_text_paranoid(text)
    elif level == "strict":
        return mask_text_strict(text)
    else:  # normal
        return mask_text_normal(text)


def mask_text_normal(text: str) -> str:
    """Normal masking: email, phone, personnummer, long numbers"""
    # Email pattern
    email_pattern = r'\b[\w\.-]+@[\w\.-]+\.\w+\b'
    text = re.sub(email_pattern, '[EMAIL]', text, flags=re.IGNORECASE)
    
    # Personnummer pattern (YYYYMMDD-XXXX or YYYYMMDDXXXX)
    personnummer_pattern = r'\b(19|20)\d{6}[- ]\d{4}\b|\b(19|20)\d{10}\b'
    text = re.sub(personnummer_pattern, '[REDACTED]', text)
    
    # Swedish phone number patterns
    phone_patterns = [
        r'\+46\s*\d{1,2}[- ]?\d{2,3}[- ]?\d{2,3}[- ]?\d{2,4}',
        r'\b0\d{1,2}[- ]\d{2,3}[- ]?\d{2,3}[- ]?\d{2,4}\b',
        r'\b07\d[- ]\d{2,3}[- ]?\d{2,3}[- ]?\d{2,4}\b',
        r'-\d{4}\b',
        r'\b\d{2,3}[- ]\d{2,3}[- ]\d{2,4}\b',
    ]
    
    for pattern in phone_patterns:
        text = re.sub(pattern, '[PHONE]', text)
    
    # Long numbers (>10 digits)
    long_number_pattern = r'\b\d{11,}\b'
    text = re.sub(long_number_pattern, '[REDACTED]', text)
    
    return text


def mask_text_strict(text: str) -> str:
    """Strict masking: normal + aggressive numeric masking (5+ digits, including spaced/hyphenated)"""
    # Start with normal masking
    text = mask_text_normal(text)
    
    # More aggressive ID label masking
    id_label_patterns = [
        r'Dok\.Id\s+\d+',
        r'ID:\s*\d+',
        r'Id:\s*\d+',
        r'\bID\s+\d+',
    ]
    
    for pattern in id_label_patterns:
        text = re.sub(pattern, '[ID]', text, flags=re.IGNORECASE)
    
    # Mask spaced/hyphenated digit soups (e.g., "24 698", "322 9448")
    # Pattern: sequences of digits separated by spaces/hyphens, total >= 5 digits
    # But exclude already masked tokens and dates
    def mask_digit_cluster(match):
        matched = match.group()
        # Skip if it's already a token
        if any(token in matched for token in ['[PHONE]', '[EMAIL]', '[REDACTED]', '[ID]', '[NUM]']):
            return matched
        # Count total digits
        digit_count = len(re.sub(r'\D', '', matched))
        if digit_count >= 5:
            return '[NUM]'
        return matched
    
    # Match digit clusters with spaces/hyphens: "24 698", "322-9448", "123 45 67"
    # But avoid matching dates like "2025-11-20" (4 digits - 2 digits - 2 digits)
    # Also avoid matching already masked patterns
    digit_cluster_pattern = r'\b(?!(?:19|20)\d{2}[- ]\d{2}[- ]\d{2})(?![\[PHONE\]\[EMAIL\]\[REDACTED\]\[ID\]\[NUM\]])\d{1,4}(?:[- ]\d{1,4}){1,4}\b'
    text = re.sub(digit_cluster_pattern, mask_digit_cluster, text)
    
    # Also mask standalone 5+ digit sequences (not already masked)
    # But check that it's not part of a token
    def mask_standalone_digits(match):
        matched = match.group()
        # Check if surrounded by brackets (already a token)
        start = match.start()
        end = match.end()
        if start > 0 and end < len(text):
            if text[start-1] == '[' and text[end] == ']':
                return matched
        return '[NUM]'
    
    standalone_long_pattern = r'\b\d{5,}\b'
    text = re.sub(standalone_long_pattern, '[NUM]', text)
    
    return text


def mask_text_paranoid(text: str) -> str:
    """Paranoid masking: replace all digits, emails/urls, mask names after labels.
    This level MUST guarantee that pii_gate_check() passes."""
    # Replace emails and URLs with [LINK] first (before digit replacement)
    email_pattern = r'\b[\w\.-]+@[\w\.-]+\.\w+\b'
    text = re.sub(email_pattern, '[LINK]', text, flags=re.IGNORECASE)
    
    url_pattern = r'https?://[^\s]+'
    text = re.sub(url_pattern, '[LINK]', text, flags=re.IGNORECASE)
    
    # Replace all digits 0-9 with [NUM] (preserve structure)
    # This ensures no numeric PII remains
    text = re.sub(r'\d', '[NUM]', text)
    
    # Mask names after known labels (preserve line structure)
    lines = text.split('\n')
    masked_lines = []
    
    name_label_patterns = [
        (r'^Sökande\s+(.+)', r'Sökande [NAME]'),
        (r'^Motpart\s+(.+)', r'Motpart [NAME]'),
        (r'^Ombud\s+(.+)', r'Ombud [NAME]'),
        (r'^RÄTTEN\s+(.+)', r'RÄTTEN [NAME]'),
        (r'^Rådmannen\s+(.+)', r'Rådmannen [NAME]'),
    ]
    
    for line in lines:
        masked_line = line
        for pattern, replacement in name_label_patterns:
            if re.match(pattern, line, flags=re.IGNORECASE):
                masked_line = re.sub(pattern, replacement, line, flags=re.IGNORECASE)
                break
        masked_lines.append(masked_line)
    
    text = '\n'.join(masked_lines)
    
    return text


def pii_gate_check(text: str) -> Tuple[bool, List[str]]:
    """
    Deterministic PII gate check on already masked text.
    Returns (is_safe, reasons) where:
    - is_safe = True only if no PII-like patterns remain
    - reasons = list of reason codes if blocked
    
    Reason codes (generic, no raw values):
    - personnummer_detected
    - birthdate_like_sequence_detected
    - email_detected
    - phone_detected
    - unmasked_id_detected
    - long_number_detected
    """
    reasons = []
    
    # Step 1: Remove allowed tokens to avoid false positives
    # Replace tokens with placeholders before pattern matching
    allowed_tokens = [
        r'\[PHONE\]',
        r'\[EMAIL\]',
        r'\[PERSONNUMMER\]',
        r'\[ID\]',
        r'\[REDACTED\]',
        r'\[NUM\]',
        r'\[LINK\]',
        r'\[NAME\]'
    ]
    
    # Create a sanitized version for pattern matching
    sanitized = text
    for token_pattern in allowed_tokens:
        sanitized = re.sub(token_pattern, '[TOKEN]', sanitized, flags=re.IGNORECASE)
    
    # Step 2: Check for personnummer patterns
    # YYYYMMDD-XXXX, YYYYMMDDXXXX, YYMMDD-XXXX, YYMMDDXXXX
    personnummer_patterns = [
        r'\b(19|20)\d{6}[- ]\d{4}\b',  # YYYYMMDD-XXXX
        r'\b(19|20)\d{10}\b',          # YYYYMMDDXXXX (12 digits)
        r'\b\d{6}[- ]\d{4}\b',         # YYMMDD-XXXX
        r'\b\d{10}\b',                 # YYMMDDXXXX (10 digits, but careful with context)
    ]
    
    for pattern in personnummer_patterns:
        if re.search(pattern, sanitized):
            if 'personnummer_detected' not in reasons:
                reasons.append('personnummer_detected')
            break
    
    # Step 3: Check for standalone birthdate-like YYYYMMDD sequences
    # Pattern: (19|20)YY(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])
    # This matches valid dates in compact form (e.g., 19780126, 20251231)
    # But NOT YYYY-MM-DD (those are explicitly allowed)
    birthdate_pattern = r'\b(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\b'
    if re.search(birthdate_pattern, sanitized):
        # Double-check: make sure it's not part of a date with dashes
        # If we find YYYY-MM-DD nearby, it's probably a date, not a birthdate
        birthdate_matches = re.finditer(birthdate_pattern, sanitized)
        for match in birthdate_matches:
            start, end = match.span()
            # Check if this is part of a YYYY-MM-DD pattern
            context_start = max(0, start - 20)
            context_end = min(len(sanitized), end + 20)
            context = sanitized[context_start:context_end]
            # If we see YYYY-MM-DD pattern nearby, skip this match
            if not re.search(r'\d{4}-\d{2}-\d{2}', context):
                if 'birthdate_like_sequence_detected' not in reasons:
                    reasons.append('birthdate_like_sequence_detected')
                break
    
    # Step 4: Check for email patterns
    email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
    if re.search(email_pattern, sanitized, flags=re.IGNORECASE):
        reasons.append('email_detected')
    
    # Step 5: Check for phone number patterns (broader: 7+ digits total)
    # Require explicit prefix: starts with 0 or + (to avoid false positives like case numbers)
    # Include variants with spaces, hyphens, and optional country code +46
    # BUT: exclude date patterns (YYYY-MM-DD) which have dashes but are not phones
    phone_patterns = [
        # Swedish format with country code: +46 70 123 45 67, +46701234567
        r'\+46\s*\d{1,2}[- ]?\d{2,3}[- ]?\d{2,3}[- ]?\d{2,4}',
        # Area code with separators: 031-123 45 67, 08-123 45 67 (must start with 0)
        r'\b0\d{1,2}[- ]\d{2,3}[- ]?\d{2,3}[- ]?\d{2,4}\b',
        # Mobile with separators: 070-123 45 67, 070-1234567 (must start with 07)
        r'\b07\d[- ]\d{2,3}[- ]?\d{2,3}[- ]?\d{2,4}\b',
    ]
    
    for pattern in phone_patterns:
        matches = re.finditer(pattern, sanitized)
        for match in matches:
            # Count total digits in the match
            matched_text = match.group()
            digit_count = len(re.sub(r'\D', '', matched_text))
            # Also check: if it looks like a date (YYYY-MM-DD), skip it
            if re.match(r'^(19|20)\d{2}-\d{2}-\d{2}$', matched_text):
                continue
            # Require at least 7 digits total
            if digit_count >= 7:
                if 'phone_detected' not in reasons:
                    reasons.append('phone_detected')
                break
        if 'phone_detected' in reasons:
            break
    
    # Step 6: Check for unmasked ID labels
    id_label_patterns = [
        r'Dok\.Id\s+\d+',
        r'ID:\s*\d+',
        r'Id:\s*\d+',
        r'\bID\s+\d+',
    ]
    
    for pattern in id_label_patterns:
        if re.search(pattern, sanitized, flags=re.IGNORECASE):
            if 'unmasked_id_detected' not in reasons:
                reasons.append('unmasked_id_detected')
            break
    
    # Step 7: Check for long numeric sequences (>8 digits, excluding tokens)
    # Find all sequences of 9+ consecutive digits
    long_number_pattern = r'\b\d{9,}\b'
    if re.search(long_number_pattern, sanitized):
        reasons.append('long_number_detected')
    
    # Return result
    is_safe = len(reasons) == 0
    return (is_safe, reasons)


def validate_file_type(file_path: str, filename: str) -> Tuple[str, bool]:
    """
    Validate file type using extension + magic bytes.
    Returns (file_type, is_valid) tuple.
    
    PDF must start with %PDF-
    TXT must be decodable as text and must not be PDF.
    """
    # Check extension
    ext = os.path.splitext(filename)[1].lower()
    
    # Read first bytes for magic number check
    try:
        with open(file_path, 'rb') as f:
            first_bytes = f.read(1024)
    except Exception:
        return ('', False)
    
    # Check for PDF
    if ext == '.pdf':
        if first_bytes.startswith(b'%PDF-'):
            return ('pdf', True)
        else:
            return ('pdf', False)
    
    # Check for TXT
    if ext == '.txt':
        # Must not be PDF
        if first_bytes.startswith(b'%PDF-'):
            return ('txt', False)
        
        # Must be decodable as text
        try:
            first_bytes.decode('utf-8')
            return ('txt', True)
        except UnicodeDecodeError:
            try:
                first_bytes.decode('latin-1')
                return ('txt', True)
            except:
                return ('txt', False)
    
    # Unknown extension
    return ('', False)

