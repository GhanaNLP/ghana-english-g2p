"""Ghanaian English grapheme-to-phoneme conversion.

>>> from ghana_english_g2p import GhanaEnglishG2P
>>> g = GhanaEnglishG2P()
>>> g.ipa('Kwabena went to Achimota', sep=' ')
'k w a b ɪ n a w ɛ n t t uː a tʃ i m o t a'
"""

from .core import (
    DEFAULT_PUNCTUATION,
    GhanaEnglishG2P,
    Result,
    segment,
)

__all__ = ['GhanaEnglishG2P', 'Result', 'segment', 'DEFAULT_PUNCTUATION', '__version__']

__version__ = '0.1.0'
