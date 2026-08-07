"""Command line interface: ghana-english-g2p 'some text'."""

from __future__ import annotations

import argparse
import sys

from .core import GhanaEnglishG2P


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog='ghana-english-g2p',
        description='Ghanaian English text to IPA. Lexicon first, espeak for '
                    'out-of-vocabulary words.')
    ap.add_argument('text', nargs='*', help='text to phonemise (default: stdin)')
    ap.add_argument('-s', '--sep', default='',
                    help="separator between phones (default none; use ' ' to space them)")
    ap.add_argument('--no-espeak', action='store_true',
                    help='do not fall back to espeak; leave unknown words empty')
    ap.add_argument('--show-source', action='store_true',
                    help='print each word with its pronunciation and source')
    args = ap.parse_args(argv)

    text = ' '.join(args.text) if args.text else sys.stdin.read()
    text = text.strip()
    if not text:
        return 0

    g2p = GhanaEnglishG2P(use_espeak=not args.no_espeak)

    if args.show_source:
        result = g2p.convert(text)
        for word, phones, source in zip(result.words, result.phones, result.sources):
            print(f'{word}\t{" ".join(phones)}\t{source}')
        print(f'# lexicon coverage: {result.coverage:.1%}', file=sys.stderr)
    else:
        print(g2p.ipa(text, sep=args.sep))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
