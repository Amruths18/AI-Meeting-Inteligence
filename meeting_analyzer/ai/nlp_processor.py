"""
ai/nlp_processor.py
Processes meeting transcripts using spaCy NLP to:
  1. Generate a concise extractive summary
  2. Extract action items, responsible persons, and deadlines
"""

import re
from collections import Counter
from typing import Optional


# ── spaCy model loader ────────────────────────────────────────────────────────

_nlp = None

def get_nlp():
    """Lazy-load the spaCy English model (run: python -m spacy download en_core_web_sm)."""
    global _nlp
    if _nlp is None:
        import spacy
        try:
            _nlp = spacy.load("en_core_web_sm")
        except OSError:
            raise RuntimeError(
                "spaCy model not found. Please run:\n"
                "  python -m spacy download en_core_web_sm"
            )
    return _nlp


# ── Summary Generation ────────────────────────────────────────────────────────

def generate_summary(transcript: str, num_sentences: int = 5) -> str:
    """
    Produce an extractive summary by scoring sentences using TF-IDF-style
    word frequency weighting, then picking the top-ranked ones.

    Args:
        transcript:     Full meeting transcript text.
        num_sentences:  Maximum number of sentences in the summary.

    Returns:
        Summary string.
    """
    if not transcript or len(transcript.strip()) < 50:
        return "Transcript too short to summarize."

    nlp = get_nlp()
    doc = nlp(transcript)

    # Collect meaningful word frequencies (exclude stopwords and punctuation)
    word_freq: Counter = Counter()
    for token in doc:
        if not token.is_stop and not token.is_punct and token.text.strip():
            word_freq[token.text.lower()] += 1

    if not word_freq:
        return transcript[:500]

    max_freq = max(word_freq.values())
    for word in word_freq:
        word_freq[word] /= max_freq  # normalize to [0, 1]

    # Score each sentence by summing its tokens' frequencies
    sentences = list(doc.sents)
    sentence_scores: dict = {}
    for sent in sentences:
        score = sum(
            word_freq.get(token.text.lower(), 0)
            for token in sent
            if not token.is_stop and not token.is_punct
        )
        if len(sent) > 3:  # skip very short fragments
            sentence_scores[sent] = score / len(sent)  # normalize by length

    if not sentence_scores:
        return transcript[:500]

    # Pick top N sentences, preserving original order
    top_sentences = sorted(
        sentence_scores, key=sentence_scores.get, reverse=True
    )[:num_sentences]
    ordered = sorted(top_sentences, key=lambda s: s.start)

    return " ".join(sent.text.strip() for sent in ordered)


# ── Task Extraction ───────────────────────────────────────────────────────────

# Action verbs commonly used when assigning work
ACTION_VERBS = {
    "will", "should", "must", "need", "needs", "going to",
    "have to", "has to", "can", "would", "please", "ensure",
    "make sure", "follow up", "send", "prepare", "complete",
    "finish", "review", "update", "create", "write", "submit",
    "schedule", "arrange", "handle", "coordinate", "check",
    "confirm", "present", "deliver", "implement", "test",
    "deploy", "fix", "resolve", "investigate", "analyse", "analyze"
}

# Patterns for deadline extraction
DEADLINE_PATTERNS = [
    r"\b(by|before|until|due|on)\s+(monday|tuesday|wednesday|thursday|friday|"
    r"saturday|sunday|january|february|march|april|may|june|july|august|"
    r"september|october|november|december)\b",
    r"\bby\s+(end of (?:the )?(?:day|week|month|year))\b",
    r"\bby\s+(\d{1,2}[\/\-]\d{1,2}(?:[\/\-]\d{2,4})?)\b",
    r"\b(next\s+(?:monday|tuesday|wednesday|thursday|friday|week|month))\b",
    r"\bwithin\s+(\d+\s+(?:days?|weeks?|hours?))\b",
    r"\btomorrow\b",
    r"\btoday\b",
    r"\bend of (?:the )?(?:day|week|month)\b",
]


def _contains_action_verb(sentence: str) -> bool:
    """Return True if the sentence contains a known action/assignment verb."""
    lower = sentence.lower()
    return any(verb in lower for verb in ACTION_VERBS)


def _extract_deadline(sentence: str) -> Optional[str]:
    """Pull a deadline phrase from a sentence, if present."""
    lower = sentence.lower()
    for pattern in DEADLINE_PATTERNS:
        match = re.search(pattern, lower, re.IGNORECASE)
        if match:
            return match.group(0).strip()
    return None


def _extract_person(sent_doc) -> Optional[str]:
    """
    Use spaCy NER to find a PERSON entity in the sentence.
    Falls back to checking for a proper noun at the start of the sentence.
    """
    # Named entity recognition
    for ent in sent_doc.ents:
        if ent.label_ == "PERSON":
            return ent.text.strip()

    # Fallback: proper noun at the sentence start
    tokens = [t for t in sent_doc if not t.is_space]
    if tokens and tokens[0].pos_ == "PROPN":
        return tokens[0].text

    return None


def _clean_task_title(sentence: str) -> str:
    """Trim and truncate a sentence into a clean task title."""
    sentence = sentence.strip()
    # Remove leading filler words
    sentence = re.sub(
        r"^(so|also|and|okay|ok|right|well|basically|essentially),?\s*",
        "", sentence, flags=re.IGNORECASE
    )
    # Capitalize first letter
    sentence = sentence[0].upper() + sentence[1:] if sentence else sentence
    # Truncate to 100 chars for a readable title
    if len(sentence) > 100:
        sentence = sentence[:97] + "..."
    return sentence


def extract_tasks(transcript: str) -> list[dict]:
    """
    Analyse the transcript and return a list of detected action items.

    Each item:
        {
            "title":       short task description (≤100 chars),
            "description": full sentence for context,
            "person":      responsible person name or None,
            "deadline":    deadline phrase or None
        }
    """
    if not transcript or len(transcript.strip()) < 20:
        return []

    nlp = get_nlp()
    doc = nlp(transcript)

    tasks = []
    seen_titles: set = set()

    for sent in doc.sents:
        text = sent.text.strip()
        if len(text) < 10:
            continue

        if _contains_action_verb(text):
            title = _clean_task_title(text)
            # Deduplicate very similar tasks
            if title.lower()[:50] in seen_titles:
                continue
            seen_titles.add(title.lower()[:50])

            tasks.append({
                "title":       title,
                "description": text,
                "person":      _extract_person(sent),
                "deadline":    _extract_deadline(text)
            })

    return tasks


# ── Combined Pipeline ─────────────────────────────────────────────────────────

def process_transcript(transcript: str) -> dict:
    """
    Run the full NLP pipeline on a transcript.

    Returns:
        {
            "summary": str,
            "tasks":   list of task dicts
        }
    """
    summary = generate_summary(transcript)
    tasks   = extract_tasks(transcript)
    return {"summary": summary, "tasks": tasks}
