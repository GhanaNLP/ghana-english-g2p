"""Build the packaged lexicon from the Gemini-phonemised word list.

Input is the JSONL produced by the DeepPhonemizer g2p pipeline
(`g2p/data/ipa.jsonl`): one {"word", "ipa"} record per line, IPA written as
space-separated phones.

Output is `src/ghana_english_g2p/data/lexicon.tsv.gz`, sorted, lowercased and
deduplicated, with the phone notation normalised to match what the espeak
fallback emits (see ghana_english_g2p.core.normalise).

    python tools/build_lexicon.py path/to/ipa.jsonl
"""

import gzip
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'src' / 'ghana_english_g2p' / 'data' / 'lexicon.tsv.gz'

sys.path.insert(0, str(ROOT / 'src'))
from ghana_english_g2p.core import segment  # noqa: E402  the one canonical segmenter

# Graphemes we accept in a headword. Digits are allowed inside a word (COVID19)
# but a bare numeral is not a lexicon entry.
LETTERS = set('abcdefghijklmnopqrstuvwxyzɔɛŋ')
ALLOWED = LETTERS | set('0123456789')

# Phones seen fewer than this many times across the whole lexicon are model
# slips rather than real contrasts, and the entries carrying them are dropped.
MIN_PHONE_COUNT = 20


def normalise_phones(ipa: str):
    """Space-separated IPA string -> list of phones, or None if unusable.

    Runs the same segmenter the espeak fallback uses, so a merged token like
    "ən" or "aɪ" is split the same way in both paths.
    """
    return segment(ipa) or None


def main():
    src = Path(sys.argv[1] if len(sys.argv) > 1
               else ROOT.parent / 'DeepPhonemizer' / 'g2p' / 'data' / 'ipa.jsonl')
    if not src.exists():
        raise SystemExit(f'lexicon source not found: {src}')

    entries = defaultdict(list)
    n_lines = n_bad = 0
    with src.open(encoding='utf-8') as f:
        for line in f:
            n_lines += 1
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                n_bad += 1
                continue
            word = rec['word'].lower()
            if not word or not ALLOWED.issuperset(word) or not LETTERS & set(word):
                n_bad += 1
                continue
            phones = normalise_phones(rec['ipa'])
            if phones is None:
                n_bad += 1
                continue
            if phones not in entries[word]:
                entries[word].append(phones)

    counts = Counter(p for v in entries.values() for ph in v for p in ph)
    keep = {p for p, c in counts.items() if c >= MIN_PHONE_COUNT}
    dropped = sorted(((c, p) for p, c in counts.items() if c < MIN_PHONE_COUNT),
                     reverse=True)
    if dropped:
        print(f'dropping {len(dropped)} rare phones: '
              f'{[(p, c) for c, p in dropped[:15]]}', file=sys.stderr)

    rows, n_rare = [], 0
    for word in sorted(entries):
        for phones in entries[word]:
            if keep.issuperset(phones):
                rows.append((word, ' '.join(phones)))
            else:
                n_rare += 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(OUT, 'wt', encoding='utf-8', compresslevel=9) as f:
        for word, ipa in rows:
            f.write(f'{word}\t{ipa}\n')

    n_words = len({w for w, _ in rows})
    print(f'read {n_lines:,} lines ({n_bad:,} rejected, {n_rare:,} on rare phones)',
          file=sys.stderr)
    print(f'wrote {len(rows):,} pronunciations for {n_words:,} words -> {OUT}',
          file=sys.stderr)
    print(f'  size: {OUT.stat().st_size / 1e6:.2f} MB', file=sys.stderr)
    print(f'  inventory ({len(keep)}): {" ".join(sorted(keep))}', file=sys.stderr)


if __name__ == '__main__':
    main()
