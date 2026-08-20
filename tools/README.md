# Maintenance scripts

## `classify_lexicon.py`

Splits the lexicon into words a Ghanaian speaker pronounces by local rules and
words pronounced as ordinary English, and keeps only the first kind. This is how
the lexicon went from 104,623 entries to 44,321.

    GEMINI_API_KEY=... python tools/classify_lexicon.py --out build/classified

The lexicon had grown to cover the whole language -- `bus`, `passed`, `way`,
`yesterday` all had entries, each recording the Ghanaian *accent* of an English
word. That made every consumer apply Ghanaian vowels to every word of every
sentence, whether or not the word was Ghanaian. A pronunciation lexicon should
record words whose pronunciation cannot be derived; an accent belongs somewhere
else.

No mechanical rule could draw the line:

  * subtracting an English word list deletes `yaw`, `cedi`, `ghana`, `accra`,
    `ama` and `tema`, all of which English also spells
  * comparing the entry with espeak's English flags every non-rhotic word --
    `backdoor`, `airspeed`, `awardee` -- because Ghanaian English drops /r/
  * spelling patterns match `twin` and `dwell`

The question is what a word *is*, so it needs a judgement. Only the words are
sent, never their pronunciations.

Two things about it are load-bearing and easy to undo by accident:

  * **Each verdict names its own word** (`kwabena 1`). The first version returned
    one bit per word, positionally. It misclassified `bus`, `way` and `cedi`
    although the prompt names all three with their answers, and 3% of replies came
    back the wrong length -- so the ones of the right length had drifted too, just
    invisibly. Repeating the word makes a drift impossible rather than unlikely.
  * **`thinkingBudget: 0`.** With thinking on, the output budget is spent reasoning
    and every reply arrives truncated.

Batches are cached per file, so a re-run costs nothing for work already done, and
a word whose IPA contains kp, ɡb or ɲ is kept whatever the verdict says -- English
has no such sounds. The run fails outright if a known Ghanaian word that English
also spells is dropped.
