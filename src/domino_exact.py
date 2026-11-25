"""Pure-stdlib exact-Z engine for Paper 30:
Dominoes Tiling a Common Figure (Peter Keevash & Jeck Lim, arXiv:2611.33154, Nov 24, 2026).

ZERO floating-point arithmetic anywhere.
Author: Lluis Eriksson
"""
from __future__ import annotations

import math
from typing import Dict, List, Sequence, Set, Tuple

Laurent2D = Dict[Tuple[int, int], int]


def l2_clean(p: Laurent2D) -> Laurent2D:
    return {k: v for k, v in sorted(p.items()) if v != 0}


def l2_add(a: Laurent2D, b: Laurent2D) -> Laurent2D:
    out = dict(a)
    for k, v in b.items():
        nv = out.get(k, 0) + v
        if nv == 0:
            out.pop(k, None)
        else:
            out[k] = nv
    return dict(sorted(out.items()))


def l2_sub(a: Laurent2D, b: Laurent2D) -> Laurent2D:
    return l2_add(a, {k: -v for k, v in b.items()})


def l2_mul(a: Laurent2D, b: Laurent2D) -> Laurent2D:
    out: Laurent2D = {}
    for (x1, y1), v1 in a.items():
        for (x2, y2), v2 in b.items():
            key = (x1 + x2, y1 + y2)
            nv = out.get(key, 0) + v1 * v2
            if nv == 0:
                out.pop(key, None)
            else:
                out[key] = nv
    return dict(sorted(out.items()))


def ap_laurent_2d(v: Tuple[int, int], d: int) -> Laurent2D:
    """Bivariate Laurent polynomial P_D(x1, x2) = sum_{j=0}^{d-1} x^{j*v}."""
    vx, vy = v
    return {(j * vx, j * vy): 1 for j in range(d)}


def poly1d_trim(p: Sequence[int]) -> List[int]:
    out = list(p)
    while out and out[-1] == 0:
        out.pop()
    return out


def poly1d_divmod_monic(dividend: Sequence[int], divisor: Sequence[int]) -> Tuple[List[int], List[int]]:
    div = poly1d_trim(divisor)
    if not div or abs(div[-1]) != 1:
        raise ValueError("Divisor must be non-zero with leading coeff +/- 1")
    rem = poly1d_trim(dividend)
    d_deg = len(div) - 1
    lc = div[-1]
    if len(rem) - 1 < d_deg:
        return [], rem
    quot = [0] * (len(rem) - d_deg)
    while rem and len(rem) - 1 >= d_deg:
        shift = len(rem) - 1 - d_deg
        q_coeff = rem[-1] * lc
        quot[shift] = q_coeff
        for j, dj in enumerate(div):
            rem[shift + j] -= q_coeff * dj
        rem = poly1d_trim(rem)
    return poly1d_trim(quot), rem


def check_1d_ap_divisible_and_tileable(cells: Sequence[int], d: int) -> Tuple[bool, bool, List[int]]:
    """For a finite non-empty set S subset Z (shifted to min 0), check:
      1. Exact Z[t]-divisibility by D_d(t) = 1 + t + ... + t^{d-1}
      2. Exact {0,1}-tileability (quotient Q has all entries >= 0, equivalently in {0,1}!).
    Returns (is_divisible, is_tileable, quotient_coeffs).
    """
    if not cells or d < 2:
        raise ValueError("Require non-empty cells and d >= 2")
    lo = min(cells)
    hi = max(cells)
    poly = [0] * (hi - lo + 1)
    for c in cells:
        poly[c - lo] += 1
    divisor = [1] * d
    q, rem = poly1d_divmod_monic(poly, divisor)
    if rem:
        return False, False, []
    is_tile = all(c >= 0 for c in q)
    return True, is_tile, q


def l2_divisible_by_binomial_diff(poly: Laurent2D, u: Tuple[int, int]) -> bool:
    """Check exact divisibility (X^u - 1) | poly in Z[X1^+-1, X2^+-1] by grouping points into
    exact u-cosets (parallel lines in direction u) and checking 1D divisibility by (t - 1) on each coset!
    Wait: (X^u - 1) | poly iff along every u-orbit {p + k*u : k in Z}, the sum of coefficients is 0!
    """
    if not poly:
        return True
    ux, uy = u
    if ux == 0 and uy == 0:
        raise ValueError("u must be non-zero")
    # Partition exponents by equivalence relation p ~ q iff (p - q) is an integer multiple of u!
    visited: Set[Tuple[int, int]] = set()
    keys = list(poly.keys())
    for p in keys:
        if p in visited:
            continue
        px, py = p
        orbit_sum = 0
        for q in keys:
            if q in visited:
                continue
            dx, dy = q[0] - px, q[1] - py
            # Check if (dx, dy) = k * (ux, uy) for some integer k
            if ux != 0:
                if dx % ux == 0 and dy == (dx // ux) * uy:
                    visited.add(q)
                    orbit_sum += poly[q]
            else:
                if dx == 0 and dy % uy == 0:
                    visited.add(q)
                    orbit_sum += poly[q]
        if orbit_sum != 0:
            return False
    return True


def l2_mod_X1d_minus_1(poly: Laurent2D, d: int) -> Dict[int, Dict[int, int]]:
    """Exact reduction pi(poly) modulo (X_1^d - 1): returns {ell in 0..d-1: {exp_X2: coeff}}."""
    out: Dict[int, Dict[int, int]] = {ell: {} for ell in range(d)}
    for (e1, e2), c in poly.items():
        ell = e1 % d
        bucket = out[ell]
        nv = bucket.get(e2, 0) + c
        if nv == 0:
            bucket.pop(e2, None)
        else:
            bucket[e2] = nv
    return out


def lcm_list(vals: Sequence[int]) -> int:
    res = 1
    for v in vals:
        res = math.lcm(res, v)
    return res
