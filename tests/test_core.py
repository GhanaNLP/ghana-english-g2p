import pytest

from ghana_english_g2p import GhanaEnglishG2P, segment


@pytest.fixture(scope='module')
def g2p():
    return GhanaEnglishG2P()


# --- segment(): the one normaliser both paths go through ------------------

def test_segment_strips_stress_marks():
    # espeak marks primary and secondary stress; the lexicon never does
    assert segment('ɐdmˈɪkstʃɚ') == ['ɐ', 'd', 'm', 'ɪ', 'k', 's', 'tʃ', 'ɚ']
    assert 'ˈ' not in ''.join(segment('ˈoʊkjuːˌeɪpənhˌiːn'))


def test_segment_accepts_both_input_shapes():
    """A run-together espeak string and a spaced lexicon string agree."""
    assert segment('ɡɑːnə') == segment('ɡ ɑː n ə') == ['ɡ', 'ɑː', 'n', 'ə']


def test_segment_keeps_length_on_its_vowel():
    assert segment('θɹˈuː') == ['θ', 'ɹ', 'uː']
    assert segment('a ː') == ['aː']          # stranded length mark reattaches
    assert segment('aːː') == ['aː']          # doubled length collapses


def test_segment_affricates_are_one_phone():
    assert segment('tʃ') == ['tʃ']
    assert segment('d͡ʒ') == ['dʒ']           # tie bar removed, still one unit


def test_segment_diphthongs_are_two_phones():
    # matches the lexicon convention: "duiker  d a ɪ k ɚ"
    assert segment('aɪ') == ['a', 'ɪ']
    assert segment('kwˈeɪbnə') == ['k', 'w', 'e', 'ɪ', 'b', 'n', 'ə']


def test_segment_empty():
    assert segment('') == []


# --- lexicon --------------------------------------------------------------

def test_lexicon_is_loaded(g2p):
    assert len(g2p) > 100_000


def test_ghanaian_names_come_from_the_lexicon(g2p):
    """The whole point: espeak reads these as English and gets them wrong."""
    for name in ['Kwabena', 'Achimota', 'Okuapenhene', 'Bawumia']:
        assert name in g2p
        assert g2p.convert(name).sources == ['lexicon']


def test_lexicon_beats_espeak_on_a_ghanaian_name(g2p):
    import espeak_english
    ours = g2p.word('Kwabena')
    theirs = segment(espeak_english.phonemes('Kwabena'))
    assert ours != theirs           # espeak gives k w e ɪ b n ə
    assert ours == ['k', 'w', 'a', 'b', 'ɪ', 'n', 'a']


def test_lookup_is_case_insensitive(g2p):
    assert g2p.word('kwabena') == g2p.word('KWABENA') == g2p.word('Kwabena')


# --- espeak fallback ------------------------------------------------------

def test_oov_falls_back_to_espeak(g2p):
    word = 'zzzqwertyfoo'
    assert word not in g2p
    result = g2p.convert(word)
    assert result.sources == ['espeak']
    assert result.phones[0]                       # non-empty


def test_no_espeak_mode_reports_unknown():
    g = GhanaEnglishG2P(use_espeak=False)
    result = g.convert('zzzqwertyfoo')
    assert result.sources == ['unknown']
    assert result.phones == [[]]


def test_espeak_output_carries_no_artifacts(g2p):
    """Fallback output must look exactly like lexicon output."""
    phones = g2p.word('zzzqwertyfoo')
    joined = ''.join(phones)
    for artifact in 'ˈˌ͡|‿':
        assert artifact not in joined
    assert all(p.strip() == p and p for p in phones)


# --- text level -----------------------------------------------------------

def test_convert_tracks_provenance(g2p):
    r = g2p.convert('Kwabena zzzqwertyfoo')
    assert r.words == ['Kwabena', 'zzzqwertyfoo']
    assert r.sources == ['lexicon', 'espeak']
    assert r.oov == ['zzzqwertyfoo']
    assert r.coverage == 0.5


def test_punctuation_is_dropped(g2p):
    assert g2p.ipa('Ghana, Ghana!') == g2p.ipa('Ghana Ghana')


def test_sep_controls_phone_spacing(g2p):
    assert g2p.ipa('Ghana', sep=' ').count(' ') > 0
    assert ' ' not in g2p.ipa('Ghana')


def test_call_is_ipa(g2p):
    assert g2p('Ghana') == g2p.ipa('Ghana')


def test_empty_text(g2p):
    assert g2p.ipa('') == ''
    assert g2p.convert('').coverage == 1.0


def test_custom_lexicon_overrides_packaged():
    g = GhanaEnglishG2P(lexicon={'Ghana': 'ɡ a n a'})
    assert g.word('ghana') == ['ɡ', 'a', 'n', 'a']


def test_coverage_helper(g2p):
    assert g2p.coverage(['Kwabena', 'zzzqwertyfoo']) == 0.5
    assert g2p.coverage([]) == 1.0
