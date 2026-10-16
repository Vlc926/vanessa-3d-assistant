set -e
export PYTHONPATH=.
echo "=========================================================="
echo "  JARVIS ASSISTANT 4-TIER E2E & UNIT TEST SUITE RUNNER    "
echo "=========================================================="
echo ""
echo "[1/4] Running Unit Tests (tests/unit)..."
.venv/bin/python -m unittest discover -s tests/unit
echo ""
echo "[2/4] Running Tier 1 Feature Coverage Tests (tests/e2e/tier1_feature_coverage)..."
.venv/bin/python -m unittest discover -s tests/e2e/tier1_feature_coverage
echo ""
echo "[3/4] Running Tier 2 Boundary Cases Tests (tests/e2e/tier2_boundary_cases)..."
.venv/bin/python -m unittest discover -s tests/e2e/tier2_boundary_cases
echo ""
echo "[4/4] Running Tier 3 & Tier 4 Integration & Scenario Tests..."
.venv/bin/python -m unittest discover -s tests/e2e/tier3_pairwise_interactions
.venv/bin/python -m unittest discover -s tests/e2e/tier4_real_world_scenarios
echo ""
echo "=========================================================="
echo "  ALL TEST TIERS (UNIT, T1, T2, T3, T4) PASSED 100%      "
echo "=========================================================="
exit 0
