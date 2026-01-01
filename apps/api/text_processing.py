"""
Text extraction and masking utilities.
Fail-closed: raises exceptions on errors.
"""
import re
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Tuple, List, Optional
from collections import Counter


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


# Whisper model singleton cache
_whisper_model = None
_whisper_model_name = None


def _get_whisper_model():
    """
    Lazy load Whisper model (singleton pattern).
    Model is cached globally to avoid reloading on each request.
    """
    global _whisper_model, _whisper_model_name
    
    import os
    import whisper
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Get model name from env (default: "base" for dev, can be overridden to "large-v3" for demo)
    model_name = os.getenv("WHISPER_MODEL", "base")
    
    # Reload if model name changed
    if _whisper_model is None or _whisper_model_name != model_name:
        logger.info(f"[STT] Loading Whisper model: {model_name} (cached={_whisper_model is not None})")
        _whisper_model = whisper.load_model(model_name)
        _whisper_model_name = model_name
        logger.info(f"[STT] Model loaded: {model_name}")
    
    return _whisper_model


def transcribe_audio(audio_path: str) -> str:
    """
    Transcribe audio file using local openai-whisper (no external API calls).
    
    Supports: webm, ogg, mp3, wav (whisper handles conversion internally).
    
    Model is cached globally (singleton) to avoid reloading on each request.
    Model name can be configured via WHISPER_MODEL env var (default: "base").
    
    NEVER log the raw transcript output.
    Fail-closed: raises exception on error (no document created).
    """
    try:
        import whisper
    except ImportError:
        raise ImportError("openai-whisper is required for transcription. Install with: pip install openai-whisper")
    
    audio_path_obj = Path(audio_path)
    if not audio_path_obj.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    
    try:
        # Get cached model (lazy load on first call)
        model = _get_whisper_model()
        
        # Transcribe (whisper handles audio format conversion internally)
        result = model.transcribe(
            str(audio_path),
            language="sv",  # Swedish
            task="transcribe"
        )
        
        # Extract transcript text
        raw_transcript = result["text"].strip()
        
        # Validate transcript is not empty and not stub-like
        if not raw_transcript or len(raw_transcript.strip()) < 10:
            raise ValueError("Transcription produced empty or too short transcript")
        
        # Check for stub-like patterns (fail-closed if detected)
        stub_patterns = [
            "Detta är en inspelning från",
            "Detta är ett röstmemo med",
            "Jag pratar om viktiga saker här"
        ]
        for pattern in stub_patterns:
            if pattern in raw_transcript:
                raise ValueError(f"Transcription appears to be stub (contains: {pattern})")
        
        return raw_transcript
        
    except Exception as e:
        # Fail-closed: raise exception (no document created)
        # Log error type only (no content leakage)
        import logging
        logger = logging.getLogger(__name__)
        error_type = type(e).__name__
        error_msg = str(e)[:100] if str(e) else ""  # Limit length, avoid full content
        logger.error(f"[STT] Transcription failed: {error_type} - {error_msg}")
        raise RuntimeError(f"Audio transcription failed: {error_type}")


def normalize_transcript_text(raw_text: str) -> str:
    """
    Normalize and correct common Swedish STT errors in transcript.
    
    Deterministic post-processing (no AI):
    - Merge fragmented sentences
    - Remove repeated words
    - Trim whitespace
    - Apply common Swedish STT error mappings
    
    NEVER log raw_text or output.
    """
    if not raw_text:
        return ""
    
    text = raw_text
    
    # Common Swedish STT error mappings (deterministic, explicit)
    # Small list (10-30 entries), easy to extend
    stt_error_mappings = {
        # Common Whisper mishearings
        "konfliktsutom": "konflikter",
        "önskimol": "önskemål",
        "öfomulerade": "oformulerade",
        "ommedvetna": "omedvetna",
        "nertonat": "nertonad",
        "frustrerad agerande": "frustrerat agerande",
        "involverad": "involverade",  # Context-dependent, but common error
        "det är uppfattar": "det uppfattas",
        "det är en konflikt består": "en konflikt består",
        "inom form av sån": "i form av en sådan",
        "sån situation": "sådan situation",
        # Additional common errors
        "det det": "det",
        "och och": "och",
        "är är": "är",
        "som som": "som",
        "för för": "för",
        "i i": "i",
        "av av": "av",
        "med med": "med",
        "till till": "till",
        "på på": "på",
        "om om": "om",
        "en en": "en",
        "ett ett": "ett",
        "den den": "den",
        "det det": "det",
    }
    
    # Apply error mappings (word boundaries to avoid partial matches)
    for error, correction in stt_error_mappings.items():
        # Use word boundaries for whole-word replacements
        pattern = r'\b' + re.escape(error) + r'\b'
        text = re.sub(pattern, correction, text, flags=re.IGNORECASE)
    
    # Remove repeated words (common STT artifact)
    # Pattern: word word (same word repeated with space)
    text = re.sub(r'\b(\w+)\s+\1\b', r'\1', text, flags=re.IGNORECASE)
    
    # Merge fragmented sentences (common pattern: sentence. sentence -> sentence. sentence)
    # Remove excessive periods that create fragments
    # This is conservative - only merge obvious fragments
    text = re.sub(r'\.\s+([a-z])', r'. \1', text)  # Ensure space after period before lowercase
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)  # Multiple spaces -> single space
    text = re.sub(r'\s+\.', '.', text)  # Space before period -> period
    text = re.sub(r'\.\s*\.', '.', text)  # Multiple periods -> single period
    text = re.sub(r'\s+,\s*', ', ', text)  # Normalize comma spacing
    text = re.sub(r'\s+:\s*', ': ', text)  # Normalize colon spacing
    
    # Remove empty lines and trim
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    text = ' '.join(lines)  # Join all lines with space
    
    # Final trim
    text = text.strip()
    
    return text


def generate_stub_transcript(filename: str, duration_seconds: Optional[int] = None) -> str:
    """
    Generate a deterministic stub transcript from filename.
    DEPRECATED: Use transcribe_audio() for real transcription.
    
    NEVER log the output of this function or any raw transcript.
    """
    # Extract base name without extension
    base_name = os.path.splitext(filename)[0]
    
    # Generate deterministic text based on filename
    # Include multiple sentences so processor has content to work with
    sentences = [
        f"Detta är en inspelning från {base_name}.",
        "Jag pratar om viktiga saker här som behöver dokumenteras.",
        "Detta är en längre mening som innehåller mer information om ämnet och problemet vi diskuterar.",
        "Vi behöver tänka på nästa steg och vad som krävs för att lösa detta.",
        "Det finns en deadline som måste hållas och källor som behöver verifieras.",
        "Detta är en risk som vi måste ta hänsyn till i vårt arbete.",
        "Ytterligare detaljer kommer här som är relevanta för projektet.",
        "Slutligen avslutar jag med några sista tankar om vad som behöver göras härnäst."
    ]
    
    if duration_seconds:
        sentences.insert(1, f"Detta är ett röstmemo med {duration_seconds} sekunder inspelning.")
    
    return " ".join(sentences)


def process_transcript(raw_transcript: str, project_name: str, recording_date: str, duration_seconds: Optional[int] = None) -> str:
    """
    Process raw transcript into structured markdown-like format.
    
    NEVER log raw_transcript or the processed output.
    Only use metadata (duration, size, mime) for logging.
    
    Output structure:
    - Title: # Röstmemo – {project_name} – {recording_date}
    - Sammanfattning: First 2 sentences or ~240 chars
    - Nyckelpunkter: 3-5 bullets (prefer sentences with keywords)
    - Tidslinje: 4-8 segments with timestamps
    """
    # Safety pre-scan: replace detected PII with tokens before processing
    # Use same patterns as masking but apply before formatting
    text = raw_transcript
    
    # Email pattern
    email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
    text = re.sub(email_pattern, '[EMAIL]', text, flags=re.IGNORECASE)
    
    # Phone patterns (similar to masking)
    phone_patterns = [
        r'\b0\d{1,2}[- ]\d{2,3}[- ]?\d{2,3}[- ]?\d{2,4}\b',  # Swedish phone
        r'\b07\d[- ]\d{2,3}[- ]?\d{2,3}[- ]?\d{2,4}\b',      # Mobile
        r'\+\d{1,3}[- ]?\d{1,4}[- ]?\d{2,4}[- ]?\d{2,4}\b',  # International
    ]
    for pattern in phone_patterns:
        text = re.sub(pattern, '[PHONE]', text)
    
    # Personnummer patterns
    personnummer_patterns = [
        r'\b(19|20)\d{6}[- ]\d{4}\b',  # YYYYMMDD-XXXX
        r'\b(19|20)\d{10}\b',          # YYYYMMDDXXXX
    ]
    for pattern in personnummer_patterns:
        text = re.sub(pattern, '[PERSONNUMMER]', text)
    
    # Split into sentences
    # Simple sentence splitting (period, exclamation, question mark followed by space or end)
    sentences = re.split(r'[.!?]+\s+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    # Build output with strict markdown formatting
    # Ensure each section is separated by blank lines (\n\n)
    output_lines = []
    
    # Title
    output_lines.append(f"# Röstmemo – {project_name} – {recording_date}")
    output_lines.append("")  # Blank line after title
    
    # Sammanfattning
    output_lines.append("## Sammanfattning")
    output_lines.append("")  # Blank line after heading
    if len(sentences) >= 2:
        summary = f"{sentences[0]}. {sentences[1]}."
        if len(summary) > 240:
            summary = summary[:237] + "..."
        output_lines.append(summary)
    elif len(sentences) == 1:
        summary = sentences[0]
        if len(summary) > 240:
            summary = summary[:237] + "..."
        output_lines.append(summary + ".")
    else:
        # Fallback
        if duration_seconds:
            output_lines.append(f"Detta är ett röstmemo med {duration_seconds} sekunder inspelning.")
        else:
            output_lines.append("Detta är ett röstmemo med inspelning.")
    output_lines.append("")  # Blank line after summary
    
    # Nyckelpunkter
    output_lines.append("## Nyckelpunkter")
    output_lines.append("")  # Blank line after heading
    
    # Keywords to prefer
    keywords = ['viktigt', 'problem', 'nästa steg', 'deadline', 'källa', 'risk', 'behöver']
    
    # Score sentences by keyword presence and length
    scored_sentences = []
    for i, sent in enumerate(sentences):
        score = len(sent)  # Base score on length
        sent_lower = sent.lower()
        for keyword in keywords:
            if keyword in sent_lower:
                score += 100  # Boost for keywords
        scored_sentences.append((score, i, sent))
    
    # Sort by score (descending) and take top 3-5
    scored_sentences.sort(reverse=True)
    key_points = scored_sentences[:min(5, len(scored_sentences))]
    key_points = sorted(key_points, key=lambda x: x[1])  # Sort by original order
    
    # If we have fewer than 3, use longest sentences
    if len(key_points) < 3:
        longest = sorted([(len(s), i, s) for i, s in enumerate(sentences)], reverse=True)
        key_points = longest[:min(5, len(longest))]
        key_points = sorted(key_points, key=lambda x: x[1])
    
    for _, _, sent in key_points[:5]:
        # Cap length at reasonable size
        if len(sent) > 150:
            sent = sent[:147] + "..."
        output_lines.append(f"- {sent}")
    
    output_lines.append("")  # Blank line after bullets
    
    # Tidslinje
    output_lines.append("## Tidslinje")
    output_lines.append("")  # Blank line after heading
    
    # Chunk transcript into 4-8 segments
    num_segments = min(8, max(4, len(sentences) // 3))
    if num_segments == 0:
        num_segments = 1
    
    chunk_size = max(1, len(sentences) // num_segments)
    
    for i in range(num_segments):
        start_idx = i * chunk_size
        end_idx = min(start_idx + chunk_size, len(sentences))
        
        if start_idx >= len(sentences):
            break
        
        # Calculate timestamp (assume ~3 seconds per sentence)
        timestamp_seconds = i * 15  # [00:00], [00:15], [00:30], etc.
        minutes = timestamp_seconds // 60
        seconds = timestamp_seconds % 60
        timestamp = f"[{minutes:02d}:{seconds:02d}]"
        
        # Use first sentence of chunk
        chunk_sentences = sentences[start_idx:end_idx]
        if chunk_sentences:
            first_sent = chunk_sentences[0].strip()
            if len(first_sent) > 120:
                first_sent = first_sent[:117] + "..."
            output_lines.append(f"{timestamp} {first_sent}")
    
    # Join with newlines and ensure no trailing whitespace
    result = "\n".join(output_lines)
    # Remove any trailing whitespace from each line
    result_lines = [line.rstrip() for line in result.split('\n')]
    return "\n".join(result_lines)


def refine_editorial_text(structured_text: str) -> str:
    """
    Refine structured transcript text to editorial-ready first draft (deterministic).
    
    Performs ONLY:
    - Trims speech signals in Nyckelpunkter ("Och…", "Det här…", "Jag tycker…")
    - Simplifies obvious speech syntax to neutral written Swedish
    - Ensures each bullet starts with noun or verb
    - If Sammanfattning has < 2 sentences: adds 1 condensed conclusion based on existing words (no new info)
    
    MUST NOT:
    - Change meaning
    - Add new facts
    - Use LLM or external services
    
    NEVER log structured_text or the refined output.
    """
    if not structured_text:
        return structured_text
    
    lines = structured_text.split('\n')
    output_lines = []
    i = 0
    
    # Common Swedish speech signals to trim from bullet points
    speech_signals = [
        r'^och\s+',
        r'^det här\s+',
        r'^detta\s+',
        r'^jag tycker\s+',
        r'^jag tror\s+',
        r'^jag tror att\s+',
        r'^tycker jag\s+',
        r'^tror jag\s+',
        r'^alltså\s+',
        r'^så\s+',
        r'^sen\s+',
        r'^sedan\s+',
        r'^då\s+',
        r'^men\s+',
        r'^eller\s+',
        r'^så att\s+',
        r'^så att säga\s+',
    ]
    
    # Speech-to-written Swedish transformations (deterministic mappings)
    speech_to_written = {
        # "det är" -> "det" (remove redundant "är")
        r'\bdet är\s+': 'det ',
        # "det här" -> "detta" (more formal)
        r'\bdet här\s+': 'detta ',
        # "så att" -> "så att" (keep, but can be context-dependent)
        # "om vi" -> "om vi" (keep)
        # "det kan" -> "det kan" (keep)
        # Remove filler words in middle of sentences
        r'\s+alltså\s+': ' ',
        r'\s+så att säga\s+': ' ',
        r'\s+typ\s+': ' ',
        # Fix common speech patterns
        r'\bdet det\b': 'det',
        r'\bär är\b': 'är',
        r'\bkan kan\b': 'kan',
        r'\bska ska\b': 'ska',
    }
    
    # Process line by line
    in_sammanfattning = False
    in_nyckelpunkter = False
    sammanfattning_lines = []
    sammanfattning_start_idx = -1
    
    while i < len(lines):
        line = lines[i]
        
        # Detect sections
        if line.strip() == "## Sammanfattning":
            in_sammanfattning = True
            in_nyckelpunkter = False
            output_lines.append(line)
            i += 1
            continue
        elif line.strip() == "## Nyckelpunkter":
            in_sammanfattning = False
            in_nyckelpunkter = True
            output_lines.append(line)
            i += 1
            continue
        elif line.strip().startswith("##"):
            in_sammanfattning = False
            in_nyckelpunkter = False
            output_lines.append(line)
            i += 1
            continue
        
        # Process Sammanfattning section
        if in_sammanfattning and line.strip() and not line.strip().startswith("#"):
            if sammanfattning_start_idx == -1:
                sammanfattning_start_idx = len(output_lines)
            sammanfattning_lines.append(line)
            # Apply speech-to-written transformations
            refined_line = line
            for pattern, replacement in speech_to_written.items():
                refined_line = re.sub(pattern, replacement, refined_line, flags=re.IGNORECASE)
            output_lines.append(refined_line)
            i += 1
            continue
        
        # Process Nyckelpunkter bullets
        if in_nyckelpunkter and line.strip().startswith("- "):
            bullet_text = line[2:].strip()  # Remove "- " prefix
            
            # Trim speech signals from beginning
            for signal_pattern in speech_signals:
                bullet_text = re.sub(signal_pattern, '', bullet_text, flags=re.IGNORECASE)
            
            # Apply speech-to-written transformations
            for pattern, replacement in speech_to_written.items():
                bullet_text = re.sub(pattern, replacement, bullet_text, flags=re.IGNORECASE)
            
            # Ensure bullet starts with noun or verb
            # Simple heuristic: check if starts with common Swedish verbs or nouns
            # Verbs: inflected forms are complex, so we check for common patterns
            # Nouns: often start with determiners (en, ett, den, det) or are capitalized
            bullet_lower = bullet_text.lower().strip()
            
            # If starts with common speech connectors, try to find next word
            connectors = ['och', 'men', 'eller', 'så', 'då', 'sen', 'sedan', 'alltså']
            words = bullet_text.split()
            if words and words[0].lower() in connectors:
                # Try to keep only if next word is a good start
                if len(words) > 1:
                    # Remove first word if it's a connector
                    bullet_text = ' '.join(words[1:])
                    bullet_lower = bullet_text.lower().strip()
            
            # Capitalize first letter if needed (basic heuristic)
            if bullet_text and bullet_text[0].islower():
                # Check if it's a verb or noun starting with lowercase
                # Common Swedish verbs that start lowercase: behöver, kan, ska, måste, vill
                # If not starting with verb, capitalize
                common_verbs = ['behöver', 'kan', 'ska', 'måste', 'vill', 'får', 'gör', 'har', 'är', 'blir']
                if not any(bullet_lower.startswith(v + ' ') for v in common_verbs):
                    bullet_text = bullet_text[0].upper() + bullet_text[1:] if len(bullet_text) > 1 else bullet_text.upper()
            
            output_lines.append(f"- {bullet_text}")
            i += 1
            continue
        
        # Pass through other lines unchanged
        output_lines.append(line)
        i += 1
    
    # Post-process: Enhance Sammanfattning if it has < 2 sentences
    if sammanfattning_start_idx != -1 and len(sammanfattning_lines) > 0:
        # Count sentences in Sammanfattning
        sammanfattning_text = ' '.join(sammanfattning_lines)
        sentences = re.split(r'[.!?]+\s+', sammanfattning_text)
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 5]
        
        if len(sentences) < 2:
            # Extract key words from existing text for condensed conclusion
            # Use words from Nyckelpunkter and Sammanfattning (no new info)
            all_words = []
            
            # Find Nyckelpunkter section and extract words from bullets
            in_nyckelpunkter_section = False
            for line in lines:
                if line.strip() == "## Nyckelpunkter":
                    in_nyckelpunkter_section = True
                    continue
                elif line.strip().startswith("##") and in_nyckelpunkter_section:
                    in_nyckelpunkter_section = False
                    continue
                
                if in_nyckelpunkter_section and line.strip().startswith("- "):
                    bullet_text = line[2:].strip()
                    all_words.extend(re.findall(r'\b\w+\b', bullet_text.lower()))
            
            # Add words from Sammanfattning
            all_words.extend(re.findall(r'\b\w+\b', sammanfattning_text.lower()))
            
            # Find common important words (nouns, verbs - simple heuristic)
            # Filter out common stop words
            stop_words = {'detta', 'detta', 'finns', 'skulle', 'borde', 'bör', 'kanske', 'möjligt', 'eller', 'också', 'även', 'där', 'här', 'där', 'denna', 'detta', 'denne'}
            important_words = [w for w in all_words if len(w) > 4 and w not in stop_words]
            
            # Create simple conclusion based on existing content
            # Just extract key concept and make a simple statement
            if important_words:
                # Use most common word or a key concept
                word_counts = Counter(important_words)
                top_words = [w for w, _ in word_counts.most_common(3)]
                
                # Build simple conclusion sentence using existing patterns
                conclusion = f"Detta fokuserar på {top_words[0] if top_words else 'huvudpunkterna'}."
            else:
                conclusion = "Detta sammanfattar huvudpunkterna."
            
            # Insert conclusion after existing Sammanfattning content
            # Find where to insert (after last line of Sammanfattning, before blank line)
            insert_idx = sammanfattning_start_idx + len(sammanfattning_lines)
            output_lines.insert(insert_idx, conclusion)
    
    # Join and return
    result = "\n".join(output_lines)
    result_lines = [line.rstrip() for line in result.split('\n')]
    return "\n".join(result_lines)

