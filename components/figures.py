"""Plotly figure builders shared by the pages."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.colors import qualitative

from components.data import columns_for, fmt, is_numeric, label, sbp_level_name

ACCENT = "#1f4e79"
NA_GREY = "#b0b7c3"
PALETTE = qualitative.Safe + qualitative.Plotly
MIN_PX, MAX_PX = 9, 38

# Domain/impact/topic display order (must match the Excel column names)
IMPACT_COLS = ["sri_impact_energy_efficiency_pct", "sri_impact_energy_flexibility_pct", "sri_impact_comfort_pct",
               "sri_impact_convenience_pct", "sri_impact_health_wellbeing_pct", "sri_impact_maintenance_pct",
               "sri_impact_information_pct"]
DOMAIN_COLS = ["sri_domain_heating_pct", "sri_domain_dhw_pct", "sri_domain_cooling_pct", "sri_domain_ventilation_pct",
               "sri_domain_lighting_pct", "sri_domain_envelope_pct", "sri_domain_electricity_pct",
               "sri_domain_ev_charging_pct", "sri_domain_monitoring_control_pct"]
KF_COLS = ["sri_kf1_building_pct", "sri_kf2_user_pct", "sri_kf3_grid_pct"]
SBP_TOPIC_COLS = ["sbp_enabling_technology_level", "sbp_indoor_environment_level", "sbp_energy_resources_level",
                  "sbp_safety_reliability_level", "sbp_adaptability_level"]


def short_label(col: str) -> str:
    """Label without the 'SRI impact – ' style prefix, for chart axes."""
    lab = label(col, with_unit=False)
    return lab.split(" – ", 1)[-1]


def empty_figure(message: str, height: int = 400) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=message, showarrow=False, font=dict(size=15, color="#555"),
                       xref="paper", yref="paper", x=0.5, y=0.5)
    fig.update_layout(height=height, xaxis_visible=False, yaxis_visible=False,
                      plot_bgcolor="white", paper_bgcolor="white", margin=dict(l=10, r=10, t=10, b=10))
    return fig


def hover_text(df: pd.DataFrame, extra_cols: list[str]) -> list[str]:
    cols = []
    for c in columns_for("hover") + [c for c in extra_cols if c]:
        if c not in cols and c not in ("building_name",):
            cols.append(c)
    texts = []
    for _, r in df.iterrows():
        lines = [f"<b>{r['building_name']}</b>"]
        for c in cols:
            v = r.get(c)
            txt = fmt(c, v)
            if c == "sbp_level" and txt != "n/a":
                txt = f"{txt} ({sbp_level_name(v)})"
            lines.append(f"{label(c, with_unit=False)}: {txt}")
        texts.append("<br>".join(lines))
    return texts


def _scaled_sizes(values: pd.Series) -> np.ndarray:
    v = values.astype(float)
    vmin, vmax = np.nanmin(v), np.nanmax(v)
    if not np.isfinite(vmin) or vmax == vmin:
        return np.where(v.notna(), (MIN_PX + MAX_PX) / 2, MIN_PX - 2)
    s = MIN_PX + (MAX_PX - MIN_PX) * (v - vmin) / (vmax - vmin)  # works for negative values too
    return np.where(v.notna(), s, MIN_PX - 3)


def _auto_view(df: pd.DataFrame) -> tuple[dict, float]:
    lat, lon = df["latitude"].astype(float), df["longitude"].astype(float)
    center = {"lat": float((lat.min() + lat.max()) / 2), "lon": float((lon.min() + lon.max()) / 2)}
    extent = max(float(lon.max() - lon.min()), float(lat.max() - lat.min()) * 2.2, 0.02)
    zoom = max(1.0, min(12.0, math.log2(360 / extent) - 0.6))
    return center, zoom


def map_figure(df: pd.DataFrame, size_col: str | None, color_col: str | None,
               basemap: str = "carto-positron", colorscale: str = "Viridis", height: int = 620) -> go.Figure:
    df = df.dropna(subset=["latitude", "longitude"])
    if df.empty:
        return empty_figure("No buildings match the current filters.", height)
    sizes = _scaled_sizes(df[size_col]) if size_col else np.full(len(df), 16.0)
    texts = hover_text(df, [size_col, color_col])
    texts = np.array(texts, dtype=object)
    fig = go.Figure()

    def add(mask, marker, name, showlegend=True):
        fig.add_trace(go.Scattermap(
            lat=df["latitude"].to_numpy()[mask], lon=df["longitude"].to_numpy()[mask],
            customdata=df["building_id"].to_numpy()[mask], hovertext=texts[mask],
            hovertemplate="%{hovertext}<extra></extra>", mode="markers",
            marker=marker, name=name, showlegend=showlegend))

    if color_col and is_numeric(color_col):
        vals = df[color_col].astype(float).to_numpy()
        has = ~np.isnan(vals)
        if has.any():
            add(has, dict(size=sizes[has], color=vals[has], colorscale=colorscale, opacity=0.85,
                          colorbar=dict(title=dict(text=label(color_col), side="right"), thickness=14)),
                label(color_col, with_unit=False), showlegend=False)
        if (~has).any():
            add(~has, dict(size=sizes[~has], color=NA_GREY, opacity=0.8), "n/a")
    else:
        groups = (df[color_col].fillna("n/a").astype(str) if color_col
                  else pd.Series(["Buildings"] * len(df), index=df.index)).to_numpy()
        for i, g in enumerate(sorted(set(groups))):
            m = groups == g
            add(m, dict(size=sizes[m], color=NA_GREY if g == "n/a" else PALETTE[i % len(PALETTE)], opacity=0.85), g)
    center, zoom = _auto_view(df)
    fig.update_layout(
        map=dict(style=basemap, center=center, zoom=zoom),
        height=height, margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(title=dict(text=label(color_col, with_unit=False) if color_col else ""), bgcolor="rgba(255,255,255,0.85)",
                    x=0.01, y=0.99, xanchor="left", yanchor="top"),
        uirevision=f"{size_col}-{color_col}",  # keep zoom when only filters change
    )
    return fig


def scatter_figure(df: pd.DataFrame, x: str, y: str, color: str | None,
                   trendline: bool = True, show_labels: bool = True, height: int = 560) -> tuple[go.Figure, str]:
    d = df.dropna(subset=[x, y])
    if d.empty:
        return empty_figure("No buildings have values for both selected parameters."), ""
    texts = hover_text(d, [x, y, color])
    fig = go.Figure()
    mode = "markers+text" if show_labels else "markers"
    marker_base = dict(size=13, line=dict(width=1, color="white"))
    if color and is_numeric(color):
        vals = d[color]
        fig.add_trace(go.Scatter(
            x=d[x], y=d[y], mode=mode, text=d["short_name"], textposition="top center",
            customdata=d["building_id"], hovertext=texts, hovertemplate="%{hovertext}<extra></extra>",
            marker=dict(**marker_base, color=vals, colorscale="Viridis",
                        colorbar=dict(title=dict(text=label(color), side="right"), thickness=14)),
            showlegend=False))
    else:
        groups = d[color].fillna("n/a").astype(str) if color else pd.Series(["Buildings"] * len(d), index=d.index)
        for i, g in enumerate(sorted(groups.unique())):
            m = (groups == g).to_numpy()
            fig.add_trace(go.Scatter(
                x=d[x][m], y=d[y][m], mode=mode, text=d["short_name"][m], textposition="top center",
                customdata=d["building_id"][m], hovertext=np.array(texts)[m],
                hovertemplate="%{hovertext}<extra></extra>", name=g,
                marker=dict(**marker_base, color=PALETTE[i % len(PALETTE)])))

    stats = f"n = {len(d)}"
    if len(d) >= 3 and d[x].nunique() > 1 and d[y].nunique() > 1:
        xv, yv = d[x].astype(float).to_numpy(), d[y].astype(float).to_numpy()
        r = float(np.corrcoef(xv, yv)[0, 1])
        slope, intercept = np.polyfit(xv, yv, 1)
        sign = "−" if intercept < 0 else "+"
        stats += f"  ·  Pearson r = {r:.2f}  ·  R² = {r * r:.2f}  ·  fit: y = {slope:.3g}·x {sign} {abs(intercept):.3g}"
        if trendline:
            xs = np.linspace(xv.min(), xv.max(), 50)
            fig.add_trace(go.Scatter(x=xs, y=slope * xs + intercept, mode="lines", name=f"Linear fit (R² = {r*r:.2f})",
                                     line=dict(color="#444", dash="dash", width=1.5), hoverinfo="skip"))
    fig.update_layout(
        height=height, plot_bgcolor="white", paper_bgcolor="white", margin=dict(l=60, r=20, t=20, b=60),
        xaxis=dict(title=dict(text=label(x)), gridcolor="#e5e8ee", zerolinecolor="#c8ccd4"),
        yaxis=dict(title=dict(text=label(y)), gridcolor="#e5e8ee", zerolinecolor="#c8ccd4"),
        legend=dict(title=dict(text=label(color, with_unit=False) if color else ""), orientation="h", y=-0.18),
    )
    return fig, stats


# ----------------------------------------------------------------- single-building / comparison charts
def bar_scores(row: pd.Series, cols: list[str], title: str, unit_range=(-50, 100), height=340) -> go.Figure:
    cols = [c for c in cols if c in row.index]
    vals = [row[c] for c in cols]
    if all(pd.isna(v) for v in vals):
        return empty_figure("Not available for this building", height)
    names = [short_label(c) for c in cols]
    colors = [NA_GREY if pd.isna(v) else ("#c0504d" if v < 0 else ACCENT) for v in vals]
    text = ["not assessed" if pd.isna(v) else f"{v:.1f}" for v in vals]
    fig = go.Figure(go.Bar(x=[0 if pd.isna(v) else v for v in vals], y=names, orientation="h",
                           marker_color=colors, text=text, textposition="outside", cliponaxis=False,
                           hovertemplate="%{y}: %{text}<extra></extra>"))
    fig.update_layout(title=dict(text=title, x=0, font=dict(size=15)), height=height,
                      xaxis=dict(range=list(unit_range), gridcolor="#e5e8ee", zerolinecolor="#888"),
                      yaxis=dict(autorange="reversed"), plot_bgcolor="white", paper_bgcolor="white",
                      margin=dict(l=10, r=40, t=40, b=30))
    return fig


def heatmap_detailed(detail: pd.DataFrame, height=420) -> go.Figure:
    if detail.empty:
        return empty_figure("No detailed domain × impact matrix available for this building", height)
    piv = detail.pivot_table(index="domain", columns="impact", values="score_pct", aggfunc="first", sort=False)
    fig = go.Figure(go.Heatmap(z=piv.values, x=piv.columns, y=piv.index, colorscale="RdYlGn", zmin=-50, zmax=100,
                               text=np.vectorize(lambda v: "" if pd.isna(v) else f"{v:.0f}")(piv.values),
                               texttemplate="%{text}", hovertemplate="%{y} × %{x}: %{z:.1f} %<extra></extra>",
                               colorbar=dict(title=dict(text="%"), thickness=12)))
    fig.update_layout(title=dict(text="Detailed SRI scores: technical domain × impact criterion [%]", x=0, font=dict(size=15)),
                      height=height, yaxis=dict(autorange="reversed"), xaxis=dict(tickangle=-25),
                      margin=dict(l=10, r=10, t=40, b=80), paper_bgcolor="white")
    return fig


def radar(df: pd.DataFrame, cols: list[str], title: str, rng=(0, 100), height=430) -> go.Figure:
    cols = [c for c in cols if c in df.columns]
    if df.empty or not cols:
        return empty_figure("Select buildings to compare", height)
    theta = [short_label(c) for c in cols]
    fig = go.Figure()
    for i, (_, r) in enumerate(df.iterrows()):
        vals = [r[c] for c in cols]
        if all(pd.isna(v) for v in vals):
            continue
        vals = [None if pd.isna(v) else v for v in vals]
        fig.add_trace(go.Scatterpolar(r=vals + vals[:1], theta=theta + theta[:1], name=r["short_name"],
                                      fill="toself", opacity=0.55, line=dict(color=PALETTE[i % len(PALETTE)]),
                                      connectgaps=True))
    if not fig.data:
        return empty_figure("No data for the selected buildings", height)
    fig.update_layout(title=dict(text=title, x=0, font=dict(size=15)), height=height,
                      polar=dict(radialaxis=dict(range=list(rng), gridcolor="#dde"), angularaxis=dict(gridcolor="#dde")),
                      legend=dict(orientation="h", y=-0.12), margin=dict(l=40, r=40, t=50, b=40), paper_bgcolor="white")
    return fig


def grouped_bars(df: pd.DataFrame, cols: list[str], title: str, rng=None, height=420) -> go.Figure:
    cols = [c for c in cols if c in df.columns]
    if df.empty:
        return empty_figure("Select buildings to compare", height)
    names = [short_label(c) for c in cols]
    fig = go.Figure()
    for i, (_, r) in enumerate(df.iterrows()):
        fig.add_trace(go.Bar(x=names, y=[r[c] for c in cols], name=r["short_name"],
                             marker_color=PALETTE[i % len(PALETTE)]))
    fig.update_layout(title=dict(text=title, x=0, font=dict(size=15)), barmode="group", height=height,
                      plot_bgcolor="white", paper_bgcolor="white", yaxis=dict(gridcolor="#e5e8ee", range=rng),
                      xaxis=dict(tickangle=-25), legend=dict(orientation="h", y=1.12), margin=dict(l=50, r=10, t=70, b=90))
    return fig


def location_map(row: pd.Series, height=300) -> go.Figure:
    if pd.isna(row.get("latitude")) or pd.isna(row.get("longitude")):
        return empty_figure("No coordinates", height)
    fig = go.Figure(go.Scattermap(lat=[row["latitude"]], lon=[row["longitude"]], mode="markers",
                                  marker=dict(size=16, color=ACCENT), hovertext=[row["building_name"]],
                                  hovertemplate="%{hovertext}<extra></extra>"))
    fig.update_layout(map=dict(style="carto-positron", center={"lat": row["latitude"], "lon": row["longitude"]}, zoom=11),
                      height=height, margin=dict(l=0, r=0, t=0, b=0))
    return fig
