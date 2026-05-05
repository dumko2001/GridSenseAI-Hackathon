"""
GridSense AI — Streamlit Dashboard (Production-Grade UI/UX)
Designed for clarity, accessibility, and operator decision-making.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

st.set_page_config(
    page_title="GridSense AI — Renewable Forecasting",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS for professional look ──────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    .main-title {
        font-size: 2.2rem; font-weight: 700;
        color: #0f172a; letter-spacing: -0.02em;
        margin-bottom: 0.25rem;
    }
    .subtitle {
        font-size: 1rem; color: #64748b;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.25rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .metric-label {
        font-size: 0.75rem; font-weight: 600;
        text-transform: uppercase; letter-spacing: 0.05em;
        color: #94a3b8; margin-bottom: 0.25rem;
    }
    .metric-value {
        font-size: 1.75rem; font-weight: 700;
        color: #0f172a; line-height: 1.2;
    }
    .metric-unit {
        font-size: 0.875rem; font-weight: 500;
        color: #64748b;
    }
    .insight-card {
        background: #f8fafc;
        border-left: 3px solid #3b82f6;
        border-radius: 0 8px 8px 0;
        padding: 0.875rem 1rem;
        margin-bottom: 0.5rem;
    }
    .insight-time {
        font-size: 0.75rem; font-weight: 600;
        color: #3b82f6; margin-bottom: 0.25rem;
    }
    .insight-text {
        font-size: 0.875rem; color: #334155; line-height: 1.5;
    }
    .alert-card {
        background: #fef2f2;
        border-left: 3px solid #ef4444;
        border-radius: 0 8px 8px 0;
        padding: 0.75rem 1rem;
        margin-bottom: 0.5rem;
    }
    .alert-time {
        font-size: 0.75rem; font-weight: 600;
        color: #ef4444; margin-bottom: 0.25rem;
    }
    .alert-text {
        font-size: 0.875rem; color: #7f1d1d; line-height: 1.5;
    }
    .driver-pill {
        display: inline-block;
        background: #eff6ff;
        color: #1d4ed8;
        font-size: 0.75rem; font-weight: 600;
        padding: 0.35rem 0.75rem;
        border-radius: 999px;
        margin-right: 0.5rem; margin-bottom: 0.5rem;
    }
    .stButton>button {
        background: #0f172a; color: #fff;
        font-weight: 600; border-radius: 8px;
        padding: 0.6rem 1.25rem; border: none;
        width: 100%; transition: all 0.2s;
    }
    .stButton>button:hover {
        background: #1e293b; transform: translateY(-1px);
    }
    .footer-text {
        font-size: 0.75rem; color: #94a3b8;
        text-align: center; margin-top: 2rem;
        padding-top: 1rem; border-top: 1px solid #e2e8f0;
    }
    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

API_URL = os.getenv("API_URL", "http://localhost:8000")

PLANTS = {
    "SOL_PAVAGADA_100": {"name": "Pavagada Solar Park", "capacity": 100, "type": "Solar", "emoji": "☀️", "lat": 14.25, "lon": 77.28},
    "SOL_KOPPAL_50":    {"name": "Koppal Solar Farm",    "capacity": 50,  "type": "Solar", "emoji": "☀️", "lat": 15.35, "lon": 76.15},
    "SOL_RAICHUR_200":  {"name": "Raichur Mega Solar",   "capacity": 200, "type": "Solar", "emoji": "☀️", "lat": 16.21, "lon": 77.35},
    "WIND_CHITRADURGA_80": {"name": "Chitradurga Wind",  "capacity": 80,  "type": "Wind",  "emoji": "💨", "lat": 14.23, "lon": 76.40},
    "WIND_HASSAN_150":  {"name": "Hassan Wind Farm",     "capacity": 150, "type": "Wind",  "emoji": "💨", "lat": 13.00, "lon": 76.10},
}

# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<div style='font-size:1.5rem;font-weight:700;color:#0f172a;margin-bottom:0.5rem;'>⚡ GridSense AI</div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:0.875rem;color:#64748b;margin-bottom:1.5rem;'>Renewable generation forecasting for Karnataka SLDCs</div>", unsafe_allow_html=True)
    
    st.markdown("<div class='metric-label' style='margin-bottom:0.5rem;'>Select Power Plant</div>", unsafe_allow_html=True)
    plant_id = st.selectbox(
        label="Plant",
        label_visibility="collapsed",
        options=list(PLANTS.keys()),
        format_func=lambda k: f"{PLANTS[k]['emoji']} {PLANTS[k]['name']} ({PLANTS[k]['capacity']} MW)",
    )
    plant = PLANTS[plant_id]
    
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        horizon = st.selectbox("Forecast Horizon", [6, 12, 24, 48], index=2, label_visibility="visible")
    with col2:
        st.metric("Resolution", "Hourly", label_visibility="visible")
    
    st.divider()
    
    submitted = st.button("Generate Forecast", type="primary")
    
    st.divider()
    
    with st.expander("🔄 Intra-day Updates"):
        st.caption("Operators can re-run forecasts at any time with the latest weather data. Simply select a new horizon and click **Generate Forecast** again.")
    
    with st.expander("ℹ️ How it works"):
        st.caption("1. **Baseline** — Chronos-Bolt model reads 7 days of history")
        st.caption("2. **Residual** — Real-time weather adjusts for clouds/wind changes")
        st.caption("3. **Physics** — Turbine curves & GHI caps ensure valid output")
        st.caption("4. **Explain** — LLM generates operator-readable reasons")
    
    with st.expander("📊 Daily Reports"):
        st.caption("Generate Excel-ready CSV reports for all plants")
        if st.button("📝 Generate Daily Report", use_container_width=True):
            with st.spinner("Running forecasts for all plants..."):
                try:
                    import subprocess
                    import os
                    result = subprocess.run(
                        ["python", "src/scheduler.py", "--mode", "custom", "--hours", "24"],
                        capture_output=True,
                        text=True,
                        cwd=os.path.dirname(os.path.dirname(__file__)),
                        timeout=120
                    )
                    if result.returncode == 0:
                        st.success("✅ Daily report generated!")
                        # Find the latest report
                        import glob
                        reports = glob.glob("reports/custom_*.csv")
                        if reports:
                            latest = max(reports, key=os.path.getctime)
                            with open(latest, "rb") as f:
                                st.download_button(
                                    label="⬇️ Download Daily Report",
                                    data=f,
                                    file_name=os.path.basename(latest),
                                    mime="text/csv",
                                    use_container_width=True
                                )
                    else:
                        st.error("Failed to generate report. Check server logs.")
                except Exception as e:
                    st.error(f"Error: {e}")
    
    with st.expander("🔒 Privacy"):
        st.caption("No SCADA data leaves this system. Weather metadata only for explanations.")
    
    st.markdown("<div class='footer-text'>Built for KREDL / KSPDCL Theme 10</div>", unsafe_allow_html=True)

# ── Main Content ──────────────────────────────────────────────
st.markdown("<div class='main-title'>Renewable Generation Forecast</div>", unsafe_allow_html=True)
st.markdown(f"<div class='subtitle'>Plant: <b>{plant['name']}</b> · Capacity: <b>{plant['capacity']} MW</b> · Type: <b>{plant['type']}</b> · Location: <b>{plant['lat']}°N, {plant['lon']}°E</b></div>", unsafe_allow_html=True)

if submitted:
    with st.spinner("Running 3-pass forecast pipeline..."):
        try:
            resp = requests.post(
                f"{API_URL}/forecast",
                json={"plant_id": plant_id, "context_hours": 168, "prediction_hours": horizon},
                timeout=90,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.ConnectionError:
            st.error("❌ Cannot connect to API server. Please start it first: `python src/api/main.py`")
            st.stop()
        except requests.exceptions.Timeout:
            st.error("❌ Request timed out. The model may still be loading — try again in 10 seconds.")
            st.stop()
        except Exception as e:
            st.error(f"❌ Error: {e}")
            st.stop()

    if not data:
        st.warning("No forecast data returned.")
        st.stop()
    
    df = pd.DataFrame(data)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["hour"] = df["timestamp"].dt.strftime("%H:%M")
    df["date"] = df["timestamp"].dt.strftime("%d %b")
    
    # ── Metrics Row ─────────────────────────────────────────
    mcol1, mcol2, mcol3, mcol4 = st.columns(4)
    peak_mw = df["forecast_MW"].max()
    min_mw = df["forecast_MW"].min()
    avg_unc = (df["confidence_upper"] - df["confidence_lower"]).mean() / 2
    n_clamps = int(df["was_clamped"].sum())
    cap = plant["capacity"]
    
    with mcol1:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Peak Forecast</div>
            <div class='metric-value'>{peak_mw:.1f}<span class='metric-unit'> MW</span></div>
            <div style='font-size:0.75rem;color:#64748b;margin-top:0.25rem;'>{peak_mw/cap*100:.0f}% of capacity</div>
        </div>
        """, unsafe_allow_html=True)
    with mcol2:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Minimum Forecast</div>
            <div class='metric-value'>{min_mw:.1f}<span class='metric-unit'> MW</span></div>
            <div style='font-size:0.75rem;color:#64748b;margin-top:0.25rem;'>{min_mw/cap*100:.0f}% of capacity</div>
        </div>
        """, unsafe_allow_html=True)
    with mcol3:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Avg. Uncertainty</div>
            <div class='metric-value'>±{avg_unc:.1f}<span class='metric-unit'> MW</span></div>
            <div style='font-size:0.75rem;color:#64748b;margin-top:0.25rem;'>{avg_unc/cap*100:.0f}% of capacity</div>
        </div>
        """, unsafe_allow_html=True)
    with mcol4:
        color = "#ef4444" if n_clamps > 0 else "#22c55e"
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Physics Events</div>
            <div class='metric-value' style='color:{color};'>{n_clamps}<span class='metric-unit'> clamps</span></div>
            <div style='font-size:0.75rem;color:#64748b;margin-top:0.25rem;'>{"Constraints triggered" if n_clamps > 0 else "All values physically valid"}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<div style='margin-bottom:1.5rem;'></div>", unsafe_allow_html=True)
    
    # ── Intra-day update banner ─────────────────────────────
    updated_at = datetime.now().strftime("%d %b %Y, %H:%M IST")
    st.markdown(f"""
    <div style='background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:0.6rem 1rem;margin-bottom:1rem;display:flex;justify-content:space-between;align-items:center;'>
        <div style='font-size:0.875rem;color:#166534;'><b>✅ Forecast generated</b> — Using latest weather data & 7 days of SCADA history</div>
        <div style='font-size:0.75rem;color:#15803d;font-weight:500;'>Updated: {updated_at}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # ── Main Chart + Insights ───────────────────────────────
    chart_col, insight_col = st.columns([3, 1])
    
    with chart_col:
        fig = make_subplots(specs=[[{"secondary_y": False}]])
        
        # Confidence band
        fig.add_trace(go.Scatter(
            x=df["timestamp"], y=df["confidence_upper"],
            mode='lines', line=dict(width=0), showlegend=False,
            hoverinfo='skip', name="Upper"
        ))
        fig.add_trace(go.Scatter(
            x=df["timestamp"], y=df["confidence_lower"],
            mode='lines', line=dict(width=0), fill='tonexty',
            fillcolor='rgba(59, 130, 246, 0.10)',
            name="Confidence Band",
            hovertemplate='Lower: %{y:.1f} MW<extra></extra>',
        ))
        
        # Forecast line
        fig.add_trace(go.Scatter(
            x=df["timestamp"], y=df["forecast_MW"],
            mode='lines+markers', line=dict(color='#2563eb', width=2.5),
            marker=dict(size=5, color='#2563eb', line=dict(width=1, color='#fff')),
            name="Forecast",
            hovertemplate='<b>%{x|%H:%M · %d %b}</b><br>Forecast: %{y:.1f} MW<extra></extra>',
        ))
        
        # Capacity reference line
        fig.add_hline(
            y=cap, line_dash="dash", line_color="#94a3b8",
            annotation_text=f"Rated Capacity ({cap} MW)",
            annotation_position="top right",
            annotation_font_size=10, annotation_font_color="#64748b",
        )
        
        fig.update_layout(
            title=dict(
                text=f"<b>{plant['name']}</b> — Next {horizon}h Generation Forecast",
                font=dict(size=16, color="#0f172a"),
                x=0, xanchor="left",
            ),
            xaxis_title="Time (IST)",
            yaxis_title="Generation (MW)",
            template="plotly_white",
            height=480,
            margin=dict(l=60, r=40, t=80, b=40),
            hovermode="x unified",
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02,
                xanchor="right", x=1, font=dict(size=11),
            ),
            xaxis=dict(showgrid=True, gridcolor="#f1f5f9", tickformat="%H:%M\n%d %b"),
            yaxis=dict(showgrid=True, gridcolor="#f1f5f9", rangemode="tozero"),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    
    with insight_col:
        st.markdown("<div style='font-size:1rem;font-weight:700;color:#0f172a;margin-bottom:0.75rem;'>🔍 Key Insights</div>", unsafe_allow_html=True)
        
        # Top 3 non-trivial explanations
        interesting = df[df["explanation"].str.len() > 40].head(3)
        if interesting.empty:
            interesting = df.head(3)
        
        for _, row in interesting.iterrows():
            st.markdown(f"""
            <div class='insight-card'>
                <div class='insight-time'>{row['hour']} · {row['date']}</div>
                <div class='insight-text'>{row['explanation'][:110]}{'...' if len(row['explanation']) > 110 else ''}</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Weather drivers
        st.markdown("<div style='font-size:0.875rem;font-weight:600;color:#0f172a;margin:1rem 0 0.5rem;'>Weather Drivers</div>", unsafe_allow_html=True)
        drivers = df.iloc[0]["drivers"] if "drivers" in df.columns else {}
        if drivers:
            if drivers.get("cloud_fraction") is not None:
                st.markdown(f"<span class='driver-pill'>☁️ Cloud: {drivers['cloud_fraction']*100:.0f}%</span>", unsafe_allow_html=True)
            if drivers.get("wind_speed_10m") is not None:
                st.markdown(f"<span class='driver-pill'>💨 Wind: {drivers['wind_speed_10m']:.1f} m/s</span>", unsafe_allow_html=True)
            st.markdown(f"<span class='driver-pill'>📉 Residual: {drivers.get('residual_MW', 0):.1f} MW</span>", unsafe_allow_html=True)
        
        # Physics alerts
        if df["was_clamped"].any():
            st.markdown("<div style='font-size:0.875rem;font-weight:600;color:#0f172a;margin:1rem 0 0.5rem;'>⚠️ Physics Alerts</div>", unsafe_allow_html=True)
            for _, row in df[df["was_clamped"]].head(3).iterrows():
                st.markdown(f"""
                <div class='alert-card'>
                    <div class='alert-time'>{row['hour']} · {row['date']}</div>
                    <div class='alert-text'>{row['clamp_reason'][:90]}{'...' if len(row['clamp_reason']) > 90 else ''}</div>
                </div>
                """, unsafe_allow_html=True)
    
    st.divider()
    
    # ── Data Table ──────────────────────────────────────────
    st.markdown("<div style='font-size:1rem;font-weight:700;color:#0f172a;margin-bottom:0.75rem;'>📋 Hourly Forecast Detail</div>", unsafe_allow_html=True)
    
    display_df = df[["hour", "date", "forecast_MW", "confidence_lower", "confidence_upper", "explanation", "was_clamped"]].copy()
    display_df.columns = ["Time", "Date", "Forecast (MW)", "Lower (MW)", "Upper (MW)", "Explanation", "Clamped"]
    display_df["Clamped"] = display_df["Clamped"].map({True: "⚠️ Yes", False: ""})
    
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Time": st.column_config.TextColumn(width="small"),
            "Date": st.column_config.TextColumn(width="small"),
            "Forecast (MW)": st.column_config.NumberColumn(format="%.1f", width="medium"),
            "Lower (MW)": st.column_config.NumberColumn(format="%.1f", width="medium"),
            "Upper (MW)": st.column_config.NumberColumn(format="%.1f", width="medium"),
            "Explanation": st.column_config.TextColumn(width="large"),
            "Clamped": st.column_config.TextColumn(width="small"),
        },
    )
    
    # ── Download & API ──────────────────────────────────────
    dl_col, api_col = st.columns([1, 2])
    with dl_col:
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Download CSV",
            data=csv,
            file_name=f"forecast_{plant_id}_{horizon}h_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with api_col:
        with st.expander("📡 API Integration Code"):
            st.code(f'''import requests

response = requests.post(
    "{API_URL}/forecast",
    json={{
        "plant_id": "{plant_id}",
        "context_hours": 168,
        "prediction_hours": {horizon}
    }}
)
data = response.json()
print(f"Forecast: {{data[0]['forecast_MW']}} MW")
print(f"Explanation: {{data[0]['explanation']}}")
''', language="python")

else:
    # ── Welcome State ───────────────────────────────────────
    st.info("👈 Select a plant from the sidebar and click **Generate Forecast** to begin.")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        <div style='background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:1.25rem;'>
            <div style='font-size:1.5rem;margin-bottom:0.5rem;'>🧠</div>
            <div style='font-weight:600;color:#0f172a;margin-bottom:0.25rem;'>Baseline Forecast</div>
            <div style='font-size:0.875rem;color:#64748b;line-height:1.5;'>Chronos-Bolt foundation model processes 7 days of historical patterns, seasonality, and weather correlations.</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div style='background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:1.25rem;'>
            <div style='font-size:1.5rem;margin-bottom:0.5rem;'>🛰️</div>
            <div style='font-weight:600;color:#0f172a;margin-bottom:0.25rem;'>Satellite Residual</div>
            <div style='font-size:0.875rem;color:#64748b;line-height:1.5;'>Real-time NASA POWER irradiance and Open-Meteo weather adjust the baseline for sudden anomalies.</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div style='background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:1.25rem;'>
            <div style='font-size:1.5rem;margin-bottom:0.5rem;'>⚙️</div>
            <div style='font-weight:600;color:#0f172a;margin-bottom:0.25rem;'>Physics Validation</div>
            <div style='font-size:0.875rem;color:#64748b;line-height:1.5;'>Turbine power curves, inverter limits, and clear-sky GHI caps ensure physically valid output.</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<div style='margin-top:2rem;text-align:center;font-size:0.875rem;color:#94a3b8;'>Built for KREDL / KSPDCL Theme 10 · On-premise ready · Zero SCADA modifications</div>", unsafe_allow_html=True)
