"""Repair transcription errors in the lexicon, in place.

Four classes, each found by scanning the lexicon rather than by hand, and each
mechanical enough to fix without judging every word. Run with --dry-run first; it
prints what it would change and writes nothing.

    python tools/repair_lexicon.py --dry-run
    python tools/repair_lexicon.py

1. **Doubled initial consonant.** 82 entries begin with the same consonant twice
   where the spelling has it once: `kofi` as [k, k, o, f, i], `consensus` as
   [k, k, n, s, ɛ, n, s, ʊ, s]. Eighty of the eighty-two start with `c` or `k`, so
   this is one bug with one signature. In 52 of them the vowel after the consonant
   is gone as well -- `c-o-n` became `k, k, n` -- so the duplicate cannot simply be
   dropped; the vowel is taken from espeak-en, which reads ordinary English
   correctly.

2. **Phones no Ghanaian language has, in Ghanaian words.** 2,104 entries in the
   Ghanaian subset contain æ, ə, ʌ, ɐ or ɒ. Akan, Ga, Ewe and Dagbani have none of
   them: the vowel systems are a e ɛ i o ɔ u. `Asantewaa` was stored
   [æ, s, æ, n, t, ɪ, w, æː], which reads as /æsæntɪwæ/ -- an English speaker's
   guess at the word, in a lexicon whose purpose is to record the Ghanaian one.

3. **A spurious final vowel on English words.** 147 English words whose spelling
   ends in a silent `e` are transcribed as if it were pronounced: `abode` as
   [a, b, o, d, e], `ache` as [a, tʃ, e]. Ghanaian words ending in a vowel are far
   more common and are correct, so this is restricted to words an English word list
   also has.

4. **Missing words.** `a` is absent, which matters more than one entry should: a
   consumer that falls back to espeak gets the *letter name* for a single letter, so
   the indefinite article was being read /eɪ/.

What this deliberately does not touch: ɪ and ʊ, which do occur in Akan and are not
errors; and any word where the fix would need a judgement rather than a rule.
"""

from __future__ import annotations

import argparse
import gzip
import subprocess
import sys
import urllib.request
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "src" / "ghana_english_g2p" / "data" / "lexicon.tsv.gz"
ENGLISH_WORDS = "https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt"

# Ghanaian vowel systems have none of these.
FOREIGN = {"æ": "a", "ə": "a", "ʌ": "a", "ɐ": "a", "ɒ": "ɔ",
           # English diphthongs, written as single units in some entries. Akan has
           # neither: FACE is [e] and GOAT is [o]. `abako` was stored [əbækoʊ].
           }

# The same diphthongs written as two phones, which is how the lexicon actually stores
# them: [o, ʊ] not [oʊ]. Akan has neither -- FACE is [e], GOAT is [o] -- so in a
# Ghanaian word the glide is an English reading of the spelling. PRICE, MOUTH and
# CHOICE are left alone: those glides are real in Ghanaian English.
SEQUENCES = {("o", "ʊ"): ["o"], ("oː", "ʊ"): ["oː"],
             ("e", "ɪ"): ["e"], ("eː", "ɪ"): ["eː"]}
CONSONANTS = set("bdfghjklmnpqrstvwxyzɡʃʒŋɲθðɹɾ")
# long forms included: a set of bare vowels missed `ɑː` and made the repair insert a
# second vowel before an existing one -- `caritas` became [k, æ, ɑː, ...].
_V = "aeiouɛɔɪʊæəʌɐɒɑ"
VOWELS = set(_V) | {v + "ː" for v in _V}
ADDITIONS = {"a": ["ə"]}


def english_vocabulary(cache: Path) -> set:
    if not cache.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(ENGLISH_WORDS, timeout=120) as r:
            cache.write_bytes(r.read())
    return {w.strip().lower() for w in cache.read_text(encoding="utf-8").split() if w.strip()}


def espeak_phones(word: str) -> list:
    """espeak-en's reading, as bare phones. Used only to recover a lost vowel."""
    out = subprocess.run(["espeak-ng", "-v", "en-us", "--ipa=3", "-q", word],
                         capture_output=True, text=True).stdout.strip()
    # Bare diacritics are dropped, not kept as phones. espeak writes its /iʲ/ glide
    # with a standalone ʲ, and left in it became an entry no consumer can map:
    # `karaoke` was stored [k, æ, ɹ, ɪ, ʲ, o, ʊ, k, i].
    return [c for c in out if c not in "ˈˌː‍ˑʲʰ ̃"]


def load(path: Path) -> dict:
    lex: dict[str, list[list[str]]] = {}
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            word, _, ipa = line.rstrip("\n").partition("\t")
            if word:
                lex.setdefault(word, []).append(ipa.split(" "))
    return lex


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--ghanaian-words", default=None,
                    help="the Ghanaian-word list (default: ask poto_tts for it)")
    ap.add_argument("--limit-report", type=int, default=8)
    args = ap.parse_args()

    lex = load(DATA)
    print(f"{len(lex)} entries in {DATA.name}", file=sys.stderr)

    if args.ghanaian_words:
        ghanaian = {w.strip().lower() for w in Path(args.ghanaian_words).read_text().split()}
    else:
        try:
            from poto_tts.dictionary import ghanaian_words
            ghanaian = ghanaian_words()
        except Exception:
            print("no Ghanaian-word list available; skipping class 2", file=sys.stderr)
            ghanaian = set()

    english = english_vocabulary(Path("build/words_alpha.txt"))
    changed: dict[str, list] = {}
    counts = dict.fromkeys(("doubled", "foreign", "final_e", "added"), 0)
    examples: dict[str, list] = {k: [] for k in counts}

    for word, prons in lex.items():
        phones = list(prons[0])
        before = list(phones)

        # 1. doubled initial consonant
        if (len(phones) > 2 and phones[0] == phones[1] and phones[0] in CONSONANTS
                and len(word) > 2 and word[0] != word[1]):
            if phones[2] in VOWELS or word[1] not in "aeiouy":
                # either the vowel survived, or the spelling has a cluster (`clo-`,
                # `chr-`) and there was never a vowel in that position
                phones = phones[1:]
            else:
                guess = espeak_phones(word)               # the vowel is gone too
                vowel = next((p for p in guess if p in VOWELS), "ɔ")
                phones = [phones[0], vowel] + phones[2:]

        # 2. phones no Ghanaian language has, in Ghanaian words
        if word in ghanaian:
            merged, i = [], 0
            while i < len(phones):
                pair = tuple(phones[i:i + 2])
                if pair in SEQUENCES:
                    merged += SEQUENCES[pair]
                    i += 2
                    continue
                merged.append(phones[i])
                i += 1
            phones = merged
            phones = [FOREIGN.get(p, p) if p in FOREIGN else p for p in phones]
            # long forms carry the same vowel
            phones = [FOREIGN.get(p[:-1], p[:-1]) + "ː" if p.endswith("ː") and p[:-1] in FOREIGN
                      else p for p in phones]

        # 3. an English word read as if its silent `e` were spoken. Truncating the
        # vowel is not enough: `ache` was [a, tʃ, e], so the `ch` was read /tʃ/ as
        # well and the whole entry is a spelling-read. Re-derived from espeak-en,
        # and only for words the Ghanaian list does not claim -- `abele` is Ga for
        # corn and its final vowel is correct.
        if (word in english and word not in ghanaian and word.endswith("e")
                and len(word) > 3 and not word.endswith(("ee", "ie", "oe", "ae"))
                and phones and phones[-1] in ("e", "ɛ")):
            guess = espeak_phones(word)
            if guess:
                phones = guess

        if phones != before:
            changed[word] = phones
            if before[0] == before[1] if len(before) > 1 else False:
                counts["doubled"] += 1
                if len(examples["doubled"]) < args.limit_report:
                    examples["doubled"].append((word, before, phones))
            elif word in english and len(phones) < len(before):
                counts["final_e"] += 1
                if len(examples["final_e"]) < args.limit_report:
                    examples["final_e"].append((word, before, phones))
            else:
                counts["foreign"] += 1
                if len(examples["foreign"]) < args.limit_report:
                    examples["foreign"].append((word, before, phones))

    for word, phones in ADDITIONS.items():
        if word not in lex:
            changed[word] = phones
            counts["added"] += 1
            examples["added"].append((word, [], phones))

    print(f"\n{len(changed)} entries to change:", file=sys.stderr)
    for key, label in (("doubled", "doubled initial consonant"),
                       ("foreign", "phone no Ghanaian language has"),
                       ("final_e", "spurious final vowel"),
                       ("added", "added")):
        print(f"  {counts[key]:>6}  {label}", file=sys.stderr)
        for word, before, after in examples[key]:
            print(f"          {word:16s} {''.join(before) or '(new)':22s} -> {''.join(after)}",
                  file=sys.stderr)

    if args.dry_run:
        print("\n--dry-run: nothing written", file=sys.stderr)
        return 0

    for word, phones in changed.items():
        lex.setdefault(word, [[]])
        lex[word][0] = phones
    with gzip.open(DATA, "wt", encoding="utf-8") as fh:
        for word in sorted(lex):
            for pron in lex[word]:
                fh.write(f"{word}\t{' '.join(pron)}\n")
    print(f"\nwrote {DATA} ({len(lex)} entries)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
