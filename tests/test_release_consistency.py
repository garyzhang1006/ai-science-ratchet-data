"""Guard against the released prose drifting away from the released numbers.

FINDINGS.md is written by hand, so a rerun of the pipeline can leave it
asserting values that no longer exist in release/results/. That happened once:
the note kept a 30-seed composition run (2327 samples, 87.4% retention) after
the analysis moved to 60 seeds (4920 samples, 62.3%). These tests re-read every
number the note states and compare it against the JSON the paper cites.
"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
REL = ROOT / "release" / "results"
NOTE = (ROOT / "release" / "FINDINGS.md").read_text()


def _load(name):
    return json.load(open(REL / name))


def _num(pattern):
    m = re.search(pattern, NOTE)
    assert m, f"FINDINGS.md no longer contains a match for {pattern!r}"
    return float(m.group(1).replace(",", ""))


def test_composition_matches_released_json():
    depths = _load("depth_distribution.json")
    qual = _load("composed.json")["markers"]["qualifier_share"]
    assert _num(r"produced\s+([\d,]+)\s*\n?citation-weighted samples") == depths["n_samples"]
    assert _num(r"median citation depth of (\d+) hops") == depths["median_depth"]
    assert _num(r"p90 of (\d+)") == depths["p90_depth"]
    assert abs(_num(r"retains ([\d.]+)% of its qualifiers")
               - qual["retention_at_median_depth"] * 100) < 0.05
    assert abs(_num(r"depth distribution is ([\d.]+)%")
               - qual["expected_retention_at_consumption"] * 100) < 0.05


def test_h3_reduction_shares_match_released_json():
    h3 = _load("results.json")["H3_regime"]
    stated = {
        "numeric_share_exact": _num(r"([\d.]+)% for numeric\s*\n?fidelity"),
        "qualifier_share": _num(r"([\d.]+)% for qualifier retention"),
        "bi_entail": _num(r"([\d.]+)% for bidirectional"),
        "hedge_density": _num(r"([\d.]+)% for hedge density"),
    }
    for marker, pct in stated.items():
        assert abs(pct - h3[marker]["reduction_share"] * 100) < 0.05, marker
    assert abs(_num(r"reduction share (-[\d.]+)%")
               - h3["causal_strength"]["reduction_share"] * 100) < 0.05
    assert abs(_num(r"interaction p = ([\d.]+)\)")
               - h3["causal_strength"]["interaction_p"]) < 0.005
    assert abs(_num(r"at p = ([\d.]+) for hedge")
               - h3["hedge_density"]["interaction_p"]) < 0.0005


def test_note_states_no_sign_flip_only_if_none_exists():
    h3 = _load("results.json")["H3_regime"]
    if "No marker flips sign" in NOTE:
        assert not any(v["sign_flip"] for v in h3.values())


def test_note_claims_no_universal_damping():
    """Causal strength drifts further under the conservative prompt, so the
    note must not claim every rate is damped."""
    h3 = _load("results.json")["H3_regime"]
    damped = [k for k, v in h3.items() if v["reduction_share"] > 0]
    assert len(damped) == 4, damped
    assert "damps every rate" not in NOTE


if __name__ == "__main__":
    import sys
    ok = True
    for _name, _fn in sorted(globals().items()):
        if _name.startswith("test_") and callable(_fn):
            try:
                _fn()
                print(f"PASS {_name}")
            except AssertionError as _e:
                ok = False
                print(f"FAIL {_name}: {_e}")
    print()
    print("ALL PASS" if ok else "FAILURES PRESENT")
    sys.exit(0 if ok else 1)
