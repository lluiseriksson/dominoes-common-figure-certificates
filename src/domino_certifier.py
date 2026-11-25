"""Pure-stdlib zero-float verifier for DOMINO-AP-TILING-CERT-1.0 certificates.
Supports four exact-Z verification modes aligned with Peter Keevash & Jeck Lim
(arXiv:2611.33154, Nov 24, 2026) "Dominoes tiling a common figure":
  1. common_figure_ap_tiling_exact   (Prob 1.1 & Thm 1.2: finite B subset Z^2 simultaneously tiled by APs D_1..D_k + Laurent identity)
  2. tile_divisible_vs_tileable_exact (Steps 5-6: signed integral Z[t]-divisibility gap vs. step-d hole-move repair to {0,1}-tileability)
  3. divisibility_boosting_lift_exact (Sec 2.1 pp.5-6: unimodular det=1 basis change, mod (X_1^d-1) lift, simultaneous boosted divisibility)
  4. ap_primitive_lcm_reduction_exact (Sec 2 p.3: primitive stretch v=c*v' & common-length lcm(d_1..d_k) exact disjoint partitions)

Author: Lluis Eriksson
"""
from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Set, Tuple

from src.domino_exact import (
    Laurent2D,
    ap_laurent_2d,
    check_1d_ap_divisible_and_tileable,
    l2_divisible_by_binomial_diff,
    l2_mod_X1d_minus_1,
    l2_mul,
    l2_sub,
    lcm_list,
)

SCHEMA_VERSION = "DOMINO-AP-TILING-CERT-1.0"


class DominoTilingCertificateError(ValueError):
    """Raised whenever any DOMINO-AP-TILING-CERT-1.0 verification check fails."""


def _assert_strict_json_types(obj: Any, path: str = "root") -> None:
    t = type(obj)
    if t is int or t is str or obj is None:
        return
    if t is dict:
        for k, v in obj.items():
            if type(k) is not str:
                raise DominoTilingCertificateError(f"Non-str dict key at {path}: {type(k).__name__}")
            _assert_strict_json_types(v, f"{path}.{k}")
        return
    if t is list:
        for i, v in enumerate(obj):
            _assert_strict_json_types(v, f"{path}[{i}]")
        return
    raise DominoTilingCertificateError(f"Forbidden type {t.__name__} at {path}")


def _parse_int(val: Any, name: str) -> int:
    if type(val) is not int:
        raise DominoTilingCertificateError(f"{name} must be strict int, got {type(val).__name__}")
    return val


def _parse_pt2(val: Any, name: str) -> Tuple[int, int]:
    if type(val) is not list or len(val) != 2:
        raise DominoTilingCertificateError(f"{name} must be [x, y]")
    return _parse_int(val[0], f"{name}[0]"), _parse_int(val[1], f"{name}[1]")


def _parse_laurent2d(raw: Any, name: str) -> Laurent2D:
    if type(raw) is not list or len(raw) > 512:
        raise DominoTilingCertificateError(f"{name} must be list of [e1, e2, coeff] triples (len <= 512)")
    out: Laurent2D = {}
    for i, item in enumerate(raw):
        if type(item) is not list or len(item) != 3:
            raise DominoTilingCertificateError(f"{name}[{i}] must be [e1, e2, coeff]")
        e1 = _parse_int(item[0], f"{name}[{i}][0]")
        e2 = _parse_int(item[1], f"{name}[{i}][1]")
        c = _parse_int(item[2], f"{name}[{i}][2]")
        if c == 0 or (e1, e2) in out:
            raise DominoTilingCertificateError(f"{name}[{i}] has zero coeff or duplicate exponent")
        out[(e1, e2)] = c
    return out


def _verify_mode1_common_figure(cert: Dict[str, Any]) -> Dict[str, Any]:
    req = {
        "schema", "mode", "name", "figure_cells", "aps",
        "tiling_origins", "claimed_num_cells", "claimed_lcm_d",
    }
    if set(cert.keys()) != req:
        raise DominoTilingCertificateError(f"Mode 1 key mismatch: {sorted(set(cert.keys()) ^ req)}")
    cells_raw = cert["figure_cells"]
    if type(cells_raw) is not list or len(cells_raw) < 2 or len(cells_raw) > 512:
        raise DominoTilingCertificateError("figure_cells must be list of 2..512 lattice points")
    B_set: Set[Tuple[int, int]] = set()
    for i, c in enumerate(cells_raw):
        pt = _parse_pt2(c, f"figure_cells[{i}]")
        if pt in B_set:
            raise DominoTilingCertificateError(f"Duplicate cell {pt} in figure_cells")
        B_set.add(pt)

    aps_raw = cert["aps"]
    ori_raw = cert["tiling_origins"]
    if type(aps_raw) is not list or not (2 <= len(aps_raw) <= 6):
        raise DominoTilingCertificateError("aps must be list of 2..6 arithmetic progressions")
    if type(ori_raw) is not list or len(ori_raw) != len(aps_raw):
        raise DominoTilingCertificateError("tiling_origins length must match aps")

    P_B: Laurent2D = {pt: 1 for pt in B_set}
    ds: List[int] = []
    seen_canonical_aps: Set[Tuple[int, int, int]] = set()
    for idx, ap in enumerate(aps_raw):
        if type(ap) is not dict or set(ap.keys()) != {"direction", "length_d"}:
            raise DominoTilingCertificateError(f"aps[{idx}] must have direction and length_d")
        v = _parse_pt2(ap["direction"], f"aps[{idx}].direction")
        d = _parse_int(ap["length_d"], f"aps[{idx}].length_d")
        if v == (0, 0) or d < 2 or d > 12:
            raise DominoTilingCertificateError(f"aps[{idx}] invalid direction or length_d")
        cvx, cvy = v
        if cvx < 0 or (cvx == 0 and cvy < 0):
            cvx, cvy = -cvx, -cvy
        if (cvx, cvy, d) in seen_canonical_aps:
            raise DominoTilingCertificateError(f"Duplicate or sign-reversed AP at index {idx}")
        seen_canonical_aps.add((cvx, cvy, d))
        ds.append(d)

        oris = ori_raw[idx]
        if type(oris) is not list or len(oris) * d != len(B_set):
            raise DominoTilingCertificateError(f"tiling_origins[{idx}] count * d != |B|")
        covered: Set[Tuple[int, int]] = set()
        Q_i: Laurent2D = {}
        for t_idx, o_raw in enumerate(oris):
            ox, oy = _parse_pt2(o_raw, f"origins[{idx}][{t_idx}]")
            if (ox, oy) in Q_i:
                raise DominoTilingCertificateError(f"Duplicate tile origin {(ox, oy)} for AP {idx}")
            Q_i[(ox, oy)] = 1
            for j in range(d):
                cell = (ox + j * v[0], oy + j * v[1])
                if cell not in B_set:
                    raise DominoTilingCertificateError(f"Tile cell {cell} lies OUTSIDE B for AP {idx}")
                if cell in covered:
                    raise DominoTilingCertificateError(f"Overlapping tiles at {cell} for AP {idx}")
                covered.add(cell)
        if covered != B_set:
            raise DominoTilingCertificateError(f"Tiling {idx} does not cover B exactly")
        # Independent Laurent polynomial multiplication check: P_D * Q_i == P_B!
        if l2_mul(ap_laurent_2d(v, d), Q_i) != P_B:
            raise DominoTilingCertificateError(f"Laurent identity P_D * Q_{idx} != P_B")

    lcm_d = lcm_list(ds)
    if len(B_set) % lcm_d != 0:
        raise DominoTilingCertificateError("Impossible: lcm(d_i) does not divide |B|")
    if _parse_int(cert["claimed_num_cells"], "claimed_num_cells") != len(B_set):
        raise DominoTilingCertificateError(f"claimed_num_cells mismatch: exact={len(B_set)}")
    if _parse_int(cert["claimed_lcm_d"], "claimed_lcm_d") != lcm_d:
        raise DominoTilingCertificateError(f"claimed_lcm_d mismatch: exact={lcm_d}")

    return {
        "verified": True,
        "mode": cert["mode"],
        "num_cells": len(B_set),
        "num_aps": len(ds),
        "lcm_d": lcm_d,
    }


def _verify_mode2_divisible_vs_tileable(cert: Dict[str, Any]) -> Dict[str, Any]:
    req = {
        "schema", "mode", "name", "length_d", "initial_cells",
        "hole_moves", "repaired_cells",
        "claimed_initial_quotient", "claimed_repaired_quotient",
    }
    if set(cert.keys()) != req:
        raise DominoTilingCertificateError(f"Mode 2 key mismatch: {sorted(set(cert.keys()) ^ req)}")
    d = _parse_int(cert["length_d"], "length_d")
    if not (2 <= d <= 8):
        raise DominoTilingCertificateError("Require 2 <= length_d <= 8")
    init_raw = cert["initial_cells"]
    rep_raw = cert["repaired_cells"]
    if type(init_raw) is not list or type(rep_raw) is not list or len(init_raw) < d or len(init_raw) != len(rep_raw):
        raise DominoTilingCertificateError("initial_cells and repaired_cells must be equal-length lists >= d")
    init_cells = [_parse_int(c, f"init[{i}]") for i, c in enumerate(init_raw)]
    rep_cells = [_parse_int(c, f"rep[{i}]") for i, c in enumerate(rep_raw)]
    if len(set(init_cells)) != len(init_cells) or len(set(rep_cells)) != len(rep_cells):
        raise DominoTilingCertificateError("Duplicate cells in initial_cells or repaired_cells")
    if max(init_cells) - min(init_cells) > 256 or max(rep_cells) - min(rep_cells) > 256:
        raise DominoTilingCertificateError("1D cell span exceeds certified bound 256")

    # 1. Verify initial_cells IS tile-divisible by D_d yet NOT tileable (strict Step 5 -> Step 6 gap!)
    div0, tile0, q0 = check_1d_ap_divisible_and_tileable(init_cells, d)
    if not div0:
        raise DominoTilingCertificateError("initial_cells is NOT D_d-divisible")
    if tile0:
        raise DominoTilingCertificateError("initial_cells is ALREADY tileable (no Step 5-6 gap)")

    # 2. Apply each exact step-d hole move [from_hole, to_cell] (congruent mod d!)
    moves_raw = cert["hole_moves"]
    if type(moves_raw) is not list or len(moves_raw) == 0 or len(moves_raw) > 32:
        raise DominoTilingCertificateError("hole_moves must be 1..32 [hole_old, hole_new] pairs")
    cur_set = set(init_cells)
    for i, mv in enumerate(moves_raw):
        if type(mv) is not list or len(mv) != 2:
            raise DominoTilingCertificateError(f"hole_moves[{i}] must be [hole_old, hole_new]")
        h_old = _parse_int(mv[0], f"mv[{i}][0]")
        h_new = _parse_int(mv[1], f"mv[{i}][1]")
        if h_old == h_new or (h_new - h_old) % d != 0:
            raise DominoTilingCertificateError(f"hole_moves[{i}] step is not a non-zero multiple of d={d}")
        if h_old in cur_set or h_new not in cur_set:
            raise DominoTilingCertificateError(f"hole_moves[{i}] invalid: h_old must be empty hole, h_new must be filled cell")
        cur_set.remove(h_new)
        cur_set.add(h_old)

    if cur_set != set(rep_cells):
        raise DominoTilingCertificateError("Result of hole_moves does NOT match repaired_cells")

    # 3. Verify repaired_cells IS both D_d-divisible AND {0,1}-tileable (all quotient entries >= 0)!
    div1, tile1, q1 = check_1d_ap_divisible_and_tileable(rep_cells, d)
    if not (div1 and tile1):
        raise DominoTilingCertificateError("repaired_cells is NOT tileable by D_d")

    cq0_raw = cert["claimed_initial_quotient"]
    cq1_raw = cert["claimed_repaired_quotient"]
    if type(cq0_raw) is not list or [_parse_int(v, "cq0") for v in cq0_raw] != q0:
        raise DominoTilingCertificateError(f"claimed_initial_quotient mismatch: exact={q0}")
    if type(cq1_raw) is not list or [_parse_int(v, "cq1") for v in cq1_raw] != q1:
        raise DominoTilingCertificateError(f"claimed_repaired_quotient mismatch: exact={q1}")

    return {
        "verified": True,
        "mode": cert["mode"],
        "length_d": d,
        "num_cells": len(init_cells),
        "num_hole_moves": len(moves_raw),
        "initial_min_q": min(q0),
        "repaired_min_q": min(q1),
    }


def _verify_mode3_divisibility_boost(cert: Dict[str, Any]) -> Dict[str, Any]:
    req = {
        "schema", "mode", "name", "length_d",
        "basis_X1", "basis_X2", "prev_dirs_u",
        "poly_f", "poly_F_star", "poly_F_lifted",
        "claimed_boosted_l1",
    }
    if set(cert.keys()) != req:
        raise DominoTilingCertificateError(f"Mode 3 key mismatch: {sorted(set(cert.keys()) ^ req)}")
    d = _parse_int(cert["length_d"], "length_d")
    if not (2 <= d <= 6):
        raise DominoTilingCertificateError("Require 2 <= length_d <= 6")
    X1 = _parse_pt2(cert["basis_X1"], "basis_X1")
    X2 = _parse_pt2(cert["basis_X2"], "basis_X2")
    if X1[0] * X2[1] - X1[1] * X2[0] != 1:
        raise DominoTilingCertificateError("Unimodular basis requires det(X1, X2) == 1")

    u_raw = cert["prev_dirs_u"]
    if type(u_raw) is not list or not (1 <= len(u_raw) <= 4):
        raise DominoTilingCertificateError("prev_dirs_u must be 1..4 vectors in (X1, X2)-coordinates")
    us = [_parse_pt2(u, f"u[{i}]") for i, u in enumerate(u_raw)]
    if any(u[1] == 0 for u in us):
        raise DominoTilingCertificateError("Each previous direction u must be non-parallel to X1 (u2 != 0)")

    poly_f = _parse_laurent2d(cert["poly_f"], "poly_f")
    poly_Fs = _parse_laurent2d(cert["poly_F_star"], "poly_F_star")
    poly_F = _parse_laurent2d(cert["poly_F_lifted"], "poly_F_lifted")
    if not poly_f or not poly_F:
        raise DominoTilingCertificateError("poly_f and poly_F_lifted must be non-zero")
    if any(not (0 <= e1 < d) for (e1, _) in poly_Fs):
        raise DominoTilingCertificateError("poly_F_star must be reduced modulo (X_1^d - 1) with 0 <= e1 < d")

    # 1. Verify preconditions (Sec 2.1 pp. 5-6):
    #    (a) (X^{d*u} - 1) | f for all u in prev_dirs_u
    for idx, u in enumerate(us):
        du = (d * u[0], d * u[1])
        if not l2_divisible_by_binomial_diff(poly_f, du):
            raise DominoTilingCertificateError(f"Precondition failed: (X^(d*u[{idx}]) - 1) does NOT divide f")
    #    (b) (X_1^d - 1) | (f - F*)
    if not l2_divisible_by_binomial_diff(l2_sub(poly_f, poly_Fs), (d, 0)):
        raise DominoTilingCertificateError("Precondition failed: (X_1^d - 1) does NOT divide (f - F*)")

    # 2. Verify modulo-(X_1^d - 1) lift congruence: pi(F_lifted) == pi(F*) == pi(f)!
    if l2_mod_X1d_minus_1(poly_F, d) != l2_mod_X1d_minus_1(poly_Fs, d):
        raise DominoTilingCertificateError("Lift congruence failed: pi(F_lifted) != pi(F*) mod (X_1^d - 1)")

    # 3. Verify BOTH boosted divisibilities on non-zero remainder f_new = f - F_lifted!
    f_new = l2_sub(poly_f, poly_F)
    if not f_new:
        raise DominoTilingCertificateError("Trivial vacuous boost (f - F_lifted == 0) is forbidden")
    if not l2_divisible_by_binomial_diff(f_new, (d, 0)):
        raise DominoTilingCertificateError("Boosted divisibility (X_1^d - 1) | (f - F) failed")
    for idx, u in enumerate(us):
        du = (d * u[0], d * u[1])
        if not l2_divisible_by_binomial_diff(poly_F, du):
            raise DominoTilingCertificateError(f"Lifted F not divisible by (X^(d*u[{idx}]) - 1)")
        if not l2_divisible_by_binomial_diff(f_new, du):
            raise DominoTilingCertificateError(f"Boosted (f - F) lost divisibility by (X^(d*u[{idx}]) - 1)")

    l1_new = sum(abs(v) for v in f_new.values())
    if _parse_int(cert["claimed_boosted_l1"], "claimed_boosted_l1") != l1_new:
        raise DominoTilingCertificateError(f"claimed_boosted_l1 mismatch: exact={l1_new}")

    return {
        "verified": True,
        "mode": cert["mode"],
        "length_d": d,
        "num_prev_dirs": len(us),
        "boosted_l1": l1_new,
    }


def _verify_mode4_primitive_lcm(cert: Dict[str, Any]) -> Dict[str, Any]:
    req = {
        "schema", "mode", "name", "raw_aps",
        "claimed_primitive_aps", "claimed_common_length", "claimed_tile_counts",
    }
    if set(cert.keys()) != req:
        raise DominoTilingCertificateError(f"Mode 4 key mismatch: {sorted(set(cert.keys()) ^ req)}")
    raw_aps = cert["raw_aps"]
    if type(raw_aps) is not list or not (2 <= len(raw_aps) <= 8):
        raise DominoTilingCertificateError("raw_aps must be 2..8 AP specs")

    prim_expected: List[Dict[str, Any]] = []
    stretched_ds: List[int] = []
    seen_raw_aps: Set[Tuple[int, int, int]] = set()
    for i, ap in enumerate(raw_aps):
        if type(ap) is not dict or set(ap.keys()) != {"direction", "length_d"}:
            raise DominoTilingCertificateError(f"raw_aps[{i}] must have direction and length_d")
        vx, vy = _parse_pt2(ap["direction"], f"raw_aps[{i}].direction")
        d = _parse_int(ap["length_d"], f"raw_aps[{i}].length_d")
        if (vx, vy) == (0, 0) or d < 2 or d > 24:
            raise DominoTilingCertificateError(f"raw_aps[{i}] invalid direction or length_d")
        cvx, cvy = (-vx, -vy) if (vx < 0 or (vx == 0 and vy < 0)) else (vx, vy)
        if (cvx, cvy, d) in seen_raw_aps:
            raise DominoTilingCertificateError(f"Duplicate or sign-reversed AP in raw_aps[{i}]")
        seen_raw_aps.add((cvx, cvy, d))
        g = math.gcd(abs(vx), abs(vy))
        px, py = vx // g, vy // g
        # Canonicalize sign so first non-zero coordinate is positive
        if px < 0 or (px == 0 and py < 0):
            px, py = -px, -py
        cd = g * d
        # Verify explicit primitive stretch partition: {0..cd-1} partitioned into g translates of {0, g, ..., (d-1)g}
        covered = set()
        for r in range(g):
            for j in range(d):
                pos = r + j * g
                if pos in covered or not (0 <= pos < cd):
                    raise DominoTilingCertificateError("Internal primitive stretch partition failed")
                covered.add(pos)
        if len(covered) != cd:
            raise DominoTilingCertificateError("Internal primitive stretch coverage failed")
        prim_expected.append({"direction": [px, py], "scale_c": g, "stretched_d": cd})
        stretched_ds.append(cd)

    L = lcm_list(stretched_ds)
    tile_counts = [L // cd for cd in stretched_ds]

    # Verify claimed_primitive_aps
    cp_raw = cert["claimed_primitive_aps"]
    if type(cp_raw) is not list or len(cp_raw) != len(prim_expected):
        raise DominoTilingCertificateError("claimed_primitive_aps length mismatch")
    for i, (got, exp) in enumerate(zip(cp_raw, prim_expected)):
        if type(got) is not dict or set(got.keys()) != {"direction", "scale_c", "stretched_d"}:
            raise DominoTilingCertificateError(f"claimed_primitive_aps[{i}] key mismatch")
        gdir = list(_parse_pt2(got["direction"], f"cp[{i}].direction"))
        gsc = _parse_int(got["scale_c"], f"cp[{i}].scale_c")
        gsd = _parse_int(got["stretched_d"], f"cp[{i}].stretched_d")
        if gdir != exp["direction"] or gsc != exp["scale_c"] or gsd != exp["stretched_d"]:
            raise DominoTilingCertificateError(f"claimed_primitive_aps[{i}] mismatch: exact={exp}")

    if _parse_int(cert["claimed_common_length"], "claimed_common_length") != L:
        raise DominoTilingCertificateError(f"claimed_common_length mismatch: exact={L}")
    tc_raw = cert["claimed_tile_counts"]
    if type(tc_raw) is not list or [_parse_int(v, "tc") for v in tc_raw] != tile_counts:
        raise DominoTilingCertificateError(f"claimed_tile_counts mismatch: exact={tile_counts}")

    return {
        "verified": True,
        "mode": cert["mode"],
        "num_aps": len(raw_aps),
        "common_length_L": L,
        "tile_counts": tile_counts,
    }


def verify_domino_tiling_certificate_exact(cert: Dict[str, Any]) -> Dict[str, Any]:
    if type(cert) is not dict:
        raise DominoTilingCertificateError("Certificate root must be a dict")
    _assert_strict_json_types(cert)
    if cert.get("schema") != SCHEMA_VERSION:
        raise DominoTilingCertificateError(f"Invalid schema: {cert.get('schema')!r}")
    name = cert.get("name")
    if type(name) is not str or not name.strip():
        raise DominoTilingCertificateError(f"Certificate name must be non-empty str, got {name!r}")
    mode = cert.get("mode")
    if mode == "common_figure_ap_tiling_exact":
        return _verify_mode1_common_figure(cert)
    if mode == "tile_divisible_vs_tileable_exact":
        return _verify_mode2_divisible_vs_tileable(cert)
    if mode == "divisibility_boosting_lift_exact":
        return _verify_mode3_divisibility_boost(cert)
    if mode == "ap_primitive_lcm_reduction_exact":
        return _verify_mode4_primitive_lcm(cert)
    raise DominoTilingCertificateError(f"Unknown mode: {mode!r}")
