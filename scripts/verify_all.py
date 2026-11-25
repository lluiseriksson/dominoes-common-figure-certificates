"""End-to-end Gate-2 verification script for Paper 30:
  1. Lean 4 kernel build + zero-sorry / zero-warning / zero-Classical.choice axiom audit (18/18 theorems)
  2. Pure-stdlib zero-float replay of all 16 DOMINO-AP-TILING-CERT-1.0 certificates
  3. Full pytest suite (exhaustive 1D gap census + 48-cell Sagdeev D4 check + 57 live adversarial attacks)
  4. SHA-256 manifest verification (or generation via --write-manifest)

Author: Lluis Eriksson
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.domino_certifier import verify_domino_tiling_certificate_exact

EXPECTED_THEOREMS = [
    "DominoesCommonFigure.ap_tiling_cardinality_divisible",
    "DominoesCommonFigure.standard_2x2_square_tiled_both",
    "DominoesCommonFigure.ap_primitive_stretch_partition",
    "DominoesCommonFigure.ap_lcm_common_length_divides",
    "DominoesCommonFigure.laurent_ap_poly_eval_one",
    "DominoesCommonFigure.laurent_ap_poly_times_diff_telescope",
    "DominoesCommonFigure.laurent_domino_checkerboard_balance",
    "DominoesCommonFigure.tile_divisible_gap_witness_d2",
    "DominoesCommonFigure.tile_divisible_gap_witness_d3",
    "DominoesCommonFigure.hole_move_step_d_preserves_mod_d",
    "DominoesCommonFigure.hole_move_repairs_d2_gap",
    "DominoesCommonFigure.hole_move_repairs_d3_gap",
    "DominoesCommonFigure.unimodular_basis_change_det_one",
    "DominoesCommonFigure.divisibility_boost_transitivity",
    "DominoesCommonFigure.mod_Xd_minus_1_lift_congruence",
    "DominoesCommonFigure.minkowski_product_tiling_div",
    "DominoesCommonFigure.common_figure_lcm_divides_size",
    "DominoesCommonFigure.line_partition_sum_conservation",
]

MANIFEST_FILES = [
    "README.md",
    "pyproject.toml",
    "lean/lakefile.lean",
    "lean/lean-toolchain",
    "lean/DominoesCommonFigure.lean",
    "lean/AuditAxioms.lean",
    "src/__init__.py",
    "src/domino_exact.py",
    "src/domino_certifier.py",
    "scripts/run_all_experiments.py",
    "scripts/make_figures.py",
    "scripts/verify_all.py",
    "tests/test_suite.py",
    "results/exp1_certified_atlas.json",
    "results/exp2_divisible_vs_tileable_census.json",
    "results/exp3_sagdeev_48cell_tilings.json",
    "results/exp4_boosting_lift_stats.json",
    "paper/main.tex",
    "paper/references.bib",
    "paper/main.pdf",
    "paper/figures/fig1_sagdeev_48cell_figure.png",
    "paper/figures/fig2_gap_census_and_boosting.png",
    "paper/figures/fig3_atlas_summary.png",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def check_lean() -> None:
    lean_dir = ROOT / "lean"
    p1 = subprocess.run(["lake", "build"], cwd=lean_dir, capture_output=True, text=True, check=False)
    if p1.returncode != 0:
        raise RuntimeError(f"lake build failed:\n{p1.stdout}\n{p1.stderr}")
    if "warning:" in (p1.stdout + p1.stderr).lower():
        raise RuntimeError(f"Lean build emitted warnings:\n{p1.stdout}\n{p1.stderr}")

    p2 = subprocess.run(["lake", "env", "lean", "AuditAxioms.lean"], cwd=lean_dir, capture_output=True, text=True, check=False)
    if p2.returncode != 0:
        raise RuntimeError(f"AuditAxioms failed:\n{p2.stdout}\n{p2.stderr}")
    out = p2.stdout + p2.stderr
    for forbidden in ("sorryAx", "Classical.choice", "Lean.ofReduceBool", "Lean.trustCompiler"):
        if forbidden in out:
            raise RuntimeError(f"Forbidden Lean axiom {forbidden!r} found:\n{out}")
    for thm in EXPECTED_THEOREMS:
        if f"'{thm}'" not in out:
            raise RuntimeError(f"Missing theorem {thm} in AuditAxioms output")
    print(f"[PASS] Lean 4 kernel: {len(EXPECTED_THEOREMS)}/18 theorems, 0 warnings, 0 sorry, 0 Classical.choice")


def check_certs() -> list[str]:
    cert_dir = ROOT / "results" / "certificates"
    cert_files = sorted(cert_dir.glob("*.cert.json"))
    if len(cert_files) != 16:
        raise RuntimeError(f"Expected 16 certificates, found {len(cert_files)}")
    rel_list = []
    for cf in cert_files:
        data = json.loads(cf.read_text(encoding="utf-8"))
        res = verify_domino_tiling_certificate_exact(data)
        if not res.get("verified"):
            raise RuntimeError(f"Certificate failed verification: {cf.name}")
        rel_list.append(cf.relative_to(ROOT).as_posix())
    print("[PASS] Exact-Z certificates: 16/16 independently verified (0 floats)")
    return rel_list


def check_pytest() -> None:
    p = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT, capture_output=True, text=True, check=False)
    if p.returncode != 0:
        raise RuntimeError(f"pytest failed:\n{p.stdout}\n{p.stderr}")
    print(f"[PASS] pytest: {p.stdout.strip()}")


def handle_manifest(cert_rels: list[str], write_manifest: bool) -> None:
    manifest_path = ROOT / "SHA256SUMS.json"
    all_files = sorted(set(MANIFEST_FILES + cert_rels))
    computed = {}
    for rel in all_files:
        p = ROOT / rel
        if not p.exists():
            raise RuntimeError(f"Manifest file missing: {rel}")
        computed[rel] = sha256_file(p)
    if write_manifest:
        manifest_path.write_text(json.dumps(computed, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"[PASS] Wrote SHA256SUMS.json ({len(computed)} files)")
        return
    if not manifest_path.exists():
        raise RuntimeError("SHA256SUMS.json missing; run with --write-manifest first")
    expected = json.loads(manifest_path.read_text(encoding="utf-8"))
    if expected != computed:
        diff_keys = sorted(set(expected.keys()) ^ set(computed.keys()))
        bad_hashes = [k for k in computed if expected.get(k) != computed[k]]
        raise RuntimeError(f"SHA256SUMS mismatch! diff_keys={diff_keys}, bad_hashes={bad_hashes}")
    print(f"[PASS] SHA256SUMS.json: {len(computed)}/{len(computed)} files verified")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write-manifest", action="store_true")
    args = ap.parse_args()
    check_lean()
    cert_rels = check_certs()
    check_pytest()
    handle_manifest(cert_rels, args.write_manifest)
    print("=== ALL PAPER 30 GATE-2 VERIFICATION CHECKS PASSED ===")


if __name__ == "__main__":
    main()
