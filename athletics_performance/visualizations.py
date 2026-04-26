"""Performance data visualization and analysis with Plotly.

This module provides interactive Plotly-based visualizations for athletics
performance data with HTML export capability. All charts include hover tooltips,
interactive filtering, and responsive design.

Features:
  - Athlete progression (personal bests over time)
  - Performance distribution (histogram, box plots)
  - Multi-athlete time series comparison
  - Event performance matrix (heatmap)
  - Ranking charts (bar charts)
  - Category analysis (distribution by age/club)
  - Statistics dashboard (summary cards + charts)
  - Season comparison (year-over-year)
  - HTML export with interactivity
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, List, Tuple
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots


class PerformanceVisualizer:
    """Main class for creating performance visualizations."""

    def __init__(self, df: pd.DataFrame):
        """Initialize visualizer with performance data.

        Args:
            df: Performance DataFrame with columns like perf_id, athlete_id,
                event_id, result_value, date, unit, measurement, etc.
        """
        self.df = df.copy()
        self._ensure_required_columns()

    def _ensure_required_columns(self) -> None:
        """Ensure required columns exist in dataframe."""
        required = {"perf_id", "athlete_id", "event_id", "result_value", "date"}
        missing = required - set(self.df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

    def athlete_progression(
        self,
        athlete_id: str,
        event_id: str,
        title: Optional[str] = None,
    ) -> go.Figure:
        """Line chart showing athlete's personal bests over time.

        Args:
            athlete_id: Athlete to visualize
            event_id: Event to track
            title: Custom chart title

        Returns:
            Plotly Figure
        """
        # Filter data
        df_athlete = self.df[
            (self.df["athlete_id"] == athlete_id) & (self.df["event_id"] == event_id)
        ].sort_values("date")

        if len(df_athlete) == 0:
            raise ValueError(f"No performances found for {athlete_id} in {event_id}")

        # Calculate personal bests over time
        df_athlete = df_athlete.copy()
        df_athlete["personal_best"] = df_athlete["result_value"].cummin()

        # Create figure
        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=df_athlete["date"],
                y=df_athlete["result_value"],
                mode="markers",
                marker=dict(size=8, color="rgba(100, 150, 255, 0.6)"),
                name="Individual Performance",
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    "Date: %{x|%Y-%m-%d}<br>"
                    "Result: %{y:.2f}<br>"
                    "<extra></extra>"
                ),
                text=[f"{athlete_id} - {event_id}"] * len(df_athlete),
            )
        )

        fig.add_trace(
            go.Scatter(
                x=df_athlete["date"],
                y=df_athlete["personal_best"],
                mode="lines",
                line=dict(color="rgb(255, 100, 100)", width=3),
                name="Personal Best Progression",
                hovertemplate=(
                    "<b>Personal Best</b><br>"
                    "Date: %{x|%Y-%m-%d}<br>"
                    "Best: %{y:.2f}<br>"
                    "<extra></extra>"
                ),
            )
        )

        fig.update_layout(
            title=title or f"{athlete_id} - {event_id} Progression",
            xaxis_title="Date",
            yaxis_title="Performance",
            hovermode="x unified",
            template="plotly_white",
            height=500,
            showlegend=True,
        )

        return fig

    def performance_distribution(
        self,
        event_id: str,
        chart_type: str = "box",
        title: Optional[str] = None,
    ) -> go.Figure:
        """Box plot or histogram of performance distribution in an event.

        Args:
            event_id: Event to analyze
            chart_type: "box" for box plot, "histogram" for histogram
            title: Custom chart title

        Returns:
            Plotly Figure
        """
        df_event = self.df[self.df["event_id"] == event_id].copy()

        if len(df_event) == 0:
            raise ValueError(f"No performances found for {event_id}")

        if chart_type == "box":
            fig = go.Figure()
            fig.add_trace(
                go.Box(
                    y=df_event["result_value"],
                    name="Distribution",
                    marker_color="rgb(100, 150, 255)",
                    boxmean="sd",
                    hovertemplate="Result: %{y:.2f}<extra></extra>",
                )
            )
        else:
            fig = go.Figure()
            fig.add_trace(
                go.Histogram(
                    x=df_event["result_value"],
                    name="Count",
                    marker_color="rgb(100, 150, 255)",
                    nbinsx=20,
                    hovertemplate="Result: %{x:.2f}<br>Count: %{y}<extra></extra>",
                )
            )

        fig.update_layout(
            title=title or f"{event_id} - Performance Distribution",
            xaxis_title="Performance" if chart_type == "histogram" else "",
            yaxis_title="Count" if chart_type == "histogram" else "Performance",
            template="plotly_white",
            height=500,
            showlegend=False,
        )

        return fig

    def multi_athlete_timeseries(
        self,
        athlete_ids: List[str],
        event_id: str,
        title: Optional[str] = None,
    ) -> go.Figure:
        """Line chart comparing multiple athletes' performances over time.

        Args:
            athlete_ids: List of athletes to compare
            event_id: Event to track
            title: Custom chart title

        Returns:
            Plotly Figure
        """
        fig = go.Figure()

        colors = px.colors.qualitative.Plotly
        for i, athlete_id in enumerate(athlete_ids):
            df_athlete = self.df[
                (self.df["athlete_id"] == athlete_id)
                & (self.df["event_id"] == event_id)
            ].sort_values("date")

            if len(df_athlete) == 0:
                continue

            color = colors[i % len(colors)]
            fig.add_trace(
                go.Scatter(
                    x=df_athlete["date"],
                    y=df_athlete["result_value"],
                    mode="lines+markers",
                    name=athlete_id,
                    line=dict(color=color, width=2),
                    marker=dict(size=6),
                    hovertemplate=(
                        f"<b>{athlete_id}</b><br>"
                        "Date: %{x|%Y-%m-%d}<br>"
                        "Result: %{y:.2f}<br>"
                        "<extra></extra>"
                    ),
                )
            )

        fig.update_layout(
            title=title or f"{event_id} - Multi-Athlete Comparison",
            xaxis_title="Date",
            yaxis_title="Performance",
            hovermode="x unified",
            template="plotly_white",
            height=500,
            showlegend=True,
        )

        return fig

    def event_performance_matrix(
        self,
        athlete_ids: Optional[List[str]] = None,
        event_ids: Optional[List[str]] = None,
        title: Optional[str] = None,
    ) -> go.Figure:
        """Heatmap showing athlete × event matrix with best performances.

        Args:
            athlete_ids: List of athletes (all if None)
            event_ids: List of events (all if None)
            title: Custom chart title

        Returns:
            Plotly Figure
        """
        df_pivot = self.df.copy()

        if athlete_ids:
            df_pivot = df_pivot[df_pivot["athlete_id"].isin(athlete_ids)]
        if event_ids:
            df_pivot = df_pivot[df_pivot["event_id"].isin(event_ids)]

        # Get best performance for each athlete-event combination
        matrix = df_pivot.groupby(["athlete_id", "event_id"])["result_value"].min()
        matrix = matrix.unstack(fill_value=None)

        fig = go.Figure(
            data=go.Heatmap(
                z=matrix.values,
                x=matrix.columns,
                y=matrix.index,
                colorscale="Viridis",
                hovertemplate="Athlete: %{y}<br>Event: %{x}<br>Best: %{z:.2f}<extra></extra>",
            )
        )

        fig.update_layout(
            title=title or "Athlete × Event Performance Matrix",
            xaxis_title="Event",
            yaxis_title="Athlete",
            template="plotly_white",
            height=max(400, len(matrix) * 25),
            width=max(600, len(matrix.columns) * 60),
        )

        return fig

    def ranking_chart(
        self,
        event_id: str,
        top_n: int = 10,
        title: Optional[str] = None,
    ) -> go.Figure:
        """Horizontal bar chart ranking athletes by best performance.

        Args:
            event_id: Event to rank
            top_n: Number of top athletes to show
            title: Custom chart title

        Returns:
            Plotly Figure
        """
        df_event = self.df[self.df["event_id"] == event_id].copy()
        df_ranking = df_event.groupby("athlete_id")["result_value"].min().reset_index()
        df_ranking = df_ranking.sort_values("result_value").head(top_n)

        fig = go.Figure(
            go.Bar(
                x=df_ranking["result_value"],
                y=df_ranking["athlete_id"],
                orientation="h",
                marker=dict(color=df_ranking["result_value"], colorscale="Blues"),
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    "Best Performance: %{x:.2f}<br>"
                    "<extra></extra>"
                ),
            )
        )

        fig.update_layout(
            title=title or f"{event_id} - Top {top_n} Athletes",
            xaxis_title="Best Performance",
            yaxis_title="Athlete",
            template="plotly_white",
            height=max(400, top_n * 30),
            showlegend=False,
        )

        return fig

    def category_analysis(
        self,
        event_id: str,
        groupby_column: str = "category_snapshot",
        title: Optional[str] = None,
    ) -> go.Figure:
        """Box plots comparing performance distribution across categories/clubs.

        Args:
            event_id: Event to analyze
            groupby_column: Column to group by (category_snapshot, club_id, etc.)
            title: Custom chart title

        Returns:
            Plotly Figure
        """
        df_event = self.df[self.df["event_id"] == event_id].copy()

        if groupby_column not in df_event.columns:
            raise ValueError(f"Column {groupby_column} not found in dataframe")

        fig = go.Figure()

        for group_val in sorted(df_event[groupby_column].dropna().unique()):
            df_group = df_event[df_event[groupby_column] == group_val]
            fig.add_trace(
                go.Box(
                    y=df_group["result_value"],
                    name=str(group_val),
                    boxmean="sd",
                    hovertemplate="Result: %{y:.2f}<extra></extra>",
                )
            )

        fig.update_layout(
            title=title or f"{event_id} - Distribution by {groupby_column}",
            yaxis_title="Performance",
            template="plotly_white",
            height=500,
            showlegend=True,
        )

        return fig

    def statistics_dashboard(
        self,
        event_id: str,
        title: Optional[str] = None,
    ) -> go.Figure:
        """Dashboard with summary statistics and distribution visualization.

        Args:
            event_id: Event to analyze
            title: Custom chart title

        Returns:
            Plotly Figure with subplots
        """
        df_event = self.df[self.df["event_id"] == event_id].copy()

        if len(df_event) == 0:
            raise ValueError(f"No performances found for {event_id}")

        # Calculate statistics
        stats = {
            "Mean": df_event["result_value"].mean(),
            "Median": df_event["result_value"].median(),
            "Best": df_event["result_value"].min(),
            "Worst": df_event["result_value"].max(),
            "Std Dev": df_event["result_value"].std(),
            "Count": len(df_event),
        }

        # Create subplots
        fig = make_subplots(
            rows=2,
            cols=2,
            subplot_titles=(
                "Distribution",
                "Time Series",
                "Statistics",
                "Top Athletes",
            ),
            specs=[
                [{"type": "histogram"}, {"type": "scatter"}],
                [{"type": "indicator"}, {"type": "bar"}],
            ],
        )

        # Histogram
        fig.add_trace(
            go.Histogram(
                x=df_event["result_value"],
                name="Distribution",
                marker_color="rgb(100, 150, 255)",
                nbinsx=15,
            ),
            row=1,
            col=1,
        )

        # Time series
        df_sorted = df_event.sort_values("date")
        fig.add_trace(
            go.Scatter(
                x=df_sorted["date"],
                y=df_sorted["result_value"],
                mode="markers",
                name="Performances",
                marker=dict(size=5, color="rgb(100, 150, 255)"),
            ),
            row=1,
            col=2,
        )

        # Top athletes
        top_athletes = (
            df_event.groupby("athlete_id")["result_value"]
            .min()
            .sort_values()
            .head(5)
        )
        fig.add_trace(
            go.Bar(
                y=top_athletes.index,
                x=top_athletes.values,
                orientation="h",
                marker_color="rgb(100, 150, 255)",
                name="Top 5",
            ),
            row=2,
            col=2,
        )

        # Statistics indicators
        stats_text = (
            f"<b>Statistics for {event_id}</b><br>"
            f"Best: {stats['Best']:.2f}<br>"
            f"Mean: {stats['Mean']:.2f}<br>"
            f"Median: {stats['Median']:.2f}<br>"
            f"Std Dev: {stats['Std Dev']:.2f}<br>"
            f"Count: {int(stats['Count'])}"
        )

        fig.add_trace(
            go.Indicator(
                mode="number+gauge",
                value=stats["Mean"],
                title={"text": "Mean Performance"},
                domain={"x": [0, 1], "y": [0, 1]},
            ),
            row=2,
            col=1,
        )

        fig.update_xaxes(title_text="Performance", row=1, col=1)
        fig.update_yaxes(title_text="Count", row=1, col=1)
        fig.update_xaxes(title_text="Date", row=1, col=2)
        fig.update_yaxes(title_text="Performance", row=1, col=2)
        fig.update_xaxes(title_text="Performance", row=2, col=2)
        fig.update_yaxes(title_text="Athlete", row=2, col=2)

        fig.update_layout(
            title=title or f"{event_id} - Statistics Dashboard",
            showlegend=False,
            height=800,
            template="plotly_white",
        )

        return fig

    def season_comparison(
        self,
        athlete_id: str,
        event_id: str,
        title: Optional[str] = None,
    ) -> go.Figure:
        """Bar chart comparing athlete performance across seasons (years).

        Args:
            athlete_id: Athlete to analyze
            event_id: Event to track
            title: Custom chart title

        Returns:
            Plotly Figure
        """
        df_athlete = self.df[
            (self.df["athlete_id"] == athlete_id) & (self.df["event_id"] == event_id)
        ].copy()

        if len(df_athlete) == 0:
            raise ValueError(f"No performances found for {athlete_id} in {event_id}")

        # Extract year from date
        df_athlete["year"] = pd.to_datetime(df_athlete["date"]).dt.year

        # Get best performance per year
        df_by_season = df_athlete.groupby("year")["result_value"].min().reset_index()
        df_by_season = df_by_season.sort_values("year")

        fig = go.Figure(
            go.Bar(
                x=df_by_season["year"],
                y=df_by_season["result_value"],
                marker=dict(color="rgb(100, 150, 255)"),
                hovertemplate=(
                    "<b>Season: %{x}</b><br>"
                    "Best Performance: %{y:.2f}<br>"
                    "<extra></extra>"
                ),
            )
        )

        fig.update_layout(
            title=title or f"{athlete_id} - {event_id} Season Comparison",
            xaxis_title="Season (Year)",
            yaxis_title="Best Performance",
            template="plotly_white",
            height=500,
            showlegend=False,
        )

        return fig


def export_to_html(
    figures: Dict[str, go.Figure],
    output_path: str,
    title: str = "Performance Analysis Dashboard",
    include_filters: bool = True,
) -> None:
    """Export multiple figures to a single interactive HTML dashboard.

    Args:
        figures: Dictionary mapping chart names to Plotly Figure objects
        output_path: Path to save HTML file
        title: Dashboard title
        include_filters: Whether to include interactive filter placeholders
    """
    from plotly.subplots import make_subplots

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Create HTML with all figures
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title}</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f5f5f5;
            padding: 20px;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            padding: 30px;
        }}
        h1 {{
            color: #333;
            margin-bottom: 10px;
            text-align: center;
        }}
        .subtitle {{
            color: #666;
            text-align: center;
            margin-bottom: 30px;
            font-size: 14px;
        }}
        .chart-section {{
            margin-bottom: 40px;
            padding-bottom: 30px;
            border-bottom: 1px solid #eee;
        }}
        .chart-section:last-child {{
            border-bottom: none;
        }}
        .chart-title {{
            color: #333;
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 15px;
            padding-left: 10px;
            border-left: 4px solid #1f77b4;
        }}
        .plotly-graph {{
            margin: 15px 0;
        }}
        .timestamp {{
            color: #999;
            font-size: 12px;
            text-align: right;
            margin-top: 20px;
        }}
        .info-box {{
            background-color: #e7f3ff;
            border-left: 4px solid #2196F3;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 4px;
            color: #333;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <p class="subtitle">Interactive Performance Analysis Dashboard</p>

        <div class="info-box">
            💡 <strong>Tip:</strong> Hover over data points for details.
            Click legend items to show/hide series.
            Use the camera icon to download charts as PNG.
        </div>
"""

    # Add each figure
    for chart_name, figure in figures.items():
        html_content += f"""
        <div class="chart-section">
            <div class="chart-title">{chart_name}</div>
            <div class="plotly-graph">
                {figure.to_html(include_plotlyjs=False, div_id=chart_name.replace(" ", "_"))}
            </div>
        </div>
"""

    # Close HTML
    html_content += f"""
        <div class="timestamp">
            Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>
</body>
</html>
"""

    # Write to file with UTF-8 encoding
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Dashboard exported to: {output_path}")


def export_individual_html(
    figure: go.Figure, output_path: str, include_toolbar: bool = True
) -> None:
    """Export a single figure to an interactive HTML file.

    Args:
        figure: Plotly Figure object
        output_path: Path to save HTML file
        include_toolbar: Whether to include Plotly toolbar
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    figure.write_html(
        output_path,
        config={
            "responsive": True,
            "displayModeBar": include_toolbar,
            "displaylogo": False,
        },
    )

    print(f"Chart exported to: {output_path}")
