import pytest

from technology_park_abm import (
    METRIC_SCHEMA_VERSION,
    TypedNetwork,
    degree_centralization,
    mann_kendall_trend,
    marginal_output,
    marginal_output_trend,
    partnership_density,
    productive_tie_count,
)


def test_metric_schema_version_is_v1() -> None:
    assert METRIC_SCHEMA_VERSION == "1.0"


def test_partnership_density() -> None:
    network = TypedNetwork()
    network.add_tie(1, 2, "partnership", 0.5)
    assert partnership_density(network, [1, 2, 3]) == 1.0 / 3.0
    assert partnership_density(network, [1, 2]) == 1.0
    assert partnership_density(network, [1]) == 0.0
    assert partnership_density(network, [3]) == 0.0


def test_density_ignores_other_tie_types_and_outsiders() -> None:
    network = TypedNetwork()
    network.add_tie(1, 2, "investment", 1.0)
    network.add_tie(6, 7, "partnership", 1.0)
    assert partnership_density(network, [1, 2, 3]) == 0.0


def test_degree_centralization() -> None:
    network = TypedNetwork()
    network.add_tie(1, 2, "partnership", 1.0)
    assert degree_centralization(network, [1, 2, 3]) == 0.5
    assert degree_centralization(network, [1, 2]) == 0.0


def test_productive_tie_count_uses_threshold() -> None:
    network = TypedNetwork()
    network.add_tie(1, 2, "partnership", 0.75)
    network.add_tie(1, 3, "partnership", 0.375)
    assert productive_tie_count(network, 0.5) == 1
    assert productive_tie_count(network, 0.0) == 2


def test_marginal_output_skips_constant_population() -> None:
    records: list[dict[str, int | float]] = [
        {"period": 1, "active_startup_count": 10, "knowledge_total": 100.0},
        {"period": 2, "active_startup_count": 10, "knowledge_total": 120.0},
        {"period": 3, "active_startup_count": 11, "knowledge_total": 140.0},
        {"period": 4, "active_startup_count": 13, "knowledge_total": 200.0},
    ]
    assert marginal_output(records, "knowledge_total") == [(3, 20.0), (4, 30.0)]


def test_marginal_output_reveals_increasing_returns() -> None:
    records: list[dict[str, int | float]] = [
        {"period": 1, "active_startup_count": 10, "knowledge_total": 100.0},
        {"period": 2, "active_startup_count": 11, "knowledge_total": 110.0},
        {"period": 3, "active_startup_count": 12, "knowledge_total": 140.0},
        {"period": 4, "active_startup_count": 13, "knowledge_total": 190.0},
    ]
    values = [value for _period, value in marginal_output(records, "knowledge_total")]
    assert values == [10.0, 30.0, 50.0]
    assert values[1] > values[0]
    assert values[2] > values[1]


def test_marginal_output_handles_short_series() -> None:
    assert marginal_output([], "knowledge_total") == []
    single: list[dict[str, int | float]] = [
        {"period": 1, "active_startup_count": 1, "knowledge_total": 1.0}
    ]
    assert marginal_output(single, "knowledge_total") == []


def test_marginal_output_uses_configured_population_key() -> None:
    records: list[dict[str, int | float]] = [
        {"period": 1, "employment_total": 5, "knowledge_total": 10.0},
        {"period": 2, "employment_total": 7, "knowledge_total": 14.0},
    ]
    assert marginal_output(
        records, "knowledge_total", population_key="employment_total"
    ) == [(2, 2.0)]


def test_mann_kendall_detects_increasing_trend() -> None:
    result = mann_kendall_trend([1.0, 2.0, 3.5, 4.0, 6.0, 7.5, 9.0, 11.0])
    assert result.trend == "increasing"
    assert result.tau > 0.0
    assert result.z > 0.0
    assert result.p_value < 0.05
    assert result.slope > 0.0


def test_mann_kendall_detects_decreasing_trend() -> None:
    result = mann_kendall_trend([11.0, 9.0, 7.5, 6.0, 4.0, 3.5, 2.0, 1.0])
    assert result.trend == "decreasing"
    assert result.tau < 0.0
    assert result.z < 0.0
    assert result.p_value < 0.05
    assert result.slope < 0.0


def test_mann_kendall_no_trend_for_flat_or_noisy_series() -> None:
    flat = mann_kendall_trend([2.0] * 8)
    assert flat.trend == "no_trend"
    assert flat.z == 0.0
    assert flat.p_value == 1.0
    assert flat.slope == 0.0
    noisy = mann_kendall_trend([1.0, 5.0, 2.0, 6.0, 3.0, 7.0, 4.0, 8.0])
    assert noisy.trend == "no_trend"
    assert noisy.p_value >= 0.05


def test_mann_kendall_handles_ties() -> None:
    result = mann_kendall_trend([1.0, 2.0, 2.0, 3.0, 3.0, 4.0, 5.0, 6.0])
    assert result.trend == "increasing"
    assert 0.0 < result.tau <= 1.0


def test_mann_kendall_short_series_is_no_trend() -> None:
    empty = mann_kendall_trend([])
    assert empty.trend == "no_trend"
    assert empty.p_value == 1.0
    single = mann_kendall_trend([3.0])
    assert single.trend == "no_trend"
    assert single.tau == 0.0


def test_mann_kendall_two_points_never_significant() -> None:
    # n=2: the continuity correction zeroes z for a single concordant or
    # discordant pair, so the test can never reach significance.
    up = mann_kendall_trend([1.0, 2.0])
    assert up.trend == "no_trend"
    assert up.z == 0.0
    assert up.p_value == 1.0
    assert up.tau == 1.0
    assert up.slope == 1.0
    down = mann_kendall_trend([2.0, 1.0])
    assert down.trend == "no_trend"
    assert down.z == 0.0
    assert down.p_value == 1.0
    assert down.tau == -1.0
    assert down.slope == -1.0


def test_mann_kendall_balanced_series_has_zero_z() -> None:
    # statistic == 0 with variance > 0 (not all ties): the else branch sets
    # z = 0, so p = 1 and the trend is no_trend.
    result = mann_kendall_trend([3.0, 1.0, 4.0, 2.0])
    assert result.z == 0.0
    assert result.p_value == 1.0
    assert result.tau == 0.0
    assert result.trend == "no_trend"


def test_mann_kendall_constant_series_zero_variance() -> None:
    # all ties -> the tie correction cancels the variance term -> z = 0 path.
    result = mann_kendall_trend([7.0, 7.0, 7.0, 7.0])
    assert result.trend == "no_trend"
    assert result.z == 0.0
    assert result.p_value == 1.0
    assert result.tau == 0.0
    assert result.slope == 0.0


def test_mann_kendall_sens_slope_is_median_pairwise_slope() -> None:
    result = mann_kendall_trend([0.0, 1.0, 2.0, 4.0])
    # pairwise slopes (x_j - x_i) / (j - i): 1, 1, 4/3, 1, 3/2, 2
    # sorted: 1, 1, 1, 4/3, 3/2, 2 -> median (1 + 4/3) / 2 = 7/6
    assert result.slope == pytest.approx(7.0 / 6.0)


def test_mann_kendall_exact_values_without_ties() -> None:
    # Hand-computed from the standard formulas: S = 10, var = 5*4*15/18,
    # z = 9/sqrt(var) with continuity correction, p = erfc(|z|/sqrt(2)).
    up = mann_kendall_trend([1.0, 2.0, 3.0, 4.0, 5.0])
    assert up.tau == 1.0
    assert up.z == pytest.approx(2.2045407685048604)
    assert up.p_value == pytest.approx(0.027486336111510353)
    assert up.slope == 1.0
    assert up.trend == "increasing"
    down = mann_kendall_trend([5.0, 4.0, 3.0, 2.0, 1.0])
    assert down.tau == -1.0
    assert down.z == pytest.approx(-2.2045407685048604)
    assert down.p_value == pytest.approx(0.027486336111510353)
    assert down.slope == -1.0
    assert down.trend == "decreasing"


def test_mann_kendall_exact_values_with_partial_ties() -> None:
    # Tie group {2: 2} -> correction 2*1*9 = 18; var = (4*3*13 - 18)/18.
    tied = mann_kendall_trend([1.0, 2.0, 2.0, 3.0])
    assert tied.tau == pytest.approx(5.0 / 6.0)
    assert tied.z == pytest.approx(1.4446302370292303)
    assert tied.p_value == pytest.approx(0.1485617748918687)
    assert tied.slope == pytest.approx(7.0 / 12.0)
    assert tied.trend == "no_trend"
    # Same tie structure, long enough to reach significance.
    significant = mann_kendall_trend([1.0, 1.0, 2.0, 3.0, 4.0])
    assert significant.tau == pytest.approx(0.9)
    assert significant.z == pytest.approx(2.0211646105596457)
    assert significant.p_value == pytest.approx(0.043262727806910685)
    assert significant.slope == 1.0
    assert significant.trend == "increasing"


def test_mann_kendall_exact_values_for_weak_and_balanced_series() -> None:
    # S = -1: the continuity correction zeroes z, so a negative statistic
    # must still report no_trend (the decision needs p < alpha).
    weak = mann_kendall_trend([3.0, 1.0, 2.0])
    assert weak.tau == pytest.approx(-1.0 / 3.0)
    assert weak.z == 0.0
    assert weak.p_value == 1.0
    assert weak.slope == -0.5
    assert weak.trend == "no_trend"
    # S = 0 with variance > 0: the else branch sets z = 0 exactly.
    balanced = mann_kendall_trend([3.0, 1.0, 4.0, 2.0])
    assert balanced.tau == 0.0
    assert balanced.z == 0.0
    assert balanced.p_value == 1.0
    assert balanced.slope == pytest.approx(1.0 / 12.0)
    assert balanced.trend == "no_trend"


def test_mann_kendall_short_series_exact_fields() -> None:
    short_series: list[list[float]] = [[], [3.0]]
    for series in short_series:
        result = mann_kendall_trend(series)
        assert result.tau == 0.0
        assert result.z == 0.0
        assert result.p_value == 1.0
        assert result.slope == 0.0
        assert result.trend == "no_trend"


def test_mann_kendall_alpha_comparison_is_strict() -> None:
    # alpha exactly equal to the p-value must NOT reach significance:
    # the trend decision uses p < alpha, not p <= alpha.
    up_series = [1.0, 2.0, 3.0, 4.0, 5.0]
    up = mann_kendall_trend(up_series)
    assert mann_kendall_trend(up_series, alpha=up.p_value).trend == "no_trend"
    down_series = [5.0, 4.0, 3.0, 2.0, 1.0]
    down = mann_kendall_trend(down_series)
    assert mann_kendall_trend(down_series, alpha=down.p_value).trend == "no_trend"


def test_mann_kendall_rejects_invalid_alpha() -> None:
    for alpha in (0.0, 1.0, -0.5, 1.5):
        with pytest.raises(ValueError, match=r"^alpha must be in \(0, 1\)$"):
            mann_kendall_trend([1.0, 2.0, 3.0], alpha=alpha)


def test_mann_kendall_is_deterministic() -> None:
    series = [3.0, 1.0, 4.0, 1.0, 5.0, 9.0, 2.0, 6.0, 5.0, 3.0]
    assert mann_kendall_trend(series) == mann_kendall_trend(series)


def test_marginal_output_trend_detects_increasing_returns() -> None:
    records: list[dict[str, int | float]] = [
        {"period": 1, "active_startup_count": 10, "knowledge_total": 100.0},
        {"period": 2, "active_startup_count": 11, "knowledge_total": 110.0},
        {"period": 3, "active_startup_count": 12, "knowledge_total": 140.0},
        {"period": 4, "active_startup_count": 13, "knowledge_total": 190.0},
        {"period": 5, "active_startup_count": 14, "knowledge_total": 260.0},
        {"period": 6, "active_startup_count": 15, "knowledge_total": 350.0},
    ]
    result = marginal_output_trend(records, "knowledge_total")
    assert result.trend == "increasing"
    assert result.slope > 0.0


def test_marginal_output_trend_detects_saturation() -> None:
    records: list[dict[str, int | float]] = [
        {"period": 1, "active_startup_count": 10, "knowledge_total": 100.0},
        {"period": 2, "active_startup_count": 11, "knowledge_total": 150.0},
        {"period": 3, "active_startup_count": 12, "knowledge_total": 180.0},
        {"period": 4, "active_startup_count": 13, "knowledge_total": 200.0},
        {"period": 5, "active_startup_count": 14, "knowledge_total": 210.0},
        {"period": 6, "active_startup_count": 15, "knowledge_total": 215.0},
    ]
    result = marginal_output_trend(records, "knowledge_total")
    assert result.trend == "decreasing"
    assert result.slope < 0.0


def test_productive_tie_count_filters_by_type_and_threshold() -> None:
    network = TypedNetwork()
    network.add_tie(1, 2, "partnership", 0.5)
    network.add_tie(2, 3, "partnership", 1.0)
    network.add_tie(1, 3, "investment", 2.0)
    # Only partnership ties count, and the threshold is inclusive.
    assert productive_tie_count(network, 0.5) == 2
    assert productive_tie_count(network, 1.0) == 1
    assert productive_tie_count(network, 1.5) == 0


def test_marginal_output_computes_delta_ratios() -> None:
    records: list[dict[str, int | float]] = [
        {"period": 1, "active_startup_count": 10, "knowledge_total": 100.0},
        {"period": 2, "active_startup_count": 10, "knowledge_total": 130.0},
        {"period": 3, "active_startup_count": 12, "knowledge_total": 160.0},
    ]
    # Period 2 has no population change and is skipped.
    assert marginal_output(records, "knowledge_total") == [(3, 15.0)]


def test_marginal_output_trend_uses_custom_population_key_and_alpha() -> None:
    records: list[dict[str, int | float]] = [
        {"period": 1, "firms": 10, "revenue": 100.0},
        {"period": 2, "firms": 11, "revenue": 110.0},
        {"period": 3, "firms": 12, "revenue": 140.0},
        {"period": 4, "firms": 13, "revenue": 190.0},
        {"period": 5, "firms": 14, "revenue": 260.0},
        {"period": 6, "firms": 15, "revenue": 350.0},
    ]
    # Marginal revenue per firm: 10, 30, 50, 70, 90 -> strongly increasing.
    result = marginal_output_trend(records, "revenue", population_key="firms")
    assert result.trend == "increasing"
    # p ~ 0.027: significant at alpha=0.05 but not at alpha=0.01.
    strict = marginal_output_trend(
        records, "revenue", population_key="firms", alpha=0.01
    )
    assert strict.trend == "no_trend"


def test_degree_centralization_exact_values() -> None:
    star = TypedNetwork()
    star.add_tie(1, 2, "partnership", 1.0)
    star.add_tie(1, 3, "partnership", 1.0)
    star.add_tie(1, 4, "partnership", 1.0)
    assert degree_centralization(star, [1, 2, 3, 4]) == 1.0
    path = TypedNetwork()
    path.add_tie(1, 2, "partnership", 1.0)
    path.add_tie(2, 3, "partnership", 1.0)
    path.add_tie(3, 4, "partnership", 1.0)
    assert degree_centralization(path, [1, 2, 3, 4]) == pytest.approx(1.0 / 3.0)


def test_degree_centralization_ignores_ties_with_outsiders() -> None:
    network = TypedNetwork()
    network.add_tie(1, 2, "partnership", 1.0)
    network.add_tie(2, 4, "partnership", 1.0)
    # Node 4 is outside the agent set: only the (1, 2) tie counts, giving
    # degrees 1, 1, 0 and centralization (0 + 0 + 1) / ((3-1)*(3-2)) = 0.5.
    assert degree_centralization(network, [1, 2, 3]) == 0.5


def test_degree_centralization_counts_only_partnership_ties() -> None:
    network = TypedNetwork()
    network.add_tie(1, 2, "partnership", 1.0)
    network.add_tie(2, 3, "investment", 1.0)
    # Only the partnership tie counts: degrees 1, 1, 0 -> 0.5.
    assert degree_centralization(network, [1, 2, 3]) == 0.5


def test_marginal_output_trend_without_population_change_is_no_trend() -> None:
    records: list[dict[str, int | float]] = [
        {"period": 1, "active_startup_count": 10, "knowledge_total": 100.0},
        {"period": 2, "active_startup_count": 10, "knowledge_total": 120.0},
        {"period": 3, "active_startup_count": 10, "knowledge_total": 150.0},
    ]
    assert marginal_output_trend(records, "knowledge_total").trend == "no_trend"
