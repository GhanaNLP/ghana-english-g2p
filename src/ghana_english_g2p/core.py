"""Ghanaian English grapheme-to-phoneme conversion.

A word is looked up in a Ghanaian English pronunciation lexicon first. Only if
it is absent does espeak-ng generate a pronunciation. The order matters: espeak
reads Ghanaian names as English spelling and gets them wrong -- `Kwabena` comes
back as `kwˈeɪbnə` rather than `k w a b e n a` -- so the lexicon is what makes
the output Ghanaian, and espeak is the general-purpose fallback behind it.

Both paths are normalised to the same phone notation, so a caller cannot tell
from the symbols alone which one produced a given word. `convert()` reports the
source explicitly.
"""

from __future__ import annotations

import gzip
import re
from dataclasses import dataclass, field
from functools import lru_cache
from importlib import resources
from typing import Dict, Iterable, List, Sequence

__all__ = ['GhanaEnglishG2P', 'Result', 'segment', 'DEFAULT_PUNCTUATION']

# Multi-character phones that stay a single unit. Diphthongs are deliberately
# absent: they are written as two phones ("a ɪ", "o ʊ"), matching the lexicon.
AFFRICATES = ('tʃ', 'dʒ', 'ts', 'dz', 'tɕ', 'dʑ', 'kp', 'ɡb', 'ŋm')

LENGTH = 'ː'
HALF_LENGTH = 'ˑ'
TIE_BAR = '͡'
STRESS = 'ˈˌ'
# Diacritics that belong to the phone they follow rather than standing alone.
TRAILING = LENGTH + HALF_LENGTH + '̩̥̯̃ʰʷʲ'
# espeak emits these; neither is a phone we want to keep as its own symbol.
DROP = STRESS + '‿ˌ|'

DEFAULT_PUNCTUATION = '().,:;?!/–—"\''

_WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)


def segment(ipa: str) -> List[str]:
    """Split an IPA string into phones.

    Accepts either a run-together transcription (espeak: 'ɐdmˈɪkstʃɚ') or an
    already space-separated one (the lexicon: 'a d m ɪ k s tʃ ə'), and returns
    the same phone list for both. Stress marks and tie bars are removed; length
    marks and other trailing diacritics stay attached to their phone.
    """
    ipa = ipa.replace(TIE_BAR, '')
    phones: List[str] = []
    i, n = 0, len(ipa)
    while i < n:
        ch = ipa[i]
        if ch.isspace() or ch in DROP:
            i += 1
            continue
        if ch in TRAILING:
            # a diacritic that lost its phone, e.g. "a ː" written with a space
            if phones and not phones[-1].endswith(ch):
                phones[-1] += ch
            i += 1
            continue
        for aff in AFFRICATES:
            if ipa.startswith(aff, i):
                phones.append(aff)
                i += len(aff)
                break
        else:
            phones.append(ch)
            i += 1
        # absorb length marks and diacritics belonging to the phone just added
        while i < n and ipa[i] in TRAILING:
            if ipa[i] in (LENGTH, HALF_LENGTH) and phones[-1].endswith(LENGTH):
                i += 1          # collapse "aːː"
                continue
            phones[-1] += ipa[i]
            i += 1
    return phones


@dataclass
class Result:
    """The pronunciation of one text, with per-word provenance."""

    text: str
    phones: List[List[str]] = field(default_factory=list)
    words: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)

    @property
    def ipa(self) -> str:
        """Phones joined per word, words joined by spaces."""
        return ' '.join(''.join(p) for p in self.phones)

    @property
    def oov(self) -> List[str]:
        """Words the lexicon did not cover, in order of appearance."""
        return [w for w, s in zip(self.words, self.sources) if s != 'lexicon']

    @property
    def coverage(self) -> float:
        """Fraction of words served by the lexicon rather than espeak."""
        if not self.sources:
            return 1.0
        return sum(s == 'lexicon' for s in self.sources) / len(self.sources)


@lru_cache(maxsize=1)
def _load_lexicon() -> Dict[str, List[List[str]]]:
    path = resources.files(__package__).joinpath('data/lexicon.tsv.gz')
    lex: Dict[str, List[List[str]]] = {}
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        for line in f:
            word, _, ipa = line.rstrip('\n').partition('\t')
            if word:
                lex.setdefault(word, []).append(ipa.split(' '))
    return lex


class GhanaEnglishG2P:
    """Ghanaian English G2P: lexicon first, espeak for out-of-vocabulary words.

    >>> g = GhanaEnglishG2P()
    >>> g.word('Kwabena')
    ['k', 'w', 'a', 'b', 'e', 'n', 'a']
    >>> g.ipa('Kwabena', sep=' ')
    'k w a b e n a'
    """

    def __init__(self, use_espeak: bool = True, lexicon: Dict[str, str] | None = None):
        """
        Args:
            use_espeak: Fall back to espeak for words missing from the lexicon.
                With False, unknown words yield no phones and are reported as
                source 'unknown' -- useful for measuring true lexicon coverage.
            lexicon: Extra word -> IPA entries, merged over the packaged lexicon
                so a caller can override or extend it. IPA may be written either
                space-separated or run-together.
        """
        self.use_espeak = use_espeak
        self._lex = dict(_load_lexicon())
        if lexicon:
            for word, ipa in lexicon.items():
                self._lex[word.lower()] = [segment(ipa)]
        self._espeak = None

    # -- espeak is imported lazily so the lexicon works without it installed
    def _phonemise_espeak(self, word: str) -> List[str]:
        if self._espeak is None:
            try:
                import espeak_english
            except ImportError as exc:  # pragma: no cover
                raise RuntimeError(
                    'espeak fallback needs the espeak-english package: '
                    'pip install espeak-english'
                ) from exc
            self._espeak = espeak_english
        return segment(self._espeak.phonemes(word))

    def word(self, word: str, variants: bool = False):
        """Phones for a single word.

        Args:
            word: The word. Case is ignored.
            variants: Return every pronunciation the lexicon holds rather than
                just the first.

        Returns:
            A list of phones, or -- with variants=True -- a list of such lists.
        """
        phones, _ = self._lookup(word)
        if variants:
            return self._lex.get(word.lower(), [phones] if phones else [])
        return phones

    def _lookup(self, word: str):
        key = word.lower()
        hit = self._lex.get(key)
        if hit:
            return list(hit[0]), 'lexicon'
        if self.use_espeak:
            return self._phonemise_espeak(word), 'espeak'
        return [], 'unknown'

    def convert(self, text: str, punctuation: str = DEFAULT_PUNCTUATION) -> Result:
        """Phonemise a text, keeping per-word provenance.

        Args:
            text: Text to phonemise.
            punctuation: Characters treated as word separators and dropped.

        Returns:
            Result: carries phones, the words they came from, and whether each
            was served by the lexicon or by espeak.
        """
        result = Result(text=text)
        for word in _WORD_RE.findall(text):
            phones, source = self._lookup(word)
            result.words.append(word)
            result.phones.append(phones)
            result.sources.append(source)
        return result

    def ipa(self, text: str, sep: str = '') -> str:
        """Phonemise a text and return the IPA.

        Args:
            text: Text to phonemise.
            sep: Separator between phones within a word. Default '' joins them
                ('kwabena'); ' ' keeps them separate ('k w a b e n a').
        """
        r = self.convert(text)
        return ' '.join(sep.join(p) for p in r.phones if p)

    def __call__(self, text: str, sep: str = '') -> str:
        return self.ipa(text, sep=sep)

    def __contains__(self, word: str) -> bool:
        return word.lower() in self._lex

    def __len__(self) -> int:
        return len(self._lex)

    def coverage(self, words: Iterable[str]) -> float:
        """Fraction of `words` present in the lexicon."""
        words = list(words)
        if not words:
            return 1.0
        return sum(w.lower() in self._lex for w in words) / len(words)
