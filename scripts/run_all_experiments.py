"""Generate all 16 canonical DOMINO-AP-TILING-CERT-1.0 certificates and 4 experiment JSONs for Paper 30.
ZERO floating-point arithmetic in any certificate generation or verification.
Author: Lluis Eriksson
"""
from __future__ import annotations

import itertools
import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.domino_certifier import verify_domino_tiling_certificate_exact
from src.domino_exact import (
    Laurent2D,
    check_1d_ap_divisible_and_tileable,
    l2_add,
    l2_mul,
    lcm_list,
)

RESULTS = ROOT / "results"
CERT_DIR = RESULTS / "certificates"
CERT_DIR.mkdir(parents=True, exist_ok=True)


def _greedy_domino_origins(cells: Sequence[Tuple[int, int]], v: Tuple[int, int], d: int = 2) -> List[List[int]]:
    vx, vy = v
    rem = set(cells)
    order = sorted(cells, key=lambda p: (p[0] * vx + p[1] * vy, p[0], p[1]))
    oris: List[List[int]] = []
    for p in order:
        if p not in rem:
            continue
        pts = [(p[0] + j * vx, p[1] + j * vy) for j in range(d)]
        if any(q not in rem for q in pts):
            raise RuntimeError(f"Tiling failed at {p} for v={v}, d={d}")
        for q in pts:
            rem.remove(q)
        oris.append([p[0], p[1]])
    return oris


def _emit_cert(filename: str, cert: Dict[str, Any]) -> Dict[str, Any]:
    path = CERT_DIR / filename
    path.write_text(json.dumps(cert, indent=2) + "\n", encoding="utf-8")
    t0 = time.perf_counter()
    res = verify_domino_tiling_certificate_exact(cert)
    dt_ms = round((time.perf_counter() - t0) * 1000.0, 3)
    return {"file": filename, "mode": cert["mode"], "verify_ms": dt_ms, "summary": res}


def _to_l2_list(p: Laurent2D) -> List[List[int]]:
    return [[e1, e2, c] for (e1, e2), c in sorted(p.items()) if c != 0]


def main() -> None:
    atlas_rows: List[Dict[str, Any]] = []

    # =========================================================================
    # MODE 1: 4 Exact Simultaneous Common-Figure AP Tiling Certificates
    # =========================================================================
    # 1a. 2x2 square tiled by horizontal (1,0) and vertical (0,1) dominoes
    sq2 = [(0, 0), (1, 0), (0, 1), (1, 1)]
    atlas_rows.append(_emit_cert("fig_2x2_standard_dominoes.cert.json", {
        "schema": "DOMINO-AP-TILING-CERT-1.0",
        "mode": "common_figure_ap_tiling_exact",
        "name": "mode1_2x2_standard_dominoes",
        "figure_cells": [[x, y] for x, y in sq2],
        "aps": [{"direction": [1, 0], "length_d": 2}, {"direction": [0, 1], "length_d": 2}],
        "tiling_origins": [_greedy_domino_origins(sq2, (1, 0), 2), _greedy_domino_origins(sq2, (0, 1), 2)],
        "claimed_num_cells": 4,
        "claimed_lcm_d": 2,
    }))

    # 1b. 2x3 rectangle tiled by horizontal d=2 and vertical d=3 APs (mixed lengths!)
    rect23 = [(x, y) for x in range(2) for y in range(3)]
    atlas_rows.append(_emit_cert("fig_2x3_mixed_ap23.cert.json", {
        "schema": "DOMINO-AP-TILING-CERT-1.0",
        "mode": "common_figure_ap_tiling_exact",
        "name": "mode1_2x3_mixed_ap_d2_d3",
        "figure_cells": [[x, y] for x, y in rect23],
        "aps": [{"direction": [1, 0], "length_d": 2}, {"direction": [0, 1], "length_d": 3}],
        "tiling_origins": [_greedy_domino_origins(rect23, (1, 0), 2), _greedy_domino_origins(rect23, (0, 1), 3)],
        "claimed_num_cells": 6,
        "claimed_lcm_d": 6,
    }))

    # 1c. 8-cell 3-direction knight-domino common figure: {(1,0),(0,1),(2,1)} Minkowski sum
    knight8 = sorted({(a + 2 * c, b + c) for a in (0, 1) for b in (0, 1) for c in (0, 1)})
    atlas_rows.append(_emit_cert("fig_8cell_3dir_knight.cert.json", {
        "schema": "DOMINO-AP-TILING-CERT-1.0",
        "mode": "common_figure_ap_tiling_exact",
        "name": "mode1_8cell_3dir_knight_dominoes",
        "figure_cells": [[x, y] for x, y in knight8],
        "aps": [
            {"direction": [1, 0], "length_d": 2},
            {"direction": [0, 1], "length_d": 2},
            {"direction": [2, 1], "length_d": 2},
        ],
        "tiling_origins": [
            _greedy_domino_origins(knight8, (1, 0), 2),
            _greedy_domino_origins(knight8, (0, 1), 2),
            _greedy_domino_origins(knight8, (2, 1), 2),
        ],
        "claimed_num_cells": 8,
        "claimed_lcm_d": 2,
    }))

    # 1d. 48-cell D4-symmetric 4-direction Sagdeev queen-domino figure: {(1,0),(0,1),(1,1),(1,-1)}!
    sagdeev48 = [
        (0, 4), (0, 5), (1, 3), (1, 4), (1, 5), (1, 6), (2, 3), (2, 4), (2, 5), (2, 6),
        (3, 1), (3, 2), (3, 4), (3, 5), (3, 7), (3, 8), (4, 0), (4, 1), (4, 2), (4, 3),
        (4, 6), (4, 7), (4, 8), (4, 9), (5, 0), (5, 1), (5, 2), (5, 3), (5, 6), (5, 7),
        (5, 8), (5, 9), (6, 1), (6, 2), (6, 4), (6, 5), (6, 7), (6, 8), (7, 3), (7, 4),
        (7, 5), (7, 6), (8, 3), (8, 4), (8, 5), (8, 6), (9, 4), (9, 5),
    ]
    atlas_rows.append(_emit_cert("fig_48cell_4dir_sagdeev.cert.json", {
        "schema": "DOMINO-AP-TILING-CERT-1.0",
        "mode": "common_figure_ap_tiling_exact",
        "name": "mode1_48cell_4dir_sagdeev_queens",
        "figure_cells": [[x, y] for x, y in sagdeev48],
        "aps": [
            {"direction": [1, 0], "length_d": 2},
            {"direction": [0, 1], "length_d": 2},
            {"direction": [1, 1], "length_d": 2},
            {"direction": [1, -1], "length_d": 2},
        ],
        "tiling_origins": [
            _greedy_domino_origins(sagdeev48, (1, 0), 2),
            _greedy_domino_origins(sagdeev48, (0, 1), 2),
            _greedy_domino_origins(sagdeev48, (1, 1), 2),
            _greedy_domino_origins(sagdeev48, (1, -1), 2),
        ],
        "claimed_num_cells": 48,
        "claimed_lcm_d": 2,
    }))

    # =========================================================================
    # MODE 2: 4 Tile-Divisible Gap vs. Step-d Hole-Move Repair Certificates (Steps 5-6)
    # =========================================================================
    m2_specs = [
        ("gap_repair_d2_single.cert.json", "mode2_gap_d2_single", 2, [0, 2, 3, 5], [[1, 5]], [0, 1, 2, 3]),
        ("gap_repair_d3_single.cert.json", "mode2_gap_d3_single", 3, [0, 2, 4], [[1, 4]], [0, 1, 2]),
        ("gap_repair_d2_double.cert.json", "mode2_gap_d2_double", 2, [0, 2, 4, 5, 7, 9], [[1, 5], [3, 9]], [0, 1, 2, 3, 4, 7]),
        # Wait: check [0,1,2,3,4,7] for d=2: 4 and 7 -> 4 is unpaired! Let's fix to [[1,9],[3,7]] -> [0,1,2,3,4,5]!
    ]
    m2_specs_clean = [
        ("gap_repair_d2_single.cert.json", "mode2_gap_d2_single", 2, [0, 2, 3, 5], [[1, 5]], [0, 1, 2, 3]),
        ("gap_repair_d3_single.cert.json", "mode2_gap_d3_single", 3, [0, 2, 4], [[1, 4]], [0, 1, 2]),
        ("gap_repair_d2_double.cert.json", "mode2_gap_d2_double", 2, [0, 2, 4, 5, 7, 9], [[1, 9], [3, 7]], [0, 1, 2, 3, 4, 5]),
        ("gap_repair_d4_double.cert.json", "mode2_gap_d4_double", 4, [0, 2, 3, 5], [[1, 5]], [0, 1, 2, 3]),
    ]
    for fname, cname, d, init_c, moves, rep_c in m2_specs_clean:
        _, _, q0 = check_1d_ap_divisible_and_tileable(init_c, d)
        _, _, q1 = check_1d_ap_divisible_and_tileable(rep_c, d)
        atlas_rows.append(_emit_cert(fname, {
            "schema": "DOMINO-AP-TILING-CERT-1.0",
            "mode": "tile_divisible_vs_tileable_exact",
            "name": cname,
            "length_d": d,
            "initial_cells": init_c,
            "hole_moves": moves,
            "repaired_cells": rep_c,
            "claimed_initial_quotient": q0,
            "claimed_repaired_quotient": q1,
        }))

    # =========================================================================
    # MODE 3: 4 Section 2.1 Unimodular Laurent Divisibility-Boosting Certificates
    # =========================================================================
    def _binom_diff(du: Tuple[int, int]) -> Laurent2D:
        return {(0, 0): -1, du: 1}

    # 3a. d=2, i=2 (1 prev dir u=(1,1)), X1=(1,0), X2=(0,1):
    #     f = (X^{(2,2)} - 1) * (1 + X^{(1,0)}) -> divisible by X^{(2,2)}-1!
    #     Lifted F = (1 - X^{(2,2)}) * X^{(0,0)} + ... pick f = (X^{(2,2)}-1)*(1 + X^{(2,0)} + X^{(0,1)}),
    #     Let F_lifted = (X^{(2,2)}-1) * (1 + X^{(0,1)}) -> f - F_lifted = (X^{(2,2)}-1)*X^{(2,0)}? Wait: needs (X_1^2 - 1) | (f - F_lifted)!
    #     Construct directly: f = (X_1^d - 1)*A + F_lifted where EVERY term of F_lifted is divisible by prod (X^{d*u} - 1),
    #     and F* = pi_rep(F_lifted) (reduced mod X_1^d - 1)! Then:
    #       (X^{d*u} - 1) | f if A is also divisible by (X^{d*u} - 1)!
    #       (X_1^d - 1) | (f - F*) AND (X_1^d - 1) | (f - F_lifted) AND (X^{d*u} - 1) | (f - F_lifted)!!
    def _make_boost_cert(
        fname: str, cname: str, d: int,
        X1: Tuple[int, int], X2: Tuple[int, int],
        us: List[Tuple[int, int]],
        Q_A: Laurent2D, Q_F: Laurent2D,
    ) -> Dict[str, Any]:
        prod_u: Laurent2D = {(0, 0): 1}
        for u in us:
            prod_u = l2_mul(prod_u, _binom_diff((d * u[0], d * u[1])))
        A = l2_mul(prod_u, Q_A)
        F_lifted = l2_mul(prod_u, Q_F)
        X1d_m1 = _binom_diff((d, 0))
        f_new = l2_mul(X1d_m1, A)
        f_poly = l2_add(f_new, F_lifted)
        # F_star = exact reduction of F_lifted mod (X_1^d - 1)
        F_star: Laurent2D = {}
        for (e1, e2), c in F_lifted.items():
            key = (e1 % d, e2)
            nv = F_star.get(key, 0) + c
            if nv == 0:
                F_star.pop(key, None)
            else:
                F_star[key] = nv
        l1_new = sum(abs(v) for v in f_new.values())
        return _emit_cert(fname, {
            "schema": "DOMINO-AP-TILING-CERT-1.0",
            "mode": "divisibility_boosting_lift_exact",
            "name": cname,
            "length_d": d,
            "basis_X1": [X1[0], X1[1]],
            "basis_X2": [X2[0], X2[1]],
            "prev_dirs_u": [[u[0], u[1]] for u in us],
            "poly_f": _to_l2_list(f_poly),
            "poly_F_star": _to_l2_list(F_star),
            "poly_F_lifted": _to_l2_list(F_lifted),
            "claimed_boosted_l1": l1_new,
        })

    atlas_rows.append(_make_boost_cert(
        "boost_d2_1prev_diag.cert.json", "mode3_boost_d2_i2", 2,
        (1, 0), (0, 1), [(1, 1)], {(0, 0): 1, (0, 1): 1}, {(0, 0): 1},
    ))
    atlas_rows.append(_make_boost_cert(
        "boost_d3_1prev_shear.cert.json", "mode3_boost_d3_i2", 3,
        (1, 1), (0, 1), [(1, -1)], {(0, 0): 1, (1, 0): -1}, {(1, 0): 1},
    ))
    atlas_rows.append(_make_boost_cert(
        "boost_d2_2prev_queens.cert.json", "mode3_boost_d2_i3", 2,
        (1, 0), (0, 1), [(0, 1), (1, 1)], {(0, 0): 1}, {(1, 0): 1},
    ))
    atlas_rows.append(_make_boost_cert(
        "boost_d2_3prev_4dir.cert.json", "mode3_boost_d2_i4", 2,
        (1, 0), (0, 1), [(0, 1), (1, 1), (1, -1)], {(0, 0): 1}, {(0, 0): 1},
    ))

    # =========================================================================
    # MODE 4: 4 Section 2 Primitive-Stretch & Common-Length LCM Reductions
    # =========================================================================
    m4_specs = [
        ("reduce_gap_domino_d5.cert.json", "mode4_tikhomirov_d5_gap", [
            {"direction": [1, 0], "length_d": 2},
            {"direction": [0, 1], "length_d": 2},
            {"direction": [1, 1], "length_d": 2},
            {"direction": [1, -1], "length_d": 2},
            {"direction": [2, 0], "length_d": 2},  # horizontal domino with gap -> c=2, stretched d=4!
        ]),
        ("reduce_mixed_aps_234.cert.json", "mode4_mixed_lengths_234", [
            {"direction": [1, 0], "length_d": 2},
            {"direction": [0, 1], "length_d": 3},
            {"direction": [1, 1], "length_d": 4},
        ]),
        ("reduce_scaled_vectors.cert.json", "mode4_scaled_nonprimitive", [
            {"direction": [2, 2], "length_d": 2},   # c=2, prim (1,1), stretched=4
            {"direction": [3, 0], "length_d": 2},   # c=3, prim (1,0), stretched=6
            {"direction": [0, -2], "length_d": 3},  # c=2, prim (0,1), stretched=6 -> L=12!
        ]),
        ("reduce_coprime_prime_aps.cert.json", "mode4_coprime_235", [
            {"direction": [1, 0], "length_d": 2},
            {"direction": [0, 1], "length_d": 3},
            {"direction": [2, 1], "length_d": 5},   # L = 30!
        ]),
    ]
    for fname, cname, raw_aps in m4_specs:
        prim = []
        sds = []
        for ap in raw_aps:
            vx, vy = ap["direction"]
            d = ap["length_d"]
            g = math.gcd(abs(vx), abs(vy))
            px, py = vx // g, vy // g
            if px < 0 or (px == 0 and py < 0):
                px, py = -px, -py
            cd = g * d
            prim.append({"direction": [px, py], "scale_c": g, "stretched_d": cd})
            sds.append(cd)
        L = lcm_list(sds)
        atlas_rows.append(_emit_cert(fname, {
            "schema": "DOMINO-AP-TILING-CERT-1.0",
            "mode": "ap_primitive_lcm_reduction_exact",
            "name": cname,
            "raw_aps": raw_aps,
            "claimed_primitive_aps": prim,
            "claimed_common_length": L,
            "claimed_tile_counts": [L // cd for cd in sds],
        }))

    (RESULTS / "exp1_certified_atlas.json").write_text(
        json.dumps({"experiment": "exp1_certified_atlas", "count": len(atlas_rows), "rows": atlas_rows}, indent=2) + "\n",
        encoding="utf-8",
    )

    # =========================================================================
    # EXP 2: Exhaustive 1D Tile-Divisible vs. Tileable Gap Census on [0..L-1] (d=2, 3)
    # =========================================================================
    exp2_rows = []
    for d, L_list in [(2, [4, 6, 8, 10]), (3, [6, 9, 12])]:
        for L_box in L_list:
            div_cnt = 0
            tile_cnt = 0
            gap_cnt = 0
            for mask in range(1, 1 << L_box):
                cells = [i for i in range(L_box) if (mask >> i) & 1]
                if len(cells) % d != 0:
                    continue
                is_div, is_tile, _ = check_1d_ap_divisible_and_tileable(cells, d)
                if is_div:
                    div_cnt += 1
                    if is_tile:
                        tile_cnt += 1
                    else:
                        gap_cnt += 1
            exp2_rows.append({
                "length_d": d,
                "box_L": L_box,
                "divisible_count": div_cnt,
                "tileable_count": tile_cnt,
                "strict_gap_count": gap_cnt,
            })
    (RESULTS / "exp2_divisible_vs_tileable_census.json").write_text(
        json.dumps({"experiment": "exp2_divisible_vs_tileable_census", "rows": exp2_rows}, indent=2) + "\n",
        encoding="utf-8",
    )

    # =========================================================================
    # EXP 3: 48-Cell 4-Direction Sagdeev Figure & Tiling Export (for Fig 1)
    # =========================================================================
    exp3 = {
        "experiment": "exp3_sagdeev_48cell_tilings",
        "num_cells": len(sagdeev48),
        "cells": [[x, y] for x, y in sagdeev48],
        "tiling_horiz": _greedy_domino_origins(sagdeev48, (1, 0), 2),
        "tiling_vert": _greedy_domino_origins(sagdeev48, (0, 1), 2),
        "tiling_diag": _greedy_domino_origins(sagdeev48, (1, 1), 2),
        "tiling_antidiag": _greedy_domino_origins(sagdeev48, (1, -1), 2),
    }
    (RESULTS / "exp3_sagdeev_48cell_tilings.json").write_text(
        json.dumps(exp3, indent=2) + "\n", encoding="utf-8"
    )

    # =========================================================================
    # EXP 4: Divisibility Boosting Support Growth (i = 2, 3, 4 directions)
    # =========================================================================
    exp4_rows = []
    for r in atlas_rows:
        if r["mode"] == "divisibility_boosting_lift_exact":
            cert = json.loads((CERT_DIR / r["file"]).read_text(encoding="utf-8"))
            exp4_rows.append({
                "name": r["file"].replace(".cert.json", ""),
                "length_d": cert["length_d"],
                "num_prev_dirs": len(cert["prev_dirs_u"]),
                "f_terms": len(cert["poly_f"]),
                "F_star_terms": len(cert["poly_F_star"]),
                "F_lifted_terms": len(cert["poly_F_lifted"]),
                "boosted_l1": cert["claimed_boosted_l1"],
            })
    (RESULTS / "exp4_boosting_lift_stats.json").write_text(
        json.dumps({"experiment": "exp4_boosting_lift_stats", "rows": exp4_rows}, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"[PASS] Generated & verified {len(atlas_rows)}/16 exact-Z certificates and 4 experiment JSONs.")
    for r in atlas_rows:
        print(f"  {r['file']:44s} {r['verify_ms']:6.3f} ms  {r['summary']}")


if __name__ == "__main__":
    main()
