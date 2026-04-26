Performance Data Visualization Guide
=====================================

Overview
--------

The visualization module provides interactive Plotly-based charts for analyzing athletics performance data. All visualizations are exportable as self-contained HTML files with full interactivity, hover tooltips, and responsive design.

Key Features
~~~~~~~~~~~~

- **Interactive Charts** — Hover for details, click legend to toggle series, zoom/pan
- **HTML Export** — Self-contained files that open in any browser
- **Multiple Chart Types** — Progression, distribution, comparison, ranking, heatmaps, dashboards
- **Rich Filtering** — Target specific athletes, events, or categories
- **Reproducible** — Same data produces identical visualizations every time

Quick Start
-----------

Basic athlete progression chart:

.. code-block:: python

    from athletics_performance import PerformanceVisualizer
    import pandas as pd

    # Load performance data
    df = pd.read_parquet("data/silver/performances.parquet")

    # Create visualizer
    viz = PerformanceVisualizer(df)

    # Generate chart
    fig = viz.athlete_progression("A001", "100m")

    # Export to HTML
    fig.write_html("athlete_progression.html")

Or use the dashboard export for multiple visualizations:

.. code-block:: python

    from athletics_performance import export_to_html

    # Create multiple visualizations
    figures = {
        "Athlete Progression": viz.athlete_progression("A001", "100m"),
        "Event Distribution": viz.performance_distribution("100m"),
        "Rankings": viz.ranking_chart("100m"),
        "Statistics": viz.statistics_dashboard("100m"),
    }

    # Export to single interactive HTML dashboard
    export_to_html(
        figures,
        "performance_analysis.html",
        title="Performance Analysis for 100m"
    )

Available Visualizations
------------------------

Athlete Progression
~~~~~~~~~~~~~~~~~~~

Line chart showing an athlete's personal bests over time for a specific event.

**Use Case**: Track an athlete's improvement trajectory and identify periods of progress or plateau.

.. code-block:: python

    fig = viz.athlete_progression(
        athlete_id="A001",
        event_id="100m",
        title="Guillaume Perrin - 100m Progression"
    )

**What You See**:
    - Individual performances as scatter points
    - Personal best (best performance) line overlay
    - Dates on X-axis, performance on Y-axis
    - Hover to see exact dates and times

Performance Distribution
~~~~~~~~~~~~~~~~~~~~~~~~

Box plot or histogram showing how athletes are distributed by performance level.

**Use Case**: Understand benchmarks, identify outliers, see spread of performance.

.. code-block:: python

    # Box plot with mean and standard deviation
    fig = viz.performance_distribution(
        event_id="100m",
        chart_type="box"
    )

    # Or histogram for count distribution
    fig = viz.performance_distribution(
        event_id="100m",
        chart_type="histogram"
    )

**What You See**:
    - Box plot: median (line), quartiles (box), range (whiskers), mean (dashed line)
    - Histogram: count of performances in each time range

Multi-Athlete Time Series
~~~~~~~~~~~~~~~~~~~~~~~~~

Compare multiple athletes' performances over time.

**Use Case**: Head-to-head comparison, identify leaders, track relative progression.

.. code-block:: python

    fig = viz.multi_athlete_timeseries(
        athlete_ids=["A001", "A002", "A003"],
        event_id="100m"
    )

**What You See**:
    - Separate colored line for each athlete
    - All on same timeline
    - Hover to see athlete name, date, performance

Event Performance Matrix
~~~~~~~~~~~~~~~~~~~~~~~~

Heatmap showing athlete × event grid with color intensity representing best performance.

**Use Case**: Quick overview of athlete strengths/weaknesses across events, identify specialists.

.. code-block:: python

    # All athletes and events
    fig = viz.event_performance_matrix()

    # Specific subset
    fig = viz.event_performance_matrix(
        athlete_ids=["A001", "A002", "A003"],
        event_ids=["100m", "200m", "400m", "long_jump"]
    )

**What You See**:
    - Rows = Athletes
    - Columns = Events
    - Color intensity = Performance (darker = better)
    - Hover to see exact best time

Ranking Charts
~~~~~~~~~~~~~~

Horizontal bar chart ranking athletes by best performance in an event.

**Use Case**: Quick leaderboard, see who's fastest/best in an event, top 10/20 view.

.. code-block:: python

    fig = viz.ranking_chart(
        event_id="100m",
        top_n=10  # Show top 10
    )

**What You See**:
    - Horizontal bars, longest = fastest
    - Athlete names on Y-axis
    - Best performance value as bar length
    - Color gradient from light to dark

Category Analysis
~~~~~~~~~~~~~~~~~

Box plots comparing performance distribution across age categories or clubs.

**Use Case**: Demographic analysis, compare M1M vs M2M vs M3M, compare club performance.

.. code-block:: python

    # Compare by age category
    fig = viz.category_analysis(
        event_id="100m",
        groupby_column="category_snapshot"
    )

    # Compare by club
    fig = viz.category_analysis(
        event_id="100m",
        groupby_column="club_id_snapshot"
    )

**What You See**:
    - Separate box plot for each category/club
    - Compare distributions side by side

Statistics Dashboard
~~~~~~~~~~~~~~~~~~~~

Multi-panel dashboard with distribution, time series, top athletes, and summary statistics.

**Use Case**: Comprehensive statistical overview of an event.

.. code-block:: python

    fig = viz.statistics_dashboard(event_id="100m")

**What You See**:
    - Histogram of performance distribution
    - Time series scatter plot
    - Top 5 athletes bar chart
    - Summary statistics (mean, median, std dev, count)

Season Comparison
~~~~~~~~~~~~~~~~~

Bar chart comparing athlete's best performance across different seasons/years.

**Use Case**: Track year-over-year improvement, identify progression patterns.

.. code-block:: python

    fig = viz.season_comparison(
        athlete_id="A001",
        event_id="100m"
    )

**What You See**:
    - Each season as a bar
    - Best performance height
    - Years on X-axis
    - Color intensity shows progression

Advanced Workflows
------------------

Workflow: Athlete Profile Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a complete profile for an athlete across all their events:

.. code-block:: python

    athlete_id = "A001"
    df = pd.read_parquet("data/silver/performances.parquet")
    viz = PerformanceVisualizer(df)

    # Get athlete's events
    athlete_events = df[df["athlete_id"] == athlete_id]["event_id"].unique()

    # Create visualizations for each event
    figures = {}
    for event in athlete_events:
        figures[f"{athlete_id} - {event}"] = viz.athlete_progression(
            athlete_id, event
        )

    # Export comprehensive profile
    export_to_html(
        figures,
        f"{athlete_id}_profile.html",
        title=f"Athlete Profile: {athlete_id}"
    )

Workflow: Club Benchmarking
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Compare club performance across events:

.. code-block:: python

    club_id = "069106"
    df = pd.read_parquet("data/silver/performances.parquet")
    df_club = df[df["club_id_snapshot"] == club_id]
    viz = PerformanceVisualizer(df_club)

    events = ["100m", "200m", "400m"]
    figures = {}

    for event in events:
        # Ranking within club
        figures[f"{event} - Rankings"] = viz.ranking_chart(event, top_n=10)
        # Distribution
        figures[f"{event} - Distribution"] = viz.performance_distribution(event)

    export_to_html(
        figures,
        f"{club_id}_benchmarking.html",
        title=f"Club Benchmarking: {club_id}"
    )

Workflow: Category Performance Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Analyze performance differences across age categories:

.. code-block:: python

    df = pd.read_parquet("data/silver/performances.parquet")
    viz = PerformanceVisualizer(df)

    figures = {}
    events = ["100m", "200m", "400m"]

    for event in events:
        figures[f"{event}"] = viz.category_analysis(
            event,
            groupby_column="category_snapshot"
        )

    export_to_html(
        figures,
        "category_analysis.html",
        title="Performance by Age Category"
    )

HTML Dashboard Features
-----------------------

All exported HTML dashboards include:

**Interactive Elements**
    - Hover tooltips with detailed information
    - Click legend entries to show/hide series
    - Zoom and pan with mouse
    - Reset axes with home button
    - Double-click to reset zoom

**Toolbar**
    - Camera icon to download chart as PNG
    - Download plot as PNG option
    - Zoom, pan, and reset controls

**Responsive Design**
    - Automatic scaling for different screen sizes
    - Works on desktop, tablet, and mobile
    - Reflows as needed

**Styling**
    - Professional light theme
    - Color-coded legend
    - Clear typography
    - Information box with usage tips

Customization
-------------

Custom Titles
~~~~~~~~~~~~~

Most visualization functions accept a ``title`` parameter:

.. code-block:: python

    fig = viz.athlete_progression(
        "A001",
        "100m",
        title="Personal Best Progression for 2026 Season"
    )

Filtering Data
~~~~~~~~~~~~~~

Filter the dataframe before passing to visualizer:

.. code-block:: python

    # Only 2026 data
    df_2026 = df[df["date"].dt.year == 2026]
    viz = PerformanceVisualizer(df_2026)

    # Only specific club
    df_club = df[df["club_id_snapshot"] == "069106"]
    viz = PerformanceVisualizer(df_club)

    # Only youth categories
    df_youth = df[df["category_snapshot"].isin(["BE", "MI"])]
    viz = PerformanceVisualizer(df_youth)

Export Options
~~~~~~~~~~~~~~

Individual HTML file:

.. code-block:: python

    fig = viz.athlete_progression("A001", "100m")
    export_individual_html(fig, "progression.html")

Multi-chart dashboard:

.. code-block:: python

    figures = { ... }
    export_to_html(figures, "dashboard.html", title="My Analysis")

Direct Plotly operations:

.. code-block:: python

    fig = viz.ranking_chart("100m")

    # Save as PNG (requires kaleido package)
    fig.write_image("ranking.png")

    # Save as SVG
    fig.write_image("ranking.svg")

    # Interactive web-based sharing
    fig.show()

API Reference
-------------

Main Class
~~~~~~~~~~

**PerformanceVisualizer(df: pd.DataFrame)**
    Initialize visualizer with performance dataframe.

    Args:
        df: DataFrame with columns: perf_id, athlete_id, event_id,
            result_value, date, unit, measurement, and optional:
            category_snapshot, club_id_snapshot, venue, etc.

    Methods:
        - athlete_progression(athlete_id, event_id, title) → Figure
        - performance_distribution(event_id, chart_type, title) → Figure
        - multi_athlete_timeseries(athlete_ids, event_id, title) → Figure
        - event_performance_matrix(athlete_ids, event_ids, title) → Figure
        - ranking_chart(event_id, top_n, title) → Figure
        - category_analysis(event_id, groupby_column, title) → Figure
        - statistics_dashboard(event_id, title) → Figure
        - season_comparison(athlete_id, event_id, title) → Figure

Export Functions
~~~~~~~~~~~~~~~~

**export_to_html(figures, output_path, title, include_filters)**
    Export multiple figures to interactive HTML dashboard.

    Args:
        figures (Dict[str, Figure]): Chart name → Plotly Figure mapping
        output_path (str): Path to save HTML file
        title (str): Dashboard title
        include_filters (bool): Show filter placeholder (default: True)

**export_individual_html(figure, output_path, include_toolbar)**
    Export single figure to HTML file.

    Args:
        figure (Figure): Plotly Figure object
        output_path (str): Path to save HTML file
        include_toolbar (bool): Show Plotly toolbar (default: True)

Best Practices
--------------

1. **Filter Before Visualizing** — Reduce data to relevant subset for cleaner charts
2. **Use Descriptive Titles** — Help viewers understand what they're seeing
3. **Combine Multiple Views** — Export related charts together in a dashboard
4. **Test Interactivity** — Open HTML file and verify hover, click, zoom all work
5. **Save Multiple Formats** — HTML for sharing, PNG for reports/presentations
6. **Responsive Design** — Test on mobile/tablet to ensure readability
7. **Accessibility** — Include descriptive titles and hover text

Troubleshooting
---------------

**Chart appears empty**
    - Check that data exists for the athlete/event combination
    - Verify date range includes performances
    - Filter dataframe to debug

**HTML file too large**
    - Reduce number of data points (filter by date range)
    - Use simpler chart types (histogram vs scatter)
    - Create separate dashboards instead of one large one

**Hover tooltips cut off**
    - Resize browser window
    - Use full-screen mode
    - Try different browser

**Colors not showing**
    - Check data range (if all values same, gradient might be invisible)
    - Use different chart type
    - Explicitly set color parameters

See Also
--------

- :doc:`guide_medallion` — Data layer architecture
- :doc:`guide_transformations` — Preparing clean data for analysis
- README.md — Quick start examples
