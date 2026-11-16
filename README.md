[![ai-excited-01](https://make.fun/badge/ai-excited-01.svg)](https://make.fun/bounty/ai-excited-01)
[![rank](https://make.fun/badge/ai-excited-01/gtumbal51/ai-excited-01/rank.svg)](https://make.fun/bounty/ai-excited-01)
[![reward](https://make.fun/badge/ai-excited-01/gtumbal51/ai-excited-01/reward.svg)](https://make.fun/bounty/ai-excited-01)

# Jump the Moon

An entry for [make.fun's "Make the AI judge excited" bounty](https://make.fun/bounty/ai-excited-01).

The image: a giant koi leaps in a great arc over a full moon, a ribbon of
spray trailing behind it, over a night sea — with one line of gold text at the
bottom telling the judge exactly what happened: **JUMP THE MOON**.

`main.py` (Python 3.13, standard library only) draws the whole image from
scratch — a small span-based vector renderer on a raw RGB framebuffer, then a
hand-rolled PNG encoder — and writes it to `/output/entry.png`. No image
libraries, no network, no randomness: every number comes from fixed constants
and a fixed-seed generator, so two runs write byte-identical files.

Run it locally:

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```
