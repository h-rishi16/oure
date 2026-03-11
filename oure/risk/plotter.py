"""
OURE Risk Calculation - Interactive B-Plane Plotter
===================================================
"""

import numpy as np
import plotly.graph_objects as go
from pathlib import Path

class RiskPlotter:
    """Generates interactive HTML plots for conjunction events."""

    @staticmethod
    def plot_bplane_from_json(event_data: dict, output_path: Path):
        """
        Generates a 2D B-Plane cross-section plot showing the primary satellite
        (with hard-body radius) and the secondary satellite's uncertainty ellipses.
        """
        sigma_x, sigma_z = event_data.get("sigma_bplane_km", [1.0, 1.0])
        miss_dist = event_data.get("miss_distance_km", 0.0)
        hbr_km = event_data.get("hard_body_radius_m", 20.0) / 1000.0
        pc = event_data.get("pc", 0.0)
        primary_id = event_data.get("primary_id", "Primary")
        secondary_id = event_data.get("secondary_id", "Secondary")
        
        fig = go.Figure()
        
        # Primary satellite at the origin with its Hard Body Radius (Collision Disk)
        fig.add_shape(type="circle",
            xref="x", yref="y",
            x0=-hbr_km, y0=-hbr_km, x1=hbr_km, y1=hbr_km,
            fillcolor="rgba(255, 0, 0, 0.5)", line_color="red",
            name="Collision Disk (HBR)"
        )
        # Dummy trace for the legend entry of the shape
        fig.add_trace(go.Scatter(x=[None], y=[None], mode='markers',
                                 marker=dict(size=15, color="rgba(255, 0, 0, 0.5)", line=dict(color="red", width=2)),
                                 name="Collision Disk (HBR)"))
        
        # Secondary satellite assumed at (miss_dist, 0) in this simplified projection
        t = np.linspace(0, 2*np.pi, 100)
        colors = ['rgba(0, 0, 255, 0.8)', 'rgba(0, 0, 255, 0.5)', 'rgba(0, 0, 255, 0.2)']
        
        for idx, n_sig in enumerate([1, 2, 3]):
            x = miss_dist + n_sig * sigma_x * np.cos(t)
            y = n_sig * sigma_z * np.sin(t)
            fig.add_trace(go.Scatter(x=x, y=y, mode='lines', 
                                     name=f'{n_sig}σ Ellipse', 
                                     line=dict(color=colors[idx], dash='dash')))
            
        fig.add_trace(go.Scatter(x=[0], y=[0], mode='markers', 
                                 marker=dict(color='black', size=8, symbol='cross'), 
                                 name=f'{primary_id} Center'))
        fig.add_trace(go.Scatter(x=[miss_dist], y=[0], mode='markers', 
                                 marker=dict(color='blue', size=8, symbol='x'), 
                                 name=f'{secondary_id} Mean'))
        
        # Format the axes to have an equal aspect ratio so circles look like circles
        axis_range = max(miss_dist + 3*sigma_x, 3*sigma_z) * 1.1
        
        fig.update_layout(
            title=f"B-Plane Encounter: {primary_id} vs {secondary_id}<br>Probability of Collision (Pc) = {pc:.2e}",
            xaxis_title="B-Plane ξ (km)",
            yaxis_title="B-Plane ζ (km)",
            xaxis=dict(range=[-axis_range * 0.2, axis_range]),
            yaxis=dict(scaleanchor="x", scaleratio=1),  # Equal aspect ratio
            plot_bgcolor="white",
            xaxis_showgrid=True, xaxis_gridcolor='lightgrey',
            yaxis_showgrid=True, yaxis_gridcolor='lightgrey',
            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
        )
        
        fig.write_html(str(output_path))
