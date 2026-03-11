import streamlit as st
import requests
import pandas as pd
import json

st.set_page_config(page_title="OURE Dashboard", page_icon="🛰️", layout="wide")

st.title("🛰️ OURE Space Operations Center")
st.markdown("Monitor high-risk conjunction events and analyze Conjunction Data Messages (CDMs) in real-time.")

st.sidebar.header("Navigation")
page = st.sidebar.radio("Go to", ["Live Fleet Status", "CDM Analysis Tool", "Risk Evolution History"])

# --- PAGE 1: Live Fleet Status ---
if page == "Live Fleet Status":
    st.header("Global Fleet Threat Assessment")
    st.info("Displaying latest conjunction data from continuous monitoring runs.")
    
    # In a real app, this would query a database. We'll load the mock results.
    try:
        with open("mock_results.json", "r") as f:
            data = json.load(f)
            
        if data:
            df = pd.DataFrame(data)
            
            # Metrics
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Events Tracked", len(df))
            col2.metric("RED Alerts (Pc > 1e-3)", len(df[df['warning_level'] == 'RED']))
            col3.metric("YELLOW Alerts (Pc > 1e-5)", len(df[df['warning_level'] == 'YELLOW']))
            
            st.subheader("High-Risk Encounter Feed")
            
            # Display styled dataframe
            def color_risk(val):
                color = 'red' if val == 'RED' else 'yellow' if val == 'YELLOW' else 'green'
                return f'color: {color}; font-weight: bold'
                
            st.dataframe(
                df[['primary_id', 'secondary_id', 'tca', 'pc', 'miss_distance_km', 'warning_level']]
                .style.map(color_risk, subset=['warning_level'])
                .format({'pc': '{:.2e}', 'miss_distance_km': '{:.3f}'}),
                use_container_width=True
            )
        else:
            st.success("No active conjunctions found.")
            
    except FileNotFoundError:
        st.warning("No live data found. Run `oure analyze` or `oure monitor` to generate results.")

# --- PAGE 2: CDM Analysis Tool ---
elif page == "CDM Analysis Tool":
    st.header("CCSDS CDM Ingestion Engine")
    st.markdown("Upload official Space Force CDMs to calculate exact collision probabilities using Foster's algorithm.")
    
    uploaded_file = st.file_uploader("Upload JSON CDM", type=["json"])
    hbr = st.number_input("Combined Hard-Body Radius (meters)", min_value=1.0, value=20.0)
    
    if uploaded_file is not None:
        if st.button("Analyze Risk"):
            with st.spinner("Processing CDM via OURE Engine..."):
                try:
                    from oure.data.cdm_parser import CDMParser
                    from oure.risk.calculator import RiskCalculator
                    from oure.risk.plotter import RiskPlotter
                    import tempfile
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
                        tmp.write(uploaded_file.getvalue())
                        tmp_path = tmp.name
                        
                    event = CDMParser.parse_json(tmp_path)
                    calc = RiskCalculator(hard_body_radius_m=hbr)
                    res = calc.compute_pc(event)
                    
                    st.success("Analysis Complete")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Probability of Collision (Pc)", f"{res.pc:.2e}")
                        st.metric("Warning Level", res.warning_level)
                    with col2:
                        st.metric("Time of Closest Approach", res.conjunction.tca.strftime('%Y-%m-%d %H:%M:%S UTC'))
                        st.metric("Miss Distance", f"{res.conjunction.miss_distance_km:.3f} km")
                        
                    if res.warning_level == "RED":
                        st.error("🚨 EMERGENCY: Collision threshold exceeded. Recommend immediate avoidance maneuver analysis.")
                        
                    st.subheader("Encounter Visualizations")
                    tab1, tab2 = st.tabs(["3D Orbital Geometry", "2D B-Plane Projection"])
                    
                    with tab1:
                        st.markdown("Interactive 3D representation of the encounter around TCA (±30 seconds).")
                        fig_3d = RiskPlotter.create_3d_encounter_figure(event)
                        st.plotly_chart(fig_3d, use_container_width=True)
                        
                    with tab2:
                        st.markdown("2D projection of the encounter onto the B-Plane (orthogonal to relative velocity).")
                        # Format data for the 2D plotter
                        event_data = {
                            "primary_id": event.primary_id,
                            "secondary_id": event.secondary_id,
                            "pc": res.pc,
                            "miss_distance_km": event.miss_distance_km,
                            "hard_body_radius_m": hbr,
                            "sigma_bplane_km": [res.b_plane_sigma_x, res.b_plane_sigma_z]
                        }
                        fig_2d = RiskPlotter.create_bplane_figure(event_data)
                        st.plotly_chart(fig_2d, use_container_width=True)
                        
                except Exception as e:
                    st.error(f"Failed to process file: {e}")

# --- PAGE 3: Risk Evolution History ---
elif page == "Risk Evolution History":
    st.header("Risk Evolution History")
    st.markdown("Track how the Probability of Collision (Pc) evolves over time as TCA approaches.")
    
    col1, col2 = st.columns(2)
    with col1:
        primary_id = st.text_input("Primary NORAD ID", value="25544")
    with col2:
        secondary_id = st.text_input("Secondary NORAD ID", value="43205")
        
    if st.button("Load History"):
        try:
            from oure.data.cache import CacheManager
            cache = CacheManager()
            records = cache.get_risk_history(primary_id, secondary_id)
            
            if not records:
                st.warning(f"No historical risk data found for {primary_id} vs {secondary_id}.")
            else:
                st.success(f"Found {len(records)} historical risk evaluations.")
                
                df = pd.DataFrame(records)
                df['evaluation_time'] = pd.to_datetime(df['evaluation_time'])
                
                import plotly.graph_objects as go
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=df['evaluation_time'], y=df['pc'], 
                    mode='lines+markers',
                    name='Probability of Collision (Pc)',
                    line=dict(color='red', width=3),
                    marker=dict(size=8, symbol='circle')
                ))
                
                fig.add_hline(y=1e-3, line_dash="dash", line_color="red", annotation_text="RED Alert (1e-3)")
                fig.add_hline(y=1e-5, line_dash="dash", line_color="orange", annotation_text="YELLOW Alert (1e-5)")

                fig.update_layout(
                    title=f"Risk Evolution: {primary_id} vs {secondary_id}",
                    xaxis_title="Evaluation Time (UTC)",
                    yaxis_title="Probability of Collision (Pc)",
                    yaxis_type="log",
                    yaxis=dict(range=[-8, 0]),
                    plot_bgcolor="white",
                    hovermode="x unified"
                )
                st.plotly_chart(fig, use_container_width=True)
                
                st.subheader("Raw History Data")
                st.dataframe(df)
        except Exception as e:
            st.error(f"Error loading history: {e}")
