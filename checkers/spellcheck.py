import re
from typing import List, Dict, Set


def check_spelling(paragraphs: List[str], known_names: Set[str]) -> List[Dict]:
    from spellchecker import SpellChecker

    spell = SpellChecker()
    for name in known_names:
        spell.word_frequency.load_words([name.lower()])
        # Load each part of compound names too
        for part in name.split():
            spell.word_frequency.load_words([part.lower()])

    word_errors: Dict[str, Dict] = {}

    for para_num, paragraph in enumerate(paragraphs, 1):
        sentences = re.split(r'(?<=[.!?])\s+', paragraph)
        for sentence in sentences:
            # Extract words 3+ chars; skip fragments that are part of contractions
            # e.g. "didn't" → apostrophe lookahead prevents matching "didn"
            words = re.findall(r"\b([a-zA-Z]{3,})(?!')\b", sentence)
            if not words:
                continue

            misspelled = spell.unknown(words)

            for original_word in words:
                if original_word.lower() not in misspelled:
                    continue
                # Skip words starting with uppercase — likely proper nouns
                if original_word[0].isupper():
                    continue

                key = original_word.lower()
                if key not in word_errors:
                    candidates = spell.candidates(key) or set()
                    suggestions = sorted(
                        [s for s in candidates if s != key],
                        key=lambda s: _edit_distance_approx(key, s)
                    )[:3]
                    word_errors[key] = {
                        'word': key,
                        'suggestions': suggestions,
                        'occurrences': [],
                    }

                occ = {'paragraph': para_num, 'context': sentence.strip()}
                if occ not in word_errors[key]['occurrences']:
                    word_errors[key]['occurrences'].append(occ)

    return sorted(word_errors.values(), key=lambda x: x['occurrences'][0]['paragraph'])


def check_repeated_words(paragraphs: List[str]) -> List[Dict]:
    results = []
    # Match word repeated immediately ("the the", ignoring punctuation between)
    pattern = re.compile(r'\b(\w{2,})\s+\1\b', re.IGNORECASE)

    for para_num, paragraph in enumerate(paragraphs, 1):
        for match in pattern.finditer(paragraph):
            word = match.group(1).lower()
            # Skip common false positives in fiction (e.g., "had had" is grammatically valid)
            if word in ('had', 'that', 'it'):
                continue
            # Get surrounding context
            start = max(0, match.start() - 40)
            end = min(len(paragraph), match.end() + 40)
            context = ('...' if start > 0 else '') + paragraph[start:end] + ('...' if end < len(paragraph) else '')
            results.append({
                'word': word,
                'paragraph': para_num,
                'context': context.strip(),
            })

    return results


def _edit_distance_approx(a: str, b: str) -> int:
    if len(a) > len(b):
        a, b = b, a
    row = list(range(len(a) + 1))
    for c in b:
        new_row = [row[0] + 1]
        for j, d in enumerate(a):
            new_row.append(min(new_row[-1] + 1, row[j + 1] + 1, row[j] + (c != d)))
        row = new_row
    return row[-1]
