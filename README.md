# ghana-english-g2p

Ghanaian English text to IPA. A **104,623-word Ghanaian pronunciation lexicon** is
consulted first; [`espeak-english`](https://github.com/GhanaNLP/espeak-english) handles
whatever is left over.

```bash
pip install ghana-english-g2p
```

```python
from ghana_english_g2p import GhanaEnglishG2P

g2p = GhanaEnglishG2P()

g2p.ipa("Kwabena went to Achimota")
# 'kwabɪna wɛnt tuː atʃimota'

g2p.ipa("Kwabena went to Achimota", sep=" ")
# 'k w a b ɪ n a w ɛ n t t uː a tʃ i m o t a'
```

```bash
ghana-english-g2p "The Bank of Ghana raised the policy rate."
```

## Why this exists

espeak reads Ghanaian names as if they were English spelling. It does not fail loudly —
it returns a confident, fluent, wrong pronunciation:

| word | espeak alone | this lexicon |
|---|---|---|
| Kwabena | `k w e ɪ b n ə` | `k w a b ɪ n a` |
| Achimota | `ɐ tʃ ɪ m o ʊ ɾ ə` | `a tʃ i m o t a` |
| Okuapenhene | `o ʊ k j uː e ɪ p ə n h iː n` | `o k w a p ɛ n h ɛ n ɛ` |
| Bawumia | `b æ w uː m i ə` | `b a w u m i a` |
| Twumasi | `t w uː m ɑː s i` | `t w u m a s i` |
| Nyantakyi | `n a ɪ ɐ n t æ k ɪ i` | `ɲ a n t a tɕ i` |

Every one of these is a name a Ghanaian TTS or ASR system will meet on its first day.
The lexicon is what makes the output Ghanaian; espeak is the general-purpose fallback
behind it, not the other way round.

Rule-based conversion is not an option for this language pair, and that is measurable.
Running [`ghana-g2p`](https://github.com/GhanaNLP/ghana-g2p)'s Twi rules over 4,000 words
of this lexicon gives **7.6% exact-match and 50.1% phoneme error** — Ghanaian names come
out roughly right, English words are destroyed (`concerts` → `tʃ o n tʃ e ɾ t s`). Twi has
a shallow orthography and rules suit it; English does not, which is the reason
pronunciation dictionaries exist at all.

## One notation, both paths

espeak emits stress marks and a run-together transcription; the lexicon stores spaced
phones. Both go through the same segmenter, so **you cannot tell from the symbols which
path produced a word**:

```python
from ghana_english_g2p import segment

segment("ɐdmˈɪkstʃɚ")        # espeak     -> ['ɐ','d','m','ɪ','k','s','tʃ','ɚ']
segment("ɡ ɑː n ə")           # lexicon    -> ['ɡ','ɑː','n','ə']
segment("ɡɑːnə")              # either     -> ['ɡ','ɑː','n','ə']
```

The conventions, applied to both sources:

| | |
|---|---|
| stress marks `ˈ ˌ` | removed |
| tie bars `d͡ʒ` | removed — `dʒ` |
| affricates `tʃ dʒ ts dz kp ɡb` | one phone |
| diphthongs `aɪ oʊ eɪ` | two phones — `a ɪ` |
| length `uː` | stays on its vowel |

The inventory is **63 phones**, derived from the data rather than declared up front.

## Provenance

Which words the lexicon actually covered is part of the output, not something to guess at:

```python
r = g2p.convert("Kwabena discussed decarbonisation")

r.ipa           # 'kwabɪna dɪskʌst dᵻkɑːɹbənəzeɪʃən'
r.words         # ['Kwabena', 'discussed', 'decarbonisation']
r.sources       # ['lexicon', 'lexicon', 'espeak']
r.oov           # ['decarbonisation']
r.coverage      # 0.667
```

To measure true lexicon coverage with no fallback masking it:

```python
GhanaEnglishG2P(use_espeak=False)   # unknown words return [], source 'unknown'
```

```bash
ghana-english-g2p --show-source "Kwabena discussed cryptocurrency"
```

## Measured coverage

Against the [twi-health-asr](https://huggingface.co/datasets/ghananlpcommunity/twi-health-asr-gemini-500hrs)
transcripts, which contributed nothing to the lexicon: **77.9% of 127,846 tokens** are
covered by lookup alone.

Read that as a lower bound. That corpus is Twi-heavy spontaneous speech, so much of the
remainder is Twi vocabulary (`yareɛ`, `ɛneɛ`, `sɛdeɛ`) and single letters, which a
*Ghanaian English* lexicon is not meant to hold. For Twi proper use
[`ghana-g2p`](https://github.com/GhanaNLP/ghana-g2p), whose rules cover 42 Ghanaian
languages.

## Extending the lexicon

```python
g2p = GhanaEnglishG2P(lexicon={"Nkrumah": "ŋ k r u m a"})
```

Entries are merged over the packaged lexicon, so this overrides as well as extends.
IPA may be written spaced or run-together — it goes through the same segmenter.

## Where the lexicon came from

Headwords are the unique vocabulary of three Ghanaian sources:

| source | contributes |
|---|---|
| [ghana-named-entities](https://huggingface.co/datasets/ghananlpcommunity/ghana-named-entities) | people, places, organisations |
| [GhanaNouns](https://github.com/GhanaNLP/GhanaNouns) | Ghanaian English nouns, incl. health and agriculture |
| [Ghana English-Twi code-switching speech](https://huggingface.co/datasets/ghananlpcommunity/Ghana_English-Twi_Code-switching_Speech) | transcript vocabulary |

Deduplication is case-insensitive and prefers the capitalised form, so named entities keep
their casing on the way in. Pronunciations were generated with **Gemini 3.6 Flash**, prompted
for the pronunciation used in Ghana and told explicitly not to anglicise Ghanaian names.
Accent variants are collapsed to the Ghanaian form; only genuine homographs (`read`, `lead`)
keep two entries.

**These transcriptions are model-generated and have not been reviewed by a phonetician.**
Known inconsistencies survive in the data: `tɕ` appears where `tʃ` is meant (`Nyantakyi`),
and `r`/`ɹ` are not used consistently across entries. Corrections by PR are welcome — the
lexicon is a plain TSV.

To rebuild it from a fresh source file:

```bash
python tools/build_lexicon.py path/to/ipa.jsonl
```

## Notes

- `espeak-english` pins espeak-ng to 1.51 and bundles it, so there is no system
  dependency and no drift between machines.
- The lexicon loads once and is cached; it is 0.72 MB gzipped.
- Lookup is case-insensitive. Punctuation is dropped. Digits inside a word are kept
  (`COVID19`); bare numerals are left to espeak, which reads them out (`2024` →
  `t uː θ a ʊ z ə n d t w ɛ n t i f oː ɹ`).

## Licence

MIT.
