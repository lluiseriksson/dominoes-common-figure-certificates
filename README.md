# Machine-Checked Exact-Integer Simultaneous Tiling, Hole-Move Repair, and Laurent Divisibility-Boosting Certificates for Dominoes Tiling a Common Figure

**Author:** Lluis Eriksson (with transparent AI assistance via Google Antigravity)  
**License:** MIT (code, Lean 4 proofs, certificates) / CC-BY-4.0 (manuscript)

Zero-dependency Lean 4 formalization and pure-stdlib exact-$\mathbb{Z}$ certificate verifier (`DOMINO-AP-TILING-CERT-1.0`) for the finite tiling, tile-divisibility gap, step-$d$ hole-move repair, unimodular basis-change, and Laurent divisibility-boosting core of Peter Keevash & Jeck Lim (*Dominoes tiling a common figure*, `arXiv:2611.33154`, November 24, 2026).

## Verification Summary
- **Lean 4 Kernel (`lean/DominoesCommonFigure.lean`, Lean 4.35.0):** 18/18 constructive theorems, 0 warnings, 0 `sorry`, 0 `Classical.choice`, 2 zero-axiom theorems (`ap_tiling_cardinality_divisible`, `standard_2x2_square_tiled_both`) + 5 `[propext]` + 11 `[propext, Quot.sound]`, formalizing primitive-stretch and LCM partitions, $(1-t)D_d(t) = 1 - t^d$, exact $d=2$ and $d=3$ tile-divisible-yet-untileable witnesses, single step-$d$ hole-move repairs, unimodular $\det=1$ Cramer basis decomposition, Laurent divisibility boosting, and parallel-line conservation.
- **Exact-$\mathbb{Z}$ Certificate Atlas (`results/certificates/*.cert.json`):** 16 canonical certificates across 4 modes (simultaneous common figures including a 48-cell $D_4$-symmetric 4-direction Sagdeev queen-domino figure tiled simultaneously by 24 dominoes in each of `(1,0),(0,1),(1,1),(1,-1)`; Step 5–6 gap-and-repair certificates for $d=2,3,4$; Section 2.1 unimodular Laurent divisibility-boosting lifts up to 4 directions; Section 2 primitive-stretch & LCM reductions including Tikhomirov's $D_5$ gap domino).
- **Cross-Checks & Red-Team Suite (`tests/test_suite.py`):** Exhaustive 1D tile-divisible vs. tileable gap census on $[0..7]$ ($d=2$) and $[0..8]$ ($d=3$), independent $D_4$-symmetry check of the 48-cell Sagdeev figure, 16/16 certificate replays, and **61/61** live adversarial attacks rejected.

## One-Command Reproducibility
```bash
python scripts/verify_all.py
```
To regenerate all certificates, experiment JSONs, and 300-DPI figures from scratch:
```bash
python scripts/run_all_experiments.py
python scripts/make_figures.py
python scripts/verify_all.py
```
