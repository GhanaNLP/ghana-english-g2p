# Contributing a pronunciation

This lexicon exists so that a Ghanaian word has one recorded pronunciation, shared by
anything that needs it — TTS, ASR, forced alignment, research. A word added here
reaches all of them. That is the reason to put it here rather than in a downstream
project.

The most valuable contributions are names: people, families, towns, rivers,
chieftaincy titles. There are more Ghanaian names than any one person knows, and a
name nobody records is a name every system mispronounces.

## The format

`src/ghana_english_g2p/data/lexicon.tsv.gz` — one entry per line, lowercase word, a
tab, then IPA phones separated by spaces:

```
kwabena	k w a b ɪ n a
achimota	a tʃ i m o t a
okuapenhene	o k w a p ɛ n h ɛ n ɛ
```

Multi-character phones are single tokens: `kp`, `ɡb`, `tʃ`, `dʒ`, `ɲ`, `ŋm`. Use `ɡ`
(U+0261, the script g) rather than ASCII `g` in `ɡb`, to match the existing entries.

A word may have more than one line if it genuinely has more than one pronunciation.

## Please listen before you open a PR

An entry that reads correctly and sounds wrong is worse than no entry: a missing word
is obviously missing, and a wrong one is confidently wrong. The quickest way to hear
yours is through [poto-tts](https://github.com/GhanaNLP/poto-tts), which compiles this
lexicon into an espeak dictionary:

```bash
pip install 'poto-tts[lexicon]'                   # needs the espeak-ng binary
printf 'Owusu\to w u s u\n' > my_words.tsv
poto-tts dict --out build/espeak-ng-data --ghanaian-stress --extra my_words.tsv
poto-tts --espeak-data build/espeak-ng-data "Owusu arrived" -o out.wav
```

Then say in the PR that you listened to it. Not as a formality: the phone string and
the sound come apart in ways that are hard to predict, and you are almost certainly a
better judge of the word than the reviewer is.

Note that a synthesiser cannot reproduce everything you can write. Pronunciations are
approximated into whatever inventory the downstream model has, so Akan vowels English
lacks land on their nearest English neighbour, and tone is not carried at all. Record
the pronunciation correctly anyway — this is a lexicon, not a TTS front-end, and a
better model later should not inherit a compromise made for this one.

## Reporting a wrong entry

Open an issue. Include the word, what it should sound like — a rhyme or a syllable
breakdown is fine, IPA is not required — and the language or region it comes from if
that is relevant.

You do not need to know IPA to report that a name is wrong. Recognising that it *is*
wrong is the part that cannot be done from the outside.

## What does not belong here

Ordinary English words, unless Ghanaian English genuinely pronounces them
differently in a way worth recording. The lexicon already contains a large number of
these, and they are why consumers need to filter it: a TTS front-end that uses every
entry pronounces every word of every sentence the Ghanaian way, which is a different
thing from pronouncing Ghanaian words properly.

Misspellings, abbreviations and run-together fragments do not belong either. Some are
already in here (`macfamous`, `preevent`, `notfor`); removing them is a welcome PR.
