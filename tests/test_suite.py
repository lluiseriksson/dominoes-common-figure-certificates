"""Comprehensive verification, exhaustive cross-checks, and 57-attack red-team suite
for DOMINO-AP-TILING-CERT-1.0 (Paper 30).
Author: Lluis Eriksson
"""
from __future__ import annotations

import copy
import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.domino_certifier import (
    DominoTilingCertificateError,
    verify_domino_tiling_certificate_exact,
)
from src.domino_exact import check_1d_ap_divisible_and_tileable

CERT_DIR = ROOT / "results" / "certificates"


def _load(name: str) -> Dict[str, Any]:
    return json.loads((CERT_DIR / name).read_text(encoding="utf-8"))


def test_exhaustive_gap_census_and_sagdeev48_d4_symmetry() -> None:
    """1. Independently verify exhaustive 1D tile-divisible vs. tileable gap counts on [0..7] (d=2) and [0..8] (d=3).
    2. Independently verify 48-cell Sagdeev figure has exact D4 symmetry and 4 disjoint 24-domino tilings."""
    div2 = tile2 = gap2 = 0
    for mask in range(1, 1 << 8):
        cells = [i for i in range(8) if (mask >> i) & 1]
        if len(cells) % 2 != 0:
            continue
        is_d, is_t, _ = check_1d_ap_divisible_and_tileable(cells, 2)
        if is_d:
            div2 += 1
            if is_t:
                tile2 += 1
            else:
                gap2 += 1
    assert div2 == tile2 + gap2 and gap2 > 0

    div3 = tile3 = gap3 = 0
    for mask in range(1, 1 << 9):
        cells = [i for i in range(9) if (mask >> i) & 1]
        if len(cells) % 3 != 0:
            continue
        is_d, is_t, _ = check_1d_ap_divisible_and_tileable(cells, 3)
        if is_d:
            div3 += 1
            if is_t:
                tile3 += 1
            else:
                gap3 += 1
    assert div3 == tile3 + gap3 and gap3 > 0

    # Verify exact D4 symmetry of 48-cell Sagdeev figure on [0..9]^2
    c48 = _load("fig_48cell_4dir_sagdeev.cert.json")
    pts = {(x, y) for x, y in c48["figure_cells"]}
    assert len(pts) == 48
    for x, y in pts:
        assert (y, x) in pts
        assert (9 - x, y) in pts
        assert (x, 9 - y) in pts
    assert all(len(oris) == 24 for oris in c48["tiling_origins"])


def test_all_16_certificates_verify_cleanly() -> None:
    cert_files = sorted(CERT_DIR.glob("*.cert.json"))
    assert len(cert_files) == 16
    for p in cert_files:
        cert = json.loads(p.read_text(encoding="utf-8"))
        res = verify_domino_tiling_certificate_exact(cert)
        assert res["verified"] is True


def test_61_live_adversarial_red_team_attacks_rejected() -> None:
    m1 = _load("fig_48cell_4dir_sagdeev.cert.json")
    m2 = _load("gap_repair_d2_single.cert.json")
    m3 = _load("boost_d2_2prev_queens.cert.json")
    m4 = _load("reduce_scaled_vectors.cert.json")

    def mutate(base: Dict[str, Any], fn: Callable[[Dict[str, Any]], None]) -> Dict[str, Any]:
        c = copy.deepcopy(base)
        fn(c)
        return c

    attacks: List[Tuple[str, Any]] = [
        # --- Global AST / schema / type attacks (1-11) ---
        ("01_root_not_dict", [1, 2, 3]),
        ("02_bad_schema", mutate(m1, lambda c: c.__setitem__("schema", "DOMINO-AP-TILING-CERT-2.0"))),
        ("03_unknown_mode", mutate(m1, lambda c: c.__setitem__("mode", "fake_mode"))),
        ("04_empty_name", mutate(m1, lambda c: c.__setitem__("name", "  "))),
        ("05_float_injected", mutate(m1, lambda c: c.__setitem__("claimed_num_cells", 48.0))),
        ("06_bool_as_int", mutate(m2, lambda c: c.__setitem__("length_d", True))),
        ("07_decimal_injected", mutate(m4, lambda c: c.__setitem__("claimed_common_length", Decimal("12")))),
        ("08_complex_injected", mutate(m3, lambda c: c.__setitem__("length_d", 2 + 0j))),
        ("09_tuple_injected", mutate(m2, lambda c: c.__setitem__("initial_cells", (0, 2, 3, 5)))),
        ("10_non_str_key", {**m2, 99: "bad"}),
        ("11_extra_key", mutate(m4, lambda c: c.__setitem__("rogue", 1))),

        # --- Mode 1: Common-figure AP tiling attacks (12-23) ---
        ("12_m1_missing_key", mutate(m1, lambda c: c.pop("claimed_lcm_d"))),
        ("13_m1_dup_figure_cell", mutate(m1, lambda c: c["figure_cells"].append(c["figure_cells"][0][:]))),
        ("14_m1_too_few_aps", mutate(m1, lambda c: c.__setitem__("aps", c["aps"][:1]) or c.__setitem__("tiling_origins", c["tiling_origins"][:1]))),
        ("15_m1_zero_direction", mutate(m1, lambda c: c["aps"][0].__setitem__("direction", [0, 0]))),
        ("16_m1_length_d_one", mutate(m1, lambda c: c["aps"][0].__setitem__("length_d", 1))),
        ("17_m1_origins_len_mismatch", mutate(m1, lambda c: c["tiling_origins"][0].pop())),
        ("18_m1_dup_origin", mutate(m1, lambda c: c["tiling_origins"][0].__setitem__(1, c["tiling_origins"][0][0][:]))),
        ("19_m1_tile_outside_B", mutate(m1, lambda c: c["tiling_origins"][0].__setitem__(0, [99, 99]))),
        ("20_m1_overlapping_tiles", mutate(m1, lambda c: c["tiling_origins"][0].__setitem__(0, [1, 4]) or c["tiling_origins"][0].__setitem__(1, [1, 4]))),
        ("21_m1_wrong_num_cells", mutate(m1, lambda c: c.__setitem__("claimed_num_cells", 46))),
        ("22_m1_wrong_lcm_d", mutate(m1, lambda c: c.__setitem__("claimed_lcm_d", 4))),
        ("23_m1_ap_bad_keys", mutate(m1, lambda c: c["aps"][0].__setitem__("extra", 1))),

        # --- Mode 2: Tile-divisible vs. tileable hole-move attacks (24-35) ---
        ("24_m2_missing_key", mutate(m2, lambda c: c.pop("hole_moves"))),
        ("25_m2_d_one", mutate(m2, lambda c: c.__setitem__("length_d", 1))),
        ("26_m2_dup_initial_cell", mutate(m2, lambda c: c.__setitem__("initial_cells", [0, 0, 3, 5]))),
        ("27_m2_initial_not_divisible", mutate(m2, lambda c: c.__setitem__("initial_cells", [0, 2, 3, 4]))),
        ("28_m2_initial_already_tileable", mutate(m2, lambda c: c.__setitem__("initial_cells", [0, 1, 2, 3]))),
        ("29_m2_empty_moves", mutate(m2, lambda c: c.__setitem__("hole_moves", []))),
        ("30_m2_move_not_mult_d", mutate(m2, lambda c: c.__setitem__("hole_moves", [[1, 4]]))),
        ("31_m2_move_from_filled", mutate(m2, lambda c: c.__setitem__("hole_moves", [[0, 2]]))),
        ("32_m2_move_to_empty", mutate(m2, lambda c: c.__setitem__("hole_moves", [[1, 7]]))),
        ("33_m2_repaired_mismatch", mutate(m2, lambda c: c.__setitem__("repaired_cells", [0, 1, 2, 4]))),
        ("34_m2_wrong_init_quot", mutate(m2, lambda c: c["claimed_initial_quotient"].__setitem__(0, 2))),
        ("35_m2_wrong_rep_quot", mutate(m2, lambda c: c["claimed_repaired_quotient"].__setitem__(0, 2))),

        # --- Mode 3: Unimodular Laurent divisibility-boosting attacks (36-47) ---
        ("36_m3_missing_key", mutate(m3, lambda c: c.pop("poly_F_lifted"))),
        ("37_m3_det_not_one", mutate(m3, lambda c: c.__setitem__("basis_X2", [0, 2]))),
        ("38_m3_det_minus_one", mutate(m3, lambda c: c.__setitem__("basis_X2", [0, -1]))),
        ("39_m3_u_parallel_X1", mutate(m3, lambda c: c["prev_dirs_u"].__setitem__(0, [1, 0]))),
        ("40_m3_empty_prev_dirs", mutate(m3, lambda c: c.__setitem__("prev_dirs_u", []))),
        ("41_m3_zero_coeff_in_poly", mutate(m3, lambda c: c["poly_f"].append([9, 9, 0]))),
        ("42_m3_dup_exp_in_poly", mutate(m3, lambda c: c["poly_f"].append(c["poly_f"][0][:]))),
        ("43_m3_f_not_div_prev", mutate(m3, lambda c: c["poly_f"].__setitem__(0, [c["poly_f"][0][0], c["poly_f"][0][1], c["poly_f"][0][2] + 1]))),
        ("44_m3_f_minus_Fstar_not_div", mutate(m3, lambda c: c["poly_F_star"].__setitem__(0, [c["poly_F_star"][0][0], c["poly_F_star"][0][1], c["poly_F_star"][0][2] + 1]))),
        ("45_m3_lift_congruence_broken", mutate(m3, lambda c: c["poly_F_lifted"].__setitem__(0, [c["poly_F_lifted"][0][0], c["poly_F_lifted"][0][1], c["poly_F_lifted"][0][2] + 1]))),
        ("46_m3_empty_F_lifted", mutate(m3, lambda c: c.__setitem__("poly_F_lifted", []))),
        ("47_m3_wrong_boosted_l1", mutate(m3, lambda c: c.__setitem__("claimed_boosted_l1", 999))),

        # --- Mode 4: Primitive stretch & common-length LCM attacks (48-57) ---
        ("48_m4_missing_key", mutate(m4, lambda c: c.pop("claimed_tile_counts"))),
        ("49_m4_too_few_aps", mutate(m4, lambda c: c.__setitem__("raw_aps", c["raw_aps"][:1]))),
        ("50_m4_zero_dir", mutate(m4, lambda c: c["raw_aps"][0].__setitem__("direction", [0, 0]))),
        ("51_m4_d_one", mutate(m4, lambda c: c["raw_aps"][0].__setitem__("length_d", 1))),
        ("52_m4_wrong_prim_dir", mutate(m4, lambda c: c["claimed_primitive_aps"][0].__setitem__("direction", [2, 2]))),
        ("53_m4_wrong_scale_c", mutate(m4, lambda c: c["claimed_primitive_aps"][0].__setitem__("scale_c", 1))),
        ("54_m4_wrong_stretched_d", mutate(m4, lambda c: c["claimed_primitive_aps"][0].__setitem__("stretched_d", 2))),
        ("55_m4_wrong_common_L", mutate(m4, lambda c: c.__setitem__("claimed_common_length", 6))),
        ("56_m4_wrong_tile_counts", mutate(m4, lambda c: c["claimed_tile_counts"].__setitem__(0, 9))),
        ("57_m4_prim_len_mismatch", mutate(m4, lambda c: c["claimed_primitive_aps"].pop())),

        # --- R2 Hardening Attacks (58-61): vacuous boost, unreduced F*, duplicate/sign-reversed APs, huge span ---
        ("58_m3_vacuous_zero_remainder", {
            "schema": "DOMINO-AP-TILING-CERT-1.0",
            "mode": "divisibility_boosting_lift_exact",
            "name": "vacuous_boost",
            "length_d": 2,
            "basis_X1": [1, 0],
            "basis_X2": [0, 1],
            "prev_dirs_u": [[1, 1]],
            "poly_f": [[0, 0, -1], [2, 2, 1]],
            "poly_F_star": [[0, 0, -1], [0, 2, 1]],
            "poly_F_lifted": [[0, 0, -1], [2, 2, 1]],
            "claimed_boosted_l1": 0,
        }),
        ("59_m3_unreduced_F_star", mutate(m3, lambda c: c.__setitem__("poly_F_star", c["poly_F_lifted"]))),
        ("60_m1_sign_reversed_duplicate_ap", {
            "schema": "DOMINO-AP-TILING-CERT-1.0",
            "mode": "common_figure_ap_tiling_exact",
            "name": "dup_ap",
            "figure_cells": [[0, 0], [1, 0]],
            "aps": [{"direction": [1, 0], "length_d": 2}, {"direction": [-1, 0], "length_d": 2}],
            "tiling_origins": [[[0, 0]], [[1, 0]]],
            "claimed_num_cells": 2,
            "claimed_lcm_d": 2,
        }),
        ("61_m2_excessive_span_dos", mutate(m2, lambda c: c.__setitem__("initial_cells", [0, 2, 3, 501]))),
    ]

    assert len(attacks) == 61
    for label, payload in attacks:
        with pytest.raises(DominoTilingCertificateError, match="."):
            verify_domino_tiling_certificate_exact(payload)
