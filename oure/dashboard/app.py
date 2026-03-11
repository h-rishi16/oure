import streamlit as st
import requests
import pandas as pd
import json

st.set_page_config(page_title="OURE Dashboard", page_icon="🛰️", layout="wide")

st.title("🛰️ OURE Space Operations Center")
st.markdown("Monitor high-risk conjunction events and analyze Conjunction Data Messages (CDMs) in real-time.")

st.sidebar.header("Navigation")
page = st.sidebar.radio("Go to", ["Live Fleet Status", "CDM Analysis Tool"])

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
                    # In a real deployment, send to FastAPI endpoint:
                    # response = requests.post("http://localhost:8000/analyze/cdm", files={"file": uploaded_file.getvalue()})
                    
                    # For this demo, we can just save it temporarily and call the parser
                    from oure.data.cdm_parser import CDMParser
                    from oure.risk.calculator import RiskCalculator
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
                except Exception as e:
                    st.error(f"Failed to process file: {e}")
