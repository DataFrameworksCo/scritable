import re
from collections import defaultdict
from typing import List, Dict, Optional

try:
    import spacy
    _nlp = None

    def _get_nlp():
        global _nlp
        if _nlp is None:
            _nlp = spacy.load("en_core_web_sm")
        return _nlp

    SPACY_OK = True
except Exception:
    SPACY_OK = False


# ── Attribute definitions ────────────────────────────────────────────────────

EYE_COLORS = [
    'blue', 'green', 'brown', 'gray', 'grey', 'hazel', 'amber',
    'violet', 'black', 'pale', 'golden', 'silver', 'dark', 'light',
    'red', 'pink', 'purple', 'heterochromia',
]

HAIR_COLORS = [
    'blonde', 'blond', 'brown', 'black', 'red', 'auburn', 'ginger',
    'gray', 'grey', 'white', 'silver', 'golden', 'dark', 'light',
    'copper', 'chestnut', 'brunette', 'strawberry',
]

HAIR_STYLES = [
    'long', 'short', 'curly', 'straight', 'wavy', 'thick', 'thin',
    'braided', 'loose', 'tangled', 'cropped', 'shaved', 'bald',
]

ATTRIBUTES = {
    'eye_color': {
        'label': 'eye color',
        'body_words': ['eye', 'eyes'],
        'values': EYE_COLORS,
        'window': 80,
    },
    'hair_color': {
        'label': 'hair color',
        'body_words': ['hair'],
        'values': HAIR_COLORS,
        'window': 80,
    },
    'hair_style': {
        'label': 'hair style',
        'body_words': ['hair'],
        'values': HAIR_STYLES,
        'window': 80,
    },
}


# ── Name extraction ──────────────────────────────────────────────────────────

def extract_names(paragraphs: List[str]) -> Dict[str, int]:
    if not SPACY_OK:
        return {}
    try:
        nlp = _get_nlp()
    except OSError:
        return {}

    counts: Dict[str, int] = defaultdict(int)
    for para in paragraphs:
        try:
            doc = nlp(para[:5000])
            for ent in doc.ents:
                if ent.label_ == "PERSON":
                    name = ent.text.strip()
                    # Strip possessive
                    name = re.sub(r"'s?$", "", name).strip()
                    if 1 < len(name) < 40 and not any(c.isdigit() for c in name):
                        counts[name] += 1
        except Exception:
            continue

    return dict(counts)


# ── Attribute detection ──────────────────────────────────────────────────────

def _find_value_near_body(sentence_lower: str, body_words: List[str],
                           values: List[str], window: int) -> Optional[str]:
    """Return first value word found within `window` chars of any body word."""
    for bw in body_words:
        p = 0
        while True:
            idx = sentence_lower.find(bw, p)
            if idx == -1:
                break
            start = max(0, idx - window)
            end = min(len(sentence_lower), idx + len(bw) + window)
            snippet = sentence_lower[start:end]
            for val in values:
                if re.search(rf'\b{re.escape(val)}\b', snippet):
                    return val
            p = idx + 1
    return None


def _name_near_body(sentence_lower: str, name_lower: str,
                     body_words: List[str], window: int) -> bool:
    """True if the character name appears within `window` chars of a body word."""
    p = 0
    while True:
        ni = sentence_lower.find(name_lower, p)
        if ni == -1:
            return False
        for bw in body_words:
            bi = sentence_lower.find(bw, 0)
            while bi != -1:
                if abs(ni - bi) <= window:
                    return True
                bi = sentence_lower.find(bw, bi + 1)
        p = ni + 1
    return False


# ── Main analysis ─────────────────────────────────────────────────────────────

def analyze_characters(paragraphs: List[str]) -> dict:
    name_counts = extract_names(paragraphs)
    # Only track characters mentioned at least twice
    characters = {n: c for n, c in name_counts.items() if c >= 2}

    profiles: Dict[str, dict] = {}

    for char_name in characters:
        char_lower = char_name.lower()
        # Also try first-name-only matching for multi-word names
        first_name = char_name.split()[0] if ' ' in char_name else None

        raw_attrs: Dict[str, List[dict]] = defaultdict(list)

        for para_num, paragraph in enumerate(paragraphs, 1):
            para_lower = paragraph.lower()
            # Quick pre-filter: skip paragraphs that don't mention this character
            name_hit = char_lower in para_lower
            first_hit = first_name and first_name.lower() in para_lower
            if not name_hit and not first_hit:
                continue

            sentences = re.split(r'(?<=[.!?])\s+', paragraph)
            for sentence in sentences:
                s_lower = sentence.lower()

                for cfg in ATTRIBUTES.values():
                    bw = cfg['body_words']
                    w = cfg['window']

                    # Check if character name (or first name) is near body word
                    name_match = (char_lower in s_lower and
                                  _name_near_body(s_lower, char_lower, bw, w))
                    first_match = (first_name and
                                   first_name.lower() in s_lower and
                                   _name_near_body(s_lower, first_name.lower(), bw, w))

                    if not name_match and not first_match:
                        continue

                    val = _find_value_near_body(s_lower, bw, cfg['values'], w)
                    if val:
                        raw_attrs[cfg['label']].append({
                            'value': val,
                            'paragraph': para_num,
                            'context': sentence.strip(),
                        })

        attributes = {k: v for k, v in raw_attrs.items()}

        # Detect inconsistencies
        inconsistencies = []
        for attr_label, mentions in attributes.items():
            unique_vals = list({m['value'] for m in mentions})
            if len(unique_vals) > 1:
                inconsistencies.append({
                    'attribute': attr_label,
                    'values_found': unique_vals,
                    'mentions': mentions,
                    'description': (
                        f"{char_name}'s {attr_label} is described as "
                        f"{' and '.join(f'\"{v}\"' for v in unique_vals)}"
                    ),
                })

        # Only include characters with detected attributes or 3+ mentions
        if attributes or characters[char_name] >= 3:
            profiles[char_name] = {
                'name': char_name,
                'mentions': characters[char_name],
                'attributes': attributes,
                'inconsistencies': inconsistencies,
            }

    total_inconsistencies = sum(len(p['inconsistencies']) for p in profiles.values())

    return {
        'character_names': list(name_counts.keys()),
        'profiles': profiles,
        'inconsistency_count': total_inconsistencies,
        'spacy_available': SPACY_OK,
    }
