"""Court diagram with zone heatmap overlay."""

import plotly.graph_objects as go


# Standard volleyball court zones (1-6) as rectangles
# Zone layout (from our perspective, looking at opponent):
#   4 | 3 | 2
#   5 | 6 | 1
ZONE_COORDS = {
    1: {"x0": 6, "x1": 9, "y0": 0, "y1": 4.5},
    2: {"x0": 6, "x1": 9, "y0": 4.5, "y1": 9},
    3: {"x0": 3, "x1": 6, "y0": 4.5, "y1": 9},
    4: {"x0": 0, "x1": 3, "y0": 4.5, "y1": 9},
    5: {"x0": 0, "x1": 3, "y0": 0, "y1": 4.5},
    6: {"x0": 3, "x1": 6, "y0": 0, "y1": 4.5},
}


def court_heatmap(zone_data: dict, metric: str = "eff", title: str = "") -> go.Figure:
    """Draw volleyball court with zones colored by a metric.
    zone_data: {zone_num: {"eff": 0.15, "kills": 10, "attempts": 50, ...}}
    """
    fig = go.Figure()

    # Draw court outline
    fig.add_shape(type="rect", x0=0, y0=0, x1=9, y1=9, line=dict(color="black", width=2))
    # Net line
    fig.add_shape(type="line", x0=0, y0=4.5, x1=9, y1=4.5, line=dict(color="black", width=3))
    # Zone dividers
    fig.add_shape(type="line", x0=3, y0=0, x1=3, y1=9, line=dict(color="gray", width=1, dash="dot"))
    fig.add_shape(type="line", x0=6, y0=0, x1=6, y1=9, line=dict(color="gray", width=1, dash="dot"))

    # Color zones
    max_val = max((d.get(metric, 0) for d in zone_data.values()), default=1) or 1
    min_val = min((d.get(metric, 0) for d in zone_data.values()), default=0)

    for zone, coords in ZONE_COORDS.items():
        data = zone_data.get(zone, {})
        val = data.get(metric, 0)
        # Normalize to 0-1 for color
        norm = (val - min_val) / (max_val - min_val) if max_val != min_val else 0.5
        r = int(255 * (1 - norm))
        g = int(255 * norm)
        color = f"rgba({r}, {g}, 100, 0.4)"

        fig.add_shape(type="rect", fillcolor=color, line=dict(width=0),
                      **coords)

        # Zone label
        cx = (coords["x0"] + coords["x1"]) / 2
        cy = (coords["y0"] + coords["y1"]) / 2
        label = f"Z{zone}<br>{val:.3f}" if isinstance(val, float) else f"Z{zone}<br>{val}"
        fig.add_annotation(x=cx, y=cy, text=label, showarrow=False,
                          font=dict(size=14, color="black"))

    fig.update_layout(
        title=title, height=500, width=450,
        xaxis=dict(visible=False, range=[-0.5, 9.5]),
        yaxis=dict(visible=False, range=[-0.5, 9.5], scaleanchor="x"),
        margin=dict(l=20, r=20, t=50, b=20),
    )
    return fig
