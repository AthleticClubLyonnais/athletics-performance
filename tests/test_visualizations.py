"""Tests for performance visualization module."""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import plotly.graph_objects as go

from athletics_performance.visualizations import (
    PerformanceVisualizer,
    export_to_html,
    export_individual_html,
)


@pytest.fixture
def sample_performance_df():
    """Create sample performance data for testing."""
    dates = pd.date_range("2024-01-01", periods=20, freq="W")
    athletes = ["A001", "A002", "A003"]
    events = ["100m", "200m", "400m"]

    data = []
    for i, date in enumerate(dates):
        for athlete in athletes:
            for event in events:
                # Generate realistic performance data with variability
                base_time = 12.5 if event == "100m" else 25.0 if event == "200m" else 55.0
                noise = (hash(f"{date}{athlete}{event}") % 100) / 100 - 0.5
                result = base_time + noise

                data.append({
                    "perf_id": f"p_{i}_{athlete}_{event}",
                    "athlete_id": athlete,
                    "event_id": event,
                    "result_value": result,
                    "date": date,
                    "unit": "s",
                    "measurement": "time",
                    "category_snapshot": "M1M" if athlete == "A001" else "M2M",
                    "club_id_snapshot": "069106",
                })

    return pd.DataFrame(data)


class TestPerformanceVisualizer:
    """Test PerformanceVisualizer class."""

    def test_init(self, sample_performance_df):
        """Initialize visualizer with valid data."""
        viz = PerformanceVisualizer(sample_performance_df)
        assert len(viz.df) == len(sample_performance_df)

    def test_init_missing_columns(self):
        """Raise error if required columns missing."""
        df = pd.DataFrame({"some_col": [1, 2, 3]})
        with pytest.raises(ValueError, match="Missing required columns"):
            PerformanceVisualizer(df)

    def test_athlete_progression(self, sample_performance_df):
        """Generate athlete progression chart."""
        viz = PerformanceVisualizer(sample_performance_df)
        fig = viz.athlete_progression("A001", "100m")

        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 2  # Performance points + personal best line
        assert "Personal Best Progression" in fig.to_json()

    def test_athlete_progression_not_found(self, sample_performance_df):
        """Raise error for athlete-event combination not found."""
        viz = PerformanceVisualizer(sample_performance_df)
        with pytest.raises(ValueError, match="No performances found"):
            viz.athlete_progression("A999", "100m")

    def test_performance_distribution_box(self, sample_performance_df):
        """Generate distribution box plot."""
        viz = PerformanceVisualizer(sample_performance_df)
        fig = viz.performance_distribution("100m", chart_type="box")

        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0

    def test_performance_distribution_histogram(self, sample_performance_df):
        """Generate distribution histogram."""
        viz = PerformanceVisualizer(sample_performance_df)
        fig = viz.performance_distribution("100m", chart_type="histogram")

        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0

    def test_multi_athlete_timeseries(self, sample_performance_df):
        """Generate multi-athlete time series chart."""
        viz = PerformanceVisualizer(sample_performance_df)
        fig = viz.multi_athlete_timeseries(["A001", "A002"], "100m")

        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 2  # Two athletes

    def test_multi_athlete_timeseries_empty(self, sample_performance_df):
        """Multi-athlete timeseries with no matching athletes."""
        viz = PerformanceVisualizer(sample_performance_df)
        fig = viz.multi_athlete_timeseries(["A999"], "100m")

        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 0

    def test_event_performance_matrix(self, sample_performance_df):
        """Generate event-athlete performance matrix heatmap."""
        viz = PerformanceVisualizer(sample_performance_df)
        fig = viz.event_performance_matrix()

        assert isinstance(fig, go.Figure)
        assert "Heatmap" in str(type(fig.data[0]))

    def test_event_performance_matrix_filtered(self, sample_performance_df):
        """Generate matrix with filtered athletes and events."""
        viz = PerformanceVisualizer(sample_performance_df)
        fig = viz.event_performance_matrix(
            athlete_ids=["A001", "A002"], event_ids=["100m", "200m"]
        )

        assert isinstance(fig, go.Figure)

    def test_ranking_chart(self, sample_performance_df):
        """Generate ranking bar chart."""
        viz = PerformanceVisualizer(sample_performance_df)
        fig = viz.ranking_chart("100m", top_n=5)

        assert isinstance(fig, go.Figure)
        assert len(fig.data[0].y) <= 5

    def test_category_analysis(self, sample_performance_df):
        """Generate category analysis box plots."""
        viz = PerformanceVisualizer(sample_performance_df)
        fig = viz.category_analysis("100m", groupby_column="category_snapshot")

        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 2  # Two categories in sample data

    def test_category_analysis_missing_column(self, sample_performance_df):
        """Raise error for missing groupby column."""
        viz = PerformanceVisualizer(sample_performance_df)
        with pytest.raises(ValueError, match="not found in dataframe"):
            viz.category_analysis("100m", groupby_column="nonexistent_col")

    def test_statistics_dashboard(self, sample_performance_df):
        """Generate statistics dashboard with subplots."""
        viz = PerformanceVisualizer(sample_performance_df)
        fig = viz.statistics_dashboard("100m")

        assert isinstance(fig, go.Figure)
        # Dashboard should have multiple traces for different visualizations
        assert len(fig.data) > 1

    def test_season_comparison(self, sample_performance_df):
        """Generate season comparison chart."""
        viz = PerformanceVisualizer(sample_performance_df)
        fig = viz.season_comparison("A001", "100m")

        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0

    def test_season_comparison_not_found(self, sample_performance_df):
        """Raise error for athlete-event not found."""
        viz = PerformanceVisualizer(sample_performance_df)
        with pytest.raises(ValueError, match="No performances found"):
            viz.season_comparison("A999", "100m")


class TestExportFunctions:
    """Test HTML export functions."""

    def test_export_individual_html(self, sample_performance_df, tmp_path):
        """Export single figure to HTML file."""
        viz = PerformanceVisualizer(sample_performance_df)
        fig = viz.athlete_progression("A001", "100m")

        output_path = tmp_path / "chart.html"
        export_individual_html(fig, str(output_path))

        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        assert "plotly" in content.lower()

    def test_export_dashboard_html(self, sample_performance_df, tmp_path):
        """Export multiple figures to dashboard HTML."""
        viz = PerformanceVisualizer(sample_performance_df)

        figures = {
            "Athlete Progression": viz.athlete_progression("A001", "100m"),
            "Distribution": viz.performance_distribution("100m"),
            "Ranking": viz.ranking_chart("100m"),
        }

        output_path = tmp_path / "dashboard.html"
        export_to_html(figures, str(output_path), title="Test Dashboard")

        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        assert "Test Dashboard" in content
        assert "Athlete Progression" in content
        assert "Distribution" in content
        assert "Ranking" in content
        assert "plotly" in content.lower()

    def test_export_creates_parent_directory(self, sample_performance_df, tmp_path):
        """Export creates parent directories if they don't exist."""
        viz = PerformanceVisualizer(sample_performance_df)
        fig = viz.athlete_progression("A001", "100m")

        output_path = tmp_path / "nested" / "dirs" / "chart.html"
        export_individual_html(fig, str(output_path))

        assert output_path.exists()


class TestIntegration:
    """Integration tests for visualization workflows."""

    def test_complete_analysis_workflow(self, sample_performance_df, tmp_path):
        """Complete workflow: create multiple visualizations and export."""
        viz = PerformanceVisualizer(sample_performance_df)

        # Create various visualizations
        progression = viz.athlete_progression("A001", "100m")
        distribution = viz.performance_distribution("100m")
        ranking = viz.ranking_chart("100m", top_n=5)
        dashboard = viz.statistics_dashboard("100m")
        matrix = viz.event_performance_matrix()
        timeseries = viz.multi_athlete_timeseries(["A001", "A002"], "100m")

        # Export all to dashboard
        figures = {
            "Athlete A001 - 100m": progression,
            "100m Distribution": distribution,
            "100m Rankings": ranking,
            "100m Dashboard": dashboard,
            "Event Matrix": matrix,
            "Multi-Athlete Comparison": timeseries,
        }

        output_path = tmp_path / "analysis.html"
        export_to_html(figures, str(output_path), title="Complete Analysis")

        assert output_path.exists()
        content = output_path.read_text()
        assert "Complete Analysis" in content
        assert all(name in content for name in figures.keys())

    def test_category_comparison_workflow(self, sample_performance_df, tmp_path):
        """Workflow comparing performance across categories."""
        viz = PerformanceVisualizer(sample_performance_df)

        figures = {}
        for event in ["100m", "200m", "400m"]:
            figures[f"{event} by Category"] = viz.category_analysis(
                event, groupby_column="category_snapshot"
            )

        output_path = tmp_path / "category_analysis.html"
        export_to_html(figures, str(output_path), title="Category Analysis")

        assert output_path.exists()

    def test_season_analysis_workflow(self, sample_performance_df, tmp_path):
        """Workflow analyzing season-to-season progression."""
        viz = PerformanceVisualizer(sample_performance_df)

        figures = {
            "A001 - 100m": viz.season_comparison("A001", "100m"),
            "A002 - 100m": viz.season_comparison("A002", "100m"),
        }

        output_path = tmp_path / "season_analysis.html"
        export_to_html(figures, str(output_path), title="Season Analysis")

        assert output_path.exists()
