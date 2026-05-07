"""
GridSense AI — Streamlit Dashboard (Production-Grade UI/UX)
Designed for clarity, accessibility, and operator decision-making.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from runtime_config import chdir_project_root, configure_runtime

configure_runtime()
chdir_project_root()

from api.main import build_forecast_frame, get_pipeline, load_inputs, validate_language
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from datetime import datetime

st.set_page_config(
    page_title="GridSense AI — Renewable Forecasting",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS for professional look ──────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');

    :root {
        --ink-950: #0b1220;
        --ink-900: #101a2b;
        --ink-850: #142238;
        --line: rgba(255, 255, 255, 0.08);
        --line-strong: rgba(255, 255, 255, 0.16);
        --paper: #f4efe5;
        --paper-strong: #fffaf1;
        --paper-line: rgba(14, 22, 34, 0.08);
        --paper-text: #132033;
        --paper-muted: #5f6f84;
        --teal: #7fb7af;
        --teal-deep: #2e6c6e;
        --amber: #d6a14d;
        --amber-soft: #ecd3a2;
        --signal: #e57a58;
        --mist: #9fb0c3;
    }

    html, body, [class*="css"] {
        font-family: 'Manrope', sans-serif;
        background: var(--ink-950);
        color: #eef3f8;
    }

    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(circle at 12% 0%, rgba(127, 183, 175, 0.18), transparent 30%),
            radial-gradient(circle at 88% 8%, rgba(214, 161, 77, 0.12), transparent 26%),
            linear-gradient(180deg, #0b1220 0%, #0d1627 52%, #0a1220 100%);
        color: #eef3f8;
    }

    [data-testid="stAppViewContainer"]::before {
        content: "";
        position: fixed;
        inset: 0;
        pointer-events: none;
        opacity: 0.14;
        background-image:
            repeating-radial-gradient(circle at 0 0, transparent 0 32px, rgba(255,255,255,0.05) 32px 33px),
            linear-gradient(115deg, transparent 0 48%, rgba(255,255,255,0.06) 48% 48.4%, transparent 48.4% 100%);
        mix-blend-mode: screen;
    }

    [data-testid="stAppViewContainer"] > .main {
        background: transparent;
    }

    .main .block-container {
        padding-top: 1.8rem;
        padding-bottom: 4rem;
        max-width: 1440px;
    }

    [data-testid="stSidebar"] {
        background:
            linear-gradient(180deg, rgba(16, 26, 43, 0.96) 0%, rgba(11, 18, 32, 0.98) 100%);
        border-right: 1px solid var(--line);
    }

    [data-testid="stSidebar"] > div:first-child {
        background: transparent;
    }

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stCaption {
        color: #d7e0ea;
    }

    [data-testid="stSidebar"] [data-baseweb="select"] > div,
    [data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div {
        background: rgba(255, 250, 241, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.10);
        border-radius: 14px;
        color: #f7f3ea;
        min-height: 3.2rem;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);
    }

    [data-testid="stSidebar"] .stMetric {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 0.75rem 0.9rem;
    }

    [data-testid="stSidebar"] .stMetric label,
    [data-testid="stSidebar"] .stMetric [data-testid="stMetricLabel"] {
        color: #93a2b7;
    }

    [data-testid="stSidebar"] .stMetric [data-testid="stMetricValue"] {
        color: #f4efe5;
        font-weight: 700;
    }

    [data-testid="stSidebar"] .stButton > button {
        background: linear-gradient(135deg, #d6a14d 0%, #b67a31 100%);
        color: #120e09;
        font-weight: 800;
        letter-spacing: 0.01em;
        border-radius: 14px;
        padding: 0.82rem 1.2rem;
        border: 1px solid rgba(236, 211, 162, 0.55);
        width: 100%;
        box-shadow: 0 16px 30px rgba(182, 122, 49, 0.18);
        transition: transform 0.18s ease, box-shadow 0.18s ease, filter 0.18s ease;
    }

    [data-testid="stSidebar"] .stButton > button:hover {
        transform: translateY(-1px);
        filter: saturate(1.06);
        box-shadow: 0 18px 34px rgba(182, 122, 49, 0.26);
    }

    [data-testid="stSidebar"] .streamlit-expanderHeader {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        color: #eef3f8;
    }

    [data-testid="stSidebar"] .streamlit-expanderContent {
        background: rgba(255, 255, 255, 0.025);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-top: none;
        border-radius: 0 0 14px 14px;
    }

    .main-title {
        font-family: 'Cormorant Garamond', serif;
        font-size: clamp(2.6rem, 4vw, 4.2rem);
        font-weight: 600;
        color: var(--paper);
        letter-spacing: -0.03em;
        line-height: 0.94;
        margin-bottom: 0.65rem;
    }

    .subtitle {
        font-size: 1rem;
        color: #c4d0de;
        line-height: 1.75;
        max-width: 52rem;
        margin-bottom: 0;
    }

    .hero-panel,
    .ops-panel,
    .section-card,
    .table-card {
        backdrop-filter: blur(14px);
        border: 1px solid var(--line);
        box-shadow: 0 24px 48px rgba(5, 9, 18, 0.28);
    }

    .hero-panel {
        background:
            linear-gradient(145deg, rgba(16, 26, 43, 0.92) 0%, rgba(10, 17, 30, 0.92) 100%);
        border-radius: 30px;
        padding: 2rem 2.1rem;
        position: relative;
        overflow: hidden;
        min-height: 14rem;
    }

    .hero-panel::after {
        content: "";
        position: absolute;
        right: -4rem;
        top: -5rem;
        width: 16rem;
        height: 16rem;
        background: radial-gradient(circle, rgba(127, 183, 175, 0.18) 0%, transparent 70%);
        pointer-events: none;
    }

    .hero-meta {
        display: flex;
        flex-wrap: wrap;
        gap: 0.65rem;
        margin-top: 1.25rem;
    }

    .meta-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.48rem 0.82rem;
        border-radius: 999px;
        background: rgba(244, 239, 229, 0.07);
        border: 1px solid rgba(244, 239, 229, 0.08);
        color: #edf2f7;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.01em;
    }

    .ops-panel {
        background: linear-gradient(180deg, rgba(21, 34, 56, 0.9) 0%, rgba(12, 20, 35, 0.94) 100%);
        border-radius: 26px;
        padding: 1.4rem 1.4rem 1.25rem;
        height: 100%;
    }

    .ops-title {
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: #9fb0c3;
        margin-bottom: 0.9rem;
        font-weight: 700;
    }

    .ops-row {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        align-items: baseline;
        padding: 0.72rem 0;
        border-bottom: 1px solid rgba(255,255,255,0.08);
    }

    .ops-row:last-child {
        border-bottom: none;
        padding-bottom: 0;
    }

    .ops-label {
        font-size: 0.8rem;
        color: #91a3b6;
        text-transform: uppercase;
        letter-spacing: 0.09em;
    }

    .ops-value {
        font-size: 0.98rem;
        color: #f7f3ea;
        font-weight: 700;
        text-align: right;
    }

    .metric-card {
        background:
            linear-gradient(180deg, rgba(255, 250, 241, 0.98) 0%, rgba(245, 239, 229, 0.98) 100%);
        border: 1px solid rgba(255, 255, 255, 0.18);
        border-radius: 22px;
        padding: 1.35rem;
        box-shadow: 0 18px 30px rgba(7, 11, 20, 0.18);
        min-height: 9.2rem;
    }

    .metric-label {
        font-size: 0.72rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: #7c8ca2;
        margin-bottom: 0.55rem;
    }

    .metric-value {
        font-size: 2rem;
        font-weight: 800;
        color: var(--paper-text);
        line-height: 1;
    }

    .metric-unit {
        font-size: 0.86rem;
        font-weight: 700;
        color: #68778c;
    }

    .section-card {
        background:
            linear-gradient(180deg, rgba(255, 250, 241, 0.98) 0%, rgba(248, 243, 234, 0.98) 100%);
        border-radius: 28px;
        padding: 1.45rem;
        color: var(--paper-text);
    }

    .section-heading {
        font-size: 0.84rem;
        text-transform: uppercase;
        letter-spacing: 0.13em;
        color: #7a8ca3;
        font-weight: 800;
        margin-bottom: 0.95rem;
    }

    .section-title {
        font-family: 'Cormorant Garamond', serif;
        font-size: 2rem;
        font-weight: 600;
        color: #162133;
        margin-bottom: 0.4rem;
    }

    .section-caption {
        color: #5f6f84;
        line-height: 1.6;
        margin-bottom: 1rem;
    }

    .insight-card {
        background: rgba(19, 32, 51, 0.045);
        border: 1px solid rgba(19, 32, 51, 0.08);
        border-left: 3px solid var(--teal-deep);
        border-radius: 0 16px 16px 0;
        padding: 0.95rem 1rem;
        margin-bottom: 0.72rem;
    }

    .insight-time {
        font-size: 0.75rem;
        font-weight: 800;
        color: var(--teal-deep);
        margin-bottom: 0.28rem;
        letter-spacing: 0.04em;
    }

    .insight-text {
        font-size: 0.9rem;
        color: #243345;
        line-height: 1.6;
    }

    .alert-card {
        background: rgba(229, 122, 88, 0.09);
        border-left: 3px solid var(--signal);
        border-radius: 0 16px 16px 0;
        padding: 0.82rem 1rem;
        margin-bottom: 0.72rem;
    }

    .alert-time {
        font-size: 0.74rem;
        font-weight: 800;
        color: #bb5232;
        margin-bottom: 0.25rem;
        letter-spacing: 0.04em;
    }

    .alert-text {
        font-size: 0.88rem;
        color: #723321;
        line-height: 1.5;
    }

    .driver-pill {
        display: inline-block;
        background: rgba(127, 183, 175, 0.16);
        color: #214c4f;
        font-size: 0.75rem;
        font-weight: 800;
        padding: 0.42rem 0.8rem;
        border-radius: 999px;
        margin-right: 0.45rem;
        margin-bottom: 0.5rem;
        border: 1px solid rgba(46, 108, 110, 0.14);
    }

    .status-ribbon {
        background: linear-gradient(90deg, rgba(127, 183, 175, 0.16) 0%, rgba(214, 161, 77, 0.14) 100%);
        border: 1px solid rgba(214, 161, 77, 0.18);
        border-radius: 18px;
        padding: 0.9rem 1rem;
        margin-bottom: 1.1rem;
        color: #ebf1f8;
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        flex-wrap: wrap;
    }

    .status-ribbon strong {
        color: var(--amber-soft);
    }

    .table-card {
        background:
            linear-gradient(180deg, rgba(255, 250, 241, 0.98) 0%, rgba(244, 239, 229, 0.98) 100%);
        border-radius: 28px;
        padding: 1.2rem;
        color: var(--paper-text);
    }

    .table-card [data-testid="stDataFrame"] {
        border-radius: 18px;
        overflow: hidden;
        border: 1px solid rgba(19, 32, 51, 0.08);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.75);
    }

    .empty-state {
        background:
            linear-gradient(155deg, rgba(16, 26, 43, 0.9) 0%, rgba(12, 20, 35, 0.88) 100%);
        border-radius: 30px;
        border: 1px solid var(--line);
        padding: 2rem;
        color: #eef3f8;
        box-shadow: 0 24px 48px rgba(5, 9, 18, 0.24);
    }

    .empty-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 1rem;
        margin-top: 1.2rem;
    }

    .empty-card {
        border-radius: 22px;
        padding: 1.2rem;
        background: rgba(244, 239, 229, 0.06);
        border: 1px solid rgba(244, 239, 229, 0.08);
    }

    .empty-card-title {
        color: var(--paper);
        font-weight: 800;
        margin-bottom: 0.42rem;
        font-size: 1rem;
    }

    .empty-card-copy {
        color: #c7d3df;
        line-height: 1.65;
        font-size: 0.92rem;
    }

    .footer-text {
        font-size: 0.75rem;
        color: #8e9db3;
        text-align: center;
        margin-top: 2rem;
        padding-top: 1rem;
        border-top: 1px solid rgba(255, 255, 255, 0.08);
    }

    [data-testid="stAlert"] {
        border-radius: 18px;
        border: 1px solid rgba(255,255,255,0.08);
    }

    .stDownloadButton > button {
        border-radius: 14px;
        background: #132033;
        color: #f6f1e8;
        border: 1px solid rgba(255,255,255,0.08);
        font-weight: 700;
    }

    @media (max-width: 900px) {
        .hero-panel,
        .ops-panel,
        .section-card,
        .table-card,
        .empty-state {
            border-radius: 22px;
            padding: 1.35rem;
        }

        .main-title {
            font-size: 2.3rem;
        }

        .status-ribbon {
            flex-direction: column;
            align-items: flex-start;
        }
    }

    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

API_URL = os.getenv("API_URL", "http://localhost:8000")
ALLOW_LOCAL_FALLBACK = os.getenv("GRIDSENSE_LOCAL_FALLBACK", "1") != "0"

PLANTS = {
    "SOL_PAVAGADA_100": {"name": "Pavagada Solar Park", "capacity": 100, "type": "Solar", "emoji": "☀️", "lat": 14.25, "lon": 77.28},
    "SOL_KOPPAL_50":    {"name": "Koppal Solar Farm",    "capacity": 50,  "type": "Solar", "emoji": "☀️", "lat": 15.35, "lon": 76.15},
    "SOL_RAICHUR_200":  {"name": "Raichur Mega Solar",   "capacity": 200, "type": "Solar", "emoji": "☀️", "lat": 16.21, "lon": 77.35},
    "WIND_CHITRADURGA_80": {"name": "Chitradurga Wind",  "capacity": 80,  "type": "Wind",  "emoji": "💨", "lat": 14.23, "lon": 76.40},
    "WIND_HASSAN_150":  {"name": "Hassan Wind Farm",     "capacity": 150, "type": "Wind",  "emoji": "💨", "lat": 13.00, "lon": 76.10},
}

st.session_state.setdefault("forecast_data", None)
st.session_state.setdefault("forecast_request", None)
st.session_state.setdefault("forecast_error", None)
st.session_state.setdefault("forecast_source", None)
st.session_state.setdefault("daily_report_path", None)
st.session_state.setdefault("daily_report_error", None)


@st.cache_resource(show_spinner=False)
def get_local_pipeline_resource():
    return get_pipeline()


@st.cache_data(show_spinner=False)
def get_local_inputs_cache():
    return load_inputs()


def run_forecast_request(request_payload):
    errors = []

    try:
        resp = requests.post(
            f"{API_URL}/forecast",
            json=request_payload,
            timeout=90,
        )
        resp.raise_for_status()
        return resp.json(), None, "api"
    except requests.exceptions.ConnectionError:
        errors.append("API connection unavailable")
    except requests.exceptions.Timeout:
        errors.append("API request timed out")
    except Exception as exc:
        errors.append(str(exc))

    if not ALLOW_LOCAL_FALLBACK:
        return None, "❌ Unable to reach the forecast API and local fallback is disabled.", None

    try:
        pipeline = get_local_pipeline_resource()
        scada, weather = get_local_inputs_cache()
        language = validate_language(request_payload.get("language", "en"))
        frame = build_forecast_frame(
            pipeline,
            scada,
            weather,
            request_payload["plant_id"],
            request_payload["context_hours"],
            request_payload["prediction_hours"],
            forecast_timestamp=request_payload.get("forecast_timestamp"),
            language=language,
        )
        return frame.to_dict(orient="records"), None, "local"
    except Exception as exc:
        errors.append(f"Local fallback failed: {exc}")
        return None, f"❌ Forecast request failed. {'; '.join(errors)}", None

# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<div style='font-family:\"Cormorant Garamond\",serif;font-size:2rem;font-weight:600;color:#f4efe5;letter-spacing:-0.03em;margin-bottom:0.15rem;'>GridSense AI</div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:0.9rem;color:#aab9ca;line-height:1.7;margin-bottom:1.5rem;'>Renewable forecasting console for Karnataka grid operations, with explainable hourly dispatch guidance.</div>", unsafe_allow_html=True)
    
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

    language_label = st.selectbox(
        "Explanation Language",
        ["English", "Kannada"],
        index=0,
        help="Offline template explanations are available in English and Kannada.",
    )
    language = "kn" if language_label == "Kannada" else "en"
    
    st.divider()
    
    submitted = st.button("Generate Forecast", type="primary")
    
    st.divider()
    
    with st.expander("🔄 Intra-day Updates"):
        st.caption("Operators can re-run forecasts at any time with the latest weather data. Simply select a new horizon and click **Generate Forecast** again.")
    
    with st.expander("ℹ️ How it works"):
        st.caption("1. **Baseline** — Chronos-Bolt model reads 7 days of history")
        st.caption("2. **Residual** — Real-time weather adjusts for clouds/wind changes")
        st.caption("3. **Physics** — Turbine curves & GHI caps ensure valid output")
        st.caption("4. **Explain** — Offline templates generate operator-readable reasons")
    
    with st.expander("📊 Daily Reports"):
        st.caption("Generate Excel-ready CSV reports for all plants")
        if st.button("📝 Generate Daily Report", use_container_width=True):
            with st.spinner("Running forecasts for all plants..."):
                try:
                    import subprocess
                    result = subprocess.run(
                        [sys.executable, "src/scheduler.py", "--mode", "custom", "--hours", "24"],
                        capture_output=True,
                        text=True,
                        env=os.environ.copy(),
                        cwd=os.path.dirname(os.path.dirname(__file__)),
                        timeout=120
                    )
                    if result.returncode == 0:
                        # Find the latest report
                        import glob
                        reports = glob.glob("reports/custom_*.csv")
                        if reports:
                            st.session_state.daily_report_path = max(reports, key=os.path.getctime)
                            st.session_state.daily_report_error = None
                    else:
                        st.session_state.daily_report_error = result.stderr[-400:] if result.stderr else result.stdout[-400:]
                except Exception as e:
                    st.session_state.daily_report_error = str(e)

        if st.session_state.daily_report_path:
            st.success("✅ Daily report generated!")
            with open(st.session_state.daily_report_path, "rb") as f:
                st.download_button(
                    label="⬇️ Download Daily Report",
                    data=f,
                    file_name=os.path.basename(st.session_state.daily_report_path),
                    mime="text/csv",
                    use_container_width=True
                )
        elif st.session_state.daily_report_error:
            st.error("Failed to generate report. Check server logs.")
            st.caption(st.session_state.daily_report_error)

    with st.expander("🔒 Privacy"):
        st.caption("No SCADA data leaves this system. Explanations are generated locally with deterministic templates.")
    
    st.markdown("<div class='footer-text'>Built for KREDL / KSPDCL Theme 10</div>", unsafe_allow_html=True)

# ── Main Content ──────────────────────────────────────────────
current_request = {
    "plant_id": plant_id,
    "context_hours": 168,
    "prediction_hours": horizon,
    "language": language,
}

if submitted:
    st.session_state.forecast_request = current_request.copy()
    with st.spinner("Running 4-pass forecast pipeline..."):
        data, error, source = run_forecast_request(st.session_state.forecast_request)
        st.session_state.forecast_data = data
        st.session_state.forecast_error = error
        st.session_state.forecast_source = source
        if not st.session_state.forecast_data and not st.session_state.forecast_error:
            st.session_state.forecast_error = "No forecast data returned."

active_request = st.session_state.forecast_request or current_request
active_plant = PLANTS[active_request["plant_id"]]
active_language_label = "Kannada" if active_request["language"] == "kn" else "English"
runtime_stamp = datetime.now().strftime("%d %b %Y · %H:%M IST")

hero_col, ops_col = st.columns([2.3, 1])
with hero_col:
    st.markdown(f"""
    <div class='hero-panel'>
        <div class='main-title'>Renewable Generation Forecast</div>
        <div class='subtitle'>
            A forecasting layer for real dispatch decisions, tuned for plant-level and cluster-level renewable operations across Karnataka.
            The current focus is <b>{active_plant['name']}</b>, a <b>{active_plant['capacity']} MW {active_plant['type'].lower()}</b> asset at
            <b>{active_plant['lat']}°N, {active_plant['lon']}°E</b>.
        </div>
        <div class='hero-meta'>
            <span class='meta-pill'>{active_plant['emoji']} {active_plant['name']}</span>
            <span class='meta-pill'>Forecast horizon: {active_request['prediction_hours']}h</span>
            <span class='meta-pill'>Explanation language: {active_language_label}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with ops_col:
    st.markdown(f"""
    <div class='ops-panel'>
        <div class='ops-title'>Operator Snapshot</div>
        <div class='ops-row'>
            <div class='ops-label'>Asset Type</div>
            <div class='ops-value'>{active_plant['type']}</div>
        </div>
        <div class='ops-row'>
            <div class='ops-label'>Rated Capacity</div>
            <div class='ops-value'>{active_plant['capacity']} MW</div>
        </div>
        <div class='ops-row'>
            <div class='ops-label'>Current Run</div>
            <div class='ops-value'>{runtime_stamp}</div>
        </div>
        <div class='ops-row'>
            <div class='ops-label'>Mode</div>
            <div class='ops-value'>Day-ahead + intra-day</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

if st.session_state.forecast_error:
    st.error(st.session_state.forecast_error)

if st.session_state.forecast_data:
    if current_request != active_request:
        st.info("Selections changed in the sidebar. Click **Generate Forecast** to refresh the chart with the new plant, horizon, or language.")

    df = pd.DataFrame(st.session_state.forecast_data)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["hour"] = df["timestamp"].dt.strftime("%H:%M")
    df["date"] = df["timestamp"].dt.strftime("%d %b")
    
    # ── Metrics Row ─────────────────────────────────────────
    mcol1, mcol2, mcol3, mcol4 = st.columns(4)
    peak_mw = df["forecast_MW"].max()
    min_mw = df["forecast_MW"].min()
    avg_unc = (df["confidence_upper"] - df["confidence_lower"]).mean() / 2
    n_clamps = int(df["was_clamped"].sum())
    cap = active_plant["capacity"]
    
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
    
    st.markdown("<div style='margin-bottom:1.35rem;'></div>", unsafe_allow_html=True)

    # ── Intra-day update banner ─────────────────────────────
    updated_at = datetime.now().strftime("%d %b %Y, %H:%M IST")
    st.markdown(f"""
    <div class='status-ribbon'>
        <div><strong>Intra-day Forecast Pipeline</strong> — Baseline: Chronos-Bolt · Adjustment: Weather Residual · Validation: Physics Clamping</div>
        <div style='font-size:0.8rem;font-weight:700;color:#dce6ef;'>Last Refresh: {updated_at}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # ── Main Chart + Insights ───────────────────────────────
    chart_col, insight_col = st.columns([3, 1])
    
    with chart_col:
        st.markdown("""
        <div class='section-card' style='margin-bottom:1rem;'>
            <div class='section-heading'>Forecast Curve</div>
            <div class='section-title'>Dispatch-facing outlook</div>
            <div class='section-caption'>Confidence is shown as a band around the final corrected forecast, after weather adjustment and physics validation.</div>
        </div>
        """, unsafe_allow_html=True)
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
            fillcolor='rgba(127, 183, 175, 0.18)',
            name="Confidence Band",
            hovertemplate='Lower: %{y:.1f} MW<extra></extra>',
        ))
        
        # Forecast line
        fig.add_trace(go.Scatter(
            x=df["timestamp"], y=df["forecast_MW"],
            mode='lines+markers', line=dict(color='#c98d35', width=3),
            marker=dict(size=5, color='#c98d35', line=dict(width=1, color='#fff8ef')),
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
                text=f"<b>{active_plant['name']}</b> — Next {active_request['prediction_hours']}h Generation Forecast",
                font=dict(size=16, color="#162133", family="Manrope"),
                x=0, xanchor="left",
            ),
            xaxis_title="Time (IST)",
            yaxis_title="Generation (MW)",
            template="plotly_white",
            height=480,
            margin=dict(l=60, r=40, t=80, b=40),
            hovermode="x unified",
            paper_bgcolor='rgba(255,250,241,0.98)',
            plot_bgcolor='rgba(252,247,238,0.95)',
            font=dict(color="#223244", family="Manrope"),
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02,
                xanchor="right", x=1, font=dict(size=11),
            ),
            xaxis=dict(showgrid=True, gridcolor="#e8dfd2", tickformat="%H:%M\n%d %b"),
            yaxis=dict(showgrid=True, gridcolor="#e8dfd2", rangemode="tozero"),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    
    with insight_col:
        st.markdown("""
        <div class='section-card' style='padding-bottom:1rem;'>
            <div class='section-heading'>Operational Intelligence</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Combine interesting explanations and physics alerts into one chronological feed
        feed = []
        # Add non-trivial explanations
        for _, row in df[df["explanation"].str.len() > 40].head(5).iterrows():
            feed.append({
                "time": row["hour"],
                "date": row["date"],
                "text": row["explanation"],
                "type": "insight"
            })
        
        # Add unique physics alerts
        seen_alerts = set()
        for _, row in df[df["was_clamped"]].iterrows():
            if row["clamp_reason"] not in seen_alerts:
                feed.append({
                    "time": row["hour"],
                    "date": row["date"],
                    "text": row["clamp_reason"],
                    "type": "alert"
                })
                seen_alerts.add(row["clamp_reason"])

        if not feed:
            st.info("System operating within nominal baseline parameters.")
        else:
            # Show top 5 sorted by importance (alerts first)
            feed.sort(key=lambda x: x["type"] == "insight")
            for item in feed[:6]:
                if item["type"] == "alert":
                    st.markdown(f"""
                    <div class='alert-card'>
                        <div class='alert-time'>⚠️ Physics Alarm · {item['time']}</div>
                        <div class='alert-text'>{item['text']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class='insight-card'>
                        <div class='insight-time'>ℹ️ Insight · {item['time']}</div>
                        <div class='insight-text'>{item['text']}</div>
                    </div>
                    """, unsafe_allow_html=True)
    
    st.divider()
    
    # ── Data Table ──────────────────────────────────────────
    st.markdown("""
    <div class='table-card' style='margin-bottom:0.9rem;'>
        <div class='section-heading'>Hourly Detail</div>
        <div class='section-title'>Export-ready forecast table</div>
        <div class='section-caption'>Every row carries the final forecast, confidence range, and the operator-facing explanation used in the UI.</div>
    </div>
    """, unsafe_allow_html=True)
    
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
            file_name=f"forecast_{active_request['plant_id']}_{active_request['prediction_hours']}h_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with api_col:
        with st.expander("📡 API Integration Code"):
            st.code(f'''import requests

response = requests.post(
    "{API_URL}/forecast",
    json={{
        "plant_id": "{active_request['plant_id']}",
        "context_hours": 168,
        "prediction_hours": {active_request['prediction_hours']},
        "language": "{active_request['language']}"
    }}
)
data = response.json()
print(f"Forecast: {{data[0]['forecast_MW']}} MW")
print(f"Explanation: {{data[0]['explanation']}}")
''', language="python")

else:
    # ── Welcome State ───────────────────────────────────────
    st.markdown("""
    <div class='empty-state'>
        <div class='section-heading' style='color:#9fb0c3;'>Ready for a live run</div>
        <div class='main-title' style='font-size:3rem;margin-bottom:0.5rem;'>Select a plant and generate a forecast.</div>
        <div class='subtitle' style='max-width:58rem;'>This console is designed to show plant-level generation outlooks, confidence bands, short operational explanations, and exportable hourly tables without changing any upstream systems.</div>
        <div class='empty-grid'>
            <div class='empty-card'>
                <div class='empty-card-title'>Baseline model</div>
                <div class='empty-card-copy'>Chronos-Bolt reads seven days of history to establish the primary generation curve.</div>
            </div>
            <div class='empty-card'>
                <div class='empty-card-title'>Weather adjustment</div>
                <div class='empty-card-copy'>Cloud and wind conditions reshape the baseline for day-ahead and intra-day planning updates.</div>
            </div>
            <div class='empty-card'>
                <div class='empty-card-title'>Physics validation</div>
                <div class='empty-card-copy'>Clear-sky and turbine-curve limits keep the final forecast within operationally plausible bounds.</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
