import streamlit as st
import pandas as pd, math
import os
import warnings, re
import gspread

warnings.filterwarnings("ignore")

st.set_page_config(page_title="MLB DW Web App", layout="wide", page_icon="⚾")

import numpy as np
import matplotlib.pyplot as plt
import streamlit.components.v1 as components
import plotly.express as px
import plotly.graph_objects as go
import altair as alt
from google.oauth2.service_account import Credentials
from datetime import datetime, timezone, timedelta

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# Store what access they have (None / "basic" / "full" / etc.)
if "access_level" not in st.session_state:
    st.session_state.access_level = None

# Optional: store which password key they used (not the raw password)
if "auth_key" not in st.session_state:
    st.session_state.auth_key = None


# ----------------------------
# Password -> access mapping
# (use env vars / st.secrets in production; see note below)
# ----------------------------
PASSWORDS = {
    "tony":   {"access_level": "full", "auth_key": "FULL"},
    "34":      {"access_level": "full", "auth_key": "FULL"},
    "tike": {"access_level": "pro",  "auth_key": "PRO"},
    "FLUB": {"access_level": "FLUB",  "auth_key": "FLUB"},
}

def check_password():
    def password_entered():
        pw = st.session_state.get("password", "")
        info = PASSWORDS.get(pw)

        if info:
            st.session_state.authenticated = True
            st.session_state.access_level = info["access_level"]
            st.session_state.auth_key = info["auth_key"]
            # clear the entered password from session state
            st.session_state.pop("password", None)
        else:
            st.session_state.authenticated = False
            st.session_state.access_level = None
            st.session_state.auth_key = None
            st.error("Incorrect password. Please try again.")

    if not st.session_state.authenticated:
        st.text_input(
            "Enter Password (!!!!!! NEW PASSWORDS SET 3/30/2026 !!!!!!!!!!!)",
            type="password",
            key="password",
            on_change=password_entered,
        )
        return False

    return True


def export_button(data: pd.DataFrame, filename: str, label: str = "⬇️ Export to CSV"):
    st.download_button(
        label=label,
        data=data.to_csv(index=False).encode("utf-8"),
        file_name=filename,
        mime="text/csv",
        use_container_width=True,
    )
# ----------------------------
# Main app content
# ----------------------------
if check_password():

    # Access variables you can use anywhere later:
    access_level = st.session_state.access_level   # "basic" or "full"
    auth_key     = st.session_state.auth_key       # e.g., "FULL"

    #st.write(f"Logged in with access: {access_level}")

    # Set page configuration

    ### count down banner 

    def render_opening_day_banner():
        from datetime import datetime
        import streamlit as st

        target = datetime(2026, 3, 26)
        now = datetime.now()
        delta = target - now
        total_seconds = int(delta.total_seconds())

        if total_seconds <= 0:
            headline = "⚾ MLB Opening Day is HERE"
            sub = "Play ball."
        else:
            days = total_seconds // 86400
            headline = f"{days} Days Until Opening Day!"
            sub = f"{days} days"

        html = f"""


        <div style="
            width:100%;
            padding:14px 20px;
            margin-bottom:18px;
            border-radius:14px;
            background:#2563eb;
            color:#ffffff;
            text-align:center;
            font-size:16px;
            font-weight:700;
            box-shadow:0 8px 20px rgba(0,0,0,0.18);
        ">
            JOIN MLB DW PRO TO UNLOCK THIS FULL APP.
            <a href="https://www.mlbdatawarehouse.com/p/re-introducing-mlb-dw-pro"
            target="_blank"
            style="
                color:#ffffff;
                text-decoration:underline;
                font-weight:900;
                margin-left:6px;
            ">
                CLICK HERE
            </a>
            FOR INFORMATION AND TO SIGN UP!
        </div>
        """

        st.markdown(html, unsafe_allow_html=True)

    # Call this once per page render (put it right after set_page_config / before your page content)
    if access_level == "pro":
        pass
    else:   
        render_opening_day_banner()

    #######

    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Roboto+Mono:wght@400;500&display=swap');

        /* ── Global ── */
        html, body, [class*="css"] {
            font-family: 'Inter', system-ui, sans-serif;
        }
        .stApp {
            background-color: #ffffff;
        }

        /* ── Sidebar — clean white, thin border ── */
        [data-testid="stSidebar"] {
            background: #ffffff !important;
            border-right: 1px solid #e5e5e5;
        }
        [data-testid="stSidebar"] .stRadio label,
        [data-testid="stSidebar"] .stRadio div,
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span {
            color: #222222 !important;
        }
        [data-testid="stSidebar"] .stRadio [data-testid="stMarkdownContainer"] p {
            font-weight: 500;
            font-size: 0.85rem;
        }
        [data-testid="stSidebar"] button {
            background: #4169e1 !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 6px !important;
            font-weight: 600;
            font-size: 0.84rem;
        }
        [data-testid="stSidebar"] button:hover {
            background: #2f54c8 !important;
        }

        /* ── Headings ── */
        h1, h2, h3, h4 {
            color: #111111;
            font-weight: 700;
        }
        h1 { font-size: 1.85rem; }
        h3 { color: #333333; font-weight: 600; }

        /* ── Main title ── */
        .main-title {
            font-size: 2rem;
            font-weight: 700;
            color: #111111;
            text-align: center;
            padding: 0.5rem 0 0.2rem;
        }
        .main-subtitle {
            text-align: center;
            color: #888888;
            font-size: 0.85rem;
            margin-bottom: 1rem;
        }

        /* ── DataFrames ── */
        .stDataFrame {
            border: 1px solid #e5e5e5;
            border-radius: 8px;
            overflow: hidden;
        }
        .dataframe {
            width: 100%;
            font-size: 13px;
            font-family: 'Inter', sans-serif;
        }
        .dataframe th {
            background-color: #f5f5f5 !important;
            color: #111111 !important;
            font-weight: 600;
            font-size: 11.5px;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            padding: 10px 12px;
            border-bottom: 1px solid #e5e5e5;
        }
        .dataframe td {
            padding: 8px 12px;
            border-bottom: 1px solid #f0f0f0;
            color: #222222;
        }
        .dataframe tr:nth-child(even) td {
            background-color: #fafafa;
        }
        .dataframe tr:hover td {
            background-color: #f0faf5 !important;
        }

        /* ── Metrics ── */
        [data-testid="stMetric"] {
            background: #fafafa;
            border: 1px solid #e5e5e5;
            border-radius: 8px;
            padding: 0.7rem 1rem;
        }
        [data-testid="stMetricLabel"] {
            font-size: 0.7rem;
            font-weight: 600;
            color: #888888;
            text-transform: uppercase;
            letter-spacing: 0.07em;
        }
        [data-testid="stMetricValue"] {
            font-size: 1.4rem;
            font-weight: 700;
            color: #111111;
        }

        /* ── Buttons ── */
        .stButton > button {
            background: #4169e1;
            color: white;
            border: none;
            border-radius: 6px;
            font-weight: 600;
            font-size: 0.84rem;
            padding: 0.45rem 1.2rem;
            transition: background 0.15s;
        }
        .stButton > button:hover {
            background: #2f54c8;
        }

        /* ── Selectboxes / Inputs ── */
        .stSelectbox > div > div,
        .stTextInput > div > div > input {
            border: 1px solid #dddddd;
            border-radius: 6px;
            font-size: 0.9rem;
            background: white;
        }
        .stSelectbox > div > div:focus-within,
        .stTextInput > div > div > input:focus {
            border-color: #4169e1 !important;
            box-shadow: 0 0 0 2px rgba(26,122,74,0.1);
        }

        /* ── Tabs ── */
        .stTabs [data-baseweb="tab-list"] {
            background: #f5f5f5;
            border-radius: 8px;
            padding: 3px;
            gap: 2px;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 6px;
            font-weight: 500;
            font-size: 0.84rem;
            color: #666666;
        }
        .stTabs [aria-selected="true"] {
            background: white !important;
            color: #111111 !important;
            font-weight: 600;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        }

        /* ── Dividers ── */
        hr { border-color: #e5e5e5; }

        /* ── Player card ── */
        .player-card {
            background: white;
            border-radius: 8px;
            padding: 16px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.06);
            border: 1px solid #e5e5e5;
            text-align: center;
            margin-bottom: 16px;
        }

        /* ── Transaction table ── */
        .txn-table {
            width: 100%;
            border-collapse: collapse;
            font-family: 'Inter', sans-serif;
            font-size: 13px;
        }
        .txn-table th {
            background: #f5f5f5;
            color: #111111;
            font-weight: 600;
            font-size: 11px;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            padding: 10px 14px;
            text-align: left;
            border-bottom: 1px solid #e5e5e5;
            position: sticky;
            top: 0;
        }
        .txn-table td {
            padding: 9px 14px;
            border-bottom: 1px solid #f0f0f0;
            vertical-align: top;
            color: #222222;
            line-height: 1.45;
        }
        .txn-table tr:nth-child(even) td { background: #fafafa; }
        .txn-table tr:hover td { background: #f0faf5; }
        .txn-table td.desc { white-space: normal; word-break: break-word; max-width: 480px; }
        .txn-table td.date { font-family: 'Roboto Mono', monospace; font-size: 12px; white-space: nowrap; color: #555555; }
        .txn-badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.03em;
        }
        .badge-trade    { background: #e8f4fd; color: #1a6fa8; }
        .badge-il       { background: #fdecea; color: #b71c1c; }
        .badge-assigned { background: #e6f5ee; color: #4169e1; }
        .badge-dfa      { background: #fff8e6; color: #996600; }
        .badge-other    { background: #f5f5f5; color: #555555; }

        /* ── Responsive ── */
        @media (max-width: 768px) {
            h1 { font-size: 1.4rem; }
            h2 { font-size: 1.2rem; }
            .player-card { padding: 10px; }
        }
        </style>
    """, unsafe_allow_html=True)


    # =========================================================================
    # GRANULAR DATA LOADERS — one per logical group, called only by the pages
    # that actually need them.
    #
    # TTL STRATEGY:
    #   LIVE_TTL  (300 s / 5 min)  – daily projections, props, ownership,
    #                                 weather, bullpen, bet values.  These
    #                                 update constantly during the season, so
    #                                 we never want a stale 1-hour cache.
    #   SLOW_TTL  (3600 s / 1 hr)  – season-long stats, fScores, profiles,
    #                                 ADP, schedules, rankings.  Stable enough
    #                                 for a one-hour window.
    #   PARQUET_TTL (1800 s / 30 min) – large hit/pitch event DBs; expensive
    #                                 to load but don't change intra-day.
    #
    # Each loader is a @st.cache_data function so results are shared across
    # ALL concurrent users — one file-read serves dozens of sessions.
    # =========================================================================

    _DATA_DIR = os.path.join(os.path.dirname(__file__), 'Data')
    LIVE_TTL    = 300     # 5 minutes — projection / live files
    SLOW_TTL    = 3600    # 1 hour    — reference / historical files
    PARQUET_TTL = 1800    # 30 minutes — large parquet databases

    # ------------------------------------------------------------------
    # ALWAYS-NEEDED: logo path (no I/O, just a string — no caching needed)
    # ------------------------------------------------------------------
    logo = os.path.join(_DATA_DIR, 'Logo.png')

    def work_in_progress():
        st.markdown("""
        <div style="
            background-color:#fff4e6;
            padding:20px;
            border-radius:10px;
            border:1px solid #ffa94d;
            text-align:center;
            margin-top:20px;
        ">
            <h2 style="color:#cc7000; margin-bottom:10px;">
                🚧 Work In Progress
            </h2>
            <p style="font-size:18px; color:#cc7000; margin-bottom:10px;">
                This page is currently being built.
            </p>
            <p style="font-size:16px; color:#cc7000;">
                We're actively working on this feature and it will be available soon.
            </p>
            <p style="font-size:14px; color:#995200; margin-top:10px;">
                Check back soon — it's going to be worth it.
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.stop()
    
    def is_pro_user():
        return st.session_state.get("access_level") in ["pro"]

    def require_pro():
        if st.session_state.get("access_level") not in ["pro"]:
            st.markdown("""
            <div style="
                background-color:#e6f0ff;
                padding:20px;
                border-radius:10px;
                border:1px solid #4da6ff;
                text-align:center;
                margin-top:20px;
            ">
                <h2 style="color:#003366; margin-bottom:10px;">
                    🔒 PRO Members Only
                </h2>
                <p style="font-size:18px; color:#003366; margin-bottom:15px;">
                    This page is for PRO members only.
                </p>
                <p style="font-size:16px; color:#003366;">
                    Become a PRO member by subscribing or upgrading at
                    <a href="https://www.mlbdatawarehouse.com/subscribe" target="_blank">
                        www.mlbdatawarehouse.com/subscribe
                    </a>.
                </p>
                <p style="font-size:16px; color:#003366; margin-top:10px;">
                    Once you've subscribed, you can
                    <a href="https://www.mlbdatawarehouse.com/p/mlb-dw-pro-resource-glossary" target="_blank">
                        find the app password here
                    </a>.
                </p>
            </div>
            """, unsafe_allow_html=True)

            st.stop()

    # ------------------------------------------------------------------
    # GROUP 1 — Daily Projections  (LIVE — used by "2026 Projections" and
    #           related pages: Game Previews, Pitcher Projections, etc.)
    # ------------------------------------------------------------------
    @st.cache_data(ttl=LIVE_TTL, show_spinner=False)
    def load_daily_projections():
        fp = _DATA_DIR
        hitterproj  = pd.read_csv(f'{fp}/hitter_proj_withids.csv')
        pitcherproj = pd.read_csv(f'{fp}/Tableau_DailyPitcherProj.csv')
        hitterproj2 = pd.read_csv(f'{fp}/Tableau_DailyHitterProj.csv')
        gameinfo    = pd.read_csv(f'{fp}/gameinfo.csv')
        return hitterproj, pitcherproj, hitterproj2, gameinfo
    

    def load_flub_data():
        fp = _DATA_DIR
        flub_data  = pd.read_csv(f'{fp}/FLB_App_Data.csv')
        return(flub_data)

    # ------------------------------------------------------------------
    # GROUP 2 — Player Stats / Matchup files  (LIVE — hot/cold streaks,
    #           vs-average comps update daily)
    # ------------------------------------------------------------------
    @st.cache_data(ttl=LIVE_TTL, show_spinner=False)
    def load_player_stats():
        fp = _DATA_DIR
        hitter_stats = pd.read_csv(f'{fp}/hitterData.csv')
        hitter_stats = hitter_stats.drop_duplicates(subset=['ID'])
        lineup_stats = pd.read_csv(f'{fp}/lineupData.csv')
        pitcher_stats= pd.read_csv(f'{fp}/pitcherStats.csv')
        h_vs_avg     = pd.read_csv(f'{fp}/vsAvg_Hit.csv')
        p_vs_avg     = pd.read_csv(f'{fp}/vsAvg_Pitch.csv')
        h_vs_sim     = pd.read_csv(f'{fp}/hitters_vs_sim_data.csv')
        hotzonedata  = pd.read_csv(f'{fp}/hotzonedata.csv')
        posdata      = pd.read_csv(f'{fp}/mlbposdata.csv')
        return hitter_stats, lineup_stats, pitcher_stats, h_vs_avg, p_vs_avg, h_vs_sim, hotzonedata, posdata

    # ------------------------------------------------------------------
    # GROUP 3 — Bullpen / Reliever data  (LIVE — BP usage changes daily)
    # ------------------------------------------------------------------
    @st.cache_data(ttl=LIVE_TTL, show_spinner=False)
    def load_bullpen_data():
        fp = _DATA_DIR
        bpreport = pd.read_csv(f'{fp}/BullpenReport.csv')
        rpstats  = pd.read_csv(f'{fp}/relieverstats.csv')
        return bpreport, rpstats

    # ------------------------------------------------------------------
    # GROUP 4 — Props / Bets / Ownership  (LIVE — lines move constantly)
    # ------------------------------------------------------------------
    @st.cache_data(ttl=LIVE_TTL, show_spinner=False)
    def load_betting_data():
        fp = _DATA_DIR
        propsdf    = pd.read_csv(f'{fp}/betValues.csv')
        ownershipdf= pd.read_csv(f'{fp}/PlayerOwnershipReport.csv')
        allbets    = pd.read_csv(f'{fp}/AllBetValues.csv')
        alllines   = pd.read_csv(f'{fp}/AllBooksLines.csv')
        bet_tracker= pd.read_csv(f'{fp}/bet_tracker.csv')
        return propsdf, ownershipdf, allbets, alllines, bet_tracker
    
    def load_prop_bet_data():

        fp = _DATA_DIR
        Tableau_DailyHitterProj = pd.read_csv(f'{fp}/Tableau_DailyHitterProj.csv')
        Tableau_DailyPitcherProj = pd.read_csv(f'{fp}/Tableau_DailyPitcherProj.csv')
        bat_hitters = pd.read_csv(f'{fp}/bat_hitters.csv')
        bat_pitchers = pd.read_csv(f'{fp}/bat_pitchers.csv')
        AllBooksLines = pd.read_csv(f'{fp}/AllBooksLines.csv')

        return(Tableau_DailyHitterProj, Tableau_DailyPitcherProj, bat_hitters, bat_pitchers, AllBooksLines)


    # ------------------------------------------------------------------
    # GROUP 5 — Weather & Umpires  (LIVE — changes day-of)
    # ------------------------------------------------------------------
    @st.cache_data(ttl=LIVE_TTL, show_spinner=False)
    def load_weather_umps():
        fp = _DATA_DIR
        umpire_data  = pd.read_csv(f'{fp}/umpData.csv')
        weather_data = pd.read_csv(f'{fp}/weatherReport.csv')
        return umpire_data, weather_data

    # ------------------------------------------------------------------
    # GROUP 6 — Trends  (LIVE — hot/cold updated daily)
    # ------------------------------------------------------------------
    @st.cache_data(ttl=LIVE_TTL, show_spinner=False)
    def load_trends():
        fp = _DATA_DIR
        trend_h = pd.read_csv(f'{fp}/hot_hit_oe_data.csv')
        trend_p = pd.read_csv(f'{fp}/hot_pit_ja_era.csv')
        return trend_h, trend_p

    # ------------------------------------------------------------------
    # GROUP 7 — Air Pull data  (LIVE — updated with new games)
    # ------------------------------------------------------------------
    @st.cache_data(ttl=LIVE_TTL, show_spinner=False)
    def load_airpull():
        fp = _DATA_DIR
        return pd.read_csv(f'{fp}/airpulldata.csv')

    # ------------------------------------------------------------------
    # GROUP 8 — Season Projections (Steamer, TheBat, ATC, JA, OOPSY)
    #           SLOW — these only update a few times a week
    # ------------------------------------------------------------------
    @st.cache_data(ttl=SLOW_TTL, show_spinner=False)
    def load_season_projections():
        fp = _DATA_DIR
        ja_hit    = pd.read_csv(f'{fp}/ja_2026_hitter_proj.csv')
        ja_pitch  = pd.read_csv(f'{fp}/ja_2026_pitching_projections.csv')
        steamerhit= pd.read_csv(f'{fp}/steamerhit.csv')
        steamerpit= pd.read_csv(f'{fp}/steamerpitch.csv')
        bathit    = pd.read_csv(f'{fp}/thebat_h.csv')
        batpit    = pd.read_csv(f'{fp}/thebat_p.csv')
        atchit    = pd.read_csv(f'{fp}/atc_h.csv')
        atcpit    = pd.read_csv(f'{fp}/atc_p.csv')
        oopsyhit  = pd.read_csv(f'{fp}/oopsy_h.csv')
        oopsypitch= pd.read_csv(f'{fp}/oopsy_p.csv')
        bat_hitters = pd.read_csv(f'{fp}/bat_hitters.csv')
        bat_pitchers= pd.read_csv(f'{fp}/bat_pitchers.csv')
        return ja_hit, ja_pitch, steamerhit, steamerpit, bathit, batpit, atchit, atcpit, oopsyhit, oopsypitch, bat_hitters, bat_pitchers

    # ------------------------------------------------------------------
    # GROUP 9 — Rankings & Scores  (SLOW)
    # ------------------------------------------------------------------
    @st.cache_data(ttl=SLOW_TTL, show_spinner=False)
    def load_rankings():
        fp = _DATA_DIR
        hitterranks  = pd.read_csv(f'{fp}/MLB DW 2026 Player Ranks - Hitters.csv')
        pitcherranks = pd.read_csv(f'{fp}/MLB DW 2026 Player Ranks - Pitchers.csv')
        fscores_mlb_hit   = pd.read_csv(f'{fp}/All_MLB_Scores.csv')
        fscores_milb_hit  = pd.read_csv(f'{fp}/All_MiLB_Scores.csv')
        fscores_mlb_pitch = pd.read_csv(f'{fp}/All_Pitching_Majors_MLB_Scores.csv')
        fscores_milb_pitch= pd.read_csv(f'{fp}/All_Pitching_Minors_MLB_Scores.csv')
        fscores_display_p = pd.read_csv(f'{fp}/Pitchers_fScores.csv')
        fscores_display_h = pd.read_csv(f'{fp}/Hitters_fScores.csv')
        timrank_hitters   = pd.read_csv(f'{fp}/timrank_hitters.csv')
        timrank_pitchers  = pd.read_csv(f'{fp}/timrank_pitchers.csv')
        posdata           = pd.read_csv(f'{fp}/mlbposdata.csv')
        return hitterranks, pitcherranks, fscores_mlb_hit, fscores_milb_hit, fscores_mlb_pitch, fscores_milb_pitch, fscores_display_p, fscores_display_h, timrank_hitters, timrank_pitchers, posdata

    # ------------------------------------------------------------------
    # GROUP 10 — ADP  (SLOW — updates a few times a day at most)
    # ------------------------------------------------------------------
    @st.cache_data(ttl=SLOW_TTL, show_spinner=False)
    def load_adp():
        return pd.read_csv(f'{_DATA_DIR}/MasterADPTableau.csv')

    # ------------------------------------------------------------------
    # GROUP 11 — Hitter Profiles  (SLOW — season-long batted ball data)
    # ------------------------------------------------------------------
    @st.cache_data(ttl=SLOW_TTL, show_spinner=False)
    def load_hitter_profiles():
        fp = _DATA_DIR
        hprofiles24   = pd.read_csv(f'{fp}/hitter_profiles_data_2024.csv')
        hprofiles25   = pd.read_csv(f'{fp}/hitter_profiles_data_2025.csv')
        hprofiles2425 = pd.read_csv(f'{fp}/hitter_profiles_data_2024_2025.csv')
        return hprofiles24, hprofiles25, hprofiles2425

    # ------------------------------------------------------------------
    # GROUP 12 — Pitch Movement  (SLOW — season-level clustering data)
    # ------------------------------------------------------------------
    @st.cache_data(ttl=SLOW_TTL, show_spinner=False)
    def load_pitch_movement():
        return pd.read_csv(f'{_DATA_DIR}/mlb_pitch_movement_clustering_data_2025.csv')

    # ------------------------------------------------------------------
    # GROUP 13 — Schedule / Upcoming  (SLOW — changes day-to-day but not
    #            intra-day, and reads are cheap)
    # ------------------------------------------------------------------
    @st.cache_data(ttl=SLOW_TTL, show_spinner=False)
    def load_schedule_data():
        fp = _DATA_DIR
        base_sched         = pd.read_csv(f'{fp}/upcoming_schedule.csv')
        upcoming_proj      = pd.read_csv(f'{fp}/next10projections.csv')
        upcoming_p_scores  = pd.read_csv(f'{fp}/upcoming_p_schedule_scores.csv')
        upcoming_start_grades = pd.read_csv(f'{fp}/upcoming_start_grades.csv')
        mlbplayerinfo      = pd.read_csv(f'{fp}/mlbplayerinfo.csv')
        ownership_df      = pd.read_csv(f'{fp}/OwnershipReport.csv')
        ownershipdict = dict(zip(ownership_df.Player,ownership_df.Owned))
        return base_sched, upcoming_proj, upcoming_p_scores, upcoming_start_grades, mlbplayerinfo, ownershipdict

    @st.cache_data(ttl=SLOW_TTL, show_spinner=False)
    def load_next_ten_proj():
        fp = _DATA_DIR
        base_sched         = pd.read_csv(f'{fp}/upcoming_schedule.csv')
        upcoming_proj      = pd.read_csv(f'{fp}/next10projections.csv')
        mlbplayerinfo      = pd.read_csv(f'{fp}/mlbplayerinfo.csv')
        ownership_df      = pd.read_csv(f'{fp}/OwnershipReport.csv')
        ownershipdict = dict(zip(ownership_df.Player,ownership_df.Owned))
        return base_sched, upcoming_proj, ownershipdict


    # ------------------------------------------------------------------
    # GROUP 14 — Large Parquet Event Databases  (PARQUET_TTL)
    #            These are big; filter to MLB regulars immediately so the
    #            cached object is as small as possible.
    # ------------------------------------------------------------------
    @st.cache_data(ttl=PARQUET_TTL, show_spinner=False)
    def load_hitdb():
        df = pd.read_parquet(f'{_DATA_DIR}/hitdb2025.parquet')
        return df[(df['level'] == 'MLB') & (df['game_type'] == 'R')].copy()

    @st.cache_data(ttl=PARQUET_TTL, show_spinner=False)
    def load_pitdb():
        df = pd.read_parquet(f'{_DATA_DIR}/pitdb2025.parquet')
        return df[(df['level'] == 'MLB') & (df['game_type'] == 'R')].copy()

    # ------------------------------------------------------------------
    # PAGE → LOADER REGISTRY
    # Maps each tab name to the loader functions it actually needs.
    # Used by the Refresh button to clear only the relevant caches.
    # ------------------------------------------------------------------
    _PAGE_LOADERS = {
        "2026 Projections":        [load_daily_projections, load_player_stats, load_bullpen_data, load_weather_umps, load_betting_data, load_trends, load_airpull],
        "Game Previews":           [load_daily_projections, load_player_stats, load_bullpen_data, load_weather_umps],
        "Pitcher Projections":     [load_daily_projections, load_player_stats, load_bullpen_data],
        "Hitter Projections":      [load_daily_projections, load_player_stats],
        "Player Projection Details":[load_daily_projections, load_player_stats],
        "Matchups":                [load_daily_projections, load_player_stats, load_weather_umps],
        "Player Trends":           [load_trends, load_player_stats],
        "Air Pull Matchups":       [load_airpull, load_daily_projections],
        "Weather & Umps":          [load_weather_umps, load_daily_projections],
        "Streamers":               [load_daily_projections, load_schedule_data],
        "SP Planner":              [load_schedule_data, load_daily_projections],
        "Zone Matchups":           [load_player_stats, load_daily_projections],
        "Prop Bets":               [load_betting_data, load_daily_projections],
        "2026 Ranks":              [load_rankings],
        "2026 ADP":                [load_adp],
        "ADP Profiles":            [load_adp],
        "Auction Value Calculator":[load_season_projections, load_rankings],
        "2026 Projections":        [load_season_projections, load_rankings],
        "Tim Kanak fScores":       [load_rankings],
        "Prospect Ranks":          [load_rankings],
        "Hitter Profiles":         [load_hitter_profiles],
        "Hitter Comps":            [load_hitter_profiles, load_player_stats],
        "Prospect Comps":          [load_rankings],
        "Player Rater":            [load_player_stats, load_hitdb, load_pitdb],
        "Pitch Movement Comps":    [load_pitch_movement],
        "Lineup Tracker":          [],   # has its own internal loader
        "Transactions Tracker":    [],   # Google Sheets loader (handled separately)
        "Tableau":                 [load_daily_projections],
    }

    color1='#FFBABA'
    color2='#FFCC99'
    color3='#FFFF99'
    color4='#CCFF99'
    color5='#99FF99'

    def applyColor_PitMatchups(val, column):
        if column == 'JA ERA':
            if val >= 4.5:
                return f'background-color: {color1}'
            elif val >= 3.75:
                return f'background-color: {color2}'
            elif val >= 3.25:
                return f'background-color: {color3}'
            elif val >= 2.5:
                return f'background-color: {color4}'
            elif val < 2.5:
                return f'background-color: {color5}'
        if column == 'JA ERA L20':
            if val >= 4.5:
                return f'background-color: {color1}'
            elif val >= 3.75:
                return f'background-color: {color2}'
            elif val >= 3.25:
                return f'background-color: {color3}'
            elif val >= 2.5:
                return f'background-color: {color4}'
            elif val < 2.5:
                return f'background-color: {color5}'
        if column == 'Hot Score':
            if val >= 1.25:
                return f'background-color: {color5}'
            elif val >= 1:
                return f'background-color: {color4}'
            elif val >= .5:
                return f'background-color: {color3}'
            elif val >= -.5:
                return f'background-color: {color2}'
            elif val < -.5:
                return f'background-color: {color1}'
    
    def applyColor_HitMatchups(val, column):
        if column == 'xwOBA OE':
            if val >= .05:
                return f'background-color: {color5}'
            elif val >= .025:
                return f'background-color: {color4}'
            elif val >= -.025:
                return f'background-color: {color3}'
            elif val >= -.05:
                return f'background-color: {color2}'
            elif val < -.05:
                return f'background-color: {color1}'
        if column == 'xwOBA OE L15':
            if val >= .05:
                return f'background-color: {color5}'
            elif val >= .025:
                return f'background-color: {color4}'
            elif val >= -.025:
                return f'background-color: {color3}'
            elif val >= -.05:
                return f'background-color: {color2}'
            elif val < -.05:
                return f'background-color: {color1}'
        if column == 'Hot Score':
            if val >= .1:
                return f'background-color: {color5}'
            elif val >= .05:
                return f'background-color: {color4}'
            elif val >= -.05:
                return f'background-color: {color3}'
            elif val >= -.1:
                return f'background-color: {color2}'
            elif val < -.1:
                return f'background-color: {color1}'
        if column == 'xwOBA':
            if val >= .35:
                return f'background-color: {color5}'
            elif val >= .325:
                return f'background-color: {color4}'
            elif val >= .3:
                return f'background-color: {color3}'
            elif val >= .275:
                return f'background-color: {color2}'
            elif val < .275:
                return f'background-color: {color1}'
        if column == 'AVG':
            if val >= .3:
                return f'background-color: {color5}'
            elif val >= .28:
                return f'background-color: {color4}'
            elif val >= .26:
                return f'background-color: {color3}'
            elif val >= .24:
                return f'background-color: {color2}'
            elif val < .24:
                return f'background-color: {color1}'
        if column == 'SLG':
            if val >= .525:
                return f'background-color: {color5}'
            elif val >= .475:
                return f'background-color: {color4}'
            elif val >= .425:
                return f'background-color: {color3}'
            elif val >= .4:
                return f'background-color: {color2}'
            elif val < .4:
                return f'background-color: {color1}'
        if column == 'xwOBA Con':
            if val >= .5:
                return f'background-color: {color5}'
            elif val >= .425:
                return f'background-color: {color4}'
            elif val >= .375:
                return f'background-color: {color3}'
            elif val >= .35:
                return f'background-color: {color2}'
            elif val < .35:
                return f'background-color: {color1}'
        if column == 'SwStr%':
            if val >= .15:
                return f'background-color: {color1}'
            elif val >= .13:
                return f'background-color: {color2}'
            elif val >= .11:
                return f'background-color: {color3}'
            elif val >= .09:
                return f'background-color: {color4}'
            elif val < .09:
                return f'background-color: {color5}'      
        if column == 'Brl%':
            if val >= .15:
                return f'background-color: {color5}'
            elif val >= .1:
                return f'background-color: {color4}'
            elif val >= .07:
                return f'background-color: {color3}'
            elif val >= .05:
                return f'background-color: {color2}'
            elif val < .05:
                return f'background-color: {color1}'
        if column == 'FB%':
            if val >= .35:
                return f'background-color: {color5}'
            elif val >= .30:
                return f'background-color: {color4}'
            elif val >= .25:
                return f'background-color: {color3}'
            elif val >= .2:
                return f'background-color: {color2}'
            elif val < .2:
                return f'background-color: {color1}'  
        if column == 'Hard%':
            if val >= .6:
                return f'background-color: {color5}'
            elif val >= .5:
                return f'background-color: {color4}'
            elif val >= .45:
                return f'background-color: {color3}'
            elif val >= .3:
                return f'background-color: {color2}'
            elif val < .3:
                return f'background-color: {color1}'  
    def applyColor_HitStat(val, column):
        if column == 'Hitter Air Pull / PA':
            if val >= .14:
                return f'background-color: {color5}'
            elif val >= .11:
                return f'background-color: {color4}'
            elif val >= .08:
                return f'background-color: {color3}'
            elif val >= .05:
                return f'background-color: {color2}'
            elif val < .05:
                return f'background-color: {color1}'
        
        if column == 'Pitcher Air Pull / PA':
            if val >= .14:
                return f'background-color: {color5}'
            elif val >= .11:
                return f'background-color: {color4}'
            elif val >= .08:
                return f'background-color: {color3}'
            elif val >= .05:
                return f'background-color: {color2}'
            elif val < .05:
                return f'background-color: {color1}'   
        if column == 'Average Air Pull':
            if val >= .14:
                return f'background-color: {color5}'
            elif val >= .11:
                return f'background-color: {color4}'
            elif val >= .08:
                return f'background-color: {color3}'
            elif val >= .05:
                return f'background-color: {color2}'
            elif val < .05:
                return f'background-color: {color1}'        
        if column == 'Hitter Air Pull / BIP':
            if val >= .2:
                return f'background-color: {color5}'
            elif val >= .17:
                return f'background-color: {color4}'
            elif val >= .13:
                return f'background-color: {color3}'
            elif val >= .1:
                return f'background-color: {color2}'
            elif val < .1:
                return f'background-color: {color1}'     
        if column == 'Pitcher Air Pull / BIP':
            if val >= .2:
                return f'background-color: {color5}'
            elif val >= .17:
                return f'background-color: {color4}'
            elif val >= .13:
                return f'background-color: {color3}'
            elif val >= .1:
                return f'background-color: {color2}'
            elif val < .1:
                return f'background-color: {color1}'        
        if column == 'PPA':
            if val >= 4:
                return f'background-color: {color1}'
            elif val >= 3.9:
                return f'background-color: {color2}'
            elif val >= 3.85:
                return f'background-color: {color3}'
            elif val >= 3.75:
                return f'background-color: {color4}'
            elif val < 3.75:
                return f'background-color: {color5}'
        
        if column == 'GB%':
            if val >= .55:
                return f'background-color: {color5}'
            elif val >= .5:
                return f'background-color: {color5}'
            elif val >= .45:
                return f'background-color: {color3}'
            elif val >= .4:
                return f'background-color: {color2}'
            elif val < .4:
                return f'background-color: {color1}'
        
        if column == 'K%':
            if val >= .3:
                return f'background-color: {color1}'
            elif val >= .26:
                return f'background-color: {color2}'
            elif val >= .23:
                return f'background-color: {color3}'
            elif val >= .2:
                return f'background-color: {color4}'
            elif val < .2:
                return f'background-color: {color5}'

        if column == 'xwOBA':
            if val >= .37:
                return f'background-color: {color5}'
            elif val >= .35:
                return f'background-color: {color4}'
            elif val >= .33:
                return f'background-color: {color3}'
            elif val >= .31:
                return f'background-color: {color2}'
            elif val < .31:
                return f'background-color: {color1}'
        
        if column == 'BB%':
            if val >= .11:
                return f'background-color: {color5}'
            elif val >= .09:
                return f'background-color: {color4}'
            elif val >= .07:
                return f'background-color: {color3}'
            elif val >= .05:
                return f'background-color: {color2}'
            elif val < .05:
                return f'background-color: {color1}'
        
        if column == 'Brl%':
            if val >= .15:
                return f'background-color: {color5}'
            elif val >= .10:
                return f'background-color: {color4}'
            elif val >= .07:
                return f'background-color: {color3}'
            elif val >= .05:
                return f'background-color: {color2}'
            elif val < .05:
                return f'background-color: {color1}'      
        if column == 'FB%':
            if val >= .35:
                return f'background-color: {color5}'
            elif val >= .30:
                return f'background-color: {color4}'
            elif val >= .25:
                return f'background-color: {color3}'
            elif val >= .2:
                return f'background-color: {color2}'
            elif val < .2:
                return f'background-color: {color1}'      
    def applyColor_weatherumps(val, column):
        if column == 'Rain%':
            if val >= 75:
                return f'background-color:{color1}'
            elif val >= 50:
                return f'background-color:{color2}'
            elif val >= 30:
                return f'background-color:{color3}'
            elif val >= 10:
                return f'background-color:{color4}'
            elif val < 10:
                return f'background-color:{color5}'
        if column == 'K Boost':
            if val >= 1.05:
                return f'background-color:{color5}'
            elif val >= 1.02:
                return f'background-color:{color4}'
            elif val >= .98:
                return f'background-color:{color3}'
            elif val >= .96:
                return f'background-color:{color2}'
            elif val < .96:
                return f'background-color:{color1}'
        if column == 'BB Boost':
            if val >= 1.05:
                return f'background-color:{color5}'
            elif val >= 1.02:
                return f'background-color:{color4}'
            elif val >= .98:
                return f'background-color:{color3}'
            elif val >= .96:
                return f'background-color:{color2}'
            elif val < .96:
                return f'background-color:{color1}'
    def applyColor_PitchStat(val, column):
        if column == 'K%':
            if val >= .3:
                return f'background-color:{color5}'
            elif val >= .26:
                return f'background-color:{color4}'
            elif val >= .23:
                return f'background-color:{color3}'
            elif val >= .2:
                return f'background-color:{color2}'
            elif val < .2:
                return f'background-color:{color1}'
        if column == 'K-BB%':
            if val >= .2:
                return f'background-color:{color5}'
            elif val >= .18:
                return f'background-color:{color4}'
            elif val >= .16:
                return f'background-color:{color3}'
            elif val >= .13:
                return f'background-color:{color2}'
            elif val < .13:
                return f'background-color:{color1}'
        if column == 'BB%':
            if val >= .11:
                return f'background-color: {color1}'
            elif val >= .09:
                return f'background-color: {color2}'
            elif val >= .07:
                return f'background-color: {color3}'
            elif val >= .05:
                return f'background-color: {color4}'
            elif val < .05:
                return f'background-color: {color5}'
        if column == 'SwStr%':
            if val >= .15:
                return f'background-color: {color5}'
            elif val >= .13:
                return f'background-color: {color4}'
            elif val >= .115:
                return f'background-color: {color3}'
            elif val >= .1:
                return f'background-color: {color2}'
            elif val < .1:
                return f'background-color: {color1}'
        if column == 'Ball%':
            if val >= .4:
                return f'background-color: {color1}'
            elif val >= .38:
                return f'background-color: {color2}'
            elif val >= .35:
                return f'background-color: {color3}'
            elif val >= .32:
                return f'background-color: {color4}'
            elif val < .32:
                return f'background-color: {color5}'
        if column == 'xwOBA':
            if val >= .37:
                return f'background-color: {color1}'
            elif val >= .35:
                return f'background-color: {color2}'
            elif val >= .33:
                return f'background-color: {color3}'
            elif val >= .31:
                return f'background-color: {color4}'
            elif val < .31:
                return f'background-color: {color5}'
        if column == 'xERA':
            if val >= .37*13.4:
                return f'background-color: {color1}'
            elif val >= .35*13.4:
                return f'background-color: {color2}'
            elif val >= .33*13.4:
                return f'background-color: {color3}'
            elif val >= .31*13.4:
                return f'background-color: {color4}'
            elif val < .31*13.4:
                return f'background-color: {color5}'
    def applyColor_PitchProj(val, column):
        if column == 'Sal':
            if val >= 10000:
                return f'background-color: {color1}'
            elif val >= 9000:
                return f'background-color: {color2}'
            elif val >= 8000:
                return f'background-color: {color3}'
            elif val >= 7000:
                return f'background-color: {color4}'
            elif val < 7000:
                return f'background-color: {color5}'
        if column == 'PC':
            if val >= 95:
                return f'background-color: {color5}'
            elif val >= 90:
                return f'background-color: {color4}'
            elif val >= 80:
                return f'background-color: {color3}'
            elif val >= 75:
                return f'background-color: {color2}'
            elif val < 75:
                return f'background-color: {color1}'
        if column == 'DKPts':
            if val >= 22:
                return f'background-color: {color5}'
            elif val >= 19:
                return f'background-color: {color4}'
            elif val >= 16:
                return f'background-color: {color3}'
            elif val >= 13:
                return f'background-color: {color2}'
            elif val < 13:
                return f'background-color: {color1}'
        if column == 'Val':
            if val >= 2.2:
                return f'background-color: {color5}'
            elif val >= 2:
                return f'background-color: {color4}'
            elif val >= 1.8:
                return f'background-color: {color3}'
            elif val >= 1.6:
                return f'background-color: {color2}'
            elif val < 1.6:
                return f'background-color: {color1}'
        if column == 'IP':
            if val >= 6.25:
                return f'background-color: {color5}'
            elif val >= 5.75:
                return f'background-color: {color4}'
            elif val >= 5.25:
                return f'background-color: {color3}'
            elif val >= 4.75:
                return f'background-color: {color2}'
            elif val < 4.75:
                return f'background-color: {color1}'
        if column == 'H':
            if val >= 5.25:
                return f'background-color: {color1}'
            elif val >= 5:
                return f'background-color: {color2}'
            elif val >= 4.75:
                return f'background-color: {color3}'
            elif val >= 4.5:
                return f'background-color: {color4}'
            elif val < 4.5:
                return f'background-color: {color5}'
        if column == 'ER':
            if val >= 2.8:
                return f'background-color: {color1}'
            elif val >= 2.65:
                return f'background-color: {color2}'
            elif val >= 2.5:
                return f'background-color: {color3}'
            elif val >= 2.35:
                return f'background-color: {color4}'
            elif val < 2.35:
                return f'background-color: {color5}'
        if column == 'SO':
            if val >= 8:
                return f'background-color: {color5}'
            elif val >= 6.5:
                return f'background-color: {color4}'
            elif val >= 5:
                return f'background-color: {color3}'
            elif val >= 3.5:
                return f'background-color: {color2}'
            elif val < 3.5:
                return f'background-color: {color1}'
        if column == 'BB':
            if val >= 2:
                return f'background-color: {color1}'
            elif val >= 1.75:
                return f'background-color: {color2}'
            elif val >= 1.5:
                return f'background-color: {color3}'
            elif val >= 1.25:
                return f'background-color: {color4}'
            elif val < 1.25:
                return f'background-color: {color5}'
        if column == 'W':
            if val >= .35:
                return f'background-color: {color5}'
            elif val >= .3:
                return f'background-color: {color4}'
            elif val >= .25:
                return f'background-color: {color3}'
            elif val >= .2:
                return f'background-color: {color2}'
            elif val < .2:
                return f'background-color: {color1}'
        if column == 'Own%':
            if val >= 40:
                return f'background-color: {color1}'
            elif val >= 30:
                return f'background-color: {color2}'
            elif val >= 20:
                return f'background-color: {color3}'
            elif val >= 10:
                return f'background-color: {color4}'
            elif val < 10:
                return f'background-color: {color5}'
        if column == 'Ceil':
            if val >= 40:
                return f'background-color: {color5}'
            elif val >= 35:
                return f'background-color: {color4}'
            elif val >= 30:
                return f'background-color: {color3}'
            elif val >= 25:
                return f'background-color: {color2}'
            elif val < 25:
                return f'background-color: {color1}'
    def applyColor_HitProj(val, column):
        if column == 'Sal':
            if val >= 5500:
                return f'background-color: {color1}'
            elif val >= 4500:
                return f'background-color: {color2}'
            elif val >= 3500:
                return f'background-color: {color3}'
            elif val >= 2500:
                return f'background-color: {color4}'
            elif val < 2500:
                return f'background-color: {color5}'
        if column == 'DKPts':
            if val >= 11:
                return f'background-color: {color5}'
            elif val >= 9.5:
                return f'background-color: {color4}'
            elif val >= 7.5:
                return f'background-color: {color3}'
            elif val >= 6:
                return f'background-color: {color2}'
            elif val < 6:
                return f'background-color: {color1}'
        if column == 'Avg DK Proj':
            if val >= 11:
                return f'background-color: {color5}'
            elif val >= 9.5:
                return f'background-color: {color4}'
            elif val >= 7.5:
                return f'background-color: {color3}'
            elif val >= 6:
                return f'background-color: {color2}'
            elif val < 6:
                return f'background-color: {color1}'
        if column == 'HR Diff':
            if val >= .05:
                return f'background-color: {color5}'
            elif val >= .03:
                return f'background-color: {color4}'
            elif val >= 0.01:
                return f'background-color: {color3}'
            elif val >= -.03:
                return f'background-color: {color2}'
            elif val < -.03:
                return f'background-color: {color1}'
        if column == 'DKPts Diff':
            if val >= 1.5:
                return f'background-color: {color5}'
            elif val >= 1:
                return f'background-color: {color4}'
            elif val >= .5:
                return f'background-color: {color3}'
            elif val >= 0:
                return f'background-color: {color2}'
            elif val < 0:
                return f'background-color: {color1}'
        if column == 'Boost':
            if val >= 1.5:
                return f'background-color: {color5}'
            elif val >= 1:
                return f'background-color: {color4}'
            elif val >= .5:
                return f'background-color: {color3}'
            elif val >= 0:
                return f'background-color: {color2}'
            elif val < 0:
                return f'background-color: {color1}'
        if column == 'Value':
            if val >= 3.2:
                return f'background-color: {color5}'
            elif val >= 2.9:
                return f'background-color: {color4}'
            elif val >= 2.6:
                return f'background-color: {color3}'
            elif val >= 2.3:
                return f'background-color: {color2}'
            elif val < 2:
                return f'background-color: {color1}'
        if column == 'HR':
            if val >= .25:
                return f'background-color: {color5}'
            elif val >= .2:
                return f'background-color: {color4}'
            elif val >= .1:
                return f'background-color: {color3}'
            elif val >= .05:
                return f'background-color: {color2}'
            elif val < .05:
                return f'background-color: {color1}'
        if column == 'Avg HR Proj':
            if val >= .25:
                return f'background-color: {color5}'
            elif val >= .2:
                return f'background-color: {color4}'
            elif val >= .1:
                return f'background-color: {color3}'
            elif val >= .05:
                return f'background-color: {color2}'
            elif val < .05:
                return f'background-color: {color1}'
        if column == 'SB':
            if val >= .25:
                return f'background-color: {color5}'
            elif val >= .2:
                return f'background-color: {color4}'
            elif val >= .1:
                return f'background-color: {color3}'
            elif val >= .05:
                return f'background-color: {color2}'
            elif val < .05:
                return f'background-color: {color1}'
    def applyColor_Props(val, column):
        if column == 'BetValue':
            if val >= .2:
                return f'background-color: {color5}'
            elif val >= .15:
                return f'background-color: {color4}'
            elif val >= .1:
                return f'background-color: {color3}'
            elif val < .1:
                return f'background-color: {color2}'

        if column == 'Price':
            if val >= 150:
                return f'background-color: {color5}'
            elif val >= 100:
                return f'background-color: {color4}'
            elif val >= -150:
                return f'background-color: {color3}'
            elif val >= -200:
                return f'background-color: {color2}'
            elif val < -200:
                return f'background-color: {color1}'
    def color_cells_weatherumps(df_subset):
        return [applyColor_weatherumps(val, col) for val, col in zip(df_subset, df_subset.index)]
    def color_cells_PitchProj(df_subset):
        return [applyColor_PitchProj(val, col) for val, col in zip(df_subset, df_subset.index)]
    def color_cells_HitProj(df_subset):
        return [applyColor_HitProj(val, col) for val, col in zip(df_subset, df_subset.index)]
    def color_cells_PitchStat(df_subset):
        return [applyColor_PitchStat(val, col) for val, col in zip(df_subset, df_subset.index)]
    def color_cells_HitStat(df_subset):
        return [applyColor_HitStat(val, col) for val, col in zip(df_subset, df_subset.index)]
    def color_cells_HitMatchups(df_subset):
        return [applyColor_HitMatchups(val, col) for val, col in zip(df_subset, df_subset.index)]
    def color_cells_PitMatchups(df_subset):
        return [applyColor_PitMatchups(val, col) for val, col in zip(df_subset, df_subset.index)]
    def color_cells_Props(df_subset):
        return [applyColor_Props(val, col) for val, col in zip(df_subset, df_subset.index)]

    # -------------------------------------------------------------------------
    # LAZY DATA LOAD — only load what the current page needs.
    # Each variable below is populated on-demand inside each "if tab ==" block.
    # The helper _load_projection_page_data() and _load_player_stats_page_data()
    # below are used by the many pages that need projection + stats together.
    # -------------------------------------------------------------------------

    def get_player_image(player_id):
        return f'https://img.mlbstatic.com/mlb-photos/image/upload/d_people:generic:headshot:67:current.png/w_426,q_auto:best/v1/people/{player_id}/headshot/67/current'

    def _prepare_projection_data(hitterproj, pitcherproj, hitterproj2, gameinfo,
                                  hitter_stats, h_vs_avg, bpreport):
        """
        Shared post-load transforms needed by all projection-related pages.
        Called inside each page block after the relevant loaders run.
        Returns prepared copies — does NOT mutate cached DataFrames.
        """
        hitterproj  = hitterproj.copy()
        pitcherproj = pitcherproj.copy()
        hitter_stats = hitter_stats.copy()
        gameinfo    = gameinfo.copy()
        bpreport    = bpreport.copy()

        # Derived columns on gameinfo
        gameinfo['RoadTeam'] = np.where(
            gameinfo['team'] == gameinfo['Park'], gameinfo['opponent'], gameinfo['team'])
        gameinfo['GameString'] = gameinfo['RoadTeam'] + '@' + gameinfo['Park']

        # Derived columns on projections
        hitterproj['RoadTeam'] = np.where(
            hitterproj['Team'] == 'HomeTeam', 'Opp', hitterproj['Team'])
        hitterproj['GameString'] = hitterproj['RoadTeam'] + '@' + hitterproj['Park']

        pitcherproj['RoadTeam'] = np.where(
            pitcherproj['Team'] == pitcherproj['HomeTeam'],
            pitcherproj['Opponent'], pitcherproj['Team'])
        pitcherproj['GameString'] = pitcherproj['RoadTeam'] + '@' + pitcherproj['HomeTeam']

        mainslateteams    = list(hitterproj[hitterproj['MainSlate'] == 'Main']['Team'])
        main_slate_gamelist = list(pitcherproj[pitcherproj['MainSlate'] == 'Main']['GameString'])

        games_df = pitcherproj[['Team', 'Opponent', 'HomeTeam']].drop_duplicates().copy()
        games_df['RoadTeam'] = np.where(
            games_df['Team'] == games_df['HomeTeam'], games_df['Opponent'], games_df['Team'])
        games_df['GameString'] = games_df['RoadTeam'] + '@' + games_df['HomeTeam']
        games_df = games_df[['RoadTeam', 'HomeTeam', 'GameString']].drop_duplicates()

        # Bullpen prep
        bpreport['BP Rank'] = bpreport['xERA'].rank()
        bpreport = bpreport.sort_values(by='BP Rank')
        bpreport['BP Rank'] = range(1, len(bpreport) + 1)
        bpcount = len(bpreport)
        bpreport['Rank'] = bpreport['BP Rank'].astype(str) + ' / ' + str(bpcount)
        for col in ['K%', 'BB%', 'K-BB%', 'SwStr%']:
            if col in bpreport.columns:
                bpreport[col] = bpreport[col] / 100

        # Hitter emoji flags
        hot_hitters  = list(hitter_stats[hitter_stats['IsHot'] == 'Y']['ID'])
        cold_hitters = list(hitter_stats[hitter_stats['IsCold'] == 'Y']['ID'])
        homer_boosts = list(h_vs_avg[(h_vs_avg['HR Diff'] >= .03) & (h_vs_avg['HR'] >= .1)]['Hitter'])

        for df, name_col, id_col in [
            (hitterproj, 'Hitter', 'ID'),
            (hitter_stats, 'Hitter', 'ID'),
        ]:
            df['Hot']      = np.where(df[id_col].isin(hot_hitters),  '🔥', '')
            df['Cold']     = np.where(df[id_col].isin(cold_hitters), '🥶', '')
            df['HR Boost'] = np.where(df[name_col].isin(homer_boosts), '🚀', '')
            df['Batter']   = df[name_col] + ' ' + df['Hot'] + ' ' + df['Cold'] + ' ' + df['HR Boost']

        try:
            confirmed_lus = list(hitterproj2[hitterproj2['Confirmed LU'] == 'Y']['Team'].unique())
        except Exception:
            confirmed_lus = []

        try:
            last_update = pitcherproj['LastUpdate'].iloc[0]
        except Exception:
            last_update = 'N/A'

        return (hitterproj, pitcherproj, hitter_stats, gameinfo, bpreport,
                games_df, mainslateteams, main_slate_gamelist,
                confirmed_lus, last_update)

    # Sidebar navigation
    st.sidebar.image(logo, width=250)  # Added logo to sidebar

    PAGE_GROUPS = {
        "Season Long Fantasy": [
            "SP Planner",
            "Upcoming Projections",
            "Streamers",
            "Player Rater", 
            "Lineup Tracker",
            "Transactions Tracker",
            "Pitch Movement Comps",
            "Player Trends",
            "Air Pull Matchups",
            "Tableau",
        ],
        "Draft Tools": [
            "ADP Profiles",
            "2026 ADP",
            "Auction Value Calculator",
        ],
        "Dynasty & Prospects": [
            "Prospect Ranks",
            "Prospect Comps",
            "Tim Kanak fScores",
        ],
        "PRO": [
            "Games & Lineups",
            "Game Previews",
            "Pitcher Projections",
            "Hitter Projections",
            "Matchups",
            "Weather & Umps",
            "Prop Bets",
            "DFS Optimizer"
        ],
        
    }

    PRO_PAGES = {
        "Game Previews",
        "Pitcher Projections",
        "Hitter Projections",
        "Matchups",
        "Weather & Umps",
        "Prop Bets",
        "DFS Optimizer"
    }


    if "selected_group" not in st.session_state:
        st.session_state.selected_group = "Season Long Fantasy"

    if "selected_tab" not in st.session_state:
        st.session_state.selected_tab = PAGE_GROUPS["Season Long Fantasy"][0]

    with st.sidebar:
        st.markdown("## MLB DW")

        group = st.radio(
            "Section",
            list(PAGE_GROUPS.keys()),
            key="selected_group"
        )

        tab = st.radio(
            "Page",
            PAGE_GROUPS[group],
            key="selected_tab"
        )

    ################

    # ------------------------------------------------------------------
    # PAGE-AWARE REFRESH BUTTON
    # Only clears cache for the loaders the current page actually uses,
    # so other pages' cached data is NOT evicted when one user refreshes.
    # ------------------------------------------------------------------
    st.sidebar.divider()
    if st.sidebar.button("🔄 Refresh Data", help="Reload data for the current page only"):
        page_loaders = _PAGE_LOADERS.get(tab, [])
        if page_loaders:
            for loader_fn in page_loaders:
                loader_fn.clear()
            st.toast(f"✅ Data refreshed for: {tab}", icon="🔄")
        else:
            # Pages with their own internal loaders (Lineup Tracker, Transactions)
            # or Google Sheets loaders — clear those specifically
            if tab == "Lineup Tracker":
                # The internal loader is defined inside the tab block;
                # force re-run by incrementing a counter
                st.session_state['lineup_tracker_refresh'] = \
                    st.session_state.get('lineup_tracker_refresh', 0) + 1
            elif tab == "Transactions Tracker":
                load_ranks_data.clear()
                get_sheet_df.clear()
            st.toast(f"✅ Data refreshed for: {tab}", icon="🔄")
        st.rerun()

    # Main content
    st.markdown("""
        <div class="main-title">⚾ MLB DW Web App</div>
        <div class="main-subtitle">Fantasy Baseball Analytics · MLB Data Warehouse</div>
    """, unsafe_allow_html=True)
    
    #st.markdown(f"""
    #            <center><h1>MLB DW Web App</h1></center>
    #            <center><b><i>On mobile, be sure to set the theme to 'light mode' (go to settings in the top right)</b></i></center></b>
    #            """, unsafe_allow_html=True)
    #st.markdown("<b><center>If you're on mobile, be sure you're using 'light mode' in settings (hit the three dots in the top right of the screen)</center></b>",unsafe_allow_html=True)
    #st.markdown(f"<center><i>Last projection update time: {last_update}est</center></i>",unsafe_allow_html=True)
    

    # --- HITTER PROFILES (drop-in) -------------------------------------------------
    # Requirements: streamlit, pandas, altair (add "altair" to requirements.txt)

    def _fmt_cols(df: pd.DataFrame, pct_cols=None, trip_cols=None, int_cols=None):
        """Return Streamlit column_config dict + a formatted copy of df."""
        pct_cols = pct_cols or []
        trip_cols = trip_cols or []  # 3-decimal (AVG/OBP/SLG)
        int_cols = int_cols or []

        cfg = {}
        df2 = df.copy()

        # Build configs only for columns that actually exist
        for c in df2.columns:
            if c in pct_cols:
                cfg[c] = st.column_config.NumberColumn(format="%.1f%%", help=f"{c} (percent)")
                # If values look like 0–1, convert to percent
                if df2[c].dropna().between(0, 1).all():
                    df2[c] = df2[c] * 100.0
            elif c in trip_cols:
                cfg[c] = st.column_config.NumberColumn(format="%.3f", help=f"{c} (triple-slash)")
            elif c in int_cols:
                cfg[c] = st.column_config.NumberColumn(format="%d")
            elif pd.api.types.is_float_dtype(df2[c]):
                cfg[c] = st.column_config.NumberColumn(format="%.2f")

        return df2, cfg

    def _cols_existing(df, wanted):
        return [c for c in wanted if c in df.columns]

    def _metric_or_dash(val):
        try:
            if pd.isna(val): return "—"
            if isinstance(val, (float, np.floating)): return f"{val:.3f}" if 0 <= val <= 1 else f"{val:.3f}" if "0." in f"{val}" else f"{val}"
            return f"{val}"
        except Exception:
            return "—"

    def render_hitter_profiles(hprofiles24: pd.DataFrame,
                            hprofiles25: pd.DataFrame,
                            hprofiles2425: pd.DataFrame):

        st.markdown("""
            <div style="text-align:center">
                <div style="font-size:38px; font-weight:800; line-height:1.1">Hitter Profiles ⚾</div>
                <div style="opacity:0.8; margin-top:4px">Fast, visual snapshots of each hitter’s skills and batted-ball DNA</div>
            </div>
            <hr style="margin:1rem 0 0.5rem 0; opacity:.2;">
        """, unsafe_allow_html=True)

        # ------------------------- Controls -------------------------
        colA, colB, colC = st.columns([2, 1, 2])
        with colA:
            hitter_options = sorted(hprofiles2425["BatterName"].dropna().unique().tolist())
            hitter = st.selectbox("Choose a Hitter", hitter_options, index=0)

        with colB:
            sample = st.selectbox("Choose Sample", ["2025", "2024", "2024-2025"], index=0)

        with colC:
            st.caption("Display options")
            show_tables = st.toggle("Show raw tables", value=False, help="Reveal the raw profile tables below the charts/cards")
            show_all_cols = st.toggle("Show all columns", value=False, help="If off, show the key subset for each table")

        if sample == "2025":
            data = hprofiles25.copy()
        elif sample == "2024":
            data = hprofiles24.copy()
        else:
            data = hprofiles2425.copy()

        player = data.loc[data["BatterName"] == hitter].copy()
        if player.empty:
            st.warning("No rows found for that hitter in the selected sample.")
            return

        # If there are multiple rows (e.g., team splits), pick the most recent/highest PA row as default view
        if "PA" in player.columns:
            player = player.sort_values("PA", ascending=False).head(1)
        else:
            player = player.head(1)

        # ------------------------- Top Cards -------------------------
        # Pull headline metrics safely
        def gv(col, default=None):
            return player[col].values[0] if col in player.columns else default

        PA = gv("PA", 0)
        HR = gv("HR", 0)
        SB = gv("SB", 0)
        AVG = gv("AVG", np.nan)
        OBP = gv("OBP", np.nan)
        SLG = gv("SLG", np.nan)
        xwOBA = gv("xwOBA", np.nan)
        wOBA = gv("wOBA", np.nan) if "wOBA" in player.columns else np.nan

        st.markdown("### Snapshot")
        mc1, mc2, mc3, mc4, mc5, mc6 = st.columns(6)
        mc1.metric("PA", f"{int(PA) if pd.notna(PA) else '—'}")
        mc2.metric("HR", f"{int(HR) if pd.notna(HR) else '—'}")
        mc3.metric("SB", f"{int(SB) if pd.notna(SB) else '—'}")
        mc4.metric("AVG", _metric_or_dash(AVG))
        mc5.metric("OBP", _metric_or_dash(OBP))
        mc6.metric("SLG", _metric_or_dash(SLG))

        # ------------------------- Quick Charts -------------------------
        st.markdown("### Visuals")

        ch_left, ch_mid, ch_right = st.columns([1.2, 1.2, 1.4])

        # Slash line bar
        with ch_left:
            slash_cols = _cols_existing(player, ["AVG", "OBP", "SLG"])
            if slash_cols:
                plot_df = pd.melt(player[slash_cols], var_name="Stat", value_name="Value")
                bar = (
                    alt.Chart(plot_df)
                    .mark_bar()
                    .encode(x=alt.X("Stat:N", title="", sort=slash_cols),
                            y=alt.Y("Value:Q", title="", scale=alt.Scale(zero=False)),
                            tooltip=[alt.Tooltip("Stat:N"), alt.Tooltip("Value:Q", format=".3f")])
                    .properties(height=200)
                )
                st.altair_chart(bar, use_container_width=True)
            else:
                st.caption("Slash chart: required columns not found.")

        # Batted-ball profile horizontal bars
        with ch_mid:
            bb_cols = _cols_existing(player, ["Brl%", "AirPull%", "GB%", "LD%", "FB%", "SweetSpot%"])
            if bb_cols:
                bb_df = player[bb_cols].T.reset_index()
                bb_df.columns = ["Metric", "Value"]
                # Normalize to percent if needed
                if bb_df["Value"].dropna().between(0, 1).all():
                    bb_df["Value"] = bb_df["Value"] * 100.0
                hbar = (
                    alt.Chart(bb_df)
                    .mark_bar()
                    .encode(
                        y=alt.Y("Metric:N", sort="-x", title=""),
                        x=alt.X("Value:Q", title="", scale=alt.Scale(domain=[0, max(100, float(bb_df["Value"].max() or 0))])),
                        tooltip=[alt.Tooltip("Metric:N"), alt.Tooltip("Value:Q", format=".1f")]
                    )
                    .properties(height=220)
                )
                st.altair_chart(hbar, use_container_width=True)
            else:
                st.caption("Batted-ball chart: required columns not found.")

        # Contact/discipline scatter (x: Z-Contact%, y: Z-Swing%, size: BB%/K% diff)
        with ch_right:
            d_cols = _cols_existing(player, ["Z-Contact%", "Z-Swing%", "BB%", "K%"])
            if d_cols:
                ddf = player.copy()
                # Convert to 0–100 if in decimals
                for c in ["Z-Contact%", "Z-Swing%", "BB%", "K%"]:
                    if c in ddf.columns:
                        if ddf[c].dropna().between(0, 1).all():
                            ddf[c] = ddf[c] * 100.0
                ddf["DisciplineScore"] = (ddf.get("BB%", 0) - ddf.get("K%", 0))
                scat = (
                    alt.Chart(ddf)
                    .mark_circle()
                    .encode(
                        x=alt.X("Z-Contact%:Q", title="Z-Contact%"), 
                        y=alt.Y("Z-Swing%:Q", title="Z-Swing%"),
                        size=alt.Size("DisciplineScore:Q", title="BB% - K%"),
                        tooltip=[
                            alt.Tooltip("Z-Contact%:Q", format=".1f"),
                            alt.Tooltip("Z-Swing%:Q", format=".1f"),
                            alt.Tooltip("BB%:Q", format=".1f"),
                            alt.Tooltip("K%:Q", format=".1f")
                        ],
                    )
                    .properties(height=230)
                )
                st.altair_chart(scat, use_container_width=True)
            else:
                st.caption("Plate-discipline scatter: required columns not found.")

        # ------------------------- Detail Tabs -------------------------
        tab1, tab2, tab3, tab4 = st.tabs(["Base Stats", "Batted Ball", "Plate Discipline", "fScores"])

        # Base stats
        with tab1:
            base_cols = _cols_existing(player, ["BatterName", "PA", "AB", "R", "HR", "RBI", "SB", "AVG", "OBP", "SLG", "xwOBA", "wOBA"])
            if base_cols:
                df_base = player[base_cols].copy()
                df_base, cfg = _fmt_cols(
                    df_base,
                    pct_cols=[],  # slash/xwOBA are 3-decimal
                    trip_cols=_cols_existing(df_base, ["AVG", "OBP", "SLG", "xwOBA", "wOBA"]),
                    int_cols=_cols_existing(df_base, ["PA", "AB", "R", "HR", "RBI", "SB"])
                )
                st.dataframe(df_base if show_all_cols else df_base[base_cols], use_container_width=True, column_config=cfg, hide_index=True)
            else:
                st.info("No base stat columns found.")

        # Batted ball
        with tab2:
            bb_cols_full = _cols_existing(player, ["BatterName","xwOBA","xwOBACON","Brl%","AirPull%","GB%","LD%","FB%","SweetSpot%"])
            if bb_cols_full:
                df_bb = player[bb_cols_full].copy()
                df_bb, cfg = _fmt_cols(
                    df_bb,
                    pct_cols=_cols_existing(df_bb, ["Brl%","AirPull%","GB%","LD%","FB%","SweetSpot%"]),
                    trip_cols=_cols_existing(df_bb, ["xwOBA","xwOBACON"]),
                )
                st.dataframe(df_bb if show_all_cols else df_bb[bb_cols_full], use_container_width=True, column_config=cfg, hide_index=True)
            else:
                st.info("No batted-ball profile columns found.")

        # Plate discipline
        with tab3:
            disc_cols = _cols_existing(player, ["BatterName","K%","BB%","Z-Contact%","Z-Swing%","O-Swing%","O-Contact%"])
            if disc_cols:
                df_disc = player[disc_cols].copy()
                df_disc, cfg = _fmt_cols(
                    df_disc,
                    pct_cols=[c for c in disc_cols if c.endswith("%")]
                )
                st.dataframe(df_disc if show_all_cols else df_disc[disc_cols], use_container_width=True, column_config=cfg, hide_index=True)
            else:
                st.info("No plate-discipline columns found.")

        # fScores
        with tab4:
            f_cols = _cols_existing(player, ["BatterName","fHitTool","fPower","fDiscipline","fSpeed","fDurability"])
            if f_cols:
                df_f = player[f_cols].copy()
                # Horizontal bar chart for fScores
                score_cols = [c for c in f_cols if c != "BatterName"]
                if score_cols:
                    longf = pd.melt(df_f[["BatterName"] + score_cols], id_vars=["BatterName"], var_name="Trait", value_name="Score")
                    fbar = (
                        alt.Chart(longf)
                        .mark_bar()
                        .encode(
                            y=alt.Y("Trait:N", sort="-x", title=""),
                            x=alt.X("Score:Q", title="", scale=alt.Scale(zero=False)),
                            tooltip=["Trait:N", alt.Tooltip("Score:Q", format=".1f")]
                        )
                        .properties(height=220)
                    )
                    st.altair_chart(fbar, use_container_width=True)

                # Table
                df_f, cfg = _fmt_cols(df_f)
                st.dataframe(df_f if show_all_cols else df_f[f_cols], use_container_width=True, column_config=cfg, hide_index=True)
            else:
                st.info("No fScore columns found.")

        # ------------------------- Optional: Raw tables -------------------------
        if show_tables:
            st.divider()
            st.subheader("Raw tables")
            st.write("Below are your original selections as plain tables (useful for debugging).")

            # These mimic your original blocks but cleaner + resilient
            base_cols_raw = _cols_existing(data, ["BatterName","PA","AB","R","HR","RBI","SB","AVG","OBP","SLG"])
            if base_cols_raw:
                df0 = player[base_cols_raw].copy()
                df0, cfg0 = _fmt_cols(df0, trip_cols=_cols_existing(df0, ["AVG","OBP","SLG"]), int_cols=_cols_existing(df0, ["PA","AB","R","HR","RBI","SB"]))
                st.dataframe(df0, use_container_width=True, column_config=cfg0, hide_index=True)

            bb_cols_raw = _cols_existing(data, ["BatterName","xwOBA","xwOBACON","Brl%","AirPull%","GB%","LD%","FB%","SweetSpot%"])
            if bb_cols_raw:
                df1 = player[bb_cols_raw].copy()
                df1, cfg1 = _fmt_cols(df1, pct_cols=_cols_existing(df1, ["Brl%","AirPull%","GB%","LD%","FB%","SweetSpot%"]),
                                    trip_cols=_cols_existing(df1, ["xwOBA","xwOBACON"]))
                st.dataframe(df1, use_container_width=True, column_config=cfg1, hide_index=True)

            disc_cols_raw = _cols_existing(data, ["BatterName","K%","BB%","Z-Contact%","Z-Swing%"])
            if disc_cols_raw:
                df2 = player[disc_cols_raw].copy()
                df2, cfg2 = _fmt_cols(df2, pct_cols=[c for c in disc_cols_raw if c.endswith("%")])
                st.dataframe(df2, use_container_width=True, column_config=cfg2, hide_index=True)

            f_cols_raw = _cols_existing(data, ["BatterName","fHitTool","fPower","fDiscipline","fSpeed","fDurability"])
            if f_cols_raw:
                df3 = player[f_cols_raw].copy()
                df3, cfg3 = _fmt_cols(df3)
                st.dataframe(df3, use_container_width=True, column_config=cfg3, hide_index=True)

    
    @st.cache_resource
    def get_gspread_client():
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
        return gspread.authorize(creds)

    # 2) Cache a single worksheet → DataFrame
    @st.cache_data(show_spinner=False)  # no TTL = cache for the app session until cleared
    def get_sheet_df(sheet_url: str, worksheet_name: str) -> pd.DataFrame:
        client = get_gspread_client()
        ws = client.open_by_url(sheet_url).worksheet(worksheet_name)
        # get_all_records respects header row; fast + clean to DataFrame
        data = ws.get_all_records()
        return pd.DataFrame(data)

    # 3) Single convenience loader for both tabs (also cached)
    @st.cache_data(show_spinner=False)
    def load_ranks_data(sheet_url: str):
        hitters  = get_sheet_df(sheet_url, "Hitters")
        pitchers = get_sheet_df(sheet_url, "Pitchers")
        return {"hitters": hitters, "pitchers": pitchers}

    # 4) Optional: a manual refresh to bust the cache
    def render_refresh_button():
        col = st.empty()
        with col.container():
            if st.button("↻ Refresh data", help="Clear cache and re-load from Google Sheets"):
                load_ranks_data.clear()
                get_sheet_df.clear()
                get_gspread_client.clear()
                st.experimental_rerun()

    
    if tab == "Lineup Tracker":
        # =========================
        # ===== LOAD DATA =========
        # =========================
        # Lineup tracker has its own internal parquet loader; keyed to
        # a refresh counter so the sidebar button can bust it.
        _lt_refresh_key = st.session_state.get('lineup_tracker_refresh', 0)

        @st.cache_data(ttl=3600, show_spinner=False)
        def load_lineup_data(_refresh_key=0):
            base_dir = os.path.dirname(__file__)
            data_dir = os.path.join(base_dir, "Data")
            path = os.path.join(data_dir, "lineup_tracker.parquet")
            df = pd.read_parquet(path)
            return df

        lineup_data = load_lineup_data(_refresh_key=_lt_refresh_key)

        # =========================
        # ===== NORMALIZE =========
        # =========================
        df = lineup_data.copy()

        # Drop junk columns if present
        for junk in ["Unnamed: 0", "index"]:
            if junk in df.columns:
                df = df.drop(columns=[junk])

        # Ensure Date is a real date
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.date

        # Ensure Spot is numeric-ish
        if "Spot" in df.columns:
            df["Spot"] = pd.to_numeric(df["Spot"], errors="coerce").astype("Int64")

        # Basic string cleanup
        for c in ["Team", "RoadTeam", "HomeTeam", "Opp", "Player", "SP", "p_throws", "h_stand"]:
            if c in df.columns:
                df[c] = df[c].astype(str).replace({"nan": np.nan, "None": np.nan}).str.strip()

        # Create/standardize PitcherHand
        if "p_throws" in df.columns:
            df["PitcherHand"] = df["p_throws"].str.upper()
            df.loc[~df["PitcherHand"].isin(["L", "R"]), "PitcherHand"] = np.nan
        else:
            df["PitcherHand"] = np.nan

        # Create a reliable Opponent column using home/road logic if available
        # If Team == RoadTeam -> Opponent = HomeTeam else RoadTeam
        if all(c in df.columns for c in ["Team", "RoadTeam", "HomeTeam"]):
            df["Opponent"] = np.where(df["Team"] == df["RoadTeam"], df["HomeTeam"], df["RoadTeam"])
        else:
            df["Opponent"] = df["Opp"] if "Opp" in df.columns else np.nan

        # Useful helpers
        df["Player_norm"] = df["Player"].fillna("").astype(str).str.strip()
        df["Team_norm"] = df["Team"].fillna("").astype(str).str.strip()

        # Dataset bounds for controls
        valid_dates = sorted([d for d in df["Date"].dropna().unique()])
        min_date = valid_dates[0] if valid_dates else None
        max_date = valid_dates[-1] if valid_dates else None

        teams = sorted([t for t in df["Team_norm"].dropna().unique() if t and t.lower() != "nan"])
        all_players = sorted([p for p in df["Player_norm"].dropna().unique() if p and p.lower() != "nan"])

        # =========================
        # ===== HEADER / KPIs =====
        # =========================
        st.subheader("2026 MLB Lineup Tracker")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Rows", f"{len(df):,}")
        k2.metric("Teams", f"{len(teams):,}")
        k3.metric("Games", f"{df['game_id'].nunique():,}" if "game_id" in df.columns else "—")
        if min_date and max_date:
            k4.metric("Date range", f"{min_date} → {max_date}")
        else:
            k4.metric("Date range", "—")

        st.caption("All filters live at the top of each view (no sidebar).")

        # =========================
        # ===== VIEW SELECTOR =====
        # =========================
        view_tabs = st.tabs(["🔎 Team Search", "🧍 Player Search", "📅 Pick a Day", "✨ Extras"])

        # -------------------------
        # Helpers
        # -------------------------
        def lineup_table(chunk: pd.DataFrame) -> pd.DataFrame:
            """Clean lineup table sorted by batting order."""
            show_cols = []
            for c in ["Spot", "Player", "h_stand", "SP", "PitcherHand", "Opponent", "game_id"]:
                if c in chunk.columns:
                    show_cols.append(c)

            out = chunk.copy()
            if "Spot" in out.columns:
                out = out.sort_values(["Spot", "Player_norm"])
            else:
                out = out.sort_values(["Player_norm"])

            out = out[show_cols].rename(
                columns={
                    "h_stand": "Bats",
                    "SP": "Opp SP",
                    "PitcherHand": "P Hand",
                }
            )
            return out

        def export_button(data: pd.DataFrame, filename: str, label: str = "⬇️ Export to CSV"):
            st.download_button(
                label=label,
                data=data.to_csv(index=False).encode("utf-8"),
                file_name=filename,
                mime="text/csv",
                use_container_width=True,
            )

        # =========================
        # ===== TEAM SEARCH =======
        # =========================
        with view_tabs[0]:
            st.markdown("### Team Search")

            # Controls at TOP (no sidebar)
            c1, c2, c3, c4, c5 = st.columns([2.2, 2.4, 2.0, 1.6, 1.6])

            with c1:
                team = st.selectbox("Team", options=teams, index=0 if teams else None, key="lt_team")

            with c2:
                if min_date and max_date:
                    dr = st.date_input("Date range", value=(min_date, max_date), key="lt_team_daterange")
                else:
                    dr = None

            with c3:
                hand = st.multiselect("Opponent pitcher hand", options=["L", "R"], default=["L", "R"], key="lt_team_hand")

            with c4:
                only_1_to_9 = st.checkbox("Only 1–9", value=True, key="lt_team_1to9")

            with c5:
                compact = st.checkbox("Compact", value=True, key="lt_team_compact")

            if not team:
                st.info("Pick a team to begin.")
            else:
                dff = df[df["Team_norm"] == team].copy()

                # date range
                if isinstance(dr, tuple) and len(dr) == 2:
                    start_d, end_d = dr
                    dff = dff[(dff["Date"] >= start_d) & (dff["Date"] <= end_d)]

                # pitcher hand filter
                if hand:
                    dff = dff[dff["PitcherHand"].isin(hand)]

                if only_1_to_9 and "Spot" in dff.columns:
                    dff = dff[(dff["Spot"].notna()) & (dff["Spot"] >= 1) & (dff["Spot"] <= 9)]

                if dff.empty:
                    st.warning("No results for that selection.")
                else:
                    # Group by game/day (prefer game_id if present)
                    group_cols = ["Date"]
                    if "game_id" in dff.columns:
                        group_cols.append("game_id")

                    # render
                    groups = (
                        dff[group_cols + ["Opponent", "Opp", "SP", "PitcherHand"]]
                        .drop_duplicates()
                        .sort_values(group_cols)
                        .to_dict("records")
                    )

                    top2 = st.columns([2, 2, 2, 2])
                    with top2[0]:
                        show_raw = st.checkbox("Show raw rows", value=False, key="lt_team_raw")
                    with top2[1]:
                        st.write("")
                    with top2[2]:
                        st.write("")
                    with top2[3]:
                        export_button(dff, f"lineups_team_{team}.csv")

                    st.divider()

                    for rec in groups:
                        dt = rec.get("Date")
                        gid = rec.get("game_id", None)
                        opp = rec.get("Opponent") if pd.notna(rec.get("Opponent")) else rec.get("Opp")
                        sp = rec.get("SP")
                        ph = rec.get("PitcherHand")

                        header = f"**{dt}** — {team} vs **{opp}** | Opp SP: **{sp}** ({ph})" + (f" | game_id: {gid}" if gid else "")
                        with st.expander(header, expanded=not compact):
                            if gid:
                                chunk = dff[(dff["Date"] == dt) & (dff["game_id"] == gid)].copy()
                            else:
                                chunk = dff[(dff["Date"] == dt)].copy()

                            st.dataframe(lineup_table(chunk), use_container_width=True, hide_index=True)

                            if show_raw:
                                st.caption("Raw rows")
                                st.dataframe(chunk.sort_values(["Spot", "Player_norm"]), use_container_width=True, hide_index=True)

        # =========================
        # ===== PLAYER SEARCH =====
        # =========================
        with view_tabs[1]:
            st.markdown("### Player Search")

            c1, c2, c3, c4 = st.columns([3.2, 2.0, 2.0, 1.6])

            with c1:
                q = st.text_input("Search player (type part of the name)", value="", key="lt_player_q")

            with c2:
                hand = st.multiselect("Opponent pitcher hand", ["L", "R"], default=["L", "R"], key="lt_player_hand")

            with c3:
                only_1_to_9 = st.checkbox("Only 1–9", value=False, key="lt_player_1to9")

            with c4:
                st.write("")

            # Build candidates
            if q.strip():
                qq = q.strip().lower()
                candidates = [p for p in all_players if qq in p.lower()]
                candidates = candidates[:250]
            else:
                candidates = all_players[:250]

            player = st.selectbox("Pick player", options=candidates, index=0 if candidates else None, key="lt_player_pick")

            if not player:
                st.info("Search and select a player.")
            else:
                dff = df[df["Player_norm"] == player].copy()
                if hand:
                    dff = dff[dff["PitcherHand"].isin(hand)]
                if only_1_to_9 and "Spot" in dff.columns:
                    dff = dff[(dff["Spot"].notna()) & (dff["Spot"] >= 1) & (dff["Spot"] <= 9)]

                if dff.empty:
                    st.warning("No rows for that player/filter.")
                else:
                    # Controls row
                    r1, r2, r3, r4 = st.columns([2, 2, 2, 2])
                    with r4:
                        export_button(dff, f"lineups_player_{player.replace(' ', '_')}.csv")

                    # ---- Timeline (fixed: no KeyError) ----
                    st.markdown("#### Lineup spot timeline")

                    view = dff.copy()

                    # If your dataset sometimes uses 'SP' and sometimes 'Opp SP', normalize to a single display column
                    if "SP" in view.columns and "Opp SP" not in view.columns:
                        view = view.rename(columns={"SP": "Opp SP"})

                    # Build requested columns, THEN intersect with what actually exists
                    requested = ["Date", "Team", "Opponent", "Spot", "h_stand", "Opp SP", "PitcherHand", "game_id"]
                    show_cols = [c for c in requested if c in view.columns]

                    # Sort keys (only include keys that exist)
                    sort_cols = [c for c in ["Date", "game_id"] if c in view.columns]

                    # Final view
                    view = (
                        view[show_cols]
                        .sort_values(sort_cols if sort_cols else None)
                        .rename(columns={"h_stand": "Bats", "PitcherHand": "P Hand"})
                    )

                    st.dataframe(view, use_container_width=True, hide_index=True)

                    # Spot distribution
                    st.markdown("#### Spot distribution")
                    if "Spot" in dff.columns:
                        spot_counts = (
                            dff.dropna(subset=["Spot"])
                            .groupby(["Spot"], as_index=False)
                            .size()
                            .rename(columns={"size": "Games"})
                            .sort_values("Spot")
                        )
                        c1, c2 = st.columns([2, 3])
                        with c1:
                            st.dataframe(spot_counts, use_container_width=True, hide_index=True)
                        with c2:
                            most_common = (
                                spot_counts.sort_values("Games", ascending=False).head(1)["Spot"].iloc[0]
                                if not spot_counts.empty else None
                            )
                            st.metric("Rows", f"{len(dff):,}")
                            st.metric("Teams appeared for", f"{dff['Team_norm'].nunique():,}")
                            st.metric("Most common spot", f"{most_common}" if most_common is not None else "—")
                    else:
                        st.info("No Spot column found; cannot build spot distribution.")

        # =========================
        # ===== PICK A DAY =========
        # =========================
        with view_tabs[2]:
            st.markdown("### Pick a Day and see all lineups")

            if not (min_date and max_date):
                st.warning("No valid dates found.")
            else:
                c1, c2, c3, c4 = st.columns([2.2, 2.0, 2.0, 1.6])
                with c1:
                    pick = st.date_input("Day", value=max_date, min_value=min_date, max_value=max_date, key="lt_day_pick")
                with c2:
                    show_raw = st.checkbox("Show raw rows", value=False, key="lt_day_raw")
                with c3:
                    only_1_to_9 = st.checkbox("Only 1–9", value=True, key="lt_day_1to9")
                with c4:
                    st.write("")

                dff = df[df["Date"] == pick].copy()
                if only_1_to_9 and "Spot" in dff.columns:
                    dff = dff[(dff["Spot"].notna()) & (dff["Spot"] >= 1) & (dff["Spot"] <= 9)]

                if dff.empty:
                    st.warning("No games found that day.")
                else:
                    # Identify games
                    if "game_id" in dff.columns and "RoadTeam" in dff.columns and "HomeTeam" in dff.columns:
                        games = (
                            dff[["game_id", "RoadTeam", "HomeTeam"]]
                            .drop_duplicates()
                            .sort_values(["HomeTeam", "RoadTeam"])
                            .to_dict("records")
                        )
                    else:
                        # fallback: group by Team/Opponent pairs
                        games = (
                            dff[["Team_norm", "Opponent"]]
                            .drop_duplicates()
                            .sort_values(["Team_norm", "Opponent"])
                            .to_dict("records")
                        )

                    st.caption(f"Games found: {len(games)}")
                    export_button(dff, f"lineups_day_{pick}.csv", label="⬇️ Export day to CSV")
                    st.divider()

                    for g in games:
                        if "game_id" in g:
                            gid = g["game_id"]
                            away = g.get("RoadTeam")
                            home = g.get("HomeTeam")
                            header = f"**{away} @ {home}** | game_id: {gid}"

                            away_df = dff[(dff["game_id"] == gid) & (dff["Team_norm"] == str(away))].copy()
                            home_df = dff[(dff["game_id"] == gid) & (dff["Team_norm"] == str(home))].copy()

                        else:
                            # fallback
                            teamA = g["Team_norm"]
                            opp = g.get("Opponent")
                            header = f"**{teamA} vs {opp}**"
                            away_df = dff[dff["Team_norm"] == teamA].copy()
                            home_df = dff[dff["Team_norm"] == opp].copy()

                        away_sp = away_df["SP"].dropna().iloc[0] if "SP" in away_df.columns and away_df["SP"].notna().any() else None
                        away_ph = away_df["PitcherHand"].dropna().iloc[0] if "PitcherHand" in away_df.columns and away_df["PitcherHand"].notna().any() else None
                        home_sp = home_df["SP"].dropna().iloc[0] if "SP" in home_df.columns and home_df["SP"].notna().any() else None
                        home_ph = home_df["PitcherHand"].dropna().iloc[0] if "PitcherHand" in home_df.columns and home_df["PitcherHand"].notna().any() else None

                        with st.expander(header, expanded=True):
                            h1, h2 = st.columns(2)
                            h1.markdown(f"**{away_df['Team_norm'].dropna().iloc[0] if not away_df.empty else 'Away'}**  \nOpp SP: **{away_sp}** ({away_ph})")
                            h2.markdown(f"**{home_df['Team_norm'].dropna().iloc[0] if not home_df.empty else 'Home'}**  \nOpp SP: **{home_sp}** ({home_ph})")

                            c1, c2 = st.columns(2)
                            with c1:
                                if away_df.empty:
                                    st.info("No lineup found.")
                                else:
                                    st.dataframe(lineup_table(away_df), use_container_width=True, hide_index=True)
                            with c2:
                                if home_df.empty:
                                    st.info("No lineup found.")
                                else:
                                    st.dataframe(lineup_table(home_df), use_container_width=True, hide_index=True)

                            if show_raw:
                                st.caption("Raw rows")
                                st.dataframe(
                                    pd.concat(
                                        [away_df.assign(_side="away"), home_df.assign(_side="home")],
                                        ignore_index=True
                                    ).sort_values(["_side", "Spot", "Player_norm"]),
                                    use_container_width=True,
                                    hide_index=True
                                )

        # =========================
        # ===== EXTRAS ============
        # =========================
        with view_tabs[3]:
            st.markdown("### Extras")

            c1, c2, c3, c4 = st.columns([2.2, 2.4, 2.0, 1.6])

            with c1:
                team = st.selectbox("Team", options=teams, index=0 if teams else None, key="lt_extras_team")
            with c2:
                mode = st.selectbox("Extra view", ["Most common spots", "Lineup stability", "Platoon usage"], key="lt_extras_mode")
            with c3:
                hand = st.multiselect("Opponent pitcher hand", ["L", "R"], default=["L", "R"], key="lt_extras_hand")
            with c4:
                only_1_to_9 = st.checkbox("Only 1–9", value=True, key="lt_extras_1to9")

            if not team:
                st.info("Pick a team.")
            else:
                dff = df[df["Team_norm"] == team].copy()
                if hand:
                    dff = dff[dff["PitcherHand"].isin(hand)]
                if only_1_to_9 and "Spot" in dff.columns:
                    dff = dff[(dff["Spot"].notna()) & (dff["Spot"] >= 1) & (dff["Spot"] <= 9)]

                if dff.empty:
                    st.warning("No data for that selection.")
                else:
                    if mode == "Most common spots":
                        st.markdown("#### Most common lineup spots (by player)")
                        t = (
                            dff.dropna(subset=["Spot"])
                            .groupby(["Player_norm", "Spot"], as_index=False)
                            .size()
                            .rename(columns={"size": "Games"})
                            .sort_values(["Spot", "Games"], ascending=[True, False])
                        )
                        st.dataframe(t, use_container_width=True, hide_index=True)
                        export_button(t, f"{team}_spot_frequency.csv")

                    elif mode == "Lineup stability":
                        st.markdown("#### Lineup stability (unique 1–9 orders)")
                        rows = []
                        group_cols = ["Date"] + (["game_id"] if "game_id" in dff.columns else [])
                        for keys, chunk in dff.groupby(group_cols):
                            dt = keys[0] if isinstance(keys, tuple) else keys
                            gid = keys[1] if isinstance(keys, tuple) and len(keys) > 1 else None

                            chunk = chunk.dropna(subset=["Spot"]).copy()
                            chunk = chunk[(chunk["Spot"] >= 1) & (chunk["Spot"] <= 9)]
                            order = (
                                chunk.sort_values("Spot")
                                .groupby("Spot")["Player_norm"]
                                .first()
                                .reindex(range(1, 10))
                            )
                            rows.append(
                                {
                                    "Date": dt,
                                    "game_id": gid,
                                    "FilledSpots": int(order.notna().sum()),
                                    "OrderKey": " | ".join(order.fillna("—").tolist()),
                                }
                            )

                        hist = pd.DataFrame(rows).sort_values(["Date"] + (["game_id"] if "game_id" in hist.columns else []))
                        st.dataframe(hist, use_container_width=True, hide_index=True)
                        st.metric("Unique lineup orders (1–9)", f"{hist['OrderKey'].nunique():,}" if not hist.empty else "0")
                        export_button(hist, f"{team}_lineup_stability.csv")

                    else:  # Platoon usage
                        st.markdown("#### Platoon usage (player spot by pitcher hand)")
                        t = (
                            dff.dropna(subset=["Spot"])
                            .groupby(["PitcherHand", "Player_norm", "Spot"], as_index=False)
                            .size()
                            .rename(columns={"size": "Games"})
                            .sort_values(["PitcherHand", "Spot", "Games"], ascending=[True, True, False])
                        )
                        st.dataframe(t, use_container_width=True, hide_index=True)
                        export_button(t, f"{team}_platoon_usage.csv")
    
    if tab == "Pitch Movement Comps":
        # --- Load only what this page needs ---
        pitch_move_data = load_pitch_movement()
        st.title("Pitch Movement Comps")
        st.caption("Find the most similar pitch shapes (by pitch type) across MLB, using averaged Statcast movement + release traits.")

        # -----------------------------
        # Expect: pitch_move_data is already loaded as a DataFrame
        # Required columns:
        # player_name, pitcher, p_throws, pitch_type, n_pitches,
        # release_speed, release_pos_x, release_pos_z, release_extension, pfx_x_in, pfx_z_in
        # -----------------------------
        df = pitch_move_data.copy()
        df['PitchGrade'] = round(df['PitchGrade'],0)
        df = df.rename({'PitchGrade': 'MLBDW Grade'},axis=1)

        grade_df = df[['pitcher','pitch_type','MLBDW Grade']]

        required = {
            "player_name","pitcher","p_throws","pitch_type","n_pitches",
            "release_speed","release_pos_x","release_pos_z","release_extension","pfx_x_in","pfx_z_in"
        }
        missing = sorted(list(required - set(df.columns)))
        if missing:
            st.error(f"pitch_move_data is missing required columns: {missing}")
            st.stop()

        # Ensure numeric
        num_cols = ["n_pitches","release_speed","release_pos_x","release_pos_z","release_extension","pfx_x_in","pfx_z_in"]
        for c in num_cols:
            df[c] = pd.to_numeric(df[c], errors="coerce")

        df = df.dropna(subset=["player_name","pitcher","pitch_type","p_throws"] + num_cols).copy()
        df["pitch_type"] = df["pitch_type"].astype(str)
        df["p_throws"] = df["p_throws"].astype(str)

        # -----------------------------
        # Layout: Left = results, Right = controls (top) + filters (below)
        # -----------------------------
        left, right = st.columns([3, 1])

        with right:
            st.subheader("Select Pitcher & Pitch")

            # Pitcher search + select (in the right pane, top)
            search = st.text_input("Search pitcher", value="", placeholder="Type a name (e.g., Cade Horton)")
            all_names = np.array(sorted(df["player_name"].unique()))

            if search.strip():
                mask = np.char.find(np.char.lower(all_names), search.strip().lower()) >= 0
                filtered_names = all_names[mask]
            else:
                filtered_names = all_names

            if len(filtered_names) == 0:
                st.warning("No names match your search.")
                st.stop()

            pitcher_name = st.selectbox("Pitcher", filtered_names, index=0)

            # Identify pitcher_id (handle duplicate names by choosing largest total sample)
            sel_name = df[df["player_name"] == pitcher_name].copy()
            totals = sel_name.groupby("pitcher", as_index=False)["n_pitches"].sum().sort_values("n_pitches", ascending=False)
            pitcher_id = int(totals.iloc[0]["pitcher"])
            sel_pitcher = sel_name[sel_name["pitcher"] == pitcher_id].copy()

            # Pitch selection box (top)
            pitch_options = (
                sel_pitcher.sort_values("n_pitches", ascending=False)["pitch_type"].unique().tolist()
            )
            default_pitch = pitch_options[0] if pitch_options else None
            selected_pitch_type = st.selectbox("Pitch type", pitch_options, index=0)

            st.divider()
            st.subheader("Filters")

            k = st.slider("Comps per pitch", min_value=5, max_value=15, value=10, step=1)
            min_target_n = st.slider("Min samples for selected pitch", min_value=1, max_value=100, value=15, step=1)
            min_comp_n = st.slider("Min samples for comp pitches", min_value=10, max_value=150, value=30, step=5)

            same_hand_only = st.checkbox("Only compare to same throwing hand", value=True)

            st.divider()
            st.subheader("Bias toward bigger samples")
            st.caption("Penalizes low-sample comps so you don’t just get random 12-pitch reliever shapes.")
            sample_penalty = st.slider(
                "Penalty strength",
                min_value=0.0, max_value=10.0, value=5.0, step=0.5,
                help="Higher = more penalty for low-sample comps. 0 = no bias, pure distance."
            )

            st.divider()
            feat_mode = st.selectbox(
                "Feature set",
                ["Shape + Release (recommended)", "Movement + Velo only"],
                index=0,
                help="Shape + Release tends to produce more intuitive pitcher-to-pitcher comps."
            )

        # -----------------------------
        # Feature selection
        # -----------------------------
        if feat_mode == "Movement + Velo only":
            feat_cols = ["release_speed","pfx_x_in","pfx_z_in"]
        else:
            feat_cols = ["release_speed","release_pos_x","release_pos_z","release_extension","pfx_x_in","pfx_z_in"]

        # -----------------------------
        # Standardize features *within pitch_type* (and optionally within hand)
        # -----------------------------
        group_keys = ["pitch_type"] + (["p_throws"] if same_hand_only else [])

        for c in feat_cols:
            df[f"{c}__mu"] = df.groupby(group_keys)[c].transform("mean")
            df[f"{c}__sd"] = df.groupby(group_keys)[c].transform("std").replace(0, np.nan)
            df[f"z_{c}"] = (df[c] - df[f"{c}__mu"]) / df[f"{c}__sd"]

        z_cols = [f"z_{c}" for c in feat_cols]
        df = df.dropna(subset=z_cols).copy()

        # -----------------------------
        # Helper: compute comps for a single (pitcher, pitch_type) row
        # -----------------------------
        def get_comps_for_row(target_row: pd.Series, top_k: int) -> pd.DataFrame:
            pt = target_row["pitch_type"]
            hand = target_row["p_throws"]

            pool = df[df["pitch_type"] == pt].copy()
            if same_hand_only:
                pool = pool[pool["p_throws"] == hand].copy()

            # Exclude same pitcher
            pool = pool[pool["pitcher"] != target_row["pitcher"]].copy()

            # Filter by comp sample size
            pool = pool[pool["n_pitches"] >= min_comp_n].copy()
            if pool.empty:
                return pool

            # Vector distances in z-space
            t = target_row[z_cols].to_numpy(dtype=float)
            X = pool[z_cols].to_numpy(dtype=float)
            d = np.sqrt(((X - t) ** 2).sum(axis=1))

            # Penalize small sample comps (optional)
            n = pool["n_pitches"].to_numpy(dtype=float)
            factor = 1.0 + (sample_penalty / np.sqrt(np.maximum(n, 1.0)))
            score = d * factor

            pool = pool.assign(distance=d, score=score)

            # Rank: primarily by score, then raw distance, then larger sample
            pool = pool.sort_values(["score","distance","n_pitches"], ascending=[True, True, False]).head(top_k)

            show_cols = [
                "player_name","pitcher","p_throws","pitch_type","n_pitches",
                "release_speed","pfx_x_in","pfx_z_in","release_pos_x","release_pos_z","release_extension",
                "distance","score"
            ]
            show_cols = [c for c in show_cols if c in pool.columns]
            return pool[show_cols].reset_index(drop=True)

        # -----------------------------
        # Selected pitcher summary + selected pitch comps in left pane
        # -----------------------------
        with left:
            #df = pd.merge(df,grade_df,how='left',on=['pitcher','pitch_type'])
            sel = df[(df["player_name"] == pitcher_name) & (df["pitcher"] == pitcher_id)].copy()
            if sel.empty:
                st.error("Selected pitcher not found in the data after filtering/standardization.")
                st.stop()

            hand = sel["p_throws"].iloc[0]

            st.subheader(f"{pitcher_name}  ·  {hand}-handed")
            st.caption(f"Pitcher ID: {pitcher_id}")

            st.markdown("### Pitch Arsenal (Averages)")
            summary_cols = ["pitch_type","n_pitches","MLBDW Grade","release_speed","pfx_x_in","pfx_z_in","release_pos_x","release_pos_z","release_extension"]
            summary_cols = [c for c in summary_cols if c in sel.columns]
            arsenal = sel[summary_cols].sort_values("n_pitches", ascending=False).reset_index(drop=True)
            st.dataframe(arsenal, use_container_width=True, hide_index=True)

            st.markdown(f"### Selected Pitch: **{selected_pitch_type}**")
            target = sel[sel["pitch_type"] == selected_pitch_type].copy()
            if target.empty:
                st.warning("That pitch type wasn't found for the selected pitcher.")
                st.stop()

            trow = target.sort_values("n_pitches", ascending=False).iloc[0]
            if int(trow["n_pitches"]) < min_target_n:
                st.warning(
                    f"{pitcher_name} {selected_pitch_type} only has n={int(trow['n_pitches'])} in your table. "
                    f"Lower 'Min samples for selected pitch' or pick a different pitch."
                )
                st.stop()

            # Target metrics row
            cols = st.columns(7)
            cols[0].metric("MLBDW Grade", f"{trow['MLBDW Grade']:.0f}")
            cols[1].metric("Velo", f"{trow['release_speed']:.1f}")
            cols[2].metric("HB (in)", f"{trow['pfx_x_in']:.1f}")
            cols[3].metric("VB (in)", f"{trow['pfx_z_in']:.1f}")
            if "release_extension" in trow:
                cols[4].metric("Ext", f"{trow['release_extension']:.2f}")
            if "release_pos_x" in trow:
                cols[5].metric("Rel X", f"{trow['release_pos_x']:.2f}")
            if "release_pos_z" in trow:
                cols[6].metric("Rel Z", f"{trow['release_pos_z']:.2f}")

            st.markdown("### Most Similar Pitches (Same Pitch Type)")
            comps = get_comps_for_row(trow, top_k=k)

            if comps.empty:
                st.info("No comps found after filters (try lowering 'Min samples for comp pitches').")
            else:
                comps = pd.merge(comps, grade_df, how='left', on=['pitcher','pitch_type'])
                display = comps.copy()

                if "distance" in display.columns:
                    display["distance"] = display["distance"].round(3)
                if "score" in display.columns:
                    display["score"] = display["score"].round(3)
                for c in ["release_speed","pfx_x_in","pfx_z_in","release_extension","release_pos_x","release_pos_z"]:
                    if c in display.columns:
                        display[c] = display[c].round(2)
                
                display = display[['player_name','pitch_type','MLBDW Grade','n_pitches','release_speed','pfx_x_in','pfx_z_in','release_pos_x','release_pos_z','release_extension','distance','score']]
                display.columns=['Pitcher','Pitch','MLBDW Grade','#','Velo','X Move','V Move','Release X','Release Y','Ext','Distance','Sim Score']
                st.dataframe(display, use_container_width=True, hide_index=True)

            # Optional movement plot
            show_plot = st.checkbox("Show movement scatter (context)", value=False)
            if show_plot:
                pool = df[df["pitch_type"] == selected_pitch_type].copy()
                if same_hand_only:
                    pool = pool[pool["p_throws"] == hand].copy()

                cloud = pool[pool["n_pitches"] >= min_comp_n].copy()
                highlight_names = set(comps["player_name"].tolist()) if not comps.empty else set()
                highlight = cloud[cloud["player_name"].isin(highlight_names)].copy()

                fig, ax = plt.subplots()
                ax.scatter(cloud["pfx_x_in"], cloud["pfx_z_in"], alpha=0.15)
                if not highlight.empty:
                    ax.scatter(highlight["pfx_x_in"], highlight["pfx_z_in"], alpha=0.9)

                ax.scatter([trow["pfx_x_in"]], [trow["pfx_z_in"]], marker="X", s=120)

                ax.set_xlabel("Horizontal Break (in)  [pitcher POV]")
                ax.set_ylabel("Vertical Break (in)")
                ax.set_title(f"{pitcher_name} {selected_pitch_type} — Movement Neighborhood")
                st.pyplot(fig, clear_figure=True)

            st.divider()
            st.caption(
                "Under the hood: we z-score features within pitch type (and optionally hand), then use nearest-neighbor distance. "
                "The sample penalty biases comps toward higher-sample pitches."
            )

    if tab == "Prospect Ranks":
        # --- Load only what this page needs ---
        hitterranks, pitcherranks, fscores_mlb_hit, fscores_milb_hit, fscores_mlb_pitch, fscores_milb_pitch, pitchers_fscores, hitters_fscores, timrank_hitters, timrank_pitchers, posdata = load_rankings()

        ## Some functions ##
        fscores_milb_hit = fscores_milb_hit.dropna()
        fscores_milb_pitch = fscores_milb_pitch.dropna()

        def score_bg_color(val: float) -> str:
            if val < 80:
                return "#7f1d1d"      # darkest red
            elif val < 100:
                return "#dc2626"      # red
            elif val < 105:
                return "#facc15"      # yellow
            elif val < 120:
                return "#86efac"      # light green
            else:
                return "#16a34a"      # greenest

        def render_score_tile(label: str, value: float):
            bg = score_bg_color(value)

            html = f"""
            <div style="
                background:{bg};
                border-radius:14px;
                padding:12px 8px;          /* ↓ was 18px 10px */
                text-align:center;
                box-shadow:0 4px 10px rgba(0,0,0,0.12);
                min-width:110px;
            ">
                <div style="
                    font-size:30px;        /* ↓ was 38px */
                    font-weight:800;
                    color:#111827;
                    line-height:1.05;
                ">
                    {value:.0f}
                </div>
                <div style="
                    font-size:13px;        /* ↓ was 14px */
                    font-weight:600;
                    margin-top:4px;        /* ↓ was 6px */
                    color:#1f2937;
                    letter-spacing:0.04em;
                ">
                    {label.upper()}
                </div>
            </div>
            """
            st.markdown(html, unsafe_allow_html=True)

        # ---------- TITLE / INTRO ----------
        st.title("Top 150 Prospect Rankings")
        #st.caption("Fantasy-focused prospect list from Tim Kanak (@fantasyaceball)")
        st.markdown("<font size=5>Fantasy-focused prospect list from Tim Kanak (@fantasyaceball)</font>", unsafe_allow_html=True)

        st.markdown(
            """
            These rankings are based on **fantasy value** (not real-life WAR), 
            with hitters generally favored over pitchers and a blend of proximity + 5-year upside.

            Tim's top 150 has been split between hitters and pitchers below. 
            """
        )

        # ---------- PLAYER TYPE TOGGLE ----------
        col_pool_left, col_pool_right = st.columns([2, 3])
        with col_pool_left:
            pool = st.radio(
                "Player type",
                ["Hitters", "Pitchers"],
                horizontal=True,
            )

        if pool == "Hitters":
            base_df = timrank_hitters.copy()
        else:
            base_df = timrank_pitchers.copy()

        #base_df = base_df.drop_duplicates(subset=['Player','MLB Team','Level'],keep='first')
        base_df["rank"] = pd.to_numeric(base_df["rank"], errors="coerce")

        # ---------- SEARCH FILTERS (PLAYER + TEAM ONLY) ----------
        st.markdown("### Search")

        c1, c2 = st.columns(2)
        with c1:
            player_query = st.text_input(
                "Search by player name",
                placeholder="e.g. Walcott, Basallo, Konnor Griffin...",
            )
        with c2:
            team_query = st.text_input(
                "Search by organization",
                placeholder="e.g. Pirates, Guardians, Dodgers...",
            )

        df = base_df.copy()

        # Player search
        if player_query:
            pat = player_query.lower()
            df = df[df["player_name"].str.lower().str.contains(pat, na=False)]

        # Team search
        if team_query:
            pat = team_query.lower()
            df = df[df["organization"].str.lower().str.contains(pat, na=False)]

        df = df.sort_values("rank")

        # ---------- LAYOUT: TABLE LEFT, DETAIL RIGHT ----------
        left_col, right_col = st.columns([2,4])

        # ===== LEFT: MAIN TABLE =====
        with left_col:
            st.markdown("### Prospect List")

            display_cols = ["rank", "player_name", "organization", "eta"]
            display_cols = [c for c in display_cols if c in df.columns]

            table_df = df[display_cols].reset_index(drop=True)

            column_config = {}
            if "rank" in table_df.columns:
                column_config["rank"] = st.column_config.NumberColumn(
                    "Rank",
                    help="Overall fantasy prospect rank",
                    format="%d",
                )
            if "player_name" in table_df.columns:
                column_config["player_name"] = st.column_config.TextColumn(
                    "Player",
                    help="Prospect name",
                )
            if "organization" in table_df.columns:
                column_config["organization"] = st.column_config.TextColumn(
                    "Org",
                    help="MLB organization",
                )
            if "eta" in table_df.columns:
                column_config["eta"] = st.column_config.TextColumn(
                    "ETA",
                    help="Estimated time of arrival",
                )

            st.dataframe(
                table_df,
                use_container_width=True,
                hide_index=True,
                column_config=column_config,
                height=min(600, 40 + 32 * len(table_df)),
            )

        # ===== RIGHT: DETAIL / POPUP =====
        with right_col:
            st.markdown("### Player Details")

            if table_df.empty:
                st.info("No prospects match your current search.")
            else:
                # Choose a player from the currently filtered list
                selected_name = st.selectbox(
                    "Select a player",
                    options=table_df["player_name"].tolist(),
                )

                ### fscores
                ## try hitter fscores
                player_f_scores_1 = fscores_milb_hit[fscores_milb_hit['Player']==selected_name]
                player_f_scores_2 = fscores_milb_pitch[fscores_milb_pitch['player_name']==selected_name]

                if len(player_f_scores_1)>0:
                    player_f_scores = player_f_scores_1
                    f_score_cat = 'Hitter'
                elif len(player_f_scores_2)>0:
                    player_f_scores = player_f_scores_2
                    f_score_cat = 'Pitcher'
                else:
                    player_f_scores = pd.DataFrame()
                    f_score_cat = 'None'
                
                if f_score_cat == 'Hitter':
                    f_hit = player_f_scores['HitTool'].iloc[0]
                    f_power = player_f_scores['Power'].iloc[0]
                    f_dur = player_f_scores['Durability'].iloc[0]
                    f_disc = player_f_scores['Discipline'].iloc[0]
                    f_speed = player_f_scores['Speed'].iloc[0]

                    f_grade = (f_power*.3) + (f_hit*.3) + (f_disc*.2) + (f_dur*.05) + (f_speed*.15)

                    st.markdown("### 🧬 fScore Grades")

                    c1, c2, c3, c4, c5, c6 = st.columns(6)

                    with c1:
                        render_score_tile("Hit", f_hit)
                    with c2:
                        render_score_tile("Power", f_power)
                    with c3:
                        render_score_tile("Discipline", f_disc)
                    with c4:
                        render_score_tile("Speed", f_speed)
                    with c5:
                        render_score_tile("Durability", f_dur)
                    with c6:
                        render_score_tile("Overall", f_grade)

                    st.markdown("---")
                
                if f_score_cat == 'Pitcher':
                    #st.write(player_f_scores)
                    f_era = player_f_scores['fERA'].iloc[0]
                    f_stuff = player_f_scores['fStuff'].iloc[0]
                    f_dur = player_f_scores['fDurability'].iloc[0]
                    f_control = player_f_scores['fControl'].iloc[0]

                    f_grade = (f_era*.3) + (f_stuff*.3) + (f_control*.3) + (f_dur*.1)

                    st.markdown("### 🧬 fScore Grades")

                    c1, c2, c3, c4, c5 = st.columns(5)

                    with c1:
                        render_score_tile("Stuff", f_stuff)
                    with c2:
                        render_score_tile("Control", f_control)
                    with c3:
                        render_score_tile("ERA", f_era)
                    with c4:
                        render_score_tile("Durability", f_dur)
                    with c5:
                        render_score_tile("Overall", f_grade)

                    st.markdown("---")


                p = base_df[base_df["player_name"] == selected_name].iloc[0]

                # Quick summary card always visible on the right
                st.markdown(
                    f"#### {p['player_name']}"
                    f"<br><span style='font-size:0.9rem; color:#6b7280;'>"
                    f"{p.get('positions', '')} • {p.get('organization', '')}"
                    f"</span>",
                    unsafe_allow_html=True,
                )

                meta_bits = []
                if pd.notna(p.get("rank")):
                    meta_bits.append(f"**Rank:** {int(p['rank'])}")
                if pd.notna(p.get("eta")):
                    meta_bits.append(f"**ETA:** {p['eta']}")
                if pd.notna(p.get("previous_rank")):
                    meta_bits.append(f"**Previous Rank:** {p['previous_rank']}")
                if meta_bits:
                    st.markdown(" | ".join(meta_bits))

                if pd.notna(p.get("comp")) and str(p["comp"]).strip():
                    st.markdown(f"**Comp:** {p['comp']}")

                # Build grades block
                grades_text = ""
                if pool == "Hitters":
                    hit = p.get("hit_grade", None)
                    pa = p.get("plate_approach_grade", None)
                    pow_ = p.get("power_grade", None)
                    spd = p.get("speed_grade", None)
                    chunks = []
                    if pd.notna(hit):
                        chunks.append(f"**Hit:** {hit}")
                    if pd.notna(pa):
                        chunks.append(f"**Plate Approach:** {pa}")
                    if pd.notna(pow_):
                        chunks.append(f"**Power:** {pow_}")
                    if pd.notna(spd):
                        chunks.append(f"**Speed:** {spd}")
                    if chunks:
                        grades_text = " • ".join(chunks)
                else:
                    pitch_cols = [c for c in base_df.columns if c.endswith("_grade")]
                    lines = []
                    for c in pitch_cols:
                        val = p.get(c)
                        if pd.notna(val):
                            label = c.replace("_grade", "")
                            lines.append(f"- **{label}:** {val}")
                    if lines:
                        grades_text = "\n".join(lines)

                if grades_text:
                    if pool == "Hitters":
                        st.markdown("**Tool Grades**")
                        st.markdown(grades_text)
                    else:
                        st.markdown("**Arsenal / Command Grades**")
                        st.markdown(grades_text)

                # Popover "cloud" for full write-up
                with st.popover("View full scouting report ✨"):
                    if pd.notna(p.get("prime_skills")) and str(p["prime_skills"]).strip():
                        st.markdown("#### Prime Skills")
                        st.write(p["prime_skills"])

                    if pd.notna(p.get("ranking_explanation")) and str(p["ranking_explanation"]).strip():
                        st.markdown("#### Ranking Explanation")
                        st.write(p["ranking_explanation"])

    if tab == "ADP Profiles":
        # --- Load only what this page needs ---
        adp2026 = load_adp()
        adp = adp2026.copy()

        # =========================
        # BASIC CLEANUP
        # =========================
        adp["Date"] = pd.to_datetime(adp["Date"], errors="coerce")
        adp["DayADP"] = pd.to_numeric(adp["DayADP"], errors="coerce")

        if "$" in adp.columns:
            adp["$"] = pd.to_numeric(adp["$"], errors="coerce")
        else:
            adp["$"] = np.nan

        # Immediately remove November/December drafts
        adp = adp[adp["Date"] >= pd.Timestamp("2026-01-01")].copy()

        # Drop junk rows
        adp["Player"] = adp["Player"].astype(str)
        adp["Format"] = adp["Format"].fillna("UNK").astype(str)
        adp["Team"] = adp["Team"].fillna("")
        adp["Primary Pos"] = adp["Primary Pos"].fillna("UNK")
        adp["Position(s)"] = adp["Position(s)"].fillna(adp["Primary Pos"])
        adp["Month"] = adp["Date"].dt.strftime("%Y-%m")
        adp["DateStr"] = adp["Date"].dt.strftime("%Y-%m-%d")

        adp = adp.dropna(subset=["Date", "Player", "Player ID"]).copy()

        if adp.empty:
            st.warning("No ADP data available after January 1, 2026.")
        else:
            latest_date = adp["Date"].max().normalize()

            # Separate snake drafts from auction drafts
            snake_df = adp[adp["Format"].str.upper() != "AUCTION"].copy()
            auction_df = adp[adp["Format"].str.upper() == "AUCTION"].copy()

            # Need player list from all rows, not just snake
            latest_player_info = (
                adp.sort_values("Date")
                .groupby("Player ID", as_index=False)
                .tail(1)[["Player ID", "Player", "Team", "Primary Pos", "Position(s)", "PitcherRole"]]
                .drop_duplicates(subset=["Player ID"])
                .copy()
            )

            latest_player_info["player_label"] = (
                latest_player_info["Player"]
                + " ("
                + latest_player_info["Team"].fillna("")
                + " - "
                + latest_player_info["Primary Pos"].fillna("")
                + ")"
            )

            latest_player_info = latest_player_info.sort_values(["Player", "Team"]).reset_index(drop=True)

            # =========================
            # PLAYER PICKER AT TOP
            # =========================
            selected_label = st.selectbox(
                "Choose a player",
                options=latest_player_info["player_label"].tolist(),
                index=0
            )

            selected_row = latest_player_info.loc[latest_player_info["player_label"] == selected_label].iloc[0]
            selected_pid = selected_row["Player ID"]
            selected_player = selected_row["Player"]
            selected_team = selected_row["Team"]
            selected_primary_pos = selected_row["Primary Pos"]
            selected_positions = selected_row["Position(s)"]
            selected_pitcher_role = selected_row["PitcherRole"] if "PitcherRole" in selected_row.index else None

            # Separate selected player's snake + auction history
            player_snake = snake_df[snake_df["Player ID"] == selected_pid].copy().sort_values("Date")
            player_auction = auction_df[auction_df["Player ID"] == selected_pid].copy().sort_values("Date")

            st.markdown(f"## {selected_player} ({selected_team} - {selected_primary_pos}) Draft Trend Summary")

            # =========================
            # DATE WINDOWS
            # =========================
            last_3_start = latest_date - pd.Timedelta(days=2)
            last_7_start = latest_date - pd.Timedelta(days=6)
            last_30_start = latest_date - pd.Timedelta(days=29)

            # Snake windows
            s3 = player_snake[(player_snake["Date"] >= last_3_start) & (player_snake["Date"] <= latest_date)].copy()
            s7 = player_snake[(player_snake["Date"] >= last_7_start) & (player_snake["Date"] <= latest_date)].copy()
            s30 = player_snake[(player_snake["Date"] >= last_30_start) & (player_snake["Date"] <= latest_date)].copy()

            # Auction windows
            a3 = player_auction[(player_auction["Date"] >= last_3_start) & (player_auction["Date"] <= latest_date)].copy()
            a7 = player_auction[(player_auction["Date"] >= last_7_start) & (player_auction["Date"] <= latest_date)].copy()
            a30 = player_auction[(player_auction["Date"] >= last_30_start) & (player_auction["Date"] <= latest_date)].copy()

            # =========================
            # HELPERS
            # =========================
            def safe_mean(series):
                s = pd.to_numeric(series, errors="coerce").dropna()
                return s.mean() if len(s) > 0 else np.nan

            def safe_median(series):
                s = pd.to_numeric(series, errors="coerce").dropna()
                return s.median() if len(s) > 0 else np.nan

            def fmt_num(val, digits=1, dollar=False):
                if pd.isna(val):
                    return "—"
                if dollar:
                    return f"${val:,.{digits}f}"
                return f"{val:,.{digits}f}"

            def fmt_signed(val, digits=1, dollar=False):
                if pd.isna(val):
                    return "—"
                if dollar:
                    return f"{val:+,.{digits}f}"
                return f"{val:+,.{digits}f}"

            def metric_card_html(label, value, subtext=None, bg="#f7f7f7", border="#dddddd", color="#111111"):
                html = f"""
                <div style="
                    background:{bg};
                    border:1px solid {border};
                    border-radius:12px;
                    padding:14px 16px;
                    margin-bottom:8px;">
                    <div style="font-size:0.9rem; color:#666; margin-bottom:4px;">{label}</div>
                    <div style="font-size:1.6rem; font-weight:700; color:{color};">{value}</div>
                """
                if subtext:
                    html += f"""<div style="font-size:0.85rem; color:#666; margin-top:4px;">{subtext}</div>"""
                html += "</div>"
                return html

            def movement_html(label, val, mode="adp"):
                if pd.isna(val):
                    return metric_card_html(label, "—", "Not enough data")

                if mode == "adp":
                    # negative ADP delta = player rising (going earlier)
                    is_rising = val < 0
                    display_val = fmt_signed(val, 1, dollar=False)
                else:
                    # positive auction delta = player rising ($ going up)
                    is_rising = val > 0
                    display_val = fmt_signed(val, 1, dollar=True)

                bg = "#e8f5e9" if is_rising else "#ffebee"
                border = "#81c784" if is_rising else "#ef9a9a"
                color = "#1b5e20" if is_rising else "#b71c1c"
                direction = "Rising" if is_rising else "Falling"

                return metric_card_html(
                    label,
                    display_val,
                    f"{direction} vs last 30 days",
                    bg=bg,
                    border=border,
                    color=color
                )

            # =========================
            # SUMMARY NUMBERS
            # =========================
            adp_last7 = safe_mean(s7["DayADP"])
            auc_last7 = safe_mean(a7["$"])

            adp_last3 = safe_mean(s3["DayADP"])
            adp_last30 = safe_mean(s30["DayADP"])
            adp_delta = adp_last3 - adp_last30  # negative = rising

            auc_last3 = safe_mean(a3["$"])
            auc_last30 = safe_mean(a30["$"])
            auc_delta = auc_last3 - auc_last30  # positive = rising

            min_adp = player_snake["DayADP"].min() if not player_snake.empty else np.nan
            max_adp = player_snake["DayADP"].max() if not player_snake.empty else np.nan
            med_adp = safe_median(player_snake["DayADP"])

            first_adp = player_snake.sort_values("Date").iloc[0]["DayADP"] if len(player_snake) else np.nan
            latest_adp = player_snake.sort_values("Date").iloc[-1]["DayADP"] if len(player_snake) else np.nan

            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown(
                    metric_card_html(
                        "Last 7 Days ADP",
                        fmt_num(adp_last7, 1),
                        f"{s7['Date'].nunique()} draft dates"
                    ),
                    unsafe_allow_html=True
                )
            with c2:
                st.markdown(
                    metric_card_html(
                        "Last 7 Days Avg Auction $",
                        fmt_num(auc_last7, 1, dollar=True),
                        f"{a7['Date'].nunique()} auction dates"
                    ),
                    unsafe_allow_html=True
                )
            with c3:
                st.markdown(
                    movement_html("3-Day vs 30-Day ADP", adp_delta, mode="adp"),
                    unsafe_allow_html=True
                )
            with c4:
                st.markdown(
                    movement_html("3-Day vs 30-Day Auction $", auc_delta, mode="auction"),
                    unsafe_allow_html=True
                )

            c5, c6, c7, c8 = st.columns(4)
            with c5:
                st.metric("Median ADP", fmt_num(med_adp, 1))
            with c6:
                st.metric("Best / Earliest ADP", fmt_num(min_adp, 1))
            with c7:
                st.metric("Worst / Latest ADP", fmt_num(max_adp, 1))
            with c8:
                st.metric("First ADP → Latest ADP", f"{fmt_num(first_adp,1)} → {fmt_num(latest_adp,1)}")

            st.divider()

            # =========================
            # ADP TREND PLOT
            # =========================
            st.markdown("### ADP Trend by Date")

            if player_snake.empty:
                st.info("No snake-draft ADP data available for this player.")
            else:
                plot_df = player_snake.copy()

                base = alt.Chart(plot_df).encode(
                    x=alt.X("Date:T", title="Date"),
                    y=alt.Y("DayADP:Q", title="ADP", scale=alt.Scale(reverse=True)),
                    color=alt.Color("Format:N", title="Format"),
                    tooltip=[
                        alt.Tooltip("Player:N"),
                        alt.Tooltip("DateStr:N", title="Date"),
                        alt.Tooltip("Format:N"),
                        alt.Tooltip("DayADP:Q", title="ADP", format=".1f"),
                        alt.Tooltip("DayMin:Q", title="Min Pick", format=".0f"),
                        alt.Tooltip("DayMax:Q", title="Max Pick", format=".0f"),
                    ]
                )

                points = base.mark_circle(size=75, opacity=0.85)

                line = (
                    alt.Chart(
                        plot_df.groupby("Date", as_index=False)["DayADP"].mean()
                    )
                    .mark_line(strokeWidth=2)
                    .encode(
                        x=alt.X("Date:T", title="Date"),
                        y=alt.Y("DayADP:Q", title="ADP", scale=alt.Scale(reverse=True)),
                        tooltip=[
                            alt.Tooltip("Date:T"),
                            alt.Tooltip("DayADP:Q", title="Avg ADP", format=".1f")
                        ]
                    )
                )

                st.altair_chart((line + points).interactive(), use_container_width=True)

            # =========================
            # AUCTION TREND PLOT
            # =========================
            st.markdown("### Auction Value Trend by Date")

            if player_auction.empty:
                st.info("No auction data available for this player.")
            else:
                aplot_df = player_auction.dropna(subset=["$"]).copy()

                if aplot_df.empty:
                    st.info("No auction dollar values available for this player.")
                else:
                    auction_min = aplot_df["$"].min()
                    auction_max = aplot_df["$"].max()

                    y_min = max(0, auction_min - 5)
                    y_max = auction_max + 2

                    auction_points = (
                        alt.Chart(aplot_df)
                        .mark_circle(size=75, opacity=0.85)
                        .encode(
                            x=alt.X("Date:T", title="Date"),
                            y=alt.Y(
                                "$:Q",
                                title="Auction $",
                                scale=alt.Scale(domain=[y_min, y_max], nice=False)
                            ),
                            tooltip=[
                                alt.Tooltip("Player:N"),
                                alt.Tooltip("DateStr:N", title="Date"),
                                alt.Tooltip("$:Q", title="Auction $", format=".1f"),
                            ]
                        )
                    )

                    auction_line = (
                        alt.Chart(
                            aplot_df.groupby("Date", as_index=False)["$"].mean()
                        )
                        .mark_line(strokeWidth=2)
                        .encode(
                            x=alt.X("Date:T", title="Date"),
                            y=alt.Y(
                                "$:Q",
                                title="Auction $",
                                scale=alt.Scale(domain=[y_min, y_max], nice=False)
                            ),
                            tooltip=[
                                alt.Tooltip("Date:T"),
                                alt.Tooltip("$:Q", title="Avg Auction $", format=".1f")
                            ]
                        )
                    )

                    st.altair_chart((auction_line + auction_points).interactive(), use_container_width=True)

            # =========================
            # TABLES: ADP BY MONTH / FORMAT
            # =========================
            st.markdown("### ADP by Month")
            if player_snake.empty:
                st.info("No ADP-by-month data available.")
            else:
                month_summary = (
                    player_snake.groupby("Month", as_index=False)
                    .agg(
                        Avg_ADP=("DayADP", "mean"),
                        Median_ADP=("DayADP", "median"),
                        Best_ADP=("DayADP", "min"),
                        Worst_ADP=("DayADP", "max"),
                        Rows=("DayADP", "size"),
                        Draft_Dates=("Date", "nunique")
                    )
                    .sort_values("Month")
                )

                for col in ["Avg_ADP", "Median_ADP", "Best_ADP", "Worst_ADP"]:
                    month_summary[col] = month_summary[col].round(2)

                st.dataframe(month_summary, use_container_width=True, hide_index=True)

            st.markdown("### ADP by Format")
            if player_snake.empty:
                st.info("No ADP-by-format data available.")
            else:
                format_summary = (
                    player_snake.groupby("Format", as_index=False)
                    .agg(
                        Avg_ADP=("DayADP", "mean"),
                        Median_ADP=("DayADP", "median"),
                        Best_ADP=("DayADP", "min"),
                        Worst_ADP=("DayADP", "max"),
                        Rows=("DayADP", "size"),
                        Draft_Dates=("Date", "nunique")
                    )
                    .sort_values("Avg_ADP")
                )

                for col in ["Avg_ADP", "Median_ADP", "Best_ADP", "Worst_ADP"]:
                    format_summary[col] = format_summary[col].round(2)

                st.dataframe(format_summary, use_container_width=True, hide_index=True)

            # =========================
            # TABLE: AUCTION BY MONTH
            # =========================
            st.markdown("### Auction Values by Month")
            if player_auction.empty:
                st.info("No auction-by-month data available.")
            else:
                auction_month_summary = (
                    player_auction.groupby("Month", as_index=False)
                    .agg(
                        Avg_Auction=("$", "mean"),
                        Median_Auction=("$", "median"),
                        Min_Auction=("$", "min"),
                        Max_Auction=("$", "max"),
                        Rows=("$", "size"),
                        Auction_Dates=("Date", "nunique")
                    )
                    .sort_values("Month")
                )

                for col in ["Avg_Auction", "Median_Auction", "Min_Auction", "Max_Auction"]:
                    auction_month_summary[col] = auction_month_summary[col].round(2)

                st.dataframe(auction_month_summary, use_container_width=True, hide_index=True)

            # =========================
            # SAME POSITION COMPS - LAST 7 DAYS
            # =========================
            st.markdown("### Same-Position Players Going Near Him in the Last 7 Days")

            recent_7_snake = snake_df[(snake_df["Date"] >= last_7_start) & (snake_df["Date"] <= latest_date)].copy()

            comp_pool = (
                recent_7_snake.groupby(["Player ID", "Player", "Team", "Primary Pos", "Position(s)"], as_index=False)
                .agg(
                    ADP_Last7=("DayADP", "mean"),
                    Draft_Dates=("Date", "nunique"),
                    Rows=("DayADP", "size")
                )
            )

            if pd.isna(adp_last7):
                st.info("No last-7-day ADP data available for this player.")
            else:
                comp_pool["adp_gap"] = (comp_pool["ADP_Last7"] - adp_last7).abs()

                same_pos = comp_pool[
                    (comp_pool["Primary Pos"] == selected_primary_pos) &
                    (comp_pool["Player ID"] != selected_pid)
                ].copy()

                same_pos = same_pos.sort_values(["adp_gap", "ADP_Last7"]).head(15)

                if same_pos.empty:
                    st.info("No nearby same-position players found in the last 7 days.")
                else:
                    same_pos["vs_selected"] = same_pos["ADP_Last7"] - adp_last7
                    same_pos["ADP_Last7"] = same_pos["ADP_Last7"].round(2)
                    same_pos["vs_selected"] = same_pos["vs_selected"].round(2)

                    st.dataframe(
                        same_pos[["Player", "Team", "Primary Pos", "ADP_Last7", "vs_selected", "Draft_Dates", "Rows"]],
                        use_container_width=True,
                        hide_index=True
                    )

            # =========================
            # POSITION CONTEXT
            # =========================
            st.markdown("### Position Context in the Last 7 Days")

            if recent_7_snake.empty:
                st.info("No recent position context available.")
            else:
                pos_pool = (
                    recent_7_snake.groupby(["Player ID", "Player", "Primary Pos"], as_index=False)
                    .agg(ADP_Last7=("DayADP", "mean"))
                )

                pos_pool = pos_pool[pos_pool["Primary Pos"] == selected_primary_pos].copy()

                if pos_pool.empty or pd.isna(adp_last7):
                    st.info("No position pool available.")
                else:
                    pos_pool = pos_pool.sort_values("ADP_Last7").reset_index(drop=True)
                    pos_pool["Pos_Rank_Last7"] = np.arange(1, len(pos_pool) + 1)

                    selected_pos_row = pos_pool[pos_pool["Player ID"] == selected_pid].copy()

                    if not selected_pos_row.empty:
                        pos_rank = int(selected_pos_row["Pos_Rank_Last7"].iloc[0])
                        pos_count = len(pos_pool)
                        st.write(
                            f"**{selected_player} is going as the {selected_primary_pos}{pos_rank}** by last-7-day ADP out of **{pos_count}** players at that position."
                        )
                    else:
                        st.write("Position rank not available.")

            # =========================
            # EXTRA: RECENT ADP LOG
            # =========================
            st.markdown("### Recent ADP Log")
            if player_snake.empty:
                st.info("No recent ADP log available.")
            else:
                adp_log_cols = [c for c in ["DateStr", "Format", "DayADP", "DayMin", "DayMax", "L3 ADP", "L5 ADP", "L7 ADP"] if c in player_snake.columns]
                recent_adp_log = player_snake.sort_values(["Date", "Format"], ascending=[False, True])[adp_log_cols].copy()
                recent_adp_log = recent_adp_log.rename(columns={"DateStr": "Date", "DayADP": "ADP"})

                for col in [c for c in recent_adp_log.columns if c not in ["Date", "Format"]]:
                    recent_adp_log[col] = pd.to_numeric(recent_adp_log[col], errors="coerce").round(2)

                st.dataframe(recent_adp_log.head(50), use_container_width=True, hide_index=True)

            # =========================
            # EXTRA: RECENT AUCTION LOG
            # =========================
            st.markdown("### Recent Auction Log")
            if player_auction.empty:
                st.info("No recent auction log available.")
            else:
                auction_log_cols = [c for c in ["DateStr", "Format", "$"] if c in player_auction.columns]
                recent_auction_log = player_auction.sort_values("Date", ascending=False)[auction_log_cols].copy()
                recent_auction_log = recent_auction_log.rename(columns={"DateStr": "Date", "$": "Auction $"})

                if "Auction $" in recent_auction_log.columns:
                    recent_auction_log["Auction $"] = pd.to_numeric(recent_auction_log["Auction $"], errors="coerce").round(2)

                st.dataframe(recent_auction_log.head(50), use_container_width=True, hide_index=True)

    if tab == "Auction Value Calculator":
        # --- Load only what this page needs ---
        ja_hit, ja_pitch, steamerhit, steamerpit, bathit, batpit, atchit, atcpit, oopsyhit, oopsypitch, bat_hitters, bat_pitchers = load_season_projections()
        hitterranks, pitcherranks, fscores_mlb_hit, fscores_milb_hit, fscores_mlb_pitch, fscores_milb_pitch, pitchers_fscores, hitters_fscores, timrank_hitters, timrank_pitchers, posdata = load_rankings()

        # =========================
        # RAW INPUTS (you already added these)
        # =========================
        steamer_h_raw = steamerhit.copy()
        steamer_p_raw = steamerpit.copy()

        ja_h_raw = ja_hit.copy()
        ja_p_raw = ja_pitch.copy()

        bat_h_raw = bathit.copy()
        bat_p_raw = batpit.copy()

        atc_h_raw = atchit.copy()
        atc_p_raw = atcpit.copy()

        oopsy_h_raw = oopsyhit.copy()
        oopsy_p_raw = oopsypitch.copy()

        atc_holds = atc_p_raw[['MLBAMID','HLD']]
        atc_holds_dict = dict(zip(atc_holds.MLBAMID,atc_holds.HLD))

        atc_saves = atc_p_raw[['MLBAMID','SV']]
        atc_saves_dict = dict(zip(atc_saves.MLBAMID,atc_saves.SV))

        ja_p_raw['HLD'] = ja_p_raw['SAVID'].map(atc_holds_dict)
        ja_p_raw['SV'] = ja_p_raw['SAVID'].map(atc_saves_dict)

        ja_p_raw['SV+HLD'] = ja_p_raw['SV'] + ja_p_raw['HLD']
        steamer_p_raw['SV+HLD'] = steamer_p_raw['SV'] + steamer_p_raw['HLD']
        bat_p_raw['SV+HLD'] = bat_p_raw['SV'] + bat_p_raw['HLD']
        atc_p_raw['SV+HLD'] = atc_p_raw['SV'] + atc_p_raw['HLD']
        oopsy_p_raw['SV+HLD'] = oopsy_p_raw['SV'] + oopsy_p_raw['HLD']

        pos_dict = dict(zip(posdata.ID,posdata.Pos))
        steamer_h_raw['Pos'] = steamer_h_raw['MLBAMID'].map(pos_dict)
        bat_h_raw['Pos'] = bat_h_raw['MLBAMID'].map(pos_dict)
        atc_h_raw['Pos'] = atc_h_raw['MLBAMID'].map(pos_dict)
        oopsy_h_raw['Pos'] = oopsy_h_raw['MLBAMID'].map(pos_dict)

        # NOTE: assumes you have these dataframes loaded elsewhere (same pattern as others):
        #   oopsy_h_raw = oopsyhit.copy()
        #   oopsy_p_raw = oopsypitch.copy()
        # If your variable names differ, just swap them below.

        # =========================
        # HELPERS
        # =========================
        def _safe_col(df, col, default=np.nan):
            return df[col] if col in df.columns else default

        def _first_present(df: pd.DataFrame, candidates: list[str]):
            for c in candidates:
                if c in df.columns:
                    return c
            return None

        def _rename_first_present(df: pd.DataFrame, candidates: list[str], to: str):
            c = _first_present(df, candidates)
            if c is not None and c != to:
                df.rename(columns={c: to}, inplace=True)

        def _coerce_numeric_cols(df: pd.DataFrame, cols: list[str]) -> None:
            for c in cols:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors="coerce")

        def _standardize_hitters(df: pd.DataFrame, system: str) -> pd.DataFrame:
            """
            Standard output columns:
            Name, Team, Pos, PA, AB, R, HR, RBI, SB, AVG, OBP, SLG, OPS, H, BB, HBP, SF
            """
            d = df.copy()

            # --- Name / Team / Pos ---
            if system == "JA":
                _rename_first_present(d, ["Player", "Name", "NameASCII", "player_name"], "Name")
            else:
                _rename_first_present(d, ["Name", "Player", "NameASCII", "player_name", "PlayerName"], "Name")

            _rename_first_present(d, ["Team", "Tm", "team", "MLB Team"], "Team")
            _rename_first_present(d, ["Pos", "POS", "Position", "Positions", "Position(s)"], "Pos")

            if "Pos" not in d.columns:
                d["Pos"] = "UTIL"

            # --- Core counting stats ---
            # These are usually consistent across systems, but we still guard them.
            for c in ["PA", "AB", "R", "HR", "RBI", "SB", "H", "BB", "HBP", "SF"]:
                if c not in d.columns:
                    d[c] = np.nan

            # --- Rate stats ---
            for c in ["AVG", "OBP", "SLG", "OPS"]:
                if c not in d.columns:
                    d[c] = np.nan

            # Common alternates some files use
            # (Only fill if the standard col is missing/empty)
            if d["AVG"].isna().all():
                alt = _first_present(d, ["BA", "AVG_"])
                if alt:
                    d["AVG"] = pd.to_numeric(d[alt], errors="coerce")

            if d["OBP"].isna().all():
                alt = _first_present(d, ["OBP_"])
                if alt:
                    d["OBP"] = pd.to_numeric(d[alt], errors="coerce")

            if d["SLG"].isna().all():
                alt = _first_present(d, ["SLG_"])
                if alt:
                    d["SLG"] = pd.to_numeric(d[alt], errors="coerce")

            # OPS: compute if missing but OBP/SLG available
            if d["OPS"].isna().all() and (not d["OBP"].isna().all()) and (not d["SLG"].isna().all()):
                d["OPS"] = pd.to_numeric(d["OBP"], errors="coerce") + pd.to_numeric(d["SLG"], errors="coerce")

            # Build AB if still missing but PA exists (rough fallback)
            if d["AB"].isna().all() and (not d["PA"].isna().all()):
                d["AB"] = np.where(pd.to_numeric(d["PA"], errors="coerce").notna(), (pd.to_numeric(d["PA"], errors="coerce") * 0.86), np.nan)

            # --- Cleanup / types ---
            d = d.dropna(subset=["Name"]).copy()
            d["Team"] = d["Team"].fillna("")
            d["Pos"] = d["Pos"].fillna("UTIL")

            _coerce_numeric_cols(d, ["PA", "AB", "R", "HR", "RBI", "SB", "AVG", "OBP", "SLG", "OPS", "H", "BB", "HBP", "SF"])

            d = d[d["PA"].fillna(0) > 0].copy()
            return d

        def _standardize_pitchers(df: pd.DataFrame, system: str) -> pd.DataFrame:
            """
            Standard output columns:
            Name, Team, Pos, GS, IP, W, SV, ERA, WHIP, SO, BB, K/9, BB/9
            """
            d = df.copy()

            # --- Name / Team ---
            if system == "JA":
                _rename_first_present(d, ["Pitcher", "Name", "NameASCII", "player_name"], "Name")
            else:
                _rename_first_present(d, ["Name", "Pitcher", "NameASCII", "player_name", "PlayerName"], "Name")

            _rename_first_present(d, ["Team", "Tm", "team", "MLB Team"], "Team")

            # --- Normalize SO/K and core cols ---
            # Some sets use K instead of SO
            if "SO" not in d.columns and "K" in d.columns:
                d["SO"] = d["K"]
            if "SO" not in d.columns:
                # sometimes "SO" is "SO_" etc
                alt = _first_present(d, ["SO_", "Ks", "KSO"])
                if alt:
                    d["SO"] = d[alt]
                else:
                    d["SO"] = np.nan

            # Ensure core columns exist
            for c in ["GS", "IP", "W", "SV", "ERA", "WHIP", "SO", "BB"]:
                if c not in d.columns:
                    d[c] = np.nan

            # Infer Pos (SP/RP) by GS if not provided
            if "Pos" not in d.columns:
                gs = pd.to_numeric(_safe_col(d, "GS", 0), errors="coerce").fillna(0)
                d["Pos"] = np.where(gs > 0, "SP", "RP")
            else:
                d["Pos"] = d["Pos"].fillna("P")

            # Compute K/9 and BB/9 if missing
            d["IP"] = pd.to_numeric(_safe_col(d, "IP", np.nan), errors="coerce")
            d["BB"] = pd.to_numeric(_safe_col(d, "BB", np.nan), errors="coerce")
            d["SO"] = pd.to_numeric(_safe_col(d, "SO", np.nan), errors="coerce")

            if "K/9" not in d.columns:
                d["K/9"] = np.where(d["IP"].fillna(0) > 0, (d["SO"] * 9) / d["IP"], np.nan)
            if "BB/9" not in d.columns:
                d["BB/9"] = np.where(d["IP"].fillna(0) > 0, (d["BB"] * 9) / d["IP"], np.nan)

            # Final type coercion
            d = d.dropna(subset=["Name"]).copy()
            d["Team"] = d["Team"].fillna("")
            d["Pos"] = d["Pos"].fillna("P")

            _coerce_numeric_cols(d, ["GS", "IP", "W", "SV", "ERA", "WHIP", "SO", "BB", "K/9", "BB/9"])

            d = d[d["IP"].fillna(0) > 0].copy()
            return d

        def _parse_roster_string(roster_str: str) -> list[str]:
            parts = [p.strip().upper() for p in roster_str.split(",") if p.strip()]
            return parts

        def _is_pitch_slot(slot: str) -> bool:
            slot = slot.upper().strip()
            return slot in {"SP", "RP", "P"}

        def _compute_marginal_hit_rate(df: pd.DataFrame, rate_col: str) -> pd.Series:
            """
            Convert a rate stat into a counting-like contribution using playing time.
            AVG/SLG use AB if present; OBP/OPS use PA.
            """
            rate = pd.to_numeric(df[rate_col], errors="coerce")

            if rate_col in {"AVG", "SLG"}:
                denom = pd.to_numeric(df["AB"], errors="coerce")
            else:
                denom = pd.to_numeric(df["PA"], errors="coerce")

            denom = denom.fillna(0)
            if denom.sum() > 0:
                lg_rate = np.nansum(rate * denom) / np.nansum(denom)
            else:
                lg_rate = np.nanmean(rate)

            return (rate - lg_rate) * denom

        def _compute_marginal_pitch_rate(df: pd.DataFrame, rate_col: str) -> pd.Series:
            """
            Convert a rate stat into a counting-like contribution.
            Lower-is-better for ERA/WHIP/BB9; higher-is-better for K9.
            """
            ip = pd.to_numeric(df["IP"], errors="coerce").fillna(0)
            r = pd.to_numeric(df[rate_col], errors="coerce")

            if rate_col in {"ERA", "WHIP"}:
                lg = np.nansum(r * ip) / np.nansum(ip) if ip.sum() > 0 else np.nanmean(r)
                return (lg - r) * ip  # better (lower) => positive

            if rate_col == "BB/9":
                w = ip / 9.0
                lg = np.nansum(r * w) / np.nansum(w) if w.sum() > 0 else np.nanmean(r)
                return (lg - r) * w

            if rate_col == "K/9":
                w = ip / 9.0
                lg = np.nansum(r * w) / np.nansum(w) if w.sum() > 0 else np.nanmean(r)
                return (r - lg) * w  # better (higher) => positive

            return r

        def _zscore(series: pd.Series) -> pd.Series:
            s = pd.to_numeric(series, errors="coerce")
            mu = np.nanmean(s)
            sd = np.nanstd(s)
            if not np.isfinite(sd) or sd == 0:
                sd = 1.0
            return (s - mu) / sd

        def _auction_values(
            hitters: pd.DataFrame,
            pitchers: pd.DataFrame,
            hit_cats: list[str],
            pit_cats: list[str],
            roster_slots: list[str],
            teams: int,
            budget_per_team: int,
            hitter_pct: float,
        ):
            # How many total players are expected to be drafted (starters only)
            total_slots = len(roster_slots) * teams
            n_hit = int(round(total_slots * hitter_pct))
            n_pit = total_slots - n_hit

            total_budget = teams * budget_per_team
            hit_budget = total_budget * hitter_pct
            pit_budget = total_budget - hit_budget

            # --- Build category matrices (with proper handling for rate cats) ---
            hit_df = hitters.copy()
            pit_df = pitchers.copy()

            hit_feat = {}
            for c in hit_cats:
                if c in {"AVG", "OBP", "SLG", "OPS"}:
                    hit_feat[c] = _compute_marginal_hit_rate(hit_df, c)
                else:
                    hit_feat[c] = pd.to_numeric(hit_df[c], errors="coerce") if c in hit_df.columns else np.nan

            pit_feat = {}
            for c in pit_cats:
                if c in {"ERA", "WHIP", "K/9", "BB/9"}:
                    pit_feat[c] = _compute_marginal_pitch_rate(pit_df, c)
                else:
                    pit_feat[c] = pd.to_numeric(pit_df[c], errors="coerce") if c in pit_df.columns else np.nan

            # --- First pass z-scores to identify the drafted pool ---
            for c, v in hit_feat.items():
                hit_df[f"z_{c}"] = _zscore(v)
            hit_df["z_total_pre"] = hit_df[[f"z_{c}" for c in hit_cats]].sum(axis=1)

            for c, v in pit_feat.items():
                pit_df[f"z_{c}"] = _zscore(v)
            pit_df["z_total_pre"] = pit_df[[f"z_{c}" for c in pit_cats]].sum(axis=1)

            hit_pool = hit_df.sort_values("z_total_pre", ascending=False).head(n_hit).copy()
            pit_pool = pit_df.sort_values("z_total_pre", ascending=False).head(n_pit).copy()

            # --- Second pass: recompute z within drafted pool (closer to FG behavior) ---
            for c in hit_cats:
                if c in {"AVG", "OBP", "SLG", "OPS"}:
                    vals = _compute_marginal_hit_rate(hit_pool, c)
                else:
                    vals = pd.to_numeric(hit_pool[c], errors="coerce") if c in hit_pool.columns else np.nan
                hit_pool[f"z_{c}"] = _zscore(vals)
            hit_pool["z_total"] = hit_pool[[f"z_{c}" for c in hit_cats]].sum(axis=1)

            for c in pit_cats:
                if c in {"ERA", "WHIP", "K/9", "BB/9"}:
                    vals = _compute_marginal_pitch_rate(pit_pool, c)
                else:
                    vals = pd.to_numeric(pit_pool[c], errors="coerce") if c in pit_pool.columns else np.nan
                pit_pool[f"z_{c}"] = _zscore(vals)
            pit_pool["z_total"] = pit_pool[[f"z_{c}" for c in pit_cats]].sum(axis=1)

            # Replacement baselines: last drafted at each pool
            hit_rep = hit_pool["z_total"].min()
            pit_rep = pit_pool["z_total"].min()

            hit_pool["AAR"] = (hit_pool["z_total"] - hit_rep).clip(lower=0)
            pit_pool["AAR"] = (pit_pool["z_total"] - pit_rep).clip(lower=0)

            # Dollar allocation (optionally $1 floor)
            def allocate(pool: pd.DataFrame, pool_budget: float, n: int) -> pd.DataFrame:
                out = pool.copy()
                if pool_budget >= n:
                    floor = 1.0
                    rem = pool_budget - (floor * n)
                    aar_sum = out["AAR"].sum()
                    if aar_sum > 0 and rem > 0:
                        out["$"] = floor + (out["AAR"] / aar_sum) * rem
                    else:
                        out["$"] = floor
                else:
                    aar_sum = out["AAR"].sum()
                    if aar_sum > 0:
                        out["$"] = (out["AAR"] / aar_sum) * pool_budget
                    else:
                        out["$"] = pool_budget / max(n, 1)
                out["$"] = out["$"].round(1)
                return out

            hit_vals = allocate(hit_pool, hit_budget, n_hit)
            pit_vals = allocate(pit_pool, pit_budget, n_pit)

            return hit_vals, pit_vals, {
                "teams": teams,
                "budget_per_team": budget_per_team,
                "total_budget": total_budget,
                "hitter_pct": hitter_pct,
                "hit_budget": hit_budget,
                "pit_budget": pit_budget,
                "slots_per_team": len(roster_slots),
                "total_drafted": total_slots,
                "drafted_hitters": n_hit,
                "drafted_pitchers": n_pit,
            }

        # =========================
        # UI
        # =========================
        st.subheader("Auction Value Calculator")

        left, right = st.columns([1, 1], gap="large")

        with left:
            proj_system = st.radio(
                "Projection system",
                ["JA", "Steamer", "THE BAT", "ATC", "OOPSY"],
                index=0,
                horizontal=True,
                help="Choose the projection set used to calculate auction values.",
            )

            roster_default = (
                "C, 1B, 2B, 3B, SS, 1B/3B, 2B/SS, "
                "OF, OF, OF, OF, OF, UTIL, UTIL, "
                "SP, SP, SP, SP, SP, SP, RP, RP, RP"
            )
            roster_str = st.text_area(
                "Starting lineup slots (comma-separated)",
                value=roster_default,
                height=90,
                help="Use SP/RP for pitchers. Anything else is treated as hitter/UTIL.",
            )
            roster_slots = _parse_roster_string(roster_str)

            teams = st.number_input("Teams", min_value=4, max_value=30, value=12, step=1)
            budget_per_team = st.number_input("Budget per team ($)", min_value=50, max_value=1000, value=260, step=10)

            hitter_pct = st.slider(
                "Drafted player split: % hitters",
                min_value=0.40,
                max_value=0.80,
                value=0.60,
                step=0.01,
            )
            st.caption(f"Pitchers: {int(round((1 - hitter_pct) * 100))}%")

        # =========================
        # Load & standardize per selection
        # =========================
        if proj_system == "JA":
            hitters = _standardize_hitters(ja_h_raw, "JA")
            pitchers = _standardize_pitchers(ja_p_raw, "JA")
        elif proj_system == "Steamer":
            hitters = _standardize_hitters(steamer_h_raw, "Steamer")
            pitchers = _standardize_pitchers(steamer_p_raw, "Steamer")
        elif proj_system == "THE BAT":
            hitters = _standardize_hitters(bat_h_raw, "THE BAT")
            pitchers = _standardize_pitchers(bat_p_raw, "THE BAT")
        elif proj_system == "ATC":
            hitters = _standardize_hitters(atc_h_raw, "ATC")
            pitchers = _standardize_pitchers(atc_p_raw, "ATC")
        else:  # OOPSY
            hitters = _standardize_hitters(oopsy_h_raw, "OOPSY")
            pitchers = _standardize_pitchers(oopsy_p_raw, "OOPSY")

        # =========================
        # Category pickers + preview
        # =========================
        with right:
            st.markdown("### League categories")

            hit_default = ["R", "HR", "RBI", "SB", "AVG"]  # common 5x5 hitters
            pit_default = ["W", "SV", "ERA", "WHIP", "SO"]  # common 5x5 pitchers

            hit_all = ["R", "HR", "RBI", "SB", "AVG", "OBP", "SLG", "OPS", "PA"]
            pit_all = ["W","L", "SV", "ERA", "WHIP", "SO", "K/9", "BB/9", "IP", "GS", "HLD","SV+HLD","QS"]

            hit_cats = st.multiselect("Hitting categories", hit_all, default=hit_default)
            pit_cats = st.multiselect("Pitching categories", pit_all, default=pit_default)

            st.markdown("### Projection table view")
            show_side = st.radio("Show", ["Hitters", "Pitchers"], index=0, horizontal=True)

            show_hit_cols = ["Name", "Team", "Pos", "PA", "R", "HR", "RBI", "SB", "AVG", "OBP", "SLG", "OPS"]
            show_pit_cols = ["Name", "Team", "Pos", "GS", "IP", "W","L", "SV", "ERA", "WHIP", "SO", "K/9", "BB/9","HLD","SV+HLD","QS"]

            if show_side == "Hitters":
                cols = [c for c in show_hit_cols if c in hitters.columns]
                st.dataframe(hitters[cols].sort_values("PA", ascending=False), use_container_width=True, height=420)
            else:
                cols = [c for c in show_pit_cols if c in pitchers.columns]
                st.dataframe(pitchers[cols].sort_values("IP", ascending=False), use_container_width=True, height=420)

        # =========================
        # RUN CALC
        # =========================
        st.divider()
        c1, c2 = st.columns([1, 3], gap="large")

        with c1:
            run = st.button("Run Auction Values", type="primary", use_container_width=True)

        with c2:
            pit_slots = sum(_is_pitch_slot(s) for s in roster_slots)
            hit_slots = len(roster_slots) - pit_slots
            st.caption(
                f"Slots per team: **{len(roster_slots)}** "
                f"(Hit: **{hit_slots}**, Pitch: **{pit_slots}**) • "
                f"Total drafted (starters): **{len(roster_slots) * int(teams)}**"
            )

        if run:
            if len(hit_cats) == 0 or len(pit_cats) == 0:
                st.error("Please select at least one hitting category and one pitching category.")
            else:
                hit_vals, pit_vals, meta = _auction_values(
                    hitters=hitters,
                    pitchers=pitchers,
                    hit_cats=hit_cats,
                    pit_cats=pit_cats,
                    roster_slots=roster_slots,
                    teams=int(teams),
                    budget_per_team=int(budget_per_team),
                    hitter_pct=float(hitter_pct),
                )

                st.success("Auction values calculated.")

                # Summary metrics
                s1, s2, s3, s4 = st.columns(4)
                s1.metric("Total Budget", f"${meta['total_budget']:.0f}")
                s2.metric("Hitter Budget", f"${meta['hit_budget']:.0f}")
                s3.metric("Pitcher Budget", f"${meta['pit_budget']:.0f}")
                s4.metric("Drafted Players", f"{meta['total_drafted']}")

                # Combine + display
                hit_out_cols = ["Name", "Team", "Pos", "$"] + [c for c in ["PA", "R", "HR", "RBI", "SB", "AVG", "OBP", "SLG", "OPS"] if c in hit_vals.columns]
                pit_out_cols = ["Name", "Team", "Pos", "$"] + [c for c in ["GS", "IP", "W","L", "SV", "ERA", "WHIP", "SO", "K/9", "BB/9","HLD","SV+HLD","QS"] if c in pit_vals.columns]

                st.markdown("### Top Auction Values — Hitters")
                st.dataframe(hit_vals[hit_out_cols].sort_values("$", ascending=False).reset_index(drop=True), use_container_width=True, height=420)

                st.markdown("### Top Auction Values — Pitchers")
                st.dataframe(pit_vals[pit_out_cols].sort_values("$", ascending=False).reset_index(drop=True), use_container_width=True, height=420)

                combined = pd.concat(
                    [
                        hit_vals.assign(Side="Hitter")[["Side"] + hit_out_cols],
                        pit_vals.assign(Side="Pitcher")[["Side"] + pit_out_cols],
                    ],
                    ignore_index=True,
                ).sort_values(["Side", "$"], ascending=[True, False])

                st.download_button(
                    f"Download auction values (CSV) — {proj_system}",
                    data=combined.to_csv(index=False).encode("utf-8"),
                    file_name=f"auction_values_{proj_system.lower().replace(' ', '_')}_2026.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

                with st.expander("How this is being calculated (quick)"):
                    st.markdown(
                        """
                        - Counting categories use **z-scores** directly (higher = better).
                        - Rate categories are converted to counting-like **marginal contributions** using playing time:
                        - Hitters: `(player_rate - league_rate) * PA` (OBP/OPS) or `* AB` (AVG/SLG).
                        - Pitchers: `(league_rate - player_rate) * IP` for ERA/WHIP; K/9 and BB/9 use IP/9 weighting.
                        - We identify the drafted pool, then recompute z-scores **within the drafted pool**.
                        - Dollar values are distributed by **above-replacement** total z-score, with a **$1 floor** when possible.
                        """.strip()
                    )

    if tab == "2026 Projections":
        # --- Load only what this page needs ---
        hitterproj_raw, pitcherproj_raw, hitterproj2, gameinfo_raw = load_daily_projections()
        hitter_stats_raw, lineup_stats, pitcher_stats, h_vs_avg, p_vs_avg, h_vs_sim, hotzonedata, posdata = load_player_stats()
        bpreport_raw, rpstats = load_bullpen_data()
        umpire_data, weather_data = load_weather_umps()
        props_df, ownershipdf, allbets, alllines, bet_tracker = load_betting_data()
        airpulldata = load_airpull()
        trend_h, trend_p = load_trends()
        # Season projections (Steamer, ATC, TheBat, JA, OOPSY) — needed for the projection comparison table
        ja_hit, ja_pitch, steamerhit, steamerpit, bathit, batpit, atchit, atcpit, oopsyhit, oopsypitch, bat_hitters_raw, bat_pitchers_raw = load_season_projections()
        # ADP needed for pos_data lookup
        adp2026 = load_adp()
        if len(weather_data) < 1:
            weather_data = pd.DataFrame()
        team_vs_sim = h_vs_sim[h_vs_sim['PC'] > 49].groupby('Team', as_index=False)[['xwOBA','SwStr%','AVG','SLG','Brl%','FB%']].mean()
        team_vs_sim['RawRank'] = len(team_vs_sim) - team_vs_sim['xwOBA'].rank() + 1
        team_vs_sim['Rank'] = team_vs_sim['RawRank'].astype(int).astype(str) + '/' + str(len(team_vs_sim))
        (hitterproj, pitcherproj, hitter_stats, gameinfo, bpreport,
         games_df, mainslateteams, main_slate_gamelist,
         confirmed_lus, last_update) = _prepare_projection_data(
            hitterproj_raw, pitcherproj_raw, hitterproj2, gameinfo_raw,
            hitter_stats_raw, h_vs_avg, bpreport_raw)
        propsdf = props_df

        # =========================
        # ===== DEBUG (optional) ===
        # =========================
        # st.write(oopsyhit)
        # st.write(oopsypitch)

        # === POSITION DATA ===
        pos_data = adp2026[["Player", "Player ID", "Position(s)"]].drop_duplicates()

        # =========================
        # ===== SRV FUNCTIONS =====
        # =========================
        def calculateSRV_Hitters(hitdf: pd.DataFrame, merge_df: pd.DataFrame | None = None):
            df = hitdf.copy()

            count_cats = ["R", "HR", "RBI", "SB"]
            for cat in count_cats:
                std = df[cat].std(ddof=0)
                df[f"{cat}_z"] = (df[cat] - df[cat].mean()) / (std if std != 0 else 1.0)

            total_ab = df["AB"].sum() if "AB" in df.columns else 0
            if "AVG" in df.columns and "AB" in df.columns and total_ab:
                lg_avg = np.divide((df["AVG"] * df["AB"]).sum(), total_ab)
            else:
                lg_avg = df["AVG"].mean() if "AVG" in df.columns else 0.0

            if "AVG" in df.columns and "AB" in df.columns:
                df["AVG_contrib"] = (df["AVG"] - lg_avg) * df["AB"]
            else:
                df["AVG_contrib"] = 0.0

            std = df["AVG_contrib"].std(ddof=0)
            df["AVG_z"] = (df["AVG_contrib"] - df["AVG_contrib"].mean()) / (std if std != 0 else 1.0)

            z_cols = [f"{c}_z" for c in count_cats] + ["AVG_z"]
            df["SRV"] = df[z_cols].sum(axis=1)

            base_cols = ["Player", "Team", "SRV"] + z_cols
            if "player_id" in df.columns:
                base_cols.insert(1, "player_id")

            df_sorted = df[base_cols].sort_values("SRV", ascending=False).reset_index(drop=True)

            if merge_df is not None:
                out = merge_df.merge(
                    df_sorted[[c for c in ["Player", "Team", "SRV", "player_id"] if c in df_sorted.columns]],
                    on=[c for c in ["Player", "Team"] if c in merge_df.columns],
                    how="left",
                )
                out["SRV"] = out["SRV"].round(2)
                return out.sort_values("SRV", ascending=False)

            return df_sorted

        def calculateSRV_Pitchers(pitchdf: pd.DataFrame, merge_df: pd.DataFrame | None = None):
            df = pitchdf.copy()

            count_cats = ["W", "SV", "SO"]
            for cat in count_cats:
                std = df[cat].std(ddof=0)
                df[f"{cat}_z"] = (df[cat] - df[cat].mean()) / (std if std != 0 else 1.0)

            ip_sum = df["IP"].sum() if "IP" in df.columns else 0.0

            lg_era = np.divide((df["ERA"] * df["IP"]).sum(), ip_sum) if ip_sum else (df["ERA"].mean() if "ERA" in df.columns else 0.0)
            df["ERA_contrib"] = (lg_era - df["ERA"]) * df["IP"] if all(c in df.columns for c in ["ERA", "IP"]) else 0.0
            std = df["ERA_contrib"].std(ddof=0)
            df["ERA_z"] = (df["ERA_contrib"] - df["ERA_contrib"].mean()) / (std if std != 0 else 1.0)

            lg_whip = np.divide((df["WHIP"] * df["IP"]).sum(), ip_sum) if ip_sum else (df["WHIP"].mean() if "WHIP" in df.columns else 0.0)
            df["WHIP_contrib"] = (lg_whip - df["WHIP"]) * df["IP"] if all(c in df.columns for c in ["WHIP", "IP"]) else 0.0
            std = df["WHIP_contrib"].std(ddof=0)
            df["WHIP_z"] = (df["WHIP_contrib"] - df["WHIP_contrib"].mean()) / (std if std != 0 else 1.0)

            z_cols = [f"{c}_z" for c in count_cats] + ["ERA_z", "WHIP_z"]
            df["SRV"] = df[z_cols].sum(axis=1)

            base_cols = ["Player", "Team", "SRV"] + z_cols
            if "player_id" in df.columns:
                base_cols.insert(1, "player_id")

            df_sorted = df[base_cols].sort_values("SRV", ascending=False).reset_index(drop=True)

            if merge_df is not None:
                out = merge_df.merge(
                    df_sorted[[c for c in ["Player", "Team", "SRV", "player_id"] if c in df_sorted.columns]],
                    on=[c for c in ["Player", "Team"] if c in merge_df.columns],
                    how="left",
                )
                out["SRV"] = out["SRV"].round(2)
                return out.sort_values("SRV", ascending=False)

            return df_sorted

        # =========================
        # ===== PER-600 HELPER =====
        # =========================
        def to_per_600_pa(df: pd.DataFrame) -> pd.DataFrame:
            """
            Scales hitter counting stats to a 600 PA basis, preserving rate.
            Only touches: PA, R, HR, RBI, SB (and AB if present).
            AVG/OBP/SLG/OPS/K%/BB% remain unchanged (rates).
            """
            out = df.copy()
            if "PA" not in out.columns:
                return out

            pa = pd.to_numeric(out["PA"], errors="coerce").fillna(0.0)
            scale = np.where(pa > 0, 600.0 / pa, 0.0)

            for c in ["R", "HR", "RBI", "SB"]:
                if c in out.columns:
                    out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0.0) * scale

            if "AB" in out.columns:
                out["AB"] = pd.to_numeric(out["AB"], errors="coerce").fillna(0.0) * scale

            out["PA"] = 600.0
            return out

        # =========================
        # ===== POINTS HELPERS =====
        # =========================
        UNDERDOG_H = {
            "1B": 3.0, "2B": 6.0, "3B": 8.0, "HR": 10.0,
            "SB": 4.0, "CS": 0.0,
            "BB": 3.0, "HBP": 3.0, "SO": 0.0,
            "R": 2.0, "RBI": 2.0,
        }
        UNDERDOG_P = {
            "IP": 3.0, "SO": 3.0,
            "BB": 0.0, "HBP": 0.0, "HR": 0.0, "L":0,
            "W": 5.0, "SV": 0.0, "QS": 5.0, "HLD": 0.0,
            "ER": -3.0,
        }

        DRAFTKINGS_H = {
            "1B": 3.0, "2B": 5.0, "3B": 8.0, "HR": 10.0,
            "SB": 5.0, "CS": 0.0,
            "BB": 2.0, "HBP": 2.0, "SO": 0.0,
            "R": 2.0, "RBI": 2.0,
        }
        DRAFTKINGS_P = {
            "IP": 2.25, "SO": 2.0,
            "BB": -0.6, "HBP": -0.6, "HR": 0.0,
            "W": 4.0, "SV": 0.0, "QS": 0.0, "HLD": 0.0,
            "ER": -2.0, "L":0,
            # DK extras (only apply if present)
            "H": -0.6, "CG": 2.5, "CGSO": 2.5, "NH": 5.0,
        }

        HITTER_CUSTOM_CATS = ["1B", "2B", "3B", "HR", "SB", "CS", "BB", "HBP", "SO", "R", "RBI"]
        #PITCHER_CUSTOM_CATS = ["IP", "SO", "BB", "HBP", "HR", "W","L", "SV", "QS", "HLD", "ER"]
        PITCHER_CUSTOM_CATS = ["IP", "SO", "H", "BB", "HBP", "HR", "W", "L", "SV", "QS", "HLD", "ER"]

        def _num(s):
            return pd.to_numeric(s, errors="coerce").fillna(0.0)

        def _ensure_event_cols_hitters(df: pd.DataFrame) -> pd.DataFrame:
            """
            Best-effort create:
            1B,2B,3B,HR,SB,CS,BB,HBP,SO,R,RBI
            """
            out = df.copy()

            # BB from BB%*PA if BB missing
            if "BB" not in out.columns:
                if "BB%" in out.columns and "PA" in out.columns:
                    out["BB"] = _num(out["BB%"]) * _num(out["PA"])
                else:
                    out["BB"] = 0.0

            # SO from SO or K or K%*PA
            if "SO" not in out.columns:
                if "K" in out.columns:
                    out["SO"] = _num(out["K"])
                elif "K%" in out.columns and "PA" in out.columns:
                    out["SO"] = _num(out["K%"]) * _num(out["PA"])
                else:
                    out["SO"] = 0.0

            # Defaults
            for c in ["HBP", "CS"]:
                if c not in out.columns:
                    out[c] = 0.0

            # Derive 1B if possible
            if "1B" not in out.columns:
                if all(c in out.columns for c in ["H", "2B", "3B", "HR"]):
                    out["1B"] = _num(out["H"]) - _num(out["2B"]) - _num(out["3B"]) - _num(out["HR"])
                else:
                    out["1B"] = 0.0

            # Ensure exist
            for c in ["2B", "3B", "HR", "R", "RBI", "SB"]:
                if c not in out.columns:
                    out[c] = 0.0

            out["1B"] = np.maximum(_num(out["1B"]), 0.0)
            return out

        def _ensure_event_cols_pitchers(df: pd.DataFrame) -> pd.DataFrame:
            """
            Best-effort create:
            IP, SO, H, BB, HBP, HR, W, L, SV, QS, HLD, ER
            from either direct count columns OR common rate columns.
            """
            out = df.copy()

            # ---- Normalize a few common alt column names ----
            rename_map = {}
            if "SO" in out.columns and "K" not in out.columns:
                rename_map["SO"] = "K"
            if "HD" in out.columns and "HLD" not in out.columns:
                rename_map["HD"] = "HLD"
            if "Holds" in out.columns and "HLD" not in out.columns:
                rename_map["Holds"] = "HLD"
            if rename_map:
                out = out.rename(columns=rename_map)

            # ---- Ensure IP exists early (needed for /9 derivations) ----
            if "IP" not in out.columns:
                out["IP"] = 0.0
            ip = _num(out["IP"])

            # ---- Strikeouts -> SO ----
            if "SO" not in out.columns:
                if "K" in out.columns:
                    out["SO"] = _num(out["K"])
                else:
                    out["SO"] = 0.0

            # ---- Hits allowed ----
            if "H" not in out.columns:
                out["H"] = 0.0

            # ---- Walks ----
            if "BB" not in out.columns:
                if "BB/9" in out.columns:
                    out["BB"] = _num(out["BB/9"]) * ip / 9.0
                else:
                    out["BB"] = 0.0

            # ---- HBP ----
            if "HBP" not in out.columns:
                # some sources use HB
                if "HB" in out.columns:
                    out["HBP"] = _num(out["HB"])
                else:
                    # try rate variants
                    rate_col = None
                    for cand in ["HBP/9", "HBP9", "HB/9", "HB9"]:
                        if cand in out.columns:
                            rate_col = cand
                            break
                    out["HBP"] = (_num(out[rate_col]) * ip / 9.0) if rate_col else 0.0

            # ---- HR allowed ----
            if "HR" not in out.columns:
                rate_col = None
                for cand in ["HR/9", "HR9"]:
                    if cand in out.columns:
                        rate_col = cand
                        break
                out["HR"] = (_num(out[rate_col]) * ip / 9.0) if rate_col else 0.0

            # ---- Basic counting stats ----
            for c in ["W", "L", "SV", "QS", "HLD", "ER"]:
                if c not in out.columns:
                    out[c] = 0.0

            # DK extras (optional)
            for c in ["CG", "CGSO", "NH"]:
                if c not in out.columns:
                    out[c] = 0.0

            return out

        def _get_scoring_dict(group: str, system: str) -> dict:
            if system == "Underdog":
                return UNDERDOG_H if group == "Hitters" else UNDERDOG_P
            if system == "DraftKings":
                return DRAFTKINGS_H if group == "Hitters" else DRAFTKINGS_P

            # Custom
            if group == "Hitters":
                return st.session_state.get("custom_scoring_hitters", {k: 0.0 for k in HITTER_CUSTOM_CATS})
            return st.session_state.get("custom_scoring_pitchers", {k: 0.0 for k in PITCHER_CUSTOM_CATS})

        def calc_points(df: pd.DataFrame, group: str, system: str) -> pd.Series:
            scoring = _get_scoring_dict(group, system)

            if group == "Hitters":
                d = _ensure_event_cols_hitters(df)
                pts = (
                    _num(d["1B"]) * scoring.get("1B", 0.0)
                    + _num(d["2B"]) * scoring.get("2B", 0.0)
                    + _num(d["3B"]) * scoring.get("3B", 0.0)
                    + _num(d["HR"]) * scoring.get("HR", 0.0)
                    + _num(d["SB"]) * scoring.get("SB", 0.0)
                    + _num(d["CS"]) * scoring.get("CS", 0.0)
                    + _num(d["BB"]) * scoring.get("BB", 0.0)
                    + _num(d["HBP"]) * scoring.get("HBP", 0.0)
                    + _num(d["SO"]) * scoring.get("SO", 0.0)
                    + _num(d["R"]) * scoring.get("R", 0.0)
                    + _num(d["RBI"]) * scoring.get("RBI", 0.0)
                )
                return pts

            d = _ensure_event_cols_pitchers(df)
            pts = (
                _num(d["IP"]) * scoring.get("IP", 0.0)
                + _num(d["SO"]) * scoring.get("SO", 0.0)
                + _num(d["H"]) * scoring.get("H", 0.0)
                + _num(d["BB"]) * scoring.get("BB", 0.0)
                + _num(d["HBP"]) * scoring.get("HBP", 0.0)
                + _num(d["HR"]) * scoring.get("HR", 0.0)
                + _num(d["W"]) * scoring.get("W", 0.0)
                + _num(d["L"]) * scoring.get("L", 0.0)
                + _num(d["SV"]) * scoring.get("SV", 0.0)
                + _num(d["QS"]) * scoring.get("QS", 0.0)
                + _num(d["HLD"]) * scoring.get("HLD", 0.0)
                + _num(d["ER"]) * scoring.get("ER", 0.0)
            )

            # keep DK extras if system == DraftKings (optional)
            if system == "DraftKings":
                pts = (
                    pts
                    + _num(d["CG"]) * DRAFTKINGS_P.get("CG", 0.0)
                    + _num(d["CGSO"]) * DRAFTKINGS_P.get("CGSO", 0.0)
                    + _num(d["NH"]) * DRAFTKINGS_P.get("NH", 0.0)
                )
            return pts

        # =========================
        # ===== TITLE =====
        # =========================
        st.markdown(
            """
            <h2 style='text-align:center;margin:.25rem 0 1rem;'>2026 Projections</h2>
            <p style='text-align:center;margin:0 0 1.25rem; font-size:0.85rem; color:#666;'>
                Compare MLB DW, Steamer, ATC, THE BAT, and OOPSY projections.
            </p>
            """,
            unsafe_allow_html=True,
        )

        # =========================
        # ===== RAW DATA PREP =====
        # =========================
        ja_hit_local = ja_hit.copy()
        steamerhit_local = steamerhit.copy()
        bathit_local = bathit.copy()
        atchit_local = atchit.copy()
        oopsyhit_local = oopsyhit.copy()

        # --- attach positions robustly to ja_hit_local ---
        ja_hit_local = ja_hit_local.merge(
            pos_data[["Player", "Position(s)"]],
            on="Player",
            how="left",
            suffixes=("", "_pos"),
        )
        ja_pos_cols = [c for c in ja_hit_local.columns if "Position(s)" in c]
        if ja_pos_cols:
            ja_hit_local["Pos"] = ja_hit_local[ja_pos_cols[-1]]
        ja_hit_local = ja_hit_local.drop(columns=ja_pos_cols, errors="ignore")

        # ensure required hitter columns exist
        for c in ["PA", "R", "HR", "RBI", "SB", "AVG", "OBP", "SLG", "OPS", "K%", "BB%", "Team", "Pos",
                "BB", "HBP", "1B", "2B", "3B", "SO", "CS"]:
            if c not in ja_hit_local.columns:
                ja_hit_local[c] = np.nan

        ja_hitters = ja_hit_local[
            ["Player", "Team", "Pos", "PA", "R", "HR", "RBI", "SB",
            "AVG", "OBP", "SLG", "OPS", "K%", "BB%",
            "BB", "HBP", "SO", "CS", "1B", "2B", "3B"]
        ].copy()

        # --- Steamer hitters ---
        steamerhit_local = steamerhit_local.rename({"Name": "Player"}, axis=1)
        steamerhit_local = steamerhit_local.merge(
            pos_data[["Player", "Position(s)"]],
            on="Player",
            how="left",
            suffixes=("", "_pos"),
        )
        steamer_pos_cols = [c for c in steamerhit_local.columns if "Position(s)" in c]
        if steamer_pos_cols:
            steamerhit_local["Pos"] = steamerhit_local[steamer_pos_cols[-1]]
        steamerhit_local = steamerhit_local.drop(columns=steamer_pos_cols, errors="ignore")

        for c in ["PA", "R", "HR", "RBI", "SB", "AVG", "OBP", "SLG", "OPS", "K%", "BB%", "Team", "Pos",
                "BB", "HBP", "1B", "2B", "3B", "SO", "CS"]:
            if c not in steamerhit_local.columns:
                steamerhit_local[c] = np.nan

        steamer_hitters = steamerhit_local[
            ["Player", "Team", "Pos", "PA", "R", "HR", "RBI", "SB",
            "AVG", "OBP", "SLG", "OPS", "K%", "BB%",
            "BB", "HBP", "SO", "CS", "1B", "2B", "3B"]
        ].copy()

        # --- THE BAT hitters ---
        if "Name" in bathit_local.columns and "Player" not in bathit_local.columns:
            bathit_local = bathit_local.rename({"Name": "Player"}, axis=1)

        bathit_local = bathit_local.merge(
            pos_data[["Player", "Position(s)"]],
            on="Player",
            how="left",
            suffixes=("", "_pos"),
        )
        bat_pos_cols = [c for c in bathit_local.columns if "Position(s)" in c]
        if bat_pos_cols:
            bathit_local["Pos"] = bathit_local[bat_pos_cols[-1]]
        bathit_local = bathit_local.drop(columns=bat_pos_cols, errors="ignore")

        for c in ["PA", "R", "HR", "RBI", "SB", "AVG", "OBP", "SLG", "OPS", "K%", "BB%", "Team", "Pos",
                "BB", "HBP", "1B", "2B", "3B", "SO", "CS"]:
            if c not in bathit_local.columns:
                bathit_local[c] = np.nan

        bat_hitters = bathit_local[
            ["Player", "Team", "Pos", "PA", "R", "HR", "RBI", "SB",
            "AVG", "OBP", "SLG", "OPS", "K%", "BB%",
            "BB", "HBP", "SO", "CS", "1B", "2B", "3B"]
        ].copy()

        # --- ATC hitters ---
        if "Name" in atchit_local.columns and "Player" not in atchit_local.columns:
            atchit_local = atchit_local.rename({"Name": "Player"}, axis=1)

        atchit_local = atchit_local.merge(
            pos_data[["Player", "Position(s)"]],
            on="Player",
            how="left",
            suffixes=("", "_pos"),
        )
        atc_pos_cols = [c for c in atchit_local.columns if "Position(s)" in c]
        if atc_pos_cols:
            atchit_local["Pos"] = atchit_local[atc_pos_cols[-1]]
        atchit_local = atchit_local.drop(columns=atc_pos_cols, errors="ignore")

        for c in ["PA", "R", "HR", "RBI", "SB", "AVG", "OBP", "SLG", "OPS", "K%", "BB%", "Team", "Pos",
                "BB", "HBP", "1B", "2B", "3B", "SO", "CS"]:
            if c not in atchit_local.columns:
                atchit_local[c] = np.nan

        atc_hitters = atchit_local[
            ["Player", "Team", "Pos", "PA", "R", "HR", "RBI", "SB",
            "AVG", "OBP", "SLG", "OPS", "K%", "BB%",
            "BB", "HBP", "SO", "CS", "1B", "2B", "3B"]
        ].copy()

        # --- OOPSY hitters ---
        if "Name" in oopsyhit_local.columns and "Player" not in oopsyhit_local.columns:
            oopsyhit_local = oopsyhit_local.rename({"Name": "Player"}, axis=1)

        oopsyhit_local = oopsyhit_local.merge(
            pos_data[["Player", "Position(s)"]],
            on="Player",
            how="left",
            suffixes=("", "_pos"),
        )
        oopsy_pos_cols = [c for c in oopsyhit_local.columns if "Position(s)" in c]
        if oopsy_pos_cols:
            oopsyhit_local["Pos"] = oopsyhit_local[oopsy_pos_cols[-1]]
        oopsyhit_local = oopsyhit_local.drop(columns=oopsy_pos_cols, errors="ignore")

        for c in ["PA", "R", "HR", "RBI", "SB", "AVG", "OBP", "SLG", "OPS", "K%", "BB%", "Team", "Pos",
                "BB", "HBP", "1B", "2B", "3B", "SO", "CS"]:
            if c not in oopsyhit_local.columns:
                oopsyhit_local[c] = np.nan

        oopsy_hitters = oopsyhit_local[
            ["Player", "Team", "Pos", "PA", "R", "HR", "RBI", "SB",
            "AVG", "OBP", "SLG", "OPS", "K%", "BB%",
            "BB", "HBP", "SO", "CS", "1B", "2B", "3B"]
        ].copy()

        # Add AB if missing (needed in SRV)
        for hdf in (ja_hitters, steamer_hitters, atc_hitters, bat_hitters, oopsy_hitters):
            if "AB" not in hdf.columns:
                hdf["AB"] = (pd.to_numeric(hdf["PA"], errors="coerce").fillna(0) * 0.9).astype(int)

        # --- Pitchers ---
        ja_pitchers = ja_pitch[
            ["Pitcher", "Team", "GS", "IP", "H", "ER", "K", "ERA", "WHIP", "K/9", "BB/9", "K%", "BB%", "W", "SV"]
        ].copy().rename({"Pitcher": "Player"}, axis=1)

        steamerpit_local = steamerpit.rename({"Name": "Player", "SO": "K"}, axis=1)
        #steamer_pitchers = steamerpit_local[
        #    ["Player", "Team", "GS", "IP", "H", "ER", "K", "ERA", "WHIP", "K/9", "BB/9", "K%", "BB%", "W","L", "SV", "QS","HLD"]
        #].copy()

        base_cols = ["Player", "Team", "GS", "IP", "H", "ER", "K", "ERA", "WHIP", "K/9", "BB/9", "K%", "BB%", "W", "L", "SV", "QS", "HLD"]
        opt_cols  = [c for c in ["HR", "HBP", "HB", "HR/9", "HR9", "HBP/9", "HBP9", "HB/9", "HB9"] if c in steamerpit_local.columns]
        steamer_pitchers = steamerpit_local[base_cols + opt_cols].copy()

        batpit_local = batpit.copy()
        if "Name" in batpit_local.columns and "Player" not in batpit_local.columns:
            batpit_local = batpit_local.rename({"Name": "Player"}, axis=1)
        if "SO" in batpit_local.columns and "K" not in batpit_local.columns:
            batpit_local = batpit_local.rename({"SO": "K"}, axis=1)

        #bat_pitchers = batpit_local[
        #    ["Player", "Team", "GS", "IP", "H", "ER", "K", "ERA", "WHIP", "K/9", "BB/9", "K%", "BB%", "W","L", "SV", "QS","HLD"]
        #].copy()
        base_cols = ["Player", "Team", "GS", "IP", "H", "ER", "K", "ERA", "WHIP", "K/9", "BB/9", "K%", "BB%", "W", "L", "SV", "QS", "HLD"]
        opt_cols  = [c for c in ["HR", "HBP", "HB", "HR/9", "HR9", "HBP/9", "HBP9", "HB/9", "HB9"] if c in batpit_local.columns]
        bat_pitchers = batpit_local[base_cols + opt_cols].copy()

        atcpit_local = atcpit.copy()
        if "Name" in atcpit_local.columns and "Player" not in atcpit_local.columns:
            atcpit_local = atcpit_local.rename({"Name": "Player"}, axis=1)
        if "SO" in atcpit_local.columns and "K" not in atcpit_local.columns:
            atcpit_local = atcpit_local.rename({"SO": "K"}, axis=1)

        #atc_pitchers = atcpit_local[
        #    ["Player", "Team", "GS", "IP", "H", "ER", "K", "ERA", "WHIP", "K/9", "BB/9", "K%", "BB%", "W","L", "SV", "QS","HLD"]
        #].copy()
        base_cols = ["Player", "Team", "GS", "IP", "H", "ER", "K", "ERA", "WHIP", "K/9", "BB/9", "K%", "BB%", "W", "L", "SV", "QS", "HLD"]
        opt_cols  = [c for c in ["HR", "HBP", "HB", "HR/9", "HR9", "HBP/9", "HBP9", "HB/9", "HB9"] if c in atcpit_local.columns]
        atc_pitchers = atcpit_local[base_cols + opt_cols].copy()

        oopsypit_local = oopsypitch.copy()
        if "Name" in oopsypit_local.columns and "Player" not in oopsypit_local.columns:
            oopsypit_local = oopsypit_local.rename({"Name": "Player"}, axis=1)
        if "SO" in oopsypit_local.columns and "K" not in oopsypit_local.columns:
            oopsypit_local = oopsypit_local.rename({"SO": "K"}, axis=1)

        req_p = ["Player", "Team", "GS", "IP", "H", "ER", "K", "ERA", "WHIP", "K/9", "BB/9", "K%", "BB%", "W","L", "SV", "QS"]
        for c in req_p:
            if c not in oopsypit_local.columns:
                oopsypit_local[c] = 0 if c in ["GS", "IP", "H", "ER", "K", "W", "SV", "QS"] else np.nan

        #oopsy_pitchers = oopsypit_local[
        #    ["Player", "Team", "GS", "IP", "H", "ER", "K", "ERA", "WHIP", "K/9", "BB/9", "K%", "BB%", "W","L", "SV","HLD"]
        #].copy()

        base_cols = ["Player", "Team", "GS", "IP", "H", "ER", "K", "ERA", "WHIP", "K/9", "BB/9", "K%", "BB%", "W", "L", "SV", "QS", "HLD"]
        opt_cols  = [c for c in ["HR", "HBP", "HB", "HR/9", "HR9", "HBP/9", "HBP9", "HB/9", "HB9"] if c in oopsypit_local.columns]
        cols_keep = [c for c in (base_cols + opt_cols) if c in oopsypit_local.columns]
        oopsy_pitchers = oopsypit_local[cols_keep].copy()


        # ensure SRV-needed columns exist
        for pdf in (ja_pitchers, steamer_pitchers, atc_pitchers, bat_pitchers, oopsy_pitchers):
            if "W" not in pdf.columns:
                pdf["W"] = 0
            if "SV" not in pdf.columns:
                pdf["SV"] = 0
            if "SO" not in pdf.columns:
                pdf["SO"] = pdf["K"] if "K" in pdf.columns else 0
            if "IP" not in pdf.columns:
                pdf["IP"] = 0

        # =========================
        # ===== CONTROLS =====
        # =========================
        top_col1, top_col2, top_col3, top_col4 = st.columns([1.1, 1.2, 1.2, 0.9])

        with top_col1:
            group = st.radio("Group", ["Hitters", "Pitchers"], horizontal=True)

        with top_col2:
            source_choice = st.radio("Source", ["MLB DW", "Steamer", "ATC", "THE BAT", "OOPSY", "All"], horizontal=True)

        with top_col4:
            per600 = st.toggle("600 PA Projections", value=False, disabled=(group != "Hitters"))
            show_points = st.checkbox("Show Points", value=False)

            if show_points:
                scoring_system = st.selectbox("Scoring", ["DraftKings", "Underdog", "Custom"], index=0)

                if scoring_system == "Custom":
                    # init defaults once
                    if "custom_scoring_hitters" not in st.session_state:
                        st.session_state["custom_scoring_hitters"] = {k: 0.0 for k in HITTER_CUSTOM_CATS}
                    if "custom_scoring_pitchers" not in st.session_state:
                        st.session_state["custom_scoring_pitchers"] = {k: 0.0 for k in PITCHER_CUSTOM_CATS}

                    with st.expander("Custom scoring settings", expanded=True):
                        st.caption("Enter point value for each event (negatives allowed for penalties). DO NOT USE MLB DW Projections for this!")

                        if group == "Hitters":
                            cols = st.columns(2)
                            for i, cat in enumerate(HITTER_CUSTOM_CATS):
                                with cols[i % 2]:
                                    st.session_state["custom_scoring_hitters"][cat] = st.number_input(
                                        f"{cat} pts",
                                        value=float(st.session_state["custom_scoring_hitters"].get(cat, 0.0)),
                                        step=0.5,
                                        format="%.2f",
                                        key=f"cust_h_{cat}",
                                    )
                        else:
                            cols = st.columns(2)
                            for i, cat in enumerate(PITCHER_CUSTOM_CATS):
                                with cols[i % 2]:
                                    st.session_state["custom_scoring_pitchers"][cat] = st.number_input(
                                        f"{cat} pts",
                                        value=float(st.session_state["custom_scoring_pitchers"].get(cat, 0.0)),
                                        step=0.5,
                                        format="%.2f",
                                        key=f"cust_p_{cat}",
                                    )
            else:
                scoring_system = None

        # team list
        if group == "Hitters":
            all_teams = (
                pd.concat(
                    [ja_hitters["Team"], steamer_hitters["Team"], atc_hitters["Team"], bat_hitters["Team"], oopsy_hitters["Team"]]
                )
                .dropna()
                .unique()
                .tolist()
            )
        else:
            all_teams = (
                pd.concat(
                    [ja_pitchers["Team"], steamer_pitchers["Team"], atc_pitchers["Team"], bat_pitchers["Team"], oopsy_pitchers["Team"]]
                )
                .dropna()
                .unique()
                .tolist()
            )
        all_teams = sorted(list(set(all_teams)))
        teams_opts = ["All Teams"] + all_teams

        with top_col3:
            team_filter = st.selectbox("Team", teams_opts, index=0)

        search_x_col1, search_x_col2 = st.columns([1, 1])

        # Build a single player pool across all sources for the chosen group
        if group == "Hitters":
            player_pool = pd.concat(
                [ja_hitters["Player"], steamer_hitters["Player"], atc_hitters["Player"], bat_hitters["Player"], oopsy_hitters["Player"]]
            ).dropna().unique()
        else:
            player_pool = pd.concat(
                [ja_pitchers["Player"], steamer_pitchers["Player"], atc_pitchers["Player"], bat_pitchers["Player"], oopsy_pitchers["Player"]]
            ).dropna().unique()
        player_pool_sorted = sorted(player_pool)

        # If All, do single-player select; otherwise keep multiselect
        with search_x_col1:
            if source_choice == "All":
                selected_player = st.selectbox(
                    "Select a player (All systems)",
                    options=player_pool_sorted,
                    index=0 if len(player_pool_sorted) else None,
                )
                player_search = [selected_player] if selected_player else []
            else:
                player_search = st.multiselect(
                    "Player search",
                    options=player_pool_sorted,
                    placeholder="Start typing player names...",
                )

        with search_x_col2:
            if group == "Hitters" and source_choice != "All":
                pos_search = st.text_input(
                    "Position search",
                    "",
                    placeholder='Type a position like "2B", "SS", "OF"...',
                )
            else:
                pos_search = ""

        st.markdown("<hr style='margin:0.75rem 0 1rem;'/>", unsafe_allow_html=True)

        # =========================
        # ===== FILTER HELPER =====
        # =========================
        def _filter_df(df: pd.DataFrame, is_hitter: bool = False) -> pd.DataFrame:
            out = df.copy()

            if team_filter != "All Teams":
                out = out[out["Team"] == team_filter]

            if player_search:
                out = out[out["Player"].isin(player_search)]

            if is_hitter and pos_search:
                if "Pos" in out.columns:
                    pos_series = out["Pos"].astype(str).fillna("")
                    token = pos_search.strip().upper()
                    out = out[pos_series.str.contains(token, case=False, na=False)]

            return out

        # =========================
        # ===== BUILD DISPLAY =====
        # =========================
        display_df = pd.DataFrame()

        hitter_sources = {
            "MLB DW": ja_hitters,
            "Steamer": steamer_hitters,
            "ATC": atc_hitters,
            "THE BAT": bat_hitters,
            "OOPSY": oopsy_hitters,
        }
        pitcher_sources = {
            "MLB DW": ja_pitchers,
            "Steamer": steamer_pitchers,
            "ATC": atc_pitchers,
            "THE BAT": bat_pitchers,
            "OOPSY": oopsy_pitchers,
        }

        if group == "Hitters":
            hitters_view = {k: (to_per_600_pa(v) if per600 else v) for k, v in hitter_sources.items()}

            if source_choice in ["MLB DW", "Steamer", "ATC", "THE BAT", "OOPSY"]:
                full_pool = hitters_view[source_choice]
                filtered = _filter_df(full_pool, is_hitter=True)
                display_df = calculateSRV_Hitters(full_pool, merge_df=filtered)

                if show_points and scoring_system:
                    display_df["Points"] = calc_points(display_df, "Hitters", scoring_system).round(1)

                cols_order = [
                    "Player", "Team", "Pos", "SRV",
                    "Points" if show_points and scoring_system else None,
                    "PA", "R", "HR", "RBI", "SB",
                    "AVG", "OBP", "SLG", "OPS", "K%", "BB%",
                ]
                cols_order = [c for c in cols_order if c is not None]
                display_df = display_df.reindex(columns=cols_order)

            else:  # All (single player, stacked rows)
                rows = []
                for src_name, pool in hitters_view.items():
                    filtered = _filter_df(pool, is_hitter=True)
                    with_srv = calculateSRV_Hitters(pool, merge_df=filtered)

                    if len(with_srv):
                        tmp = with_srv.copy()
                        tmp.insert(0, "Source", src_name)

                        if show_points and scoring_system:
                            tmp["Points"] = calc_points(tmp, "Hitters", scoring_system).round(1)

                        rows.append(tmp)

                cols_order = [
                    "Player", "Team", "Pos", "Source", "SRV",
                    "Points" if show_points and scoring_system else None,
                    "PA", "R", "HR", "RBI", "SB",
                    "AVG", "OBP", "SLG", "OPS", "K%", "BB%",
                ]
                cols_order = [c for c in cols_order if c is not None]

                display_df = pd.concat(rows, ignore_index=True).reindex(columns=cols_order) if rows else pd.DataFrame(columns=cols_order)

                if player_search:
                    st.markdown(f"<h3 style='margin:0 0 .5rem;'>{player_search[0]}</h3>", unsafe_allow_html=True)

        else:  # Pitchers
            if source_choice in ["MLB DW", "Steamer", "ATC", "THE BAT", "OOPSY"]:
                full_pool = pitcher_sources[source_choice]
                filtered = _filter_df(full_pool, is_hitter=False)
                display_df = calculateSRV_Pitchers(full_pool, merge_df=filtered)

                if show_points and scoring_system:
                    display_df["Points"] = calc_points(display_df, "Pitchers", scoring_system).round(1)

                cols_order = ["Player", "Team", "SRV"]
                if show_points and scoring_system:
                    cols_order += ["Points"]
                cols_order += ["GS", "IP", "ERA", "WHIP", "K%", "BB%", "W", "SV"]

                display_df = display_df.reindex(columns=cols_order)

            else:  # All (single player, stacked rows)
                rows = []
                for src_name, pool in pitcher_sources.items():
                    filtered = _filter_df(pool, is_hitter=False)
                    with_srv = calculateSRV_Pitchers(pool, merge_df=filtered)

                    if len(with_srv):
                        tmp = with_srv.copy()
                        tmp.insert(0, "Source", src_name)

                        if show_points and scoring_system:
                            tmp["Points"] = calc_points(tmp, "Pitchers", scoring_system).round(1)

                        rows.append(tmp)

                cols_order = ["Player", "Team", "Source", "SRV"]
                if show_points and scoring_system:
                    cols_order += ["Points"]
                cols_order += ["GS", "IP", "ERA", "WHIP", "K%", "BB%", "W", "SV", "SO", "K/9", "BB/9"]

                display_df = pd.concat(rows, ignore_index=True).reindex(columns=cols_order) if rows else pd.DataFrame(columns=cols_order)

                if player_search:
                    st.markdown(f"<h3 style='margin:0 0 .5rem;'>{player_search[0]}</h3>", unsafe_allow_html=True)

        # =========================
        # ===== STYLING =====
        # =========================
        def style_table(df: pd.DataFrame):
            fmt = {}
            for col in df.columns:
                if col in ["PA", "R", "HR", "RBI", "SB", "SO", "W", "SV", "GS", "H", "ER"]:
                    fmt[col] = "{:.0f}"
                elif col == "Points":
                    fmt[col] = "{:.1f}"
                elif any(stat in col for stat in ["AVG", "OBP", "SLG", "OPS"]):
                    fmt[col] = "{:.3f}"
                elif "ERA" in col or "WHIP" in col:
                    fmt[col] = "{:.2f}"
                elif col == "IP" or col.endswith("IP"):
                    fmt[col] = "{:.1f}"
                elif "SRV" in col:
                    fmt[col] = "{:.2f}"
                elif col.endswith("%"):
                    fmt[col] = "{:.1%}"
                elif "/9" in col:
                    fmt[col] = "{:.1f}"

            numeric_cols = df.select_dtypes(include=["float", "int"]).columns.tolist()
            sty = df.style.format(fmt)

            if numeric_cols:
                sty = sty.background_gradient(axis=0, cmap="Blues", subset=numeric_cols)

            if hasattr(sty, "hide_index"):
                sty = sty.hide_index()

            sty = sty.set_properties(**{"text-align": "left", "font-size": "0.8rem"})
            return sty

        height = 250 if len(display_df) < 5 else 650
        st.dataframe(
            style_table(display_df),
            use_container_width=True,
            hide_index=True,
            height=height,
        )

        st.markdown(
            "<center><hr><font face=Oswald><b>The MLB DW system gives every hitter on the 40-man roster a baseline 100 PA so we can use the 600 PA adjustment to see what they <i>would</i> project like in the case they get unexpected playing time</b></font><hr>",
            unsafe_allow_html=True,
        )

        # =========================
        # ===== DOWNLOAD =====
        # =========================
        csv = display_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download current view as CSV",
            csv,
            "2026_projections.csv",
            "text/csv",
        )

    if tab == "Prospect Comps":
        # --- Load only what this page needs ---
        hitterranks, pitcherranks, fscores_mlb_hit, fscores_milb_hit, fscores_mlb_pitch, fscores_milb_pitch, pitchers_fscores, hitters_fscores, timrank_hitters, timrank_pitchers, posdata = load_rankings()
        st.markdown(
            "<h2 style='text-align:center;margin:.25rem 0 1rem;'>Prospect Comps</h2>",
            unsafe_allow_html=True,
        )

        # ========= Helpers =========
        def _prep_hitters(minors: pd.DataFrame, majors: pd.DataFrame):
            use_cols = ["Player", "Team", "Pos", "Age", "HitTool", "Discipline", "Power", "Speed", "Durability"]
            minors = minors.copy()
            majors = majors.copy()
            minors = minors[[c for c in use_cols if c in minors.columns]].dropna(subset=["Player"])
            majors = majors[[c for c in use_cols if c in majors.columns]].dropna(subset=["Player"])

            # numeric cols must exist in BOTH
            num_cols = [
                c
                for c in ["Age", "HitTool", "Discipline", "Power", "Speed", "Durability"]
                if c in minors.columns and c in majors.columns
            ]
            for c in num_cols:
                minors[c] = pd.to_numeric(minors[c], errors="coerce")
                majors[c] = pd.to_numeric(majors[c], errors="coerce")

            minors = minors.dropna(subset=num_cols)
            majors = majors.dropna(subset=num_cols)
            return minors, majors, num_cols

        def _prep_pitchers(minors: pd.DataFrame, majors: pd.DataFrame):
            if "Player" not in minors.columns and "player_name" in minors.columns:
                minors = minors.rename(columns={"player_name": "Player"})
            if "Player" not in majors.columns and "player_name" in majors.columns:
                majors = majors.rename(columns={"player_name": "Player"})

            keep = ["Player", "pitcher", "fERA", "fControl", "fStuff", "fDurability", "Age"]
            minors = minors[[c for c in keep if c in minors.columns]].dropna(subset=["Player"])
            majors = majors[[c for c in keep if c in majors.columns]].dropna(subset=["Player"])

            num_cols = [c for c in ["fERA", "fControl", "fStuff", "fDurability", "Age"] if c in minors.columns and c in majors.columns]
            for c in num_cols:
                minors[c] = pd.to_numeric(minors[c], errors="coerce")
                majors[c] = pd.to_numeric(majors[c], errors="coerce")

            # allow Age to be optional
            minors = minors.dropna(subset=[c for c in num_cols if c != "Age"] or num_cols)
            majors = majors.dropna(subset=[c for c in num_cols if c != "Age"] or num_cols)

            core_feats = [c for c in ["fERA", "fControl", "fStuff", "fDurability"] if c in num_cols]
            has_age = "Age" in num_cols
            return minors, majors, core_feats, has_age

        def _standardize(maj_matrix: np.ndarray, vec: np.ndarray, flip_mask=None):
            mu = maj_matrix.mean(axis=0)
            sd = maj_matrix.std(axis=0, ddof=0)
            sd = np.where(sd == 0, 1.0, sd)
            A = (maj_matrix - mu) / sd
            b = (vec - mu) / sd
            if flip_mask is not None:
                A = np.where(flip_mask, -A, A)
                b = np.where(flip_mask, -b, b)
            return A, b

        def _cosine(A: np.ndarray, b: np.ndarray, weights: np.ndarray | None = None) -> np.ndarray:
            if weights is not None:
                A = A * weights
                b = b * weights
            An = np.linalg.norm(A, axis=1)
            bn = np.linalg.norm(b)
            An = np.where(An == 0, 1.0, An)
            if bn == 0:
                bn = 1.0
            sims = (A @ b) / (An * bn)
            return np.clip(sims, -1.0, 1.0)

        def _sim_to_score(sim: np.ndarray) -> np.ndarray:
            return ((sim + 1.0) / 2.0) * 100.0

        def _build_output_no_dupes(pool, q_row, features, scores, top_n):
            """
            Build one dataframe (same index!) so columns don't get misaligned.
            """
            base_cols = ["Player"] + [c for c in ["Team", "Pos", "Age"] if c in pool.columns]

            # start with base + feature values from MLB player
            all_feat_cols = [c for c in features if c not in base_cols]
            df = pool[base_cols + all_feat_cols].copy()

            # similarity
            df.insert(1, "Similarity", np.round(scores, 1))

            # deltas vs selected minor leaguer
            for c in features:
                df[f"Δ {c}"] = (pool[c].to_numpy() - float(q_row[c])).round(1)

            # sort and trim
            df = df.sort_values("Similarity", ascending=False).head(top_n).reset_index(drop=True)

            # final guard
            df = df.loc[:, ~df.columns.duplicated()]
            return df

        def _run_comps(
            minors_df: pd.DataFrame,
            majors_df: pd.DataFrame,
            features: list[str],
            query_name: str,
            top_n: int = 10,
            same_pos_only: bool = False,
            pos_col: str | None = None,
            weights_dict: dict | None = None,
            flip_lower_is_better: list[str] | None = None,
        ) -> tuple[pd.DataFrame, pd.Series]:
            q = minors_df[minors_df["Player"] == query_name]
            if q.empty:
                return pd.DataFrame(), pd.Series(dtype=float)
            q = q.iloc[0]

            pool = majors_df.copy()
            if same_pos_only and pos_col and pos_col in minors_df.columns and pos_col in majors_df.columns:
                pool = pool[pool[pos_col] == q[pos_col]].copy()
                if pool.empty:
                    pool = majors_df.copy()

            A = pool[features].to_numpy(dtype=float)
            b = q[features].to_numpy(dtype=float)

            weights = None
            if weights_dict:
                weights = np.array([weights_dict.get(f, 1.0) for f in features], dtype=float)

            flip_mask = np.array([f in (flip_lower_is_better or []) for f in features], dtype=bool)

            A_z, b_z = _standardize(A, b, flip_mask=flip_mask)
            sims = _cosine(A_z, b_z, weights=weights)
            scores = _sim_to_score(sims)

            out = _build_output_no_dupes(pool, q, features, scores, top_n)
            return out, q  # also return the selected player row so we can show it

        # ========= UI =========
        group = st.radio("Group", ["Hitters", "Pitchers"], horizontal=True, index=0)

        if group == "Hitters":
            # these must already be in your session
            minors_hit = fscores_milb_hit.copy()
            majors_hit = fscores_mlb_hit.copy()
            minors_hit, majors_hit, hit_features = _prep_hitters(minors_hit, majors_hit)

            left, right = st.columns([2, 1])
            with left:
                sel_player = st.selectbox(
                    "Select a Minor League Hitter",
                    options=sorted(minors_hit["Player"].unique().tolist()),
                    index=0,
                )
            with right:
                top_n = st.slider("How many comps?", 3, 10, 5, 1)

            with st.expander("Advanced options"):
                same_pos = st.checkbox("Limit comps to the same primary position", value=True)
                st.caption("Similarity = cosine over MLB-standardized features (0–100 score).")
                w_cols = st.columns(6)
                w_hittool   = w_cols[0].number_input("HitTool",   min_value=0.0, value=1.0, step=0.1)
                w_disc      = w_cols[1].number_input("Discipline", min_value=0.0, value=1.0, step=0.1)
                w_power     = w_cols[2].number_input("Power",      min_value=0.0, value=1.0, step=0.1)
                w_speed     = w_cols[3].number_input("Speed",      min_value=0.0, value=1.0, step=0.1)
                w_dur       = w_cols[4].number_input("Durability", min_value=0.0, value=1.0, step=0.1)
                w_age       = w_cols[5].number_input("Age",        min_value=0.0, value=0.5, step=0.1)

                weights_hit = {
                    "HitTool": w_hittool,
                    "Discipline": w_disc,
                    "Power": w_power,
                    "Speed": w_speed,
                    "Durability": w_dur,
                    "Age": w_age,
                }

            with st.spinner("Computing hitter comps..."):
                comps, sel_row = _run_comps(
                    minors_df=minors_hit,
                    majors_df=majors_hit,
                    features=hit_features,
                    query_name=sel_player,
                    top_n=top_n,
                    same_pos_only=same_pos,
                    pos_col="Pos",
                    weights_dict=weights_hit,
                    flip_lower_is_better=None,
                )

            # ---- show selected minor leaguer's scores ----
            sel1,sel2,sel3 = st.columns([1,5,1])
            with sel2:
                if not sel_row.empty:
                    st.markdown("#### Selected player's scores")
                    sel_display = {
                        "Player": sel_player,
                        "Team": sel_row.get("Team", ""),
                        "Pos": sel_row.get("Pos", ""),
                    }
                    for c in hit_features:
                        sel_display[c] = sel_row.get(c, "")
                    st.dataframe(
                        pd.DataFrame([sel_display]),
                        use_container_width=True,
                        hide_index=True,
                    )

            # ---- show comps ----
            st.markdown(f"### Top {top_n} MLB Comps for **{sel_player}**")
            if comps.empty:
                st.info("No comps found. Try turning off same-position filter or adjusting weights.")
            else:
                st.dataframe(
                    comps.style.format(precision=1, thousands=","),
                    use_container_width=True,
                    hide_index=True
                    #height=len(comps)*50,
                )
                st.download_button(
                    "⬇️ Download comps as CSV",
                    data=comps.to_csv(index=False).encode("utf-8"),
                    file_name=f"{sel_player.replace(' ','_')}_MLB_Comps.csv",
                    mime="text/csv",
                )

        else:  # Pitchers
            minors_pitch = fscores_milb_pitch.copy()
            majors_pitch = fscores_mlb_pitch.copy()
            minors_pitch, majors_pitch, pit_core_feats, has_age = _prep_pitchers(minors_pitch, majors_pitch)
            pit_features = pit_core_feats + (["Age"] if has_age else [])

            left, right = st.columns([2, 1])
            with left:
                sel_player = st.selectbox(
                    "Select a Minor League Pitcher",
                    options=sorted(minors_pitch["Player"].unique().tolist()),
                    index=0,
                )
            with right:
                top_n = st.slider("How many comps?", 3, 10, 5, 1)
                #top_n = st.slider("How many comps?", 5, 25, 10, 1)

            with st.expander("Advanced options"):
                st.caption("fERA is treated as ‘lower is better’.")
                w_cols = st.columns(5 if has_age else 4)
                w_fera   = w_cols[0].number_input("fERA",        min_value=0.0, value=1.2, step=0.1)
                w_fctl   = w_cols[1].number_input("fControl",    min_value=0.0, value=1.0, step=0.1)
                w_fstuff = w_cols[2].number_input("fStuff",      min_value=0.0, value=1.0, step=0.1)
                w_fdur   = w_cols[3].number_input("fDurability", min_value=0.0, value=0.7, step=0.1)
                weights_pit = {"fERA": w_fera, "fControl": w_fctl, "fStuff": w_fstuff, "fDurability": w_fdur}
                if has_age:
                    w_age = w_cols[4].number_input("Age", min_value=0.0, value=0.4, step=0.1)
                    weights_pit["Age"] = w_age

            with st.spinner("Computing pitcher comps..."):
                comps, sel_row = _run_comps(
                    minors_df=minors_pitch,
                    majors_df=majors_pitch,
                    features=pit_features,
                    query_name=sel_player,
                    top_n=top_n,
                    same_pos_only=False,
                    pos_col=None,
                    weights_dict=weights_pit,
                    flip_lower_is_better=["fERA"],
                )

            zzz1,zzz2,zzz3 = st.columns([1,5,1])
            with zzz2:
                if not sel_row.empty:
                    st.markdown("#### Selected pitcher's scores")
                    sel_display = {
                        "Player": sel_player,
                    }
                    for c in pit_features:
                        sel_display[c] = sel_row.get(c, "")
                    st.dataframe(
                        pd.DataFrame([sel_display]),
                        use_container_width=True,
                        hide_index=True,
                    )

            st.markdown(f"### Top {top_n} MLB Comps for **{sel_player}**")
            if comps.empty:
                st.info("No comps found. Try adjusting weights.")
            else:
                st.dataframe(
                    comps.style.format(precision=2, thousands=","),
                    use_container_width=True,
                    hide_index=True
                    #height=460,
                )
                st.download_button(
                    "⬇️ Download comps as CSV",
                    data=comps.to_csv(index=False).encode("utf-8"),
                    file_name=f"{sel_player.replace(' ','_')}_MLB_Comps.csv",
                    mime="text/csv",
                )


    if tab == "2026 Ranks":
        # --- Load only what this page needs ---
        hitterranks, pitcherranks, fscores_mlb_hit, fscores_milb_hit, fscores_mlb_pitch, fscores_milb_pitch, pitchers_fscores, hitters_fscores, timrank_hitters, timrank_pitchers, posdata = load_rankings()
        import pandas as pd, numpy as np, html
        import streamlit as st
        import streamlit.components.v1 as components

        # ===== Title =====
        st.markdown('<h2 style="text-align:center;margin:.25rem 0 1rem;">2026 Ranks</h2>', unsafe_allow_html=True)

        # ===== Load data =====
        # If you want to swap to live Sheets later, hook back into your helper functions.
        hitters_raw = hitterranks.copy()
        pitchers_raw = pitcherranks.copy()

        #st.write(hitters_raw)

        teams_completed = hitters_raw['Team'].unique()

        #st.markdown(f'<h5 style="text-align:center;margin:.25rem 0 1rem;">work in progress...</h5><center>Teams Completed: {teams_completed}</center>', unsafe_allow_html=True)


        # Build link dicts from the Link column
        h_with_links = hitters_raw[~hitters_raw['Link'].isna()]
        h_link_dict = dict(zip(h_with_links['Player'], h_with_links['Link']))

        p_with_links = pitchers_raw[~pitchers_raw['Link'].isna()]
        p_link_dict = dict(zip(p_with_links['Player'], p_with_links['Link']))

        # ===== Toggle =====
        group = st.radio("Group", ["Hitters", "Pitchers"], horizontal=True, index=0)
        df_raw = hitters_raw.copy() if group == "Hitters" else pitchers_raw.copy()

        # Expected cols
        expected = ["Rank","Player","Team","Pos","Primary Pos","Pos Rank","Comments","Link"]
        for c in expected:
            if c not in df_raw.columns:
                df_raw[c] = np.nan

        # Coerce numeric ints for display
        for c in ["Rank","Pos Rank"]:
            df_raw[c] = pd.to_numeric(df_raw[c], errors="coerce").astype("Int64")

        # ===== Filters =====
        pos_field = "Primary Pos" if group == "Hitters" else "Pos"

        c1, c2, c3 = st.columns([1,1,1.6])
        with c1:
            pos_opts = ["All"] + sorted(df_raw[pos_field].dropna().astype(str).unique().tolist())
            sel_pos = st.selectbox(pos_field, pos_opts, index=0)
        with c2:
            team_opts = ["All"] + sorted(df_raw["Team"].dropna().astype(str).unique().tolist())
            sel_team = st.selectbox("Team", team_opts, index=0)
        with c3:
            q = st.text_input("Search Player", placeholder="type a name…").strip().lower()

        df = df_raw.copy()
        if sel_pos != "All":
            df = df[df[pos_field] == sel_pos]
        if sel_team != "All":
            df = df[df["Team"] == sel_team]
        if q:
            df = df[df["Player"].fillna("").str.lower().str.contains(q, na=False)]
        df = df.sort_values(["Rank","Player"], na_position="last").reset_index(drop=True)

        # ===== Row colors =====
        pos_colors = (
            {"C":"#E691FF","1B":"#FFE5B4","2B":"#FF7F47","3B":"#D9EBFA","SS":"#47C5FF","OF":"#5CEDB5","DH":"#91C6FF"}
            if group == "Hitters" else
            {"SP":"#004687","RP":"#004687","P":"#004687"}
        )

        # Which link dict to use
        link_dict = h_link_dict if group == "Hitters" else p_link_dict

        # ===== Utilities =====
        def esc(x):
            if pd.isna(x):
                return ""
            try:
                return html.escape(str(x))
            except Exception:
                return ""

        # ===== CSS =====
        css = """
        <style>
        .wrap { max-width: 1200px; margin: 0 auto; }
        .card { background:#fff; border:1px solid #e9e9ee; border-radius:16px; box-shadow:0 4px 14px rgba(0,0,0,.05); overflow:hidden; }
        table.tbl { width:100%; border-collapse:separate; border-spacing:0; font-size:15px; }
        thead th { position:sticky; top:0; background:#f7f8fb; padding:10px; text-align:center; font-weight:700; border-bottom:1px solid #ececf4; z-index:1; }
        tbody td { padding:10px; text-align:center; border-bottom:1px solid #f2f2f6; }
        tbody tr:last-child td { border-bottom:none; }
        td.player { text-align:left; }
        .pwrap { position:relative; display:inline-block; }
        .pname { font-weight:700; color:#0f172a; cursor:help; }
        .tip {
            visibility:hidden; opacity:0; transition:opacity .12s ease-in-out;
            position:absolute; left:0; top:110%;
            min-width:260px; max-width:540px;
            background:#0f172a; color:#fff; border-radius:10px; padding:10px 12px;
            box-shadow:0 8px 22px rgba(0,0,0,.18); z-index:5; line-height:1.35;
            white-space:normal; word-wrap:break-word;
        }
        .tip::after { content:""; position:absolute; top:-6px; left:14px; border-width:6px; border-style:solid;
                        border-color:transparent transparent #0f172a transparent; }
        .pwrap:hover .tip { visibility:visible; opacity:1; }
        @media (max-width: 800px) { .tip { max-width: 80vw; } }

        /* Read button */
        .readcol { text-align:center; }
        .readbtn {
            display:inline-block; padding:4px 8px; border-radius:80px;
            text-decoration:none; font-weight:600; border:1px solid #dbe0ea;
            background:#f2f5fb; color:#0f172a;
        }
        .readbtn:hover { background:#e6ecf7; }
        .muted { color:#9aa3b2; font-style:italic; }
        </style>
        """

        # ----- Header (conditional) -----
        if group == "Hitters":
            header = """
            <div class="wrap"><div class="card">
            <table class="tbl">
                <thead>
                <tr>
                    <th style="width:70px;">Rank</th>
                    <th>Player</th>
                    <th style="width:90px;">Team</th>
                    <th style="width:90px;">Pos</th>
                    <th style="width:120px;">Primary Pos</th>
                    <th style="width:110px;">Pos Rank</th>
                    <th style="width:160px;">Link</th>
                    <th style="width:45%;">Comments</th>
                </tr>
                </thead>
                <tbody>
            """
        else:  # Pitchers
            header = """
            <div class="wrap"><div class="card">
            <table class="tbl">
                <thead>
                <tr>
                    <th style="width:70px;">Rank</th>
                    <th>Player</th>
                    <th style="width:90px;">Team</th>
                    <th style="width:120px;">Pos</th>
                    <th style="width:160px;">Read</th>
                    <th style="width:55%;">Comments</th>
                </tr>
                </thead>
                <tbody>
            """

        # ----- Rows -----
        rows = []
        for _, r in df.iterrows():
            # background color by position key (Primary Pos for hitters, Pos for pitchers)
            pos_key = esc(r.get(pos_field, ""))
            bg = pos_colors.get(pos_key, "#47C5FF")

            rank    = "" if pd.isna(r["Rank"]) else int(r["Rank"])
            player  = esc(r["Player"])
            team    = esc(r["Team"])
            pos     = esc(r["Pos"])
            ppos    = esc(r.get("Primary Pos", ""))
            posrank = "" if pd.isna(r.get("Pos Rank", np.nan)) else int(r["Pos Rank"])

            cm_full = esc(r["Comments"]).replace("\n"," ")
            cm_prev = (cm_full[:180] + "…") if len(cm_full) > 180 else cm_full

            # Link cell
            raw_player = r["Player"]
            plink = None
            # Prefer dict lookup; if missing, fall back to row's Link column
            if isinstance(raw_player, str):
                plink = link_dict.get(raw_player)
            if (not isinstance(plink, str) or not plink.strip()) and isinstance(r.get("Link", None), str):
                if r["Link"].strip():
                    plink = r["Link"].strip()

            if isinstance(plink, str) and plink.strip():
                link_cell = f'<a class="readbtn" href="{html.escape(plink)}" target="_blank" rel="noopener noreferrer">Read Full Breakdown</a>'
            else:
                link_cell = '<span class="muted">—</span>'

            if group == "Hitters":
                rows.append(f"""
                <tr style="background:{bg};">
                    <td>{rank}</td>
                    <td class="player">
                        <span class="pwrap">
                            <span class="pname">{player}</span>
                            <span class="tip">{cm_full or "No comment."}</span>
                        </span>
                    </td>
                    <td>{team}</td>
                    <td>{pos}</td>
                    <td>{ppos}</td>
                    <td>{posrank}</td>
                    <td class="readcol">{link_cell}</td>
                    <td style="text-align:left;">{cm_prev}</td>
                </tr>
                """)
            else:
                rows.append(f"""
                <tr style="background:{bg};">
                    <td>{rank}</td>
                    <td class="player">
                        <span class="pwrap">
                            <span class="pname">{player}</span>
                            <span class="tip">{cm_full or "No comment."}</span>
                        </span>
                    </td>
                    <td>{team}</td>
                    <td>{pos}</td>
                    <td class="readcol">{link_cell}</td>
                    <td style="text-align:left;">{cm_prev}</td>
                </tr>
                """)

        footer = """
                </tbody>
            </table>
            </div></div>
        """

        html_out = css + header + "\n".join(rows) + footer

        # Sensible container height
        row_h = 44     # px per row (roughly)
        base_h = 120   # header + padding
        max_h = 900
        height = min(max_h, base_h + row_h * max(1, len(df)))

        components.html(html_out, height=height, scrolling=True)


    ######### HITTER COMP

    def _norm(s: str) -> str:
        return re.sub(r"[^a-z0-9]", "", (s or "").lower())

    # Map flexible user-provided names to your canonical stat keys
    CANON_KEYS = {
        "brl%": ["brl%", "barrel%", "brl", "barrels%"],
        "gb%": ["gb%", "groundball%", "gbpct"],
        "airpull%": ["airpull%", "air pull%", "pullair%", "pullfb%", "airpullpct"],
        "swing%": ["swing%", "swingpct", "sw%"],
        "contact%": ["contact%", "contactpct", "ct%"],
        "k%": ["k%", "so%", "strikeout%"],
        "bb%": ["bb%", "walk%", "baseonballs%"],
        "sbatt%": ["sbatt%", "sb attempt%", "steal attempt%", "sbattpct", "sbatt"],
    }

    def _locate_columns(df: pd.DataFrame):
        found = {}
        all_cols = { _norm(c): c for c in df.columns }
        for canon, variants in CANON_KEYS.items():
            for v in variants:
                key = _norm(v)
                if key in all_cols:
                    found[canon] = all_cols[key]
                    break
            # If we didn't find via variants, try exact canon
            if canon not in found and _norm(canon) in all_cols:
                found[canon] = all_cols[_norm(canon)]
        return found

    def _percentify(series: pd.Series) -> pd.Series:
        """Convert 0–1 decimals to 0–100 if needed; leave 0–100 ints/floats alone."""
        s = series.astype(float)
        if s.dropna().between(0, 1.0).all():
            return s * 100.0
        return s

    def _zscore(df: pd.DataFrame) -> pd.DataFrame:
        mu = df.mean(numeric_only=True)
        sd = df.std(ddof=0, numeric_only=True).replace(0, np.nan)
        z = (df - mu) / sd
        return z.fillna(0.0)

    def _cosine_dist(a: np.ndarray, B: np.ndarray) -> np.ndarray:
        a = a.astype(float)
        B = B.astype(float)
        a_norm = np.linalg.norm(a)
        B_norm = np.linalg.norm(B, axis=1)
        # Avoid divide by zero
        a_norm = 1e-12 if a_norm == 0 else a_norm
        B_norm = np.where(B_norm == 0, 1e-12, B_norm)
        sim = (B @ a) / (B_norm * a_norm)
        return 1.0 - sim  # distance = 1 - cosine similarity

    def _euclid_dist(a: np.ndarray, B: np.ndarray) -> np.ndarray:
        return np.linalg.norm(B - a[None, :], axis=1)

    def _mahalanobis_dist(a: np.ndarray, B: np.ndarray, VI: np.ndarray) -> np.ndarray:
        diff = B - a[None, :]
        # sqrt((x-μ)^T V^{-1} (x-μ))
        return np.sqrt(np.einsum("ij,jk,ik->i", diff, VI, diff))

    def _mahalanobis_inv(cov: np.ndarray) -> np.ndarray | None:
        try:
            return np.linalg.inv(cov)
        except Exception:
            return None

    if tab == "Player Rater":
        # --- Load only what this page needs ---
        hitter_stats_raw, lineup_stats, pitcher_stats, h_vs_avg, p_vs_avg, h_vs_sim, hotzonedata, posdata = load_player_stats()
        hitter_stats = hitter_stats_raw.copy()
        hitdb = load_hitdb()
        pitdb = load_pitdb()
        st.markdown("<h1><center>Dynamic Player Rater</center></h1><br><br><i>SRV = Standard Roto Value</i>", unsafe_allow_html=True)

        # ==== build team dicts (latest affiliate per player) ====
        team_selection_list = list(hitdb["affiliate"].unique())
        teamlist = hitdb[["player_id", "game_date", "affiliate"]].sort_values(by="game_date")
        teamlist = teamlist[["player_id", "affiliate"]].drop_duplicates(keep="last")
        teamdict = dict(zip(teamlist.player_id, teamlist.affiliate))

        teamlist_p = pitdb[["player_id", "game_date", "affiliate"]].sort_values(by="game_date")
        teamlist_p = teamlist_p[["player_id", "affiliate"]].drop_duplicates(keep="last")
        teamdict_p = dict(zip(teamlist_p.player_id, teamlist_p.affiliate))

        # ========= FUNCTIONS =========
        def calculateSRV_Hitters(hitdf: pd.DataFrame, merge_df: pd.DataFrame | None = None):
            """
            Same logic as your old SGP, but final col is now SRV.
            Also preserves player_id when present so we can look players up later.
            """
            df = hitdf.copy()

            count_cats = ["R", "HR", "RBI", "SB"]
            for cat in count_cats:
                std = df[cat].std(ddof=0)
                df[f"{cat}_z"] = (df[cat] - df[cat].mean()) / (std if std != 0 else 1.0)

            total_ab = df["AB"].sum()
            lg_avg = np.divide((df["AVG"] * df["AB"]).sum(), total_ab) if total_ab else df["AVG"].mean()

            df["AVG_contrib"] = (df["AVG"] - lg_avg) * df["AB"]
            std = df["AVG_contrib"].std(ddof=0)
            df["AVG_z"] = (df["AVG_contrib"] - df["AVG_contrib"].mean()) / (std if std != 0 else 1.0)

            z_cols = [f"{c}_z" for c in count_cats] + ["AVG_z"]
            df["SRV"] = df[z_cols].sum(axis=1)

            # keep player_id if we have it
            base_cols = ["Player", "Team", "SRV"] + z_cols
            if "player_id" in df.columns:
                base_cols.insert(1, "player_id")

            df_sorted = df[base_cols].sort_values("SRV", ascending=False).reset_index(drop=True)

            if merge_df is not None:
                out = merge_df.merge(df_sorted[[c for c in ["Player", "Team", "SRV", "player_id"] if c in df_sorted.columns]],
                                    on=[c for c in ["Player", "Team"] if c in merge_df.columns],
                                    how="left")
                out["SRV"] = out["SRV"].round(2)
                return out.sort_values("SRV", ascending=False)

            return df_sorted

        def calculateSRV_Pitchers(pitchdf: pd.DataFrame, merge_df: pd.DataFrame | None = None):
            df = pitchdf.copy()

            count_cats = ["W", "SV", "SO"]
            for cat in count_cats:
                std = df[cat].std(ddof=0)
                df[f"{cat}_z"] = (df[cat] - df[cat].mean()) / (std if std != 0 else 1.0)

            # rate cats as contrib * IP
            lg_era = np.divide((df["ERA"] * df["IP"]).sum(), df["IP"].sum()) if df["IP"].sum() else df["ERA"].mean()
            df["ERA_contrib"] = (lg_era - df["ERA"]) * df["IP"]
            std = df["ERA_contrib"].std(ddof=0)
            df["ERA_z"] = (df["ERA_contrib"] - df["ERA_contrib"].mean()) / (std if std != 0 else 1.0)

            lg_whip = np.divide((df["WHIP"] * df["IP"]).sum(), df["IP"].sum()) if df["IP"].sum() else df["WHIP"].mean()
            df["WHIP_contrib"] = (lg_whip - df["WHIP"]) * df["IP"]
            std = df["WHIP_contrib"].std(ddof=0)
            df["WHIP_z"] = (df["WHIP_contrib"] - df["WHIP_contrib"].mean()) / (std if std != 0 else 1.0)

            z_cols = [f"{c}_z" for c in count_cats] + ["ERA_z", "WHIP_z"]
            df["SRV"] = df[z_cols].sum(axis=1)

            base_cols = ["Player", "Team", "SRV"] + z_cols
            if "player_id" in df.columns:
                base_cols.insert(1, "player_id")

            df_sorted = df[base_cols].sort_values("SRV", ascending=False).reset_index(drop=True)

            if merge_df is not None:
                out = merge_df.merge(df_sorted[[c for c in ["Player", "Team", "SRV", "player_id"] if c in df_sorted.columns]],
                                    on=[c for c in ["Player", "Team"] if c in merge_df.columns],
                                    how="left")
                out["SRV"] = out["SRV"].round(2)
                return out.sort_values("SRV", ascending=False)

            return df_sorted

        def select_and_filter_by_date_slider(df: pd.DataFrame, date_col: str = "Timestamp") -> pd.DataFrame:
            from datetime import timedelta

            dt = pd.to_datetime(df[date_col], errors="coerce", utc=True)
            if getattr(dt.dt, "tz", None) is None:
                dt = dt.dt.tz_localize("UTC")

            df = df.copy()
            df[date_col] = dt

            if not df[date_col].notna().any():
                st.warning(f"No valid dates found in column '{date_col}'.")
                return df.iloc[0:0]

            min_date = df[date_col].min().date()
            max_date = df[date_col].max().date()

            datecol1, datecol2, datecol3 = st.columns([1, 1.5, 1])
            with datecol2:
                start_date, end_date = st.slider(
                    "Select date range",
                    min_value=min_date,
                    max_value=max_date,
                    value=(min_date, max_date),
                    step=timedelta(days=1),
                    format="YYYY-MM-DD",
                )

            start_dt = pd.Timestamp(start_date).tz_localize("UTC")
            end_dt_exclusive = pd.Timestamp(end_date).tz_localize("UTC") + pd.Timedelta(days=1)

            mask = (df[date_col] >= start_dt) & (df[date_col] < end_dt_exclusive)
            filtered = df.loc[mask].copy()

            st.caption(f"Showing {len(filtered):,} of {len(df):,} rows from {start_date} to {end_date} (inclusive).")
            return filtered

        # === FILTER ROW ===
        pos_col1, pos_col2, pos_col3, pos_col4, pos_col5 = st.columns([1, 1, 1, 1, 1])
        with pos_col1:
            player_search = st.text_input("Player search", "").strip()
        with pos_col2:
            pos_chosen = st.selectbox("Choose Position", ["Hitters", "Pitchers"])
        with pos_col3:
            h_pos_chosen = st.selectbox("Hitter Pos", ["All", "C", "1B", "2B", "3B", "SS", "OF"])
        with pos_col4:
            team_selection_list.sort()
            team_selection_list = ["All"] + team_selection_list
            team_choose = st.selectbox("Choose Team", team_selection_list)

        # ===== HITERS =====
        if pos_chosen == "Hitters":
            filtered_hitdb = select_and_filter_by_date_slider(hitdb, date_col="game_date")

            # aggregate over chosen date range
            df = (
                filtered_hitdb
                .groupby(["Player", "player_id"], as_index=False)[["R", "HR", "RBI", "SB", "H", "AB"]]
                .sum()
            )

            # merge in position info
            posdata_unique = posdata.drop_duplicates()
            df = pd.merge(df, posdata_unique, how="left", left_on="player_id", right_on="ID")

            df["Pos2"] = df["Pos"].str.split("/", expand=True)[0]
            df["AVG"] = (df["H"] / df["AB"]).round(3)
            df = df[df["AB"] > 9]  # keep only hitters with some AB
            df["Team"] = df["player_id"].map(teamdict)
            df = df[["Player", "player_id", "Team", "Pos2", "AB", "R", "HR", "RBI", "SB", "AVG"]]
            df = df.rename({"Pos2": "Pos"}, axis=1)

            hitter_srv = calculateSRV_Hitters(df)
            # drop AB from the srv frame; we already have it in df
            if "AB" in hitter_srv.columns:
                hitter_srv = hitter_srv.drop(["AB"], axis=1, errors="ignore")

            show_df = pd.merge(df, hitter_srv, on=["Player", "Team", "player_id"], how="left")
            show_df = show_df.round(2)
            show_df = show_df.sort_values(by="SRV", ascending=False)
            show_df['player_id'] = show_df['player_id'].astype(int)

            # apply team filter
            if team_choose != "All":
                show_df = show_df[show_df["Team"] == team_choose]

            # apply hitter pos filter
            if h_pos_chosen != "All":
                show_df = show_df[show_df["Pos"] == h_pos_chosen]

            show_df = show_df[['Player','player_id','Team','Pos','SRV','AB','R','HR','RBI','SB','AVG']]
            # apply player search filter
            if player_search:
                show_df = show_df[show_df["Player"].str.contains(player_search, case=False, na=False)]
            
                show_df = show_df[['Player','player_id','Team','Pos','SRV','AB','R','HR','RBI','SB','AVG']]


            styled_df = (
                show_df.style
                .background_gradient(subset=["SRV"], cmap="Blues")
                .set_table_styles(
                    [{
                        "selector": "th, td",
                        "props": [("font-size", "16px")]
                    }]
                )
                .set_properties(subset=["SRV"], **{"font-weight": "bold", "font-size": "18px"})
                .format({
                    "AB": "{:.0f}",
                    "R": "{:.0f}",
                    "HR": "{:.0f}",
                    "RBI": "{:.0f}",
                    "SB": "{:.0f}",
                    "AVG": "{:.3f}",
                    "SRV": "{:.2f}",
                    "R_z": "{:.2f}",
                    "HR_z": "{:.2f}",
                    "RBI_z": "{:.2f}",
                    "SB_z": "{:.2f}",
                    "AVG_z": "{:.2f}",
                })
            )

            h_rv_showcol1,h_rv_showcol2,h_rv_showcol3 = st.columns([1,3,1])
            with h_rv_showcol2:
                if len(show_df)<2:
                    st.dataframe(
                        styled_df,
                        hide_index=True,
                        use_container_width=True,
                        height=70,
                    )
                    
                else:
                    st.dataframe(
                        styled_df,
                        hide_index=True,
                        use_container_width=True,
                        height=600,
                    )

            st.markdown("<br><hr>",unsafe_allow_html=True)
            # ===== 30-day rolling SRV plot (hitters) =====
            # show only when we've narrowed to exactly one player
            unique_players = show_df["player_id"].dropna().unique()
            if len(unique_players) == 1:
                selected_pid = unique_players[0]

                # build day-by-day 30d SRV for that player
                hd = hitdb.copy()
                hd["game_date"] = pd.to_datetime(hd["game_date"])
                hd = hd.sort_values("game_date")

                all_dates = hd["game_date"].dt.normalize().unique()
                rows = []
                for d in all_dates:
                    start = d - np.timedelta64(29, "D")
                    window = hd[(hd["game_date"] >= start) & (hd["game_date"] <= d)]
                    if window.empty:
                        continue

                    agg = (
                        window.groupby(["Player", "player_id"], as_index=False)[["R", "HR", "RBI", "SB", "H", "AB"]]
                        .sum()
                    )
                    agg["AVG"] = np.where(agg["AB"] > 0, agg["H"] / agg["AB"], 0)
                    agg["Team"] = agg["player_id"].map(teamdict)

                    srv_frame = calculateSRV_Hitters(agg)
                    this_row = srv_frame[srv_frame["player_id"] == selected_pid]
                    if not this_row.empty:
                        rows.append({"date": pd.to_datetime(d).date(), "SRV": float(this_row["SRV"].iloc[0])})

                if rows:
                    srv_hist = pd.DataFrame(rows).sort_values("date")
                    st.subheader(f"30-Day Rolling SRV – {show_df['Player'].iloc[0]}")
                    srv_hist = srv_hist.set_index("date")
                    st.line_chart(srv_hist)

        # ===== PITCHERS =====
        if pos_chosen == "Pitchers":
            rp_only = st.checkbox("Show Only RP?")

            filtered_pitdb = select_and_filter_by_date_slider(pitdb, date_col="game_date")

            df = (
                filtered_pitdb
                .groupby(["Player", "player_id"], as_index=False)[["IP", "ER", "H", "BB", "SO", "W", "SV"]]
                .sum()
            )

            df["ERA"] = (df["ER"] * 9 / df["IP"]).round(3)
            df["WHIP"] = ((df["H"] + df["BB"]) / df["IP"]).round(3)
            df = df[df["IP"] > 1]

            df["Team"] = df["player_id"].map(teamdict_p)
            df = df[["Player", "player_id", "Team", "IP", "W", "SO", "SV", "ERA", "WHIP"]]

            pitcher_srv = calculateSRV_Pitchers(df)
            if "IP" in pitcher_srv.columns:
                pitcher_srv = pitcher_srv.drop(["IP"], axis=1, errors="ignore")

            show_df = pd.merge(df, pitcher_srv, on=["Player", "Team", "player_id"], how="left")
            show_df = show_df.round(2)
            show_df = show_df.sort_values(by="SRV", ascending=False)

            if team_choose != "All":
                show_df = show_df[show_df["Team"] == team_choose]

            if rp_only:
                show_df = show_df[show_df["SV"] > 0]

            if player_search:
                show_df = show_df[show_df["Player"].str.contains(player_search, case=False, na=False)]

            
            show_df = show_df[['Player','player_id','Team','SRV','IP','W','SO','SV','ERA','WHIP']]
            prvcol1,prvcol2,prvcol3 = st.columns([1,5,1])
            with prvcol2:
                styled_df = (
                    show_df.style
                    .background_gradient(subset=["SRV"], cmap="Blues")
                    .set_table_styles(
                        [{
                            "selector": "th, td",
                            "props": [("font-size", "16px")]
                        }]
                    )
                    .set_properties(subset=["SRV"], **{"font-weight": "bold", "font-size": "18px"})
                    .format({
                        "IP": "{:.1f}",
                        "ERA": "{:.2f}",
                        "WHIP": "{:.2f}",
                        "SRV": "{:.2f}",
                        "W_z": "{:.2f}",
                        "SV_z": "{:.2f}",
                        "SO_z": "{:.2f}",
                        "ERA_z": "{:.2f}",
                        "WHIP_z": "{:.2f}",
                    })
                )

                if len(show_df)<2:
                    st.dataframe(
                    styled_df,
                    hide_index=True,
                    use_container_width=True,
                    height=75,
                )
                else:
                    st.dataframe(
                        styled_df,
                        hide_index=True,
                        use_container_width=True,
                        height=600,
                    )

            st.markdown("<br><hr>",unsafe_allow_html=True)
            # ===== 30-day rolling SRV plot (pitchers) =====
            unique_players = show_df["player_id"].dropna().unique()
            if len(unique_players) == 1:
                selected_pid = unique_players[0]

                pdx = pitdb.copy()
                pdx["game_date"] = pd.to_datetime(pdx["game_date"])
                pdx = pdx.sort_values("game_date")
                all_dates = pdx["game_date"].dt.normalize().unique()
                rows = []
                for d in all_dates:
                    start = d - np.timedelta64(29, "D")
                    window = pdx[(pdx["game_date"] >= start) & (pdx["game_date"] <= d)]
                    if window.empty:
                        continue

                    agg = (
                        window.groupby(["Player", "player_id"], as_index=False)[["IP", "ER", "H", "BB", "SO", "W", "SV"]]
                        .sum()
                    )
                    # rebuild rate stats
                    agg = agg[agg["IP"] > 0]
                    agg["ERA"] = (agg["ER"] * 9 / agg["IP"]).round(3)
                    agg["WHIP"] = ((agg["H"] + agg["BB"]) / agg["IP"]).round(3)
                    agg["Team"] = agg["player_id"].map(teamdict_p)

                    srv_frame = calculateSRV_Pitchers(agg)
                    this_row = srv_frame[srv_frame["player_id"] == selected_pid]
                    if not this_row.empty:
                        rows.append({"date": pd.to_datetime(d).date(), "SRV": float(this_row["SRV"].iloc[0])})

                if rows:
                    srv_hist = pd.DataFrame(rows).sort_values("date").set_index("date")
                    st.subheader(f"30-Day Rolling SRV – {show_df['Player'].iloc[0]}")
                    st.line_chart(srv_hist)

    
    if tab == "Player Rater2":
        # --- Load only what this page needs ---
        hitter_stats_raw, lineup_stats, pitcher_stats, h_vs_avg, p_vs_avg, h_vs_sim, hotzonedata, posdata = load_player_stats()
        hitter_stats = hitter_stats_raw.copy()
        hitdb = load_hitdb()
        pitdb = load_pitdb()
        st.markdown("<h1><center>Dynamic Player Rater</center></h1>", unsafe_allow_html=True)
        team_selection_list = list(hitdb['affiliate'].unique())
        teamlist=hitdb[['player_id','game_date','affiliate']].sort_values(by='game_date')
        teamlist[['player_id','affiliate']].drop_duplicates(keep='last')
        teamdict = dict(zip(teamlist.player_id,teamlist.affiliate))

        teamlist_p=pitdb[['player_id','game_date','affiliate']].sort_values(by='game_date')
        teamlist_p[['player_id','affiliate']].drop_duplicates(keep='last')
        teamdict_p = dict(zip(teamlist_p.player_id,teamlist_p.affiliate))

        ### FUNCTIONS
        def calculateSGP_Hitters(hitdb: pd.DataFrame, merge_df: pd.DataFrame | None = None):
            df = hitdb.copy()

            count_cats = ["R", "HR", "RBI", "SB"]
            for cat in count_cats:
                std = df[cat].std(ddof=0)
                df[f"{cat}_z"] = (df[cat] - df[cat].mean()) / (std if std != 0 else 1.0)

            total_ab = df["AB"].sum()
            lg_avg = np.divide((df["AVG"] * df["AB"]).sum(), total_ab) if total_ab else df["AVG"].mean()

            df["AVG_contrib"] = (df["AVG"] - lg_avg) * df["AB"]
            std = df["AVG_contrib"].std(ddof=0)
            df["AVG_z"] = (df["AVG_contrib"] - df["AVG_contrib"].mean()) / (std if std != 0 else 1.0)

            z_cols = [f"{c}_z" for c in count_cats] + ["AVG_z"]
            df["SGP"] = df[z_cols].sum(axis=1)

            df_sorted = (
                df[["Player", "Team", "AB", "SGP"] + z_cols]
                .sort_values("SGP", ascending=False)
                .reset_index(drop=True)
            )

            if merge_df is not None:
                out = merge_df.merge(df_sorted[["Player", "Team", "SGP"]], on=["Player", "Team"], how="left")
                out["SGP"] = out["SGP"].round(2)
                return out.sort_values("SGP", ascending=False)

            return df_sorted
        
        def calculateSGP_Pitchers(pitchdb: pd.DataFrame, merge_df: pd.DataFrame | None = None):
            df = pitchdb.copy()

            count_cats = ["W", "SV", "SO"]
            for cat in count_cats:
                std = df[cat].std(ddof=0)
                df[f"{cat}_z"] = (df[cat] - df[cat].mean()) / (std if std != 0 else 1.0)

            lg_era = np.divide((df["ERA"] * df["IP"]).sum(), df["IP"].sum()) if df["IP"].sum() else df["ERA"].mean()
            df["ERA_contrib"] = (lg_era - df["ERA"]) * df["IP"]
            std = df["ERA_contrib"].std(ddof=0)
            df["ERA_z"] = (df["ERA_contrib"] - df["ERA_contrib"].mean()) / (std if std != 0 else 1.0)

            lg_whip = np.divide((df["WHIP"] * df["IP"]).sum(), df["IP"].sum()) if df["IP"].sum() else df["WHIP"].mean()
            df["WHIP_contrib"] = (lg_whip - df["WHIP"]) * df["IP"]
            std = df["WHIP_contrib"].std(ddof=0)
            df["WHIP_z"] = (df["WHIP_contrib"] - df["WHIP_contrib"].mean()) / (std if std != 0 else 1.0)

            z_cols = [f"{c}_z" for c in count_cats] + ["ERA_z", "WHIP_z"]
            df["SGP"] = df[z_cols].sum(axis=1)

            df_sorted = (
                df[["Player", "Team", "IP", "SGP"] + z_cols]
                .sort_values("SGP", ascending=False)
                .reset_index(drop=True)
            )

            if merge_df is not None:
                out = merge_df.merge(df_sorted[["Player", "Team", "SGP"]], on=["Player", "Team"], how="left")
                out["SGP"] = out["SGP"].round(2)
                return out.sort_values("SGP", ascending=False)

            return df_sorted
        
        def select_and_filter_by_date_slider(df: pd.DataFrame, date_col: str = "Timestamp") -> pd.DataFrame:
            """
            Build a date RANGE SLIDER from the data's min/max dates and
            return df filtered to that inclusive range.
            """
            from datetime import timedelta

            # Parse robustly (e.g., "2025-09-01 13:17:19 EDT")
            dt = pd.to_datetime(df[date_col], errors="coerce", utc=True)
            if getattr(dt.dt, "tz", None) is None:
                dt = dt.dt.tz_localize("UTC")

            df = df.copy()
            df[date_col] = dt

            if not df[date_col].notna().any():
                st.warning(f"No valid dates found in column '{date_col}'.")
                return df.iloc[0:0]

            # Slider uses date (not datetime) for a nice UX
            min_date = df[date_col].min().date()
            max_date = df[date_col].max().date()

            datecol1, datecol2, datecol3 = st.columns([1,1.5,1])
            with datecol2:
                start_date, end_date = st.slider(
                    "Select date range",
                    min_value=min_date,
                    max_value=max_date,
                    value=(min_date, max_date),
                    step=timedelta(days=1),
                    format="YYYY-MM-DD",
                )

            # Inclusive end: [start, end] by filtering < (end + 1 day)
            start_dt = pd.Timestamp(start_date).tz_localize("UTC")
            end_dt_exclusive = pd.Timestamp(end_date).tz_localize("UTC") + pd.Timedelta(days=1)

            mask = (df[date_col] >= start_dt) & (df[date_col] < end_dt_exclusive)
            filtered = df.loc[mask].copy()

            st.caption(f"Showing {len(filtered):,} of {len(df):,} rows from {start_date} to {end_date} (inclusive).")
            return filtered

        
        pos_col1, pos_col2,pos_col3,pos_col4,pos_col5 = st.columns([1,1,1,1,1])
        with pos_col2:
            pos_chosen = st.selectbox('Choose Position',['Hitters','Pitchers'])
        with pos_col3:
            h_pos_chosen = st.selectbox('Hitter Pos',['All','C','1B','2B','3B','SS','OF'])
        with pos_col4:
            team_selection_list.sort()
            team_selection_list = ['All'] + team_selection_list
            team_choose = st.selectbox('Choose Team', team_selection_list)

        if pos_chosen == 'Hitters':
            filtered_hitdb = select_and_filter_by_date_slider(hitdb, date_col="game_date")

            df = filtered_hitdb.groupby(['Player','player_id'],as_index=False)[['R','HR','RBI','SB','H','AB']].sum()
            posdata = posdata.drop_duplicates()
            df = pd.merge(df,posdata,how='left',left_on='player_id', right_on='ID')
            df['Pos2'] = df['Pos'].str.split('/',expand=True)[0]
            df['AVG'] = round(df['H']/df['AB'],3)
            df = df[df['AB']>9]
            df['Team'] = df['player_id'].map(teamdict)
            df = df[['Player','Team','Pos2','AB','R','HR','RBI','SB','AVG']]
            df = df.rename({'Pos2': 'Pos'},axis=1)

            hitter_sgp = calculateSGP_Hitters(df)
            hitter_sgp = hitter_sgp.drop(['AB'],axis=1)
            show_df = pd.merge(df,hitter_sgp,on=['Player','Team'],how='left')
            show_df = show_df.round(2)
            show_df = show_df.sort_values(by='SGP',ascending=False)

            if team_choose == 'All':
                pass
            else:
                show_df = show_df[show_df['Team']==team_choose]

            if h_pos_chosen == 'All':
                pass
            else:
                show_df = show_df[show_df['Pos']==h_pos_chosen]

            

            styled_df = (
                show_df.style
                .background_gradient(subset=["SGP"], cmap="Blues")   # blue shading on SGP
                .set_table_styles(                                   # make text bigger
                    [{
                        "selector": "th, td",
                        "props": [("font-size", "16px")]
                    }]
                ).set_properties(subset=["SGP"], **{"font-weight": "bold", "font-size": "18px"})
                .format({"AB": "{:.0f}",
                        "R": "{:.0f}",
                        "HR": "{:.0f}",
                        "RBI": "{:.0f}",
                        "SB": "{:.0f}",
                        "AVG": "{:.3f}",
                        "SGP": "{:.2f}",
                        "R_z": "{:.2f}",
                        "HR_z": "{:.2f}",
                        "RBI_z": "{:.2f}",
                        "SB_z": "{:.2f}",
                        "AVG_z": "{:.2f}",})
                )

            st.dataframe(
                styled_df, hide_index=True,
                use_container_width=True,   # stretch across page
                height=600                  # adjust height to your liking
            )
        if pos_chosen == 'Pitchers':
            rp_only = st.checkbox('Show Only RP?')

            filtered_pitdb = select_and_filter_by_date_slider(pitdb, date_col="game_date")

            df = filtered_pitdb.groupby(['Player','player_id'],as_index=False)[['IP','ER','H','BB','SO','W','SV']].sum()

            df['ERA'] = round(df['ER']*9/df['IP'],3)
            df['WHIP'] = round((df['H']+df['BB'])/df['IP'],3)

            df = df[df['IP']>1]
            df['Team'] = df['player_id'].map(teamdict_p)
            df = df[['Player','Team','IP','W','SO','SV','ERA','WHIP']]

            pitcher_sgp = calculateSGP_Pitchers(df)
            pitcher_sgp = pitcher_sgp.drop(['IP'],axis=1)
            show_df = pd.merge(df,pitcher_sgp,on=['Player','Team'],how='left')
            show_df = show_df.round(2)
            show_df = show_df.sort_values(by='SGP',ascending=False)

            if team_choose == 'All':
                pass
            else:
                show_df = show_df[show_df['Team']==team_choose]

            if rp_only:
                show_df = show_df[show_df['SV']>0]

            styled_df = (
                show_df.style
                .background_gradient(subset=["SGP"], cmap="Blues")   # blue shading on SGP
                .set_table_styles(                                   # make text bigger
                    [{
                        "selector": "th, td",
                        "props": [("font-size", "16px")]
                    }]
                ).set_properties(subset=["SGP"], **{"font-weight": "bold", "font-size": "18px"})
                .format({"IP": "{:.1f}",
                         "ERA": "{:.2f}",
                         "WHIP": "{:.2f}",
                         "SGP": "{:.2f}",
                         "W_z": "{:.2f}",
                         "SV_z": "{:.2f}",
                         "SO_z": "{:.2f}",
                         "ERA_z": "{:.2f}",
                         "WHIP_z": "{:.2f}",
                         })
                )

            st.dataframe(
                styled_df, hide_index=True,
                use_container_width=True,   # stretch across page
                height=600                  # adjust height to your liking
            )
    
    if tab == "Game Previews":
        #work_in_progress()

        require_pro()
        # --- Load only what this page needs ---
        hitterproj_raw, pitcherproj_raw, hitterproj2, gameinfo_raw = load_daily_projections()
        hitter_stats_raw, lineup_stats, pitcher_stats, h_vs_avg, p_vs_avg, h_vs_sim, hotzonedata, posdata = load_player_stats()
        bpreport_raw, rpstats = load_bullpen_data()
        umpire_data, weather_data = load_weather_umps()


        props_df, ownershipdf, allbets, alllines, bet_tracker = load_betting_data()
        if len(weather_data) < 1:
            weather_data = pd.DataFrame()
        team_vs_sim = h_vs_sim[h_vs_sim['PC'] > 49].groupby('Team', as_index=False)[['xwOBA','SwStr%','AVG','SLG','Brl%','FB%']].mean()
        team_vs_sim['RawRank'] = len(team_vs_sim) - team_vs_sim['xwOBA'].rank() + 1
        team_vs_sim['Rank'] = team_vs_sim['RawRank'].astype(int).astype(str) + '/' + str(len(team_vs_sim))
        
        (hitterproj, pitcherproj, hitter_stats, gameinfo, bpreport,
         games_df, mainslateteams, main_slate_gamelist,
         confirmed_lus, last_update) = _prepare_projection_data(
            hitterproj_raw, pitcherproj_raw, hitterproj2, gameinfo_raw,
            hitter_stats_raw, h_vs_avg, bpreport_raw)
        
        game_selection = list(gameinfo['GameString'].unique())
        selected_game = st.selectbox('Select a Game', game_selection, help="Select a game to view detailed projections and stats.")

        selected_home_team = selected_game.split('@')[1]
        selected_road_team = selected_game.split('@')[0]

        road_bullpen_team = bpreport[bpreport['Team']==selected_road_team]
        road_bullpen_rp = rpstats[rpstats['Team']==selected_road_team]

        home_bullpen_team = bpreport[bpreport['Team']==selected_home_team]
        home_bullpen_rp = rpstats[rpstats['Team']==selected_home_team]

        home_lineup_stats = lineup_stats[lineup_stats['Opp']==selected_home_team]
        road_lineup_stats = lineup_stats[lineup_stats['Opp']==selected_road_team]

        these_sim = h_vs_sim[h_vs_sim['Team'].isin([selected_home_team,selected_road_team])]

        this_game_ump = umpire_data[umpire_data['HomeTeam'] == selected_home_team]
        known_ump = 'Y' if len(this_game_ump) > 0 else 'N'

        these_pitcherproj = pitcherproj[pitcherproj['GameString'] == selected_game]
        try:
            this_weather = weather_data[weather_data['HomeTeam'] == selected_home_team]
            this_winds = this_weather['Winds'].iloc[0]
            this_winds = this_winds.replace(' mph','')
            this_winds = float(this_winds)
        except:
            this_winds = ''
        
        try:
            if this_weather['Rain%'].iloc[0]>25:
                rain_emoji = '🌧️'
            else:
                rain_emoji = ''
            if this_winds > 10:
                winds_emoji = '💨'
            else:
                winds_emoji = ''
        except:
            winds_emoji = ''
            rain_emoji = ''
        
        weather_emoji = rain_emoji + ' ' + winds_emoji
        try:
            game_name = this_weather['Game'].iloc[0]
        except:
            game_name = selected_game
        try:
            this_gameinfo = gameinfo[gameinfo['Park']==selected_home_team]
            this_gametime = this_gameinfo['game_time'].iloc[0]
            this_gameinfo['Favorite'] = np.where(this_gameinfo['moneyline']<-100,1,0)
            this_favorite = this_gameinfo[this_gameinfo['Favorite']==1]['team'].iloc[0]
            this_favorite_odds = this_gameinfo[this_gameinfo['Favorite']==1]['moneyline'].iloc[0]
            this_over_under = this_gameinfo['overunder'].iloc[0]
            game_info_fail = 'N'
        except:
            game_info_fail = 'Y'
            this_favorite=''
            this_favorite_odds=''
            this_over_under=''
        #st.write(this_gameinfo)

        # Get pitcher matchups
        road_sp_pid = str(these_pitcherproj[these_pitcherproj['Team'] == these_pitcherproj['RoadTeam']]['ID'].iloc[0]).replace('.0', '')
        road_sp_name = these_pitcherproj[these_pitcherproj['Team'] == these_pitcherproj['RoadTeam']]['Pitcher'].iloc[0]
        home_sp_pid = str(these_pitcherproj[these_pitcherproj['Team'] == these_pitcherproj['HomeTeam']]['ID'].iloc[0]).replace('.0', '')
        home_sp_name = these_pitcherproj[these_pitcherproj['Team'] == these_pitcherproj['HomeTeam']]['Pitcher'].iloc[0]

        p_proj_cols = ['Sal', 'DKPts', 'Val', 'PC','IP', 'H', 'ER', 'SO', 'BB', 'W', 'Ownership']
        road_sp_projection = these_pitcherproj[these_pitcherproj['Pitcher'] == road_sp_name]
        home_sp_projection = these_pitcherproj[these_pitcherproj['Pitcher'] == home_sp_name]
        p_stats_cols = ['IP', 'K%', 'BB%', 'SwStr%', 'Ball%', 'xwOBA']
        road_sp_stats = pitcher_stats[pitcher_stats['Pitcher'] == road_sp_name]
        
        if len(road_sp_stats)>0:
            road_sp_hand = road_sp_stats['Hand'].iloc[0]
            is_road_p_hot = road_sp_stats['IsHot'].iloc[0]
            is_road_p_cold = road_sp_stats['IsCold'].iloc[0]
        else:
            road_sp_hand = 'R'
            is_road_p_hot = 0
            is_road_p_cold = 0
        if is_road_p_hot == 1:
            road_p_emoji = '🔥'
        elif is_road_p_cold == 1:
            road_p_emoji = '🥶'
        else:
            road_p_emoji = ''
        
        home_sp_stats = pitcher_stats[pitcher_stats['Pitcher'] == home_sp_name]
        
        if len(home_sp_stats)>0:
            home_sp_hand = home_sp_stats['Hand'].iloc[0]
            is_home_p_hot = home_sp_stats['IsHot'].iloc[0]
            is_home_p_cold = home_sp_stats['IsCold'].iloc[0]
        else:
            home_sp_hand = 'R'
            is_home_p_hot = 0
            is_home_p_cold = 0
        
        if is_home_p_hot == 1:
            home_p_emoji = '🔥'
        elif is_home_p_cold == 1:
            home_p_emoji = '🥶'
        else:
            home_p_emoji = ''
        
        road_sp_show_name = road_sp_name + ' ' + road_p_emoji
        home_sp_show_name = home_sp_name + ' ' + home_p_emoji
        pitcher_props = props_df[props_df['Player'].isin([road_sp_name,home_sp_name])]
        pitcher_props = pitcher_props[pitcher_props['Type']!='pitcher_outs']
        # Player profiles in cards
        col1, col2, col3 = st.columns([2, 4, 2])
        with col1:
            st.markdown(
                f"""
                <div class="player-card">
                    <img src="{get_player_image(road_sp_pid)}" width="150" style="border-radius: 10px;">
                    <h4>{road_sp_show_name}</h4>
                </div>
                """,
                unsafe_allow_html=True
            )
        with col2:
            st.markdown(f"<center><h2>{game_name} {rain_emoji} </h2></center>", unsafe_allow_html=True)
            st.markdown(f"<center><h5>{road_sp_show_name} vs. {home_sp_show_name}</h5></center>", unsafe_allow_html=True)
            st.markdown(f"<center><h6><i>{this_gametime}</i></h6></center>", unsafe_allow_html=True)

            if game_info_fail == 'N':
                st.markdown(f"<center><h5>{this_favorite} ({this_favorite_odds}), O/U: {this_over_under}</h5></center>",unsafe_allow_html=True)
            
            try:
                weather_cond = this_weather['Conditions'].iloc[0]
                weather_temp = this_weather['Temp'].iloc[0]
            except:
                weather_cond = ''
                weather_temp = ''
            
            try:
                try:
                    weather_winds = this_weather['Winds'].iloc[0] + ' ' + this_weather['Wind Dir'].iloc[0]
                except:
                    weather_winds = this_weather.get('Winds', ['No Weather Data Found']).iloc[0]
            except:
                weather_winds = ''
            st.markdown(f"<center><b>{weather_emoji} Weather: {weather_cond}, {weather_temp}F<br>Winds: {weather_winds}</b></center>", unsafe_allow_html=True)
            if known_ump == 'Y':
                umpname = this_game_ump['Umpire'].iloc[0]
                k_boost = (this_game_ump['K Boost'].iloc[0] - 1) * 100
                k_symbol = '+' if k_boost > 0 else '' if k_boost == 0 else ''
                bb_boost = (this_game_ump['BB Boost'].iloc[0] - 1) * 100
                bb_symbol = '+' if bb_boost > 0 else '' if bb_boost == 0 else ''
                st.markdown(f"<center><b>Umpire: {umpname}<br>{k_symbol}{int(k_boost)}% K, {bb_symbol}{int(bb_boost)}% BB</b></center>", unsafe_allow_html=True)
            
            st.markdown("<br><center><font size=3>🔥 <i>= hot player</i>, 🥶 <i>= cold player</i>, 🚀 elevated HR proj</center></i></font>", unsafe_allow_html=True)
        
        with col3:
            st.markdown(
                f"""
                <div class="player-card">
                    <img src="{get_player_image(home_sp_pid)}" width="150" style="border-radius: 10px;">
                    <h4>{home_sp_show_name}</h4>
                </div>
                """,
                unsafe_allow_html=True
            )

        # Pitcher projections
        col1, col2, col3 = st.columns([1,1,5])
        with col1:
            bp_checked = st.checkbox("Show Bullpens", value=False, key=None, help=None, on_change=None)
        with col2:
            lu_checked = st.checkbox("Show Lineup Stats", value=False, key=None, help=None, on_change=None)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"<h4>{road_sp_name} Projection</h4>", unsafe_allow_html=True)
            filtered_pproj = road_sp_projection[p_proj_cols].rename({'Ownership': 'Own%'}, axis=1)
            styled_df = filtered_pproj.style.apply(
                color_cells_PitchProj, subset=['DKPts', 'Sal', 'Val','IP','H','ER','PC','SO','BB','W','Own%'], axis=1
            ).format({
                'Own%': '{:.0f}', 'Sal': '${:,.0f}', 'W': '{:.2f}', 'BB': '{:.2f}', 'PC': '{:.1f}',
                'SO': '{:.2f}', 'ER': '{:.2f}', 'H': '{:.2f}', 'IP': '{:.1f}',
                'DKPts': '{:.2f}', 'Val': '{:.2f}'
            })
            st.dataframe(styled_df, hide_index=True, use_container_width=True)
            st.markdown("<h4>2024-2025 Stats</h4>", unsafe_allow_html=True)
            show_all_df = road_sp_stats[p_stats_cols].assign(vs='All')
            vs_r_df = road_sp_stats[['IP RHB', 'K% RHB', 'BB% RHB', 'SwStr% RHB', 'Ball% RHB', 'xwOBA RHB']].assign(vs='RHB')
            vs_r_df.columns = ['IP', 'K%', 'BB%', 'SwStr%', 'Ball%', 'xwOBA', 'vs']
            vs_l_df = road_sp_stats[['IP LHB', 'K% LHB', 'BB% LHB', 'SwStr% LHB', 'Ball% LHB', 'xwOBA LHB']].assign(vs='LHB')
            vs_l_df.columns = ['IP', 'K%', 'BB%', 'SwStr%', 'Ball%', 'xwOBA', 'vs']
            stats_build = pd.concat([show_all_df, vs_r_df, vs_l_df]).reset_index(drop=True)[['vs', 'IP', 'K%', 'BB%', 'SwStr%', 'Ball%', 'xwOBA']]
            styled_df = stats_build.style.apply(
                color_cells_PitchStat, subset=['K%', 'BB%', 'SwStr%', 'Ball%', 'xwOBA'], axis=1
            ).format({
                'K%': '{:.1%}', 'BB%': '{:.1%}', 'SwStr%': '{:.1%}', 'Ball%': '{:.1%}', 'xwOBA': '{:.3f}', 'IP': '{:.1f}'
            })
            st.dataframe(styled_df, hide_index=True, use_container_width=True)

            #lu_checked = st.checkbox("Show Lineup Stats", value=False, key=None, help=None, on_change=None)
            if lu_checked:
                ### lineup stuff
                home_lineup_stats = home_lineup_stats[['K%','BB%','Brl%','GB%','FB%','xwOBA','PPA']]
                st.markdown(f"<h4>{selected_home_team} Lineup Stats</h4>", unsafe_allow_html=True)
                styled_df = home_lineup_stats.style.apply(
                    color_cells_HitStat, subset=['K%', 'BB%', 'Brl%', 'GB%', 'FB%','PPA','xwOBA'], axis=1
                ).format({
                    'K%': '{:.1%}', 'BB%': '{:.1%}', 'GB%': '{:.1%}', 'FB%': '{:.1%}', 'Brl%': '{:.1%}', 'xwOBA': '{:.3f}', 'PPA': '{:.3f}', 'IP': '{:.1f}'
                })
                st.dataframe(styled_df,hide_index=True,width=450)

        with col2:
            st.markdown(f"<h4>{home_sp_name} Projection</h4>", unsafe_allow_html=True)
            filtered_pproj = home_sp_projection[p_proj_cols].rename({'Ownership': 'Own%'}, axis=1)
            styled_df = filtered_pproj.style.apply(
                color_cells_PitchProj, subset=['DKPts', 'Sal','PC', 'Val','IP','H','ER','SO','BB','W','Own%'], axis=1
            ).format({
                'Own%': '{:.0f}', 'Sal': '${:,.0f}', 'W': '{:.2f}', 'BB': '{:.2f}', 'PC': '{:.0f}',
                'SO': '{:.2f}', 'ER': '{:.2f}', 'H': '{:.2f}', 'IP': '{:.1f}',
                'DKPts': '{:.2f}', 'Val': '{:.2f}'
            })
            st.dataframe(styled_df, hide_index=True, use_container_width=True)
            st.markdown("<h4>2024-2025 Stats</h4>", unsafe_allow_html=True)
            show_all_df = home_sp_stats[p_stats_cols].assign(vs='All')
            vs_r_df = home_sp_stats[['IP RHB', 'K% RHB', 'BB% RHB', 'SwStr% RHB', 'Ball% RHB', 'xwOBA RHB']].assign(vs='RHB')
            vs_r_df.columns = ['IP', 'K%', 'BB%', 'SwStr%', 'Ball%', 'xwOBA', 'vs']
            vs_l_df = home_sp_stats[['IP LHB', 'K% LHB', 'BB% LHB', 'SwStr% LHB', 'Ball% LHB', 'xwOBA LHB']].assign(vs='LHB')
            vs_l_df.columns = ['IP', 'K%', 'BB%', 'SwStr%', 'Ball%', 'xwOBA', 'vs']
            stats_build = pd.concat([show_all_df, vs_r_df, vs_l_df]).reset_index(drop=True)[['vs', 'IP', 'K%', 'BB%', 'SwStr%', 'Ball%', 'xwOBA']]
            styled_df = stats_build.style.apply(
                color_cells_PitchStat, subset=['K%', 'BB%', 'SwStr%', 'Ball%', 'xwOBA'], axis=1
            ).format({
                'K%': '{:.1%}', 'BB%': '{:.1%}', 'SwStr%': '{:.1%}', 'Ball%': '{:.1%}', 'xwOBA': '{:.3f}', 'IP': '{:.1f}'
            })
            st.dataframe(styled_df, hide_index=True, use_container_width=True)

            if lu_checked:
                road_lineup_stats = road_lineup_stats[['K%','BB%','Brl%','GB%','FB%','xwOBA','PPA']]
                st.markdown(f"<h4>{selected_road_team} Lineup Stats</h4>", unsafe_allow_html=True)
                styled_df = road_lineup_stats.style.apply(
                    color_cells_HitStat, subset=['K%', 'BB%', 'Brl%', 'GB%', 'FB%','PPA','xwOBA'], axis=1
                ).format({
                    'K%': '{:.1%}', 'BB%': '{:.1%}', 'GB%': '{:.1%}', 'FB%': '{:.1%}', 'Brl%': '{:.1%}', 'xwOBA': '{:.3f}', 'PPA': '{:.3f}', 'IP': '{:.1f}'
                })
                st.dataframe(styled_df,hide_index=True,width=450)

        
        # Bullpens
        #checked = st.checkbox("Show Bullpens", value=False, key=None, help=None, on_change=None)
        if bp_checked:
            #st.write("Checkbox is checked!")

            col1, col2 = st.columns([1,1])
            with col1:
                team_rp_list = rpstats[rpstats['Team']==selected_road_team]
                team_rp_rhp = len(team_rp_list[team_rp_list['Hand']=='R'])
                team_rp_lhp = len(team_rp_list[team_rp_list['Hand']=='L'])
                road_bp_unavail = road_bullpen_team['Unavailable'].iloc[0]
                st.markdown(f"<h4>{selected_road_team} Bullpen</h4>", unsafe_allow_html=True)
                    
                show_road_bullpen = road_bullpen_team[['Rank','K%','BB%','K-BB%','SwStr%','xwOBA','xERA']]
                show_road_bullpen = road_bullpen_team[['Rank','K%','BB%','K-BB%','SwStr%','xwOBA','xERA']]
                show_road_bullpen['RHP'] = team_rp_rhp
                show_road_bullpen['LHP'] = team_rp_lhp

                styled_df = show_road_bullpen.style.apply(
                    color_cells_PitchStat, subset=['K%','BB%','K-BB%','SwStr%','xwOBA','xERA'], axis=1).format({
                        'K%': '{:.1%}','BB%': '{:.1%}', 'K-BB%': '{:.1%}','SwStr%': '{:.1%}','xwOBA': '{:.3f}','xERA': '{:.2f}'})
                st.dataframe(styled_df, hide_index=True)
                try:
                    if len(road_bp_unavail)>1:
                        st.write(f'Unavailable: {road_bp_unavail}')
                except:
                    pass
            
                team_rp_list = team_rp_list[['Player','Hand','K%','BB%','SwStr%','estimated_woba_using_speedangle']]
                team_rp_list = team_rp_list.rename({'estimated_woba_using_speedangle': 'xwOBA'},axis=1)
                styled_df = team_rp_list.style.apply(
                    color_cells_PitchStat, subset=['K%','BB%','SwStr%','xwOBA'], axis=1).format({
                        'K%': '{:.1%}','BB%': '{:.1%}', 'K-BB%': '{:.1%}','SwStr%': '{:.1%}','xwOBA': '{:.3f}','xERA': '{:.2f}'})
                st.dataframe(styled_df, hide_index=True,width=500)
            
            with col2:
                team_rp_list = rpstats[rpstats['Team']==selected_home_team]
                team_rp_rhp = len(team_rp_list[team_rp_list['Hand']=='R'])
                team_rp_lhp = len(team_rp_list[team_rp_list['Hand']=='L'])

                home_bp_unavail = home_bullpen_team['Unavailable'].iloc[0]
                #st.write(home_bp_unavail)
                st.markdown(f"<h4>{selected_home_team} Bullpen </h4>", unsafe_allow_html=True)

                show_home_bullpen = home_bullpen_team[['Rank','K%','BB%','K-BB%','SwStr%','xwOBA','xERA']]
                show_home_bullpen['RHP'] = team_rp_rhp
                show_home_bullpen['LHP'] = team_rp_lhp
                
                styled_df = show_home_bullpen.style.apply(
                    color_cells_PitchStat, subset=['K%','BB%','K-BB%','SwStr%','xwOBA','xERA'], axis=1).format({
                        'K%': '{:.1%}','BB%': '{:.1%}', 'K-BB%': '{:.1%}','SwStr%': '{:.1%}','xwOBA': '{:.3f}','xERA': '{:.2f}'})
                st.dataframe(styled_df, hide_index=True)

                try:
                    if len(home_bp_unavail)>1:
                        st.write(f'Unavailable: {home_bp_unavail}')
                except:
                    pass
                    
                team_rp_list = team_rp_list[['Player','Hand','K%','BB%','SwStr%','estimated_woba_using_speedangle']]
                team_rp_list = team_rp_list.rename({'estimated_woba_using_speedangle': 'xwOBA'},axis=1)
                styled_df = team_rp_list.style.apply(
                    color_cells_PitchStat, subset=['K%','BB%','SwStr%','xwOBA'], axis=1).format({
                        'K%': '{:.1%}','BB%': '{:.1%}', 'K-BB%': '{:.1%}','SwStr%': '{:.1%}','xwOBA': '{:.3f}','xERA': '{:.2f}'})
                st.dataframe(styled_df, hide_index=True,width=500)

        # Hitter projections/stats
        col1, col2 = st.columns([1, 3])
        with col1:
            option = st.selectbox(
                label="View Options",
                options=["Team Matchup", "Best Matchups", "Projections","Projection vs. Avg", "Stats", "Splits", "Matchups", "Props"],
                index=0,
                help="Choose to view hitter projections, stats, or splits."
            )
        if option == "Team Matchup":
            col1, col2 = st.columns(2)
            with col1:
                road_team_matchups = team_vs_sim[team_vs_sim['Team']==selected_home_team]
                road_team_matchups = road_team_matchups[['Team','Rank','xwOBA','SwStr%','AVG','SLG','Brl%','FB%']]
                styled_df = road_team_matchups.style.apply(color_cells_HitMatchups, subset=['AVG','SLG','xwOBA','SwStr%','Brl%','FB%'], axis=1).format({'xwOBA': '{:.3f}',
                                                                                                            'xwOBA Con': '{:.3f}',
                                                                                                            'SwStr%': '{:.1%}', 'AVG':  '{:.3f}',
                                                                                                            'Brl%': '{:.1%}','SLG':  '{:.3f}',
                                                                                                            'FB%': '{:.1%}',
                                                                                                            'Hard%': '{:.1%}',})
                st.dataframe(styled_df, hide_index=True, use_container_width=True)
            
            with col2:
                home_team_matchups = team_vs_sim[team_vs_sim['Team']==selected_road_team]
                home_team_matchups = home_team_matchups[['Team','Rank','xwOBA','SwStr%','AVG','SLG','Brl%','FB%']]
                styled_df = home_team_matchups.style.apply(color_cells_HitMatchups, subset=['AVG','SLG','xwOBA','SwStr%','Brl%','FB%'], axis=1).format({'xwOBA': '{:.3f}',
                                                                                                            'xwOBA Con': '{:.3f}',
                                                                                                            'SwStr%': '{:.1%}', 'AVG':  '{:.3f}',
                                                                                                            'Brl%': '{:.1%}','SLG':  '{:.3f}',
                                                                                                            'FB%': '{:.1%}',
                                                                                                            'Hard%': '{:.1%}',})
                st.dataframe(styled_df, hide_index=True, use_container_width=True)

        if option == "Projection vs. Avg":
            luspotdict = dict(zip(hitterproj.Hitter,hitterproj.LU))
            h_vs_avg = h_vs_avg.drop(['Unnamed: 0'],axis=1)
            col1, col2 = st.columns(2)
            with col1:
                if selected_road_team in confirmed_lus:
                    lu_confirmation_string = 'Confirmed'
                else:
                    lu_confirmation_string = 'Not Confirmed'
                st.markdown(f"<h4>{selected_road_team} Lineup ({lu_confirmation_string})</h4>", unsafe_allow_html=True)
                road_projection_oa = h_vs_avg[h_vs_avg['Team'] == selected_road_team]
                road_projection_oa['Spot'] = road_projection_oa['Hitter'].map(luspotdict)
                road_projection_oa['Boost'] = road_projection_oa['DKPts']/road_projection_oa['Avg DK Proj']
                road_projection_oa = road_projection_oa[['Hitter','Spot','DKPts','Avg DK Proj','DKPts Diff','Boost']].sort_values(by='Spot')
                road_projection_oa = road_projection_oa.round(2)
                styled_df = road_projection_oa.style.apply(color_cells_HitProj, subset=['DKPts','Avg DK Proj','Boost'], axis=1).format({'DKPts': '{:.2f}', 'Avg DK Proj': '{:.2f}', 'DKPts Diff': '{:.2f}', 'Boost': '{:.2f}'})                         
                st.dataframe(styled_df,hide_index=True)
            with col2:
                if selected_home_team in confirmed_lus:
                    lu_confirmation_string = 'Confirmed'
                else:
                    lu_confirmation_string = 'Not Confirmed'
                st.markdown(f"<h4>{selected_home_team} Lineup ({lu_confirmation_string})</h4>", unsafe_allow_html=True)
                home_projection_oa = h_vs_avg[h_vs_avg['Team'] == selected_home_team]
                home_projection_oa['Spot'] = home_projection_oa['Hitter'].map(luspotdict)
                home_projection_oa['Boost'] = home_projection_oa['DKPts']/home_projection_oa['Avg DK Proj']
                home_projection_oa = home_projection_oa[['Hitter','Spot','DKPts','Avg DK Proj','DKPts Diff','Boost']].sort_values(by='Spot')
                home_projection_oa = home_projection_oa.round(2)
                styled_df = home_projection_oa.style.apply(color_cells_HitProj, subset=['DKPts','Avg DK Proj','Boost'], axis=1).format({'DKPts': '{:.2f}', 'Avg DK Proj': '{:.2f}', 'DKPts Diff': '{:.2f}', 'Boost': '{:.2f}'})                         
                st.dataframe(styled_df,hide_index=True)
                


        if option == 'Projections':
            avg_merge = h_vs_avg[['Hitter','DKPts Diff']]
            avg_merge.columns=['Batter','ProjOA']
            oa_look = dict(zip(avg_merge.Batter,avg_merge.ProjOA))
            col1, col2 = st.columns(2)
            hitter_proj_cols = ['Batter', 'Pos', 'LU', 'Sal', 'DKPts', 'HR', 'SB']
            with col1:
                if selected_road_team in confirmed_lus:
                    lu_confirmation_string = 'Confirmed'
                else:
                    lu_confirmation_string = 'Not Confirmed'
                st.markdown(f"<h4>{selected_road_team} Lineup ({lu_confirmation_string})</h4>", unsafe_allow_html=True)
                road_projection_data = hitterproj[hitterproj['Team'] == selected_road_team][hitter_proj_cols]
                styled_df = road_projection_data.style.apply(
                    color_cells_HitProj, subset=['DKPts', 'Sal', 'HR', 'SB'], axis=1
                ).format({
                    'DKPts': '{:.2f}', 'Value': '{:.2f}', 'Sal': '${:,.0f}',
                    'PA': '{:.1f}', 'R': '{:.2f}', 'HR': '{:.2f}', 'RBI': '{:.2f}', 'SB': '{:.2f}'
                })
                st.dataframe(styled_df, hide_index=True, use_container_width=True)
            with col2:
                if selected_road_team in confirmed_lus:
                    lu_confirmation_string = 'Confirmed'
                else:
                    lu_confirmation_string = 'Not Confirmed'
                st.markdown(f"<h4>{selected_home_team} Lineup ({lu_confirmation_string})</h4>", unsafe_allow_html=True)
                home_projection_data = hitterproj[hitterproj['Team'] == selected_home_team][hitter_proj_cols]
                styled_df = home_projection_data.style.apply(
                    color_cells_HitProj, subset=['DKPts',  'Sal', 'HR', 'SB'], axis=1
                ).format({
                    'DKPts': '{:.2f}', 'Value': '{:.2f}', 'Sal': '${:,.0f}',
                    'PA': '{:.1f}', 'R': '{:.2f}', 'HR': '{:.2f}', 'RBI': '{:.2f}', 'SB': '{:.2f}'
                })
                st.dataframe(styled_df, hide_index=True, use_container_width=True)
        elif option in ['Stats', 'Splits']:
            road_hitter_stats = hitter_stats[hitter_stats['Team'] == selected_road_team]
            home_hitter_stats = hitter_stats[hitter_stats['Team'] == selected_home_team]
            if option == 'Stats':
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"<h4>{selected_road_team} Stats</h4>", unsafe_allow_html=True)
                    road_hitter_stats = road_hitter_stats[['Batter', 'PA', 'K%', 'BB%', 'Brl%', 'xwOBA', 'FB%']]
                    styled_df = road_hitter_stats.style.apply(
                        color_cells_HitStat, subset=['Brl%', 'FB%', 'K%', 'BB%', 'xwOBA'], axis=1
                    ).format({
                        'K%': '{:.1%}', 'BB%': '{:.1%}', 'FB%': '{:.1%}', 'PA': '{:.0f}', 'Brl%': '{:.1%}', 'xwOBA': '{:.3f}'
                    })
                    st.dataframe(styled_df, hide_index=True, use_container_width=True)
                with col2:
                    st.markdown(f"<h4>{selected_home_team} Stats</h4>", unsafe_allow_html=True)
                    home_hitter_stats = home_hitter_stats[['Batter', 'PA', 'K%', 'BB%', 'Brl%', 'xwOBA', 'FB%']]
                    styled_df = home_hitter_stats.style.apply(
                        color_cells_HitStat, subset=['Brl%', 'FB%', 'K%', 'BB%', 'xwOBA'], axis=1
                    ).format({
                        'K%': '{:.1%}', 'BB%': '{:.1%}', 'FB%': '{:.1%}', 'PA': '{:.0f}', 'Brl%': '{:.1%}', 'xwOBA': '{:.3f}'
                    })
                    st.dataframe(styled_df, hide_index=True, use_container_width=True)
            elif option == 'Splits':
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"<h4>{selected_road_team} vs. {home_sp_hand}HP</h4>", unsafe_allow_html=True)
                    road_hitter_splits = road_hitter_stats[['Batter', 'Split PA', 'Split K%', 'Split BB%', 'Split Brl%', 'Split xwOBA', 'Split FB%']]
                    road_hitter_splits.columns = ['Hitter', 'PA', 'K%', 'BB%', 'Brl%', 'xwOBA', 'FB%']
                    styled_df = road_hitter_splits.style.apply(
                        color_cells_HitStat, subset=['Brl%', 'FB%', 'K%', 'BB%', 'xwOBA'], axis=1
                    ).format({
                        'K%': '{:.1%}', 'BB%': '{:.1%}', 'FB%': '{:.1%}', 'PA': '{:.0f}', 'Brl%': '{:.1%}', 'xwOBA': '{:.3f}'
                    })
                    st.dataframe(styled_df, hide_index=True, use_container_width=True)
                with col2:
                    st.markdown(f"<h4>{selected_home_team} vs. {road_sp_hand}HP</h4>", unsafe_allow_html=True)
                    home_hitter_splits = home_hitter_stats[['Batter', 'Split PA', 'Split K%', 'Split BB%', 'Split Brl%', 'Split xwOBA', 'Split FB%']]
                    home_hitter_splits.columns = ['Hitter', 'PA', 'K%', 'BB%', 'Brl%', 'xwOBA', 'FB%']
                    styled_df = home_hitter_splits.style.apply(
                        color_cells_HitStat, subset=['Brl%', 'FB%', 'K%', 'BB%', 'xwOBA'], axis=1
                    ).format({
                        'K%': '{:.1%}', 'BB%': '{:.1%}', 'FB%': '{:.1%}', 'PA': '{:.0f}', 'Brl%': '{:.1%}', 'xwOBA': '{:.3f}'
                    })
                    st.dataframe(styled_df, hide_index=True, use_container_width=True)
        elif option == "Matchups":
            st.markdown(f"<b><i>Matchups is an algorithm that finds hitter stats against similar pitch movements as the ones they will see in this matchup</b></i>", unsafe_allow_html=True)
            col1, col2 = st.columns([1,1])
            with col1:
                road_sim = these_sim[these_sim['Team']==selected_road_team]
                #avg_matchup = road_sim[road_sim['PC']>99][['xwOBA','xwOBA Con','Brl%','FB%']].mean()
                #st.write(avg_matchup)
                #road_sim = road_sim[(road_sim['xwOBA Con']>=.375)&(road_sim['SwStr%']<.11)]
                road_sim = road_sim[['Hitter','PC','xwOBA','xwOBA Con','SwStr%','Brl%','FB%','Hard%']]
                styled_df = road_sim.style.apply(color_cells_HitMatchups, subset=['xwOBA','xwOBA Con',
                                                                                'SwStr%','Brl%','FB%',
                                                                                'Hard%'], axis=1).format({'xwOBA': '{:.3f}',
                                                                                                            'xwOBA Con': '{:.3f}',
                                                                                                            'SwStr%': '{:.1%}',
                                                                                                            'Brl%': '{:.1%}',
                                                                                                            'FB%': '{:.1%}',
                                                                                                            'Hard%': '{:.1%}',})
                st.dataframe(styled_df, hide_index=True, use_container_width=True)
                #st.dataframe(road_sim)
            with col2:
                home_sim = these_sim[these_sim['Team']==selected_home_team]
                #home_sim = home_sim[(home_sim['xwOBA Con']>=.375)&(home_sim['SwStr%']<.11)]
                home_sim = home_sim[['Hitter','PC','xwOBA','xwOBA Con','SwStr%','Brl%','FB%','Hard%']]
                styled_df = home_sim.style.apply(color_cells_HitMatchups, subset=['xwOBA','xwOBA Con',
                                                                                'SwStr%','Brl%','FB%',
                                                                                'Hard%'], axis=1).format({'xwOBA': '{:.3f}',
                                                                                                            'xwOBA Con': '{:.3f}',
                                                                                                            'SwStr%': '{:.1%}',
                                                                                                            'Brl%': '{:.1%}',
                                                                                                            'FB%': '{:.1%}',
                                                                                                            'Hard%': '{:.1%}',})
                st.dataframe(styled_df, hide_index=True, use_container_width=True)

        elif option == "Best Matchups":
            col1, col2 = st.columns([1,1])
            with col1:
                road_sim = these_sim[these_sim['Team']==selected_road_team]
                road_sim = road_sim[(road_sim['xwOBA Con']>=.375)&(road_sim['SwStr%']<.11)&(road_sim['PC']>=50)]
                road_sim = road_sim[['Hitter','PC','xwOBA','xwOBA Con','SwStr%','Brl%','FB%','Hard%']]
                styled_df = road_sim.style.apply(color_cells_HitMatchups, subset=['xwOBA','xwOBA Con',
                                                                                'SwStr%','Brl%','FB%',
                                                                                'Hard%'], axis=1).format({'xwOBA': '{:.3f}',
                                                                                                            'xwOBA Con': '{:.3f}',
                                                                                                            'SwStr%': '{:.1%}',
                                                                                                            'Brl%': '{:.1%}',
                                                                                                            'FB%': '{:.1%}',
                                                                                                            'Hard%': '{:.1%}',})
                st.dataframe(styled_df, hide_index=True, use_container_width=True)
                #st.dataframe(road_sim)
            with col2:
                home_sim = these_sim[these_sim['Team']==selected_home_team]
                home_sim = home_sim[(home_sim['xwOBA Con']>=.375)&(home_sim['SwStr%']<.11)&(home_sim['PC']>=50)]
                home_sim = home_sim[['Hitter','PC','xwOBA','xwOBA Con','SwStr%','Brl%','FB%','Hard%']]
                styled_df = home_sim.style.apply(color_cells_HitMatchups, subset=['xwOBA','xwOBA Con',
                                                                                'SwStr%','Brl%','FB%',
                                                                                'Hard%'], axis=1).format({'xwOBA': '{:.3f}',
                                                                                                            'xwOBA Con': '{:.3f}',
                                                                                                            'SwStr%': '{:.1%}',
                                                                                                            'Brl%': '{:.1%}',
                                                                                                            'FB%': '{:.1%}',
                                                                                                            'Hard%': '{:.1%}',})
                st.dataframe(styled_df, hide_index=True, use_container_width=True)
        elif option == "Props":
            game_hitter_list = list(hitterproj[hitterproj['Team'].isin([selected_road_team,selected_home_team])]['Hitter'])
            hitter_props = props_df[props_df['Player'].isin(game_hitter_list)]
            pitcher_props = pitcher_props[pitcher_props['Type']!='pitcher_outs']
            game_props = pd.concat([hitter_props,pitcher_props])
            game_props = game_props[['Player','Book','Type','OU','Line','Price','BetValue']].sort_values(by='BetValue',ascending=False)
            game_props = game_props[(game_props['BetValue']>=.1)|((game_props['Type']=='batter_home_runs')&(game_props['BetValue']>=.05))]
            if len(game_props)>0:
                styled_df = game_props.style.apply(color_cells_Props, subset=['BetValue','Price'], axis=1).format({'BetValue': '{:.1%}',
                                                                                                                    'Price': '{:.0f}',
                                                                                                                    'Line': '{:.1f}'})
                st.dataframe(styled_df, hide_index=True, width=750)
            else:
                st.write('No recommended props for this game')

            #pitcher_props

    if tab == "Pitcher Projections":
        import streamlit as st
        import pandas as pd
        import numpy as np

        require_pro()

        # =========================================================
        # LOAD DATA
        # =========================================================
        hitterproj_raw, pitcherproj_raw, hitterproj2, gameinfo_raw = load_daily_projections()
        hitter_stats_raw, lineup_stats, pitcher_stats, h_vs_avg, p_vs_avg, h_vs_sim, hotzonedata, posdata = load_player_stats()
        bpreport_raw, rpstats = load_bullpen_data()

        (
            hitterproj,
            pitcherproj,
            hitter_stats,
            gameinfo,
            bpreport,
            games_df,
            mainslateteams,
            main_slate_gamelist,
            confirmed_lus,
            last_update
        ) = _prepare_projection_data(
            hitterproj_raw,
            pitcherproj_raw,
            hitterproj2,
            gameinfo_raw,
            hitter_stats_raw,
            h_vs_avg,
            bpreport_raw
        )

        # =========================================================
        # PAGE STYLING
        # =========================================================
        st.markdown("""
        <style>
        .pitch-hero {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 55%, #334155 100%);
            padding: 24px 28px;
            border-radius: 18px;
            margin-bottom: 18px;
            border: 1px solid rgba(255,255,255,0.08);
        }
        .pitch-hero h1 {
            margin: 0;
            color: white;
            font-size: 2.0rem;
        }
        .pitch-hero p {
            margin: 6px 0 0 0;
            color: #cbd5e1;
            font-size: 0.95rem;
        }
        .mini-note {
            font-size: 0.85rem;
            color: #94a3b8;
            margin-top: -8px;
            margin-bottom: 10px;
        }
        .block-header {
            font-weight: 700;
            font-size: 1.05rem;
            margin-bottom: 6px;
        }
        </style>
        """, unsafe_allow_html=True)

        st.markdown(
            f"""
            <div class="pitch-hero">
                <h1>Pitcher Projections</h1>
                <p>Daily DFS pitcher projections, filters, highlights, and downloadable CSV export.</p>
                <p><b>Last update:</b> {last_update} EST</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        # =========================================================
        # PREP AUX DATA
        # =========================================================
        pitcherproj = pitcherproj.copy()
        p_vs_avg = p_vs_avg.copy()

        slate_options = list(pitcherproj['MainSlate'].unique())

        pitcher_matchups = dict(zip(pitcherproj["Team"], pitcherproj["Opponent"]))
        p_vs_avg["Opp"] = p_vs_avg["Team"].map(pitcher_matchups)

        top_five_proj = pitcherproj.sort_values(by="DKPts", ascending=False).head(5)

        # =========================================================
        # HIGHLIGHTS TOGGLE
        # =========================================================
        show_highlights = st.toggle("Show Projection Highlights", value=False, key="show_pitcher_highlights")

        if show_highlights:
            st.markdown("### Top Projected Arms")

            top_cols = st.columns(5)
            for i, col in enumerate(top_cols):
                if i < len(top_five_proj):
                    row = top_five_proj.iloc[i]
                    with col:
                        st.image(get_player_image(row["ID"]), width=110)
                        st.markdown(f"**{row['Pitcher']}**")
                        st.caption(f"{row['Team']} vs {row['Opponent']}")
                        st.write(f"DK: **{row['DKPts']:.2f}**")
                        if "Sal" in row.index and pd.notnull(row["Sal"]):
                            st.write(f"Sal: **${row['Sal']:,.0f}**")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### Highest Projection vs Season Avg")
                show_p_vs_avg_hi = (
                    p_vs_avg[["Pitcher", "Team", "Opp", "DKPts", "Avg DK Proj", "DKPts Diff"]]
                    .sort_values(by="DKPts Diff", ascending=False)
                    .head(5)
                )
                st.dataframe(show_p_vs_avg_hi, hide_index=True, use_container_width=True)

            with col2:
                st.markdown("#### Lowest Projection vs Season Avg")
                show_p_vs_avg_lo = (
                    p_vs_avg[["Pitcher", "Team", "Opp", "DKPts", "Avg DK Proj", "DKPts Diff"]]
                    .sort_values(by="DKPts Diff", ascending=True)
                    .head(5)
                )
                st.dataframe(show_p_vs_avg_lo, hide_index=True, use_container_width=True)

            st.markdown("---")

        # =========================================================
        # FILTERS
        # =========================================================
        st.markdown("### Filters")

        filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)

        with filter_col1:
            slate_filter = st.selectbox(
                "Slate",
                #["Show All", "Main Slate Only"],
                slate_options,
                index=0,
                key="slate_filter_pitcher"
            )

        with filter_col2:
            teams = ["All Teams"] + sorted(pitcherproj["Team"].dropna().unique().tolist())
            team_filter = st.selectbox(
                "Team",
                teams,
                index=0,
                key="team_filter_pitcher"
            )

        with filter_col3:
            opp_filter = st.text_input(
                "Opponent",
                placeholder="Ex: TOR, NYY",
                key="opp_filter_pitcher"
            )

        with filter_col4:
            pitcher_search = st.text_input(
                "Pitcher Search",
                placeholder="Search pitcher name",
                key="pitcher_search_pitcher"
            )

        filter_col5, filter_col6, filter_col7, filter_col8 = st.columns(4)

        with filter_col5:
            home_away_filter = st.selectbox(
                "Location",
                ["All", "Home Only", "Away Only"],
                index=0,
                key="home_away_filter_pitcher"
            )

        with filter_col6:
            sort_by = st.selectbox(
                "Sort By",
                ["DKPts", "Val", "Sal", "Ceil", "SO", "Own%"],
                index=0,
                key="sort_pitcher_proj"
            )

        with filter_col7:
            min_dkpts = st.number_input(
                "Min DKPts",
                min_value=0.0,
                value=0.0,
                step=0.5,
                key="min_dkpts_pitcher"
            )

        with filter_col8:
            min_salary = st.number_input(
                "Min Salary",
                min_value=0,
                value=0,
                step=100,
                key="min_salary_pitcher"
            )

        # =========================================================
        # FILTER DATAFRAME
        # =========================================================
        show_pproj = pitcherproj.copy()

        if slate_filter == "Main":
            show_pproj = show_pproj[show_pproj["MainSlate"] == "Main"]

        if slate_filter == "Early":
            show_pproj = show_pproj[show_pproj["MainSlate"] == "Early"]

        if team_filter != "All Teams":
            show_pproj = show_pproj[show_pproj["Team"] == team_filter]

        if opp_filter:
            show_pproj = show_pproj[
                show_pproj["Opponent"].astype(str).str.contains(opp_filter, case=False, na=False)
            ]

        if pitcher_search:
            show_pproj = show_pproj[
                show_pproj["Pitcher"].astype(str).str.contains(pitcher_search, case=False, na=False)
            ]

        if home_away_filter == "Home Only":
            show_pproj = show_pproj[show_pproj["HomeTeam"] == show_pproj["Team"]]
        elif home_away_filter == "Away Only":
            show_pproj = show_pproj[show_pproj["HomeTeam"] != show_pproj["Team"]]

        if "DKPts" in show_pproj.columns:
            show_pproj = show_pproj[show_pproj["DKPts"].fillna(0) >= min_dkpts]

        if "Sal" in show_pproj.columns:
            show_pproj = show_pproj[show_pproj["Sal"].fillna(0) >= min_salary]

        show_pproj = show_pproj.rename({"Ownership": "Own%"}, axis=1)

        desired_cols = [
            "Pitcher", "Team", "Opponent", "HomeTeam",
            "Sal", "DKPts", "Val", "PC", "IP", "SO", "BB", "W", "Ceil", "Own%"
        ]
        desired_cols = [c for c in desired_cols if c in show_pproj.columns]
        show_pproj = show_pproj[desired_cols]

        ascending = False if sort_by in show_pproj.columns else False
        if sort_by in show_pproj.columns:
            show_pproj = show_pproj.sort_values(by=sort_by, ascending=ascending)

        # =========================================================
        # COLUMN PICKER
        # =========================================================
        st.markdown("### Table Options")

        default_visible_cols = [c for c in ["Pitcher", "Team", "Opponent", "Sal", "DKPts", "Val", "IP", "SO", "W", "Ceil", "Own%"] if c in show_pproj.columns]

        visible_cols = st.multiselect(
            "Choose columns to display",
            options=show_pproj.columns.tolist(),
            default=default_visible_cols,
            key="visible_pitcher_columns"
        )

        if visible_cols:
            display_df = show_pproj[visible_cols].copy()
        else:
            display_df = show_pproj.copy()

        # =========================================================
        # EXPORT CSV
        # =========================================================
        @st.cache_data
        def convert_df_to_csv(df):
            return df.to_csv(index=False).encode("utf-8")

        csv_data = convert_df_to_csv(display_df)

        export_col1, export_col2 = st.columns([1, 5])
        with export_col1:
            st.download_button(
                label="EXPORT TO CSV",
                data=csv_data,
                file_name="pitcher_projections.csv",
                mime="text/csv",
                use_container_width=True
            )
        with export_col2:
            st.caption("Downloads directly through the browser to the user's computer.")

        # =========================================================
        # STYLED DISPLAY
        # =========================================================
        numeric_format_dict = {}
        for col in display_df.columns:
            if col in ["DKPts", "Val", "SO", "BB", "W", "Ceil"]:
                numeric_format_dict[col] = "{:.2f}"
            elif col in ["IP"]:
                numeric_format_dict[col] = "{:.2f}"
            elif col in ["PC", "Own%"]:
                numeric_format_dict[col] = "{:.0f}"
            elif col in ["Sal"]:
                numeric_format_dict[col] = "${:,.0f}"

        style_subset = [c for c in ["DKPts", "Val", "Sal", "SO", "W", "Ceil", "Own%", "BB", "PC", "IP"] if c in display_df.columns]

        if len(display_df) > 0:
            styled_df = (
                display_df.style
                .apply(color_cells_PitchProj, subset=style_subset, axis=1)
                .format(numeric_format_dict)
                .set_table_styles([
                    {"selector": "th", "props": [("text-align", "left"), ("font-weight", "bold")]},
                    {"selector": "td", "props": [("text-align", "left")]}
                ])
            )

            st.markdown("### Pitcher Projection Table")
            st.dataframe(
                styled_df,
                use_container_width=True,
                height=800,
                hide_index=True
            )
        else:
            st.warning("No pitchers match the current filters.")

    if tab == "Hitter Projections":
        import streamlit as st
        import pandas as pd
        import numpy as np

        require_pro()

        # =========================================================
        # LOAD DATA
        # =========================================================
        hitterproj_raw, pitcherproj_raw, hitterproj2, gameinfo_raw = load_daily_projections()
        hitter_stats_raw, lineup_stats, pitcher_stats, h_vs_avg, p_vs_avg, h_vs_sim, hotzonedata, posdata = load_player_stats()
        bpreport_raw, rpstats = load_bullpen_data()

        (
            hitterproj,
            pitcherproj,
            hitter_stats,
            gameinfo,
            bpreport,
            games_df,
            mainslateteams,
            main_slate_gamelist,
            confirmed_lus,
            last_update
        ) = _prepare_projection_data(
            hitterproj_raw,
            pitcherproj_raw,
            hitterproj2,
            gameinfo_raw,
            hitter_stats_raw,
            h_vs_avg,
            bpreport_raw
        )

        # =========================================================
        # CLEAN / PREP
        # =========================================================
        hitterproj = hitterproj.copy()
        h_vs_avg = h_vs_avg.copy()

        hitterproj["Hitter"] = hitterproj["Hitter"].astype(str).str.replace("🔥", "", regex=False).str.replace("🥶", "", regex=False).str.strip()

        if "Batter" not in hitterproj.columns and "Hitter" in hitterproj.columns:
            hitterproj["Batter"] = hitterproj["Hitter"]

        if "Value" not in hitterproj.columns and {"DKPts", "Sal"}.issubset(hitterproj.columns):
            hitterproj["Value"] = np.where(
                hitterproj["Sal"].fillna(0) > 0,
                hitterproj["DKPts"] / (hitterproj["Sal"] / 1000),
                np.nan
            )

        hitterproj["Value"] = np.where(
            hitterproj["Sal"].fillna(0) > 0,
            hitterproj["DKPts"] / (hitterproj["Sal"] / 1000),
            np.nan
        )

        if "Ownership" in hitterproj.columns and "Own%" not in hitterproj.columns:
            hitterproj = hitterproj.rename({"Ownership": "Own%"}, axis=1)

        if "LU" in hitterproj.columns:
            hitterproj["LU"] = pd.to_numeric(hitterproj["LU"], errors="coerce")

        if "Sal" in hitterproj.columns:
            hitterproj["Sal"] = pd.to_numeric(hitterproj["Sal"], errors="coerce")

        if "DKPts" in hitterproj.columns:
            hitterproj["DKPts"] = pd.to_numeric(hitterproj["DKPts"], errors="coerce")

        if "HR" in hitterproj.columns:
            hitterproj["HR"] = pd.to_numeric(hitterproj["HR"], errors="coerce")

        if "SB" in hitterproj.columns:
            hitterproj["SB"] = pd.to_numeric(hitterproj["SB"], errors="coerce")

        if "Floor" in hitterproj.columns:
            hitterproj["Floor"] = pd.to_numeric(hitterproj["Floor"], errors="coerce")

        if "Ceil" in hitterproj.columns:
            hitterproj["Ceil"] = pd.to_numeric(hitterproj["Ceil"], errors="coerce")

        hitter_name_id_dict = dict(zip(hitterproj["Hitter"], hitterproj["ID"])) if "ID" in hitterproj.columns else {}
        hitter_matchups_dict = dict(zip(hitterproj["Team"], hitterproj["Opp"])) if {"Team", "Opp"}.issubset(hitterproj.columns) else {}
        hitter_matchups_pp_dict = dict(zip(hitterproj["Team"], hitterproj["OppSP"])) if {"Team", "OppSP"}.issubset(hitterproj.columns) else {}
        hitter_park_dict = dict(zip(hitterproj["Team"], hitterproj["Park"])) if {"Team", "Park"}.issubset(hitterproj.columns) else {}

        if "Team" in h_vs_avg.columns:
            h_vs_avg["Opp"] = h_vs_avg["Team"].map(hitter_matchups_dict)
            h_vs_avg["OppSP"] = h_vs_avg["Team"].map(hitter_matchups_pp_dict)

        @st.cache_data
        def convert_df_to_csv(df):
            return df.to_csv(index=False).encode("utf-8")

        # =========================================================
        # STACK FINDER HELPERS
        # =========================================================
        def _stack_sequence_label(spots):
            spots = [int(x) for x in spots]
            return "-".join(str(x) for x in spots)

        def _is_consecutive_circular(spots):
            if len(spots) <= 1:
                return True
            s = sorted([int(x) for x in spots])
            n = len(s)
            diffs = []
            for i in range(n - 1):
                diffs.append(s[i + 1] - s[i])
            diffs.append((s[0] + 9) - s[-1])
            return diffs.count(1) == 1 and diffs.count(1) + diffs.count(0) == len([d for d in diffs if d == 1]) + len([d for d in diffs if d == 0]) and sum(diffs) == 9

        def _generate_consecutive_windows(stack_size):
            windows = []
            for start in range(1, 10):
                seq = [((start - 1 + i) % 9) + 1 for i in range(stack_size)]
                windows.append(seq)
            return windows

        def _build_stack_finder_df(source_df, stack_size=4, min_player_proj=0.0, max_salary_each=None, confirmed_only=False):
            needed_cols = ["Batter", "Team", "Opp", "OppSP", "Park", "LU", "DKPts", "Sal", "Value"]
            for col in ["HR", "SB", "Ceil", "Floor", "Own%", "ID", "MainSlate"]:
                if col in source_df.columns and col not in needed_cols:
                    needed_cols.append(col)

            df = source_df.copy()
            keep_cols = [c for c in needed_cols if c in df.columns]
            df = df[keep_cols].copy()

            if "LU" not in df.columns:
                return pd.DataFrame(), pd.DataFrame()

            df = df[df["LU"].between(1, 9, inclusive="both")]
            df = df[df["DKPts"].fillna(0) >= min_player_proj]

            if max_salary_each is not None:
                df = df[df["Sal"].fillna(999999) <= max_salary_each]

            if confirmed_only:
                team_spot_ct = df.groupby("Team")["LU"].nunique().reset_index(name="spot_ct")
                confirmed_teams = team_spot_ct[team_spot_ct["spot_ct"] >= 9]["Team"].tolist()
                df = df[df["Team"].isin(confirmed_teams)]

            if df.empty:
                return pd.DataFrame(), pd.DataFrame()

            stack_rows = []
            windows = _generate_consecutive_windows(stack_size)

            for team, tdf in df.groupby("Team"):
                tdf = tdf.copy()
                tdf["LU"] = tdf["LU"].astype(int)

                # Make sure we only use one player per lineup spot
                tdf = (
                    tdf.sort_values(["LU", "DKPts"], ascending=[True, False])
                       .drop_duplicates(subset=["LU"], keep="first")
                )

                team_spots = set(tdf["LU"].tolist())

                for window in windows:
                    if not set(window).issubset(team_spots):
                        continue

                    stack_df = tdf[tdf["LU"].isin(window)].copy()
                    if len(stack_df) != stack_size:
                        continue

                    stack_df = stack_df.sort_values("LU")
                    players = stack_df["Batter"].tolist()
                    spots = stack_df["LU"].tolist()

                    total_dk = stack_df["DKPts"].sum()
                    total_sal = stack_df["Sal"].sum() if "Sal" in stack_df.columns else np.nan
                    total_hr = stack_df["HR"].sum() if "HR" in stack_df.columns else np.nan
                    total_sb = stack_df["SB"].sum() if "SB" in stack_df.columns else np.nan
                    total_ceil = stack_df["Ceil"].sum() if "Ceil" in stack_df.columns else np.nan
                    total_floor = stack_df["Floor"].sum() if "Floor" in stack_df.columns else np.nan
                    avg_value = stack_df["Value"].mean() if "Value" in stack_df.columns else np.nan
                    total_value = total_dk / (total_sal / 1000) if pd.notna(total_sal) and total_sal > 0 else np.nan
                    avg_own = stack_df["Own%"].mean() if "Own%" in stack_df.columns else np.nan

                    wrap_bonus = 1 if (9 in spots and 1 in spots) else 0
                    stack_quality = (
                        total_dk
                        + (0.18 * total_ceil if pd.notna(total_ceil) else 0)
                        + (0.60 * total_hr if pd.notna(total_hr) else 0)
                        + (0.20 * total_sb if pd.notna(total_sb) else 0)
                        + (0.35 * wrap_bonus)
                    )

                    value_quality = (
                        total_value * 2.4 if pd.notna(total_value) else 0
                    ) + (
                        0.12 * total_dk
                    ) + (
                        0.12 * total_hr if pd.notna(total_hr) else 0
                    ) + (
                        0.20 * wrap_bonus
                    )

                    row = {
                        "Team": team,
                        "Stack Type": f"{stack_size}-Man",
                        "Lineup Seq": _stack_sequence_label(spots),
                        "Players": " / ".join(players),
                        "Opp": stack_df["Opp"].iloc[0] if "Opp" in stack_df.columns else "",
                        "OppSP": stack_df["OppSP"].iloc[0] if "OppSP" in stack_df.columns else "",
                        "Park": stack_df["Park"].iloc[0] if "Park" in stack_df.columns else "",
                        "Tot DKPts": round(total_dk, 2),
                        "Total Sal": int(total_sal) if pd.notna(total_sal) else np.nan,
                        "Stack Value": round(total_value, 2) if pd.notna(total_value) else np.nan,
                        "Avg Value": round(avg_value, 2) if pd.notna(avg_value) else np.nan,
                        "Tot HR": round(total_hr, 2) if pd.notna(total_hr) else np.nan,
                        "Tot SB": round(total_sb, 2) if pd.notna(total_sb) else np.nan,
                        "Tot Floor": round(total_floor, 2) if pd.notna(total_floor) else np.nan,
                        "Tot Ceil": round(total_ceil, 2) if pd.notna(total_ceil) else np.nan,
                        "Avg Own%": round(avg_own, 1) if pd.notna(avg_own) else np.nan,
                        "Wrap Bonus": wrap_bonus,
                        "Top Stack Score": round(stack_quality, 2),
                        "Top Value Score": round(value_quality, 2),
                    }

                    stack_rows.append(row)

            if not stack_rows:
                return pd.DataFrame(), pd.DataFrame()

            stacks = pd.DataFrame(stack_rows)

            stacks = stacks.sort_values(
                ["Top Stack Score", "Tot DKPts", "Tot Ceil", "Stack Value"],
                ascending=False
            ).reset_index(drop=True)

            value_stacks = stacks.sort_values(
                ["Top Value Score", "Stack Value", "Tot DKPts", "Total Sal"],
                ascending=[False, False, False, True]
            ).reset_index(drop=True)

            return stacks, value_stacks

        def _team_stack_summary(source_df):
            if source_df.empty:
                return pd.DataFrame()

            grp = source_df.groupby(["Team", "Opp", "OppSP"], as_index=False).agg({
                "DKPts": "sum",
                "Sal": "sum",
                "HR": "sum" if "HR" in source_df.columns else "first",
                "SB": "sum" if "SB" in source_df.columns else "first",
                "LU": "count"
            })

            grp = grp.rename(columns={"LU": "Hitters Shown"})
            grp["Team Value"] = np.where(
                grp["Sal"].fillna(0) > 0,
                grp["DKPts"] / (grp["Sal"] / 1000),
                np.nan
            )

            if "HR" in grp.columns:
                grp["HR"] = pd.to_numeric(grp["HR"], errors="coerce")
            if "SB" in grp.columns:
                grp["SB"] = pd.to_numeric(grp["SB"], errors="coerce")

            return grp.sort_values("DKPts", ascending=False)

        # =========================================================
        # PAGE STYLING
        # =========================================================
        st.markdown("""
        <style>
        .hit-hero {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 55%, #334155 100%);
            padding: 24px 28px;
            border-radius: 18px;
            margin-bottom: 18px;
            border: 1px solid rgba(255,255,255,0.08);
        }
        .hit-hero h1 {
            margin: 0;
            color: white;
            font-size: 2rem;
        }
        .hit-hero p {
            margin: 6px 0 0 0;
            color: #cbd5e1;
            font-size: 0.96rem;
        }
        .stack-card {
            background: linear-gradient(135deg, rgba(15,23,42,.98) 0%, rgba(30,41,59,.98) 100%);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 16px;
            padding: 14px 16px;
            margin-bottom: 10px;
        }
        .stack-card .stack-team {
            font-size: 1.1rem;
            font-weight: 700;
            color: #f8fafc;
            margin-bottom: 3px;
        }
        .stack-card .stack-sub {
            color: #cbd5e1;
            font-size: 0.88rem;
            margin-bottom: 8px;
        }
        .stack-card .stack-metric {
            display: inline-block;
            margin-right: 14px;
            color: #e2e8f0;
            font-size: 0.88rem;
        }
        .stack-card .stack-players {
            color: #f8fafc;
            font-size: 0.92rem;
            margin-top: 8px;
            line-height: 1.4;
        }
        .stack-section-header {
            background: linear-gradient(90deg, #0f172a 0%, #1d4ed8 100%);
            color: white;
            padding: 10px 14px;
            border-radius: 12px;
            font-weight: 700;
            margin: 8px 0 14px 0;
        }
        </style>
        """, unsafe_allow_html=True)

        st.markdown(
            f"""
            <div class="hit-hero">
                <h1>Hitter Projections</h1>
                <p>Explore daily hitter projections, matchup boosts, team outlooks, downloadable CSV exports, and a premium stack finder built for serious DFS lineup construction.</p>
                <p><b>Last update:</b> {last_update} EST</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        # =========================================================
        # TOP OPTIONS
        # =========================================================
        top_opt1, top_opt2, top_opt3, top_opt4, top_opt5 = st.columns(5)

        with top_opt1:
            show_highlights = st.toggle("Show Projection Highlights", value=False, key="show_hitter_highlights")

        with top_opt2:
            show_team_proj = st.toggle("Show Team Projections", value=False, key="show_team_hitter_proj")

        with top_opt3:
            main_slate_check = st.toggle("Show Main Slate Only", value=False, key="show_main_slate_hitters")

        with top_opt4:
            show_only_confirmed = st.toggle("Confirmed Lineups Only", value=False, key="confirmed_only_hitters")

        with top_opt5:
            show_stack_finder = st.toggle("STACK FINDER", value=False, key="show_stack_finder_hitters")

        slate_options = ["Main", "Early"]

        # =========================================================
        # STACK FINDER VIEW
        # =========================================================
        if show_stack_finder:
            st.markdown('<div class="stack-section-header">STACK FINDER</div>', unsafe_allow_html=True)

            sf1, sf2, sf3, sf4, sf5, sf6 = st.columns(6)

            with sf1:
                stack_slate = st.selectbox(
                    "Slate",
                    slate_options,
                    index=0 if main_slate_check else 0,
                    key="stackfinder_slate"
                )

            with sf2:
                stack_size = st.selectbox(
                    "Stack Size",
                    [3, 4, 5],
                    index=1,
                    key="stackfinder_size"
                )

            with sf3:
                stack_team_filter = st.selectbox(
                    "Team",
                    ["All Teams"] + sorted(hitterproj["Team"].dropna().unique().tolist()),
                    index=0,
                    key="stackfinder_team_filter"
                )

            with sf4:
                min_stack_player_proj = st.number_input(
                    "Min Player DKPts",
                    min_value=0.0,
                    value=3.0,
                    step=0.5,
                    key="stackfinder_min_player_proj"
                )

            with sf5:
                max_stack_player_salary = st.number_input(
                    "Max Player Salary",
                    min_value=0,
                    value=99999,
                    step=100,
                    key="stackfinder_max_player_salary"
                )

            with sf6:
                top_stack_n = st.selectbox(
                    "Show Top",
                    [5, 10, 15, 20, 30],
                    index=1,
                    key="stackfinder_topn"
                )

            sf7, sf8, sf9, sf10 = st.columns(4)

            with sf7:
                value_sort_emphasis = st.selectbox(
                    "Primary View",
                    ["Best Overall Stacks", "Best Value Stacks", "Team Stack Overview"],
                    index=0,
                    key="stackfinder_primary_view"
                )

            with sf8:
                force_confirmed_stacks = st.toggle(
                    "Confirmed Only for Stacks",
                    value=show_only_confirmed,
                    key="stackfinder_confirmed"
                )

            with sf9:
                min_stack_total_salary = st.number_input(
                    "Min Stack Salary",
                    min_value=0,
                    value=0,
                    step=100,
                    key="stackfinder_min_total_sal"
                )

            with sf10:
                max_stack_total_salary = st.number_input(
                    "Max Stack Salary",
                    min_value=0,
                    value=30000,
                    step=100,
                    key="stackfinder_max_total_sal"
                )

            stack_source = hitterproj.copy()

            if stack_slate == "Main" and "MainSlate" in stack_source.columns:
                stack_source = stack_source[stack_source["MainSlate"] == "Main"]
            elif stack_slate == "Early" and "MainSlate" in stack_source.columns:
                stack_source = stack_source[stack_source["MainSlate"] == "Early"]

            if stack_team_filter != "All Teams":
                stack_source = stack_source[stack_source["Team"] == stack_team_filter]

            stack_source = stack_source[stack_source["DKPts"].fillna(0) > 0]
            stack_source = stack_source[stack_source["Sal"].fillna(0) > 0]

            if max_stack_player_salary >= 100:
                stack_max_sal_each = max_stack_player_salary
            else:
                stack_max_sal_each = None

            overall_stacks, value_stacks = _build_stack_finder_df(
                stack_source,
                stack_size=stack_size,
                min_player_proj=min_stack_player_proj,
                max_salary_each=stack_max_sal_each,
                confirmed_only=force_confirmed_stacks
            )

            if not overall_stacks.empty:
                overall_stacks = overall_stacks[
                    (overall_stacks["Total Sal"].fillna(0) >= min_stack_total_salary) &
                    (overall_stacks["Total Sal"].fillna(999999) <= max_stack_total_salary)
                ].reset_index(drop=True)

            if not value_stacks.empty:
                value_stacks = value_stacks[
                    (value_stacks["Total Sal"].fillna(0) >= min_stack_total_salary) &
                    (value_stacks["Total Sal"].fillna(999999) <= max_stack_total_salary)
                ].reset_index(drop=True)

            stack_team_summary_source = stack_source.copy()
            if force_confirmed_stacks and "LU" in stack_team_summary_source.columns:
                team_spot_ct = stack_team_summary_source.groupby("Team")["LU"].nunique().reset_index(name="spot_ct")
                confirmed_teams = team_spot_ct[team_spot_ct["spot_ct"] >= 9]["Team"].tolist()
                stack_team_summary_source = stack_team_summary_source[stack_team_summary_source["Team"].isin(confirmed_teams)]

            team_stack_summary = _team_stack_summary(stack_team_summary_source)
            if not team_stack_summary.empty and stack_team_filter != "All Teams":
                team_stack_summary = team_stack_summary[team_stack_summary["Team"] == stack_team_filter]

            m1, m2, m3, m4 = st.columns(4)

            with m1:
                st.metric("Teams In Pool", int(stack_source["Team"].nunique()) if not stack_source.empty else 0)
            with m2:
                st.metric("Valid Overall Stacks", len(overall_stacks))
            with m3:
                st.metric("Valid Value Stacks", len(value_stacks))
            with m4:
                st.metric("Stack Size", f"{stack_size}-Man")

            def render_stack_cards(df, title, score_col, n_cards=5):
                st.markdown(f"### {title}")
                if df.empty:
                    st.warning("No valid stacks found for the current filters.")
                    return

                for _, row in df.head(n_cards).iterrows():
                    st.markdown(
                        f"""
                        <div class="stack-card">
                            <div class="stack-team">{row['Team']} &nbsp;•&nbsp; {row['Lineup Seq']}</div>
                            <div class="stack-sub">vs {row['Opp']} | {row['OppSP']} | {row['Park']}</div>
                            <div class="stack-metric"><b>DKPts:</b> {row['Tot DKPts']:.2f}</div>
                            <div class="stack-metric"><b>Salary:</b> ${row['Total Sal']:,.0f}</div>
                            <div class="stack-metric"><b>Value:</b> {row['Stack Value']:.2f}</div>
                            <div class="stack-metric"><b>HR:</b> {row['Tot HR']:.2f}</div>
                            <div class="stack-metric"><b>Ceil:</b> {row['Tot Ceil']:.2f}</div>
                            <div class="stack-metric"><b>{score_col}:</b> {row[score_col]:.2f}</div>
                            <div class="stack-players"><b>Players:</b> {row['Players']}</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

            if value_sort_emphasis == "Best Overall Stacks":
                col_a, col_b = st.columns(2)

                with col_a:
                    render_stack_cards(overall_stacks, f"Top {top_stack_n} Overall {stack_size}-Man Stacks", "Top Stack Score", n_cards=min(top_stack_n, 10))

                with col_b:
                    render_stack_cards(value_stacks, f"Top {top_stack_n} Value {stack_size}-Man Stacks", "Top Value Score", n_cards=min(top_stack_n, 10))

            elif value_sort_emphasis == "Best Value Stacks":
                col_a, col_b = st.columns(2)

                with col_a:
                    render_stack_cards(value_stacks, f"Top {top_stack_n} Value {stack_size}-Man Stacks", "Top Value Score", n_cards=min(top_stack_n, 10))

                with col_b:
                    render_stack_cards(overall_stacks, f"Top {top_stack_n} Raw Ceiling {stack_size}-Man Stacks", "Top Stack Score", n_cards=min(top_stack_n, 10))

            else:
                st.markdown("### Team Stack Overview")
                if team_stack_summary.empty:
                    st.warning("No team stack overview available for the current filters.")
                else:
                    show_team_stack_summary = team_stack_summary.copy()
                    show_team_stack_summary = show_team_stack_summary.sort_values(["DKPts", "Team Value"], ascending=False)

                    if "HR" not in show_team_stack_summary.columns:
                        show_team_stack_summary["HR"] = np.nan
                    if "SB" not in show_team_stack_summary.columns:
                        show_team_stack_summary["SB"] = np.nan

                    styled_team_stacks = (
                        show_team_stack_summary.style
                        .format({
                            "DKPts": "{:.2f}",
                            "Sal": "${:,.0f}",
                            "Team Value": "{:.2f}",
                            "HR": "{:.2f}",
                            "SB": "{:.2f}",
                        })
                    )

                    st.dataframe(
                        styled_team_stacks,
                        hide_index=True,
                        use_container_width=True,
                        height=500
                    )

            st.markdown("### Full Stack Tables")

            stack_table_col1, stack_table_col2 = st.columns(2)

            with stack_table_col1:
                st.markdown(f"#### Overall Top {stack_size}-Man Stacks")
                if overall_stacks.empty:
                    st.warning("No overall stacks found.")
                else:
                    show_overall = overall_stacks.head(top_stack_n).copy()
                    overall_csv = convert_df_to_csv(show_overall)

                    st.download_button(
                        label="EXPORT OVERALL STACKS CSV",
                        data=overall_csv,
                        file_name=f"overall_{stack_size}man_stacks.csv",
                        mime="text/csv",
                        use_container_width=True
                    )

                    styled_overall = show_overall.style.format({
                        "Tot DKPts": "{:.2f}",
                        "Total Sal": "${:,.0f}",
                        "Stack Value": "{:.2f}",
                        "Avg Value": "{:.2f}",
                        "Tot HR": "{:.2f}",
                        "Tot SB": "{:.2f}",
                        "Tot Floor": "{:.2f}",
                        "Tot Ceil": "{:.2f}",
                        "Avg Own%": "{:.1f}",
                        "Top Stack Score": "{:.2f}",
                        "Top Value Score": "{:.2f}",
                    })

                    st.dataframe(
                        styled_overall,
                        hide_index=True,
                        use_container_width=True,
                        height=600
                    )

            with stack_table_col2:
                st.markdown(f"#### Value Top {stack_size}-Man Stacks")
                if value_stacks.empty:
                    st.warning("No value stacks found.")
                else:
                    show_value = value_stacks.head(top_stack_n).copy()
                    value_csv = convert_df_to_csv(show_value)

                    st.download_button(
                        label="EXPORT VALUE STACKS CSV",
                        data=value_csv,
                        file_name=f"value_{stack_size}man_stacks.csv",
                        mime="text/csv",
                        use_container_width=True
                    )

                    styled_value = show_value.style.format({
                        "Tot DKPts": "{:.2f}",
                        "Total Sal": "${:,.0f}",
                        "Stack Value": "{:.2f}",
                        "Avg Value": "{:.2f}",
                        "Tot HR": "{:.2f}",
                        "Tot SB": "{:.2f}",
                        "Tot Floor": "{:.2f}",
                        "Tot Ceil": "{:.2f}",
                        "Avg Own%": "{:.1f}",
                        "Top Stack Score": "{:.2f}",
                        "Top Value Score": "{:.2f}",
                    })

                    st.dataframe(
                        styled_value,
                        hide_index=True,
                        use_container_width=True,
                        height=600
                    )

            st.info(
                "Stack Finder prioritizes consecutive lineup clusters only. That means it naturally surfaces combos like 1-2-3, 2-3-4-5, 3-4-5, and wraparound groups like 9-1-2 when the lineup is present."
            )

        # =========================================================
        # HIGHLIGHTS
        # =========================================================
        elif show_highlights:
            st.markdown("### Projection Highlights")

            top_hr = h_vs_avg.sort_values(by="HR", ascending=False).head(5).copy()
            top_hr["Opp"] = top_hr["Team"].map(hitter_matchups_dict)
            top_hr["OppSP"] = top_hr["Team"].map(hitter_matchups_pp_dict)
            top_hr["Park"] = top_hr["Team"].map(hitter_park_dict)
            top_hr["ID"] = top_hr["Hitter"].map(hitter_name_id_dict)

            st.markdown("#### Top HR Projections")
            cols = st.columns(5)
            for i, col in enumerate(cols):
                if i < len(top_hr):
                    row = top_hr.iloc[i]
                    with col:
                        st.image(get_player_image(row["ID"]), width=105)
                        st.markdown(f"**{row['Hitter']}**")
                        st.caption(f"{row['Team']} vs {row['Opp']} | {row['OppSP']}")
                        st.write(f"HR: **{row['HR']:.2f}**")

            st.markdown("#### Top HR Projection Boosts")
            top_hr_boost = h_vs_avg.sort_values(by="HR Diff", ascending=False).head(5).copy()
            top_hr_boost["Opp"] = top_hr_boost["Team"].map(hitter_matchups_dict)
            top_hr_boost["OppSP"] = top_hr_boost["Team"].map(hitter_matchups_pp_dict)
            top_hr_boost["Park"] = top_hr_boost["Team"].map(hitter_park_dict)
            top_hr_boost["ID"] = top_hr_boost["Hitter"].map(hitter_name_id_dict)

            cols = st.columns(5)
            for i, col in enumerate(cols):
                if i < len(top_hr_boost):
                    row = top_hr_boost.iloc[i]
                    with col:
                        st.image(get_player_image(row["ID"]), width=105)
                        st.markdown(f"**{row['Hitter']}**")
                        st.caption(f"{row['Team']} vs {row['Opp']} | {row['OppSP']}")
                        st.write(f"Boost: **+{row['HR Diff']:.2f} HR**")

            st.markdown("#### Biggest Fantasy Point Boosts")
            show_leaders = h_vs_avg.sort_values(by="DKPts Diff", ascending=False).copy()
            show_leaders["Opp"] = show_leaders["Team"].map(hitter_matchups_dict)
            show_leaders["OppSP"] = show_leaders["Team"].map(hitter_matchups_pp_dict)
            show_leaders = show_leaders[["Hitter", "Team", "Opp", "OppSP", "DKPts", "Avg DK Proj", "DKPts Diff"]].head(10)

            st.dataframe(show_leaders, hide_index=True, use_container_width=True)
            st.markdown("---")

        # =========================================================
        # TEAM PROJECTIONS
        # =========================================================
        if (not show_stack_finder) and show_team_proj:
            st.markdown("### Team Projection Data")

            team_col1, team_col2 = st.columns(2)

            with team_col1:
                teamproj_source = hitterproj.copy()
                if main_slate_check and "MainSlate" in teamproj_source.columns:
                    teamproj_source = teamproj_source[teamproj_source["MainSlate"] == "Main"]

                teamproj = (
                    teamproj_source.groupby(["Team", "Opp", "OppSP"], as_index=False)[["DKPts", "R", "HR", "SB"]]
                    .sum()
                    .sort_values(by="DKPts", ascending=False)
                )

                styled_teamproj = teamproj.style.format({
                    "DKPts": "{:.2f}",
                    "R": "{:.2f}",
                    "HR": "{:.2f}",
                    "SB": "{:.2f}"
                })

                st.markdown("#### Raw Team Totals")
                st.dataframe(styled_teamproj, hide_index=True, use_container_width=True)

            with team_col2:
                team_avg_source = h_vs_avg.copy()

                if main_slate_check and "MainSlate" in hitterproj.columns:
                    mainslate_teams = hitterproj[hitterproj["MainSlate"] == "Main"]["Team"].dropna().unique().tolist()
                    team_avg_source = team_avg_source[team_avg_source["Team"].isin(mainslate_teams)]

                team_v_avg = (
                    team_avg_source.groupby(["Team", "Opp", "OppSP"], as_index=False)[["HR", "Avg HR Proj", "DKPts", "Avg DK Proj"]]
                    .sum()
                )
                team_v_avg.columns = ["Team", "Opp", "OppSP", "Today HR", "Season HR", "Today DK", "Season DK"]

                team_v_avg["Today HR Boost"] = np.where(
                    team_v_avg["Season HR"] != 0,
                    team_v_avg["Today HR"] / team_v_avg["Season HR"],
                    np.nan
                )
                team_v_avg["Today DK Boost"] = np.where(
                    team_v_avg["Season DK"] != 0,
                    team_v_avg["Today DK"] / team_v_avg["Season DK"],
                    np.nan
                )

                team_v_avg = team_v_avg.sort_values(by="Today DK Boost", ascending=False)

                styled_team_v_avg = team_v_avg.style.format({
                    "Today HR": "{:.2f}",
                    "Season HR": "{:.2f}",
                    "Today DK": "{:.2f}",
                    "Season DK": "{:.2f}",
                    "Today HR Boost": "{:.1%}",
                    "Today DK Boost": "{:.1%}"
                })

                st.markdown("#### Today vs Season")
                st.dataframe(styled_team_v_avg, hide_index=True, use_container_width=True)

            st.markdown("---")

        # =========================================================
        # MAIN VIEW SELECTOR
        # =========================================================
        if not show_stack_finder:
            st.markdown("### Full Projections")

            mode_col1, mode_col2 = st.columns([1, 3])
            with mode_col1:
                hproj_option = st.selectbox(
                    "What Type To Show",
                    ["Todays Projections", "Today vs. Season Avg"],
                    index=0,
                    key="projtype_hitters"
                )

            # =========================================================
            # TODAYS PROJECTIONS
            # =========================================================
            if hproj_option == "Todays Projections":
                filt1, filt2, filt3, filt4, filt5, filt6 = st.columns(6)

                with filt1:
                    slate_option = st.selectbox(
                        "Slate",
                        slate_options,
                        index=0 if main_slate_check else 0,
                        key="slate_filter_hitters"
                    )

                with filt2:
                    teams = ["All Teams"] + sorted(hitterproj["Team"].dropna().unique().tolist())
                    team_filter = st.selectbox(
                        "Filter by Team",
                        teams,
                        index=0,
                        key="team_filter_hitters"
                    )

                with filt3:
                    pos_filter = st.text_input(
                        "Filter by Position",
                        placeholder="OF, SS, C, etc.",
                        key="pos_filter_hitters"
                    )

                with filt4:
                    hitter_search = st.text_input(
                        "Search Hitter",
                        placeholder="Player name",
                        key="hitter_search_name"
                    )

                with filt5:
                    min_dkpts = st.number_input(
                        "Min DKPts",
                        min_value=0.0,
                        value=0.0,
                        step=0.5,
                        key="min_dkpts_hitters"
                    )

                with filt6:
                    min_salary = st.number_input(
                        "Min Salary",
                        min_value=0,
                        value=0,
                        step=100,
                        key="min_salary_hitters"
                    )

                filt7, filt8, filt9, filt10 = st.columns(4)

                with filt7:
                    sort_by = st.selectbox(
                        "Sort By",
                        ["DKPts", "Value", "Sal", "HR", "SB", "Floor", "Ceil", "Own%"],
                        index=0,
                        key="sort_hitters_proj"
                    )

                with filt8:
                    lineup_filter = st.selectbox(
                        "Lineup Spot",
                        ["All"] + [str(i) for i in range(1, 10)],
                        index=0,
                        key="lineup_spot_filter"
                    )

                with filt9:
                    park_filter = st.text_input(
                        "Filter by Park",
                        placeholder="Park name",
                        key="park_filter_hitters"
                    )

                with filt10:
                    top_n = st.selectbox(
                        "Show Top N",
                        ["All", 25, 50, 100],
                        index=0,
                        key="top_n_hitters"
                    )

                show_hproj = hitterproj.copy()

                if slate_option == "Main" and "MainSlate" in show_hproj.columns:
                    show_hproj = show_hproj[show_hproj["MainSlate"] == "Main"]

                if slate_option == "Early" and "MainSlate" in show_hproj.columns:
                    show_hproj = show_hproj[show_hproj["MainSlate"] == "Early"]

                if team_filter != "All Teams":
                    show_hproj = show_hproj[show_hproj["Team"] == team_filter]

                if pos_filter and "Pos" in show_hproj.columns:
                    show_hproj = show_hproj[show_hproj["Pos"].astype(str).str.contains(pos_filter, case=False, na=False)]

                if hitter_search:
                    search_col = "Batter" if "Batter" in show_hproj.columns else "Hitter"
                    show_hproj = show_hproj[show_hproj[search_col].astype(str).str.contains(hitter_search, case=False, na=False)]

                if "DKPts" in show_hproj.columns:
                    show_hproj = show_hproj[show_hproj["DKPts"].fillna(0) >= min_dkpts]

                if "Sal" in show_hproj.columns:
                    show_hproj = show_hproj[show_hproj["Sal"].fillna(0) >= min_salary]

                if lineup_filter != "All" and "LU" in show_hproj.columns:
                    show_hproj = show_hproj[show_hproj["LU"].astype(str) == lineup_filter]

                if park_filter and "Park" in show_hproj.columns:
                    show_hproj = show_hproj[show_hproj["Park"].astype(str).str.contains(park_filter, case=False, na=False)]

                if show_only_confirmed and "LU" in show_hproj.columns:
                    show_hproj = show_hproj[show_hproj["LU"].notna()]

                desired_cols = [
                    "Batter", "Pos", "Team", "Sal", "Opp", "Park", "OppSP", "LU",
                    "DKPts", "Value", "HR", "SB", "Floor", "Ceil", "Own%"
                ]
                desired_cols = [c for c in desired_cols if c in show_hproj.columns]
                show_hproj = show_hproj[desired_cols]

                if sort_by in show_hproj.columns:
                    show_hproj = show_hproj.sort_values(by=sort_by, ascending=False)

                if top_n != "All":
                    show_hproj = show_hproj.head(int(top_n))

                st.markdown("### Table Options")

                default_visible_cols = [c for c in ["Batter", "Pos", "Team", "Sal", "Opp", "OppSP", "LU", "DKPts", "Value", "HR", "SB", "Floor", "Ceil", "Own%"] if c in show_hproj.columns]

                visible_cols = st.multiselect(
                    "Choose columns to display",
                    options=show_hproj.columns.tolist(),
                    default=default_visible_cols,
                    key="visible_hitter_columns"
                )

                if visible_cols:
                    display_df = show_hproj[visible_cols].copy()
                else:
                    display_df = show_hproj.copy()

                csv_data = convert_df_to_csv(display_df)

                dl_col1, dl_col2 = st.columns([1, 5])
                with dl_col1:
                    st.download_button(
                        label="EXPORT TO CSV",
                        data=csv_data,
                        file_name="hitter_projections.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                with dl_col2:
                    st.caption("Downloads directly through the browser to the user's computer.")

                numeric_format_dict = {}
                for col in display_df.columns:
                    if col in ["DKPts", "Value", "HR", "SB", "Floor", "Ceil"]:
                        numeric_format_dict[col] = "{:.2f}"
                    elif col in ["Sal"]:
                        numeric_format_dict[col] = "${:,.0f}"
                    elif col in ["Own%"]:
                        numeric_format_dict[col] = "{:.0f}"

                style_subset = [c for c in ["DKPts", "Value", "Sal", "HR", "SB"] if c in display_df.columns]

                if len(display_df) > 0:
                    styled_df = (
                        display_df.style
                        .apply(color_cells_HitProj, subset=style_subset, axis=1)
                        .format(numeric_format_dict)
                        .set_table_styles([
                            {"selector": "th", "props": [("text-align", "left"), ("font-weight", "bold")]},
                            {"selector": "td", "props": [("text-align", "left")]}
                        ])
                    )

                    st.dataframe(
                        styled_df,
                        use_container_width=True,
                        hide_index=True,
                        height=700
                    )
                else:
                    st.warning("No hitters match the current filters.")

            # =========================================================
            # TODAY VS SEASON AVG
            # =========================================================
            elif hproj_option == "Today vs. Season Avg":
                needed_cols = [c for c in ["Hitter", "Sal", "Pos"] if c in hitterproj.columns]
                needed_proj_data = hitterproj[needed_cols].drop_duplicates(subset=["Hitter"]).copy()

                havg = h_vs_avg.copy()
                havg = pd.merge(havg, needed_proj_data, on="Hitter", how="left")

                if main_slate_check and "MainSlate" in hitterproj.columns:
                    mainslate_teams = hitterproj[hitterproj["MainSlate"] == "Main"]["Team"].dropna().unique().tolist()
                    havg = havg[havg["Team"].isin(mainslate_teams)]

                filt1, filt2, filt3, filt4, filt5 = st.columns(5)

                with filt1:
                    team_options = ["All"] + sorted(havg["Team"].dropna().unique().tolist())
                    selected_team = st.selectbox("Select a Team", team_options, key="havg_team_filter")

                with filt2:
                    pos_filter_avg = st.text_input(
                        "Filter by Position",
                        placeholder="OF, SS, C, etc.",
                        key="pos_filter_avg_hitters"
                    )

                with filt3:
                    hitter_search_avg = st.text_input(
                        "Search Hitter",
                        placeholder="Player name",
                        key="hitter_search_avg"
                    )

                with filt4:
                    sort_avg_by = st.selectbox(
                        "Sort FP Table By",
                        ["DKPts Diff", "DKPts", "Avg DK Proj", "Sal"],
                        index=0,
                        key="sort_avg_hitters_fp"
                    )

                with filt5:
                    sort_hr_by = st.selectbox(
                        "Sort HR Table By",
                        ["HR Diff", "HR", "Avg HR Proj"],
                        index=0,
                        key="sort_avg_hitters_hr"
                    )

                filtered_havg = havg.copy()

                if selected_team != "All":
                    filtered_havg = filtered_havg[filtered_havg["Team"] == selected_team]

                if pos_filter_avg and "Pos" in filtered_havg.columns:
                    filtered_havg = filtered_havg[filtered_havg["Pos"].astype(str).str.contains(pos_filter_avg, case=False, na=False)]

                if hitter_search_avg:
                    filtered_havg = filtered_havg[filtered_havg["Hitter"].astype(str).str.contains(hitter_search_avg, case=False, na=False)]

                fp_cols = [c for c in ["Hitter", "Team", "Sal", "Pos", "Opp", "OppSP", "DKPts", "Avg DK Proj", "DKPts Diff"] if c in filtered_havg.columns]
                show_proj_df = filtered_havg[fp_cols].copy()

                if sort_avg_by in show_proj_df.columns:
                    show_proj_df = show_proj_df.sort_values(by=sort_avg_by, ascending=False)

                hr_cols = [c for c in ["Hitter", "Team", "Pos", "Opp", "OppSP", "HR", "Avg HR Proj", "HR Diff"] if c in filtered_havg.columns]
                show_proj_df_hr = filtered_havg[hr_cols].copy()

                if sort_hr_by in show_proj_df_hr.columns:
                    show_proj_df_hr = show_proj_df_hr.sort_values(by=sort_hr_by, ascending=False)

                st.markdown("### Fantasy Point Projection")

                fp_csv = convert_df_to_csv(show_proj_df)
                fpdl1, fpdl2 = st.columns([1, 5])
                with fpdl1:
                    st.download_button(
                        label="EXPORT FP CSV",
                        data=fp_csv,
                        file_name="hitter_today_vs_avg_fantasy_points.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                with fpdl2:
                    st.caption("Downloads the filtered fantasy-point comparison table.")

                styled_fp = show_proj_df.style.apply(
                    color_cells_HitProj,
                    subset=[c for c in ["DKPts", "Sal", "Avg DK Proj", "DKPts Diff"] if c in show_proj_df.columns],
                    axis=1
                ).format({
                    "DKPts": "{:.2f}",
                    "Sal": "${:,.0f}",
                    "Avg DK Proj": "{:.2f}",
                    "DKPts Diff": "{:.2f}"
                })

                st.dataframe(
                    styled_fp,
                    hide_index=True,
                    use_container_width=True,
                    height=600 if len(show_proj_df) > 20 else None
                )

                st.markdown("### Home Run Projection")

                hr_csv = convert_df_to_csv(show_proj_df_hr)
                hrdl1, hrdl2 = st.columns([1, 5])
                with hrdl1:
                    st.download_button(
                        label="EXPORT HR CSV",
                        data=hr_csv,
                        file_name="hitter_today_vs_avg_hr.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                with hrdl2:
                    st.caption("Downloads the filtered HR comparison table.")

                styled_hr = show_proj_df_hr.style.apply(
                    color_cells_HitProj,
                    subset=[c for c in ["HR", "Avg HR Proj", "HR Diff"] if c in show_proj_df_hr.columns],
                    axis=1
                ).format({
                    "HR": "{:.2f}",
                    "Avg HR Proj": "{:.2f}",
                    "HR Diff": "{:.2f}"
                })

                st.dataframe(
                    styled_hr,
                    hide_index=True,
                    use_container_width=True,
                    height=600 if len(show_proj_df_hr) > 20 else None
                )

    if tab == "Hitter Projections _ ":
        import streamlit as st
        import pandas as pd
        import numpy as np

        require_pro()

        # =========================================================
        # LOAD DATA
        # =========================================================
        hitterproj_raw, pitcherproj_raw, hitterproj2, gameinfo_raw = load_daily_projections()
        hitter_stats_raw, lineup_stats, pitcher_stats, h_vs_avg, p_vs_avg, h_vs_sim, hotzonedata, posdata = load_player_stats()
        bpreport_raw, rpstats = load_bullpen_data()

        (
            hitterproj,
            pitcherproj,
            hitter_stats,
            gameinfo,
            bpreport,
            games_df,
            mainslateteams,
            main_slate_gamelist,
            confirmed_lus,
            last_update
        ) = _prepare_projection_data(
            hitterproj_raw,
            pitcherproj_raw,
            hitterproj2,
            gameinfo_raw,
            hitter_stats_raw,
            h_vs_avg,
            bpreport_raw
        )

        # =========================================================
        # CLEAN / PREP
        # =========================================================
        hitterproj = hitterproj.copy()
        h_vs_avg = h_vs_avg.copy()

        slate_options = list(hitterproj['MainSlate'].unique())

        hitterproj["Hitter"] = hitterproj["Hitter"].astype(str).str.replace("🔥", "", regex=False).str.replace("🥶", "", regex=False).str.strip()

        if "Batter" not in hitterproj.columns and "Hitter" in hitterproj.columns:
            hitterproj["Batter"] = hitterproj["Hitter"]

        if "Value" not in hitterproj.columns and {"DKPts", "Sal"}.issubset(hitterproj.columns):
            hitterproj["Value"] = np.where(
                hitterproj["Sal"].fillna(0) > 0,
                round(hitterproj["DKPts"] / (hitterproj["Sal"] / 1000), 2),
                np.nan
            )
        hitterproj["Value"] = np.where(
                hitterproj["Sal"].fillna(0) > 0,
                round(hitterproj["DKPts"] / (hitterproj["Sal"] / 1000), 2),
                np.nan
            )

        hitter_name_id_dict = dict(zip(hitterproj["Hitter"], hitterproj["ID"]))
        hitter_matchups_dict = dict(zip(hitterproj["Team"], hitterproj["Opp"]))
        hitter_matchups_pp_dict = dict(zip(hitterproj["Team"], hitterproj["OppSP"]))
        hitter_park_dict = dict(zip(hitterproj["Team"], hitterproj["Park"]))

        h_vs_avg["Opp"] = h_vs_avg["Team"].map(hitter_matchups_dict)
        h_vs_avg["OppSP"] = h_vs_avg["Team"].map(hitter_matchups_pp_dict)

        # =========================================================
        # PAGE STYLING
        # =========================================================
        st.markdown("""
        <style>
        .hit-hero {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 55%, #334155 100%);
            padding: 24px 28px;
            border-radius: 18px;
            margin-bottom: 18px;
            border: 1px solid rgba(255,255,255,0.08);
        }
        .hit-hero h1 {
            margin: 0;
            color: white;
            font-size: 2rem;
        }
        .hit-hero p {
            margin: 6px 0 0 0;
            color: #cbd5e1;
            font-size: 0.96rem;
        }
        </style>
        """, unsafe_allow_html=True)

        st.markdown(
            f"""
            <div class="hit-hero">
                <h1>Hitter Projections</h1>
                <p>Explore daily hitter projections, matchup boosts, team outlooks, and downloadable CSV exports.</p>
                <p><b>Last update:</b> {last_update} EST</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        # =========================================================
        # TOP OPTIONS
        # =========================================================
        top_opt1, top_opt2, top_opt3, top_opt4 = st.columns(4)

        with top_opt1:
            show_highlights = st.toggle("Show Projection Highlights", value=False, key="show_hitter_highlights")

        with top_opt2:
            show_team_proj = st.toggle("Show Team Projections", value=False, key="show_team_hitter_proj")

        with top_opt3:
            slate_options = ['Main','Early']
            main_slate_check = st.toggle("Show Main Slate Only", value=False, key="show_main_slate_hitters")
            #main_slate_check = st.selectbox("Choose Slate", slate_options, key="show_main_slate_hitters")

        with top_opt4:
            show_only_confirmed = st.toggle("Confirmed Lineups Only", value=False, key="confirmed_only_hitters")

        # =========================================================
        # HIGHLIGHTS
        # =========================================================
        if show_highlights:
            st.markdown("### Projection Highlights")

            top_hr = h_vs_avg.sort_values(by="HR", ascending=False).head(5).copy()
            top_hr["Opp"] = top_hr["Team"].map(hitter_matchups_dict)
            top_hr["OppSP"] = top_hr["Team"].map(hitter_matchups_pp_dict)
            top_hr["Park"] = top_hr["Team"].map(hitter_park_dict)
            top_hr["ID"] = top_hr["Hitter"].map(hitter_name_id_dict)

            st.markdown("#### Top HR Projections")
            cols = st.columns(5)
            for i, col in enumerate(cols):
                if i < len(top_hr):
                    row = top_hr.iloc[i]
                    with col:
                        st.image(get_player_image(row["ID"]), width=105)
                        st.markdown(f"**{row['Hitter']}**")
                        st.caption(f"{row['Team']} vs {row['Opp']} | {row['OppSP']}")
                        st.write(f"HR: **{row['HR']:.2f}**")

            st.markdown("#### Top HR Projection Boosts")
            top_hr_boost = h_vs_avg.sort_values(by="HR Diff", ascending=False).head(5).copy()
            top_hr_boost["Opp"] = top_hr_boost["Team"].map(hitter_matchups_dict)
            top_hr_boost["OppSP"] = top_hr_boost["Team"].map(hitter_matchups_pp_dict)
            top_hr_boost["Park"] = top_hr_boost["Team"].map(hitter_park_dict)
            top_hr_boost["ID"] = top_hr_boost["Hitter"].map(hitter_name_id_dict)

            cols = st.columns(5)
            for i, col in enumerate(cols):
                if i < len(top_hr_boost):
                    row = top_hr_boost.iloc[i]
                    with col:
                        st.image(get_player_image(row["ID"]), width=105)
                        st.markdown(f"**{row['Hitter']}**")
                        st.caption(f"{row['Team']} vs {row['Opp']} | {row['OppSP']}")
                        st.write(f"Boost: **+{row['HR Diff']:.2f} HR**")

            st.markdown("#### Biggest Fantasy Point Boosts")
            show_leaders = h_vs_avg.sort_values(by="DKPts Diff", ascending=False).copy()
            show_leaders["Opp"] = show_leaders["Team"].map(hitter_matchups_dict)
            show_leaders["OppSP"] = show_leaders["Team"].map(hitter_matchups_pp_dict)
            show_leaders = show_leaders[["Hitter", "Team", "Opp", "OppSP", "DKPts", "Avg DK Proj", "DKPts Diff"]].head(10)

            st.dataframe(show_leaders, hide_index=True, use_container_width=True)
            st.markdown("---")

        # =========================================================
        # TEAM PROJECTIONS
        # =========================================================
        if show_team_proj:
            st.markdown("### Team Projection Data")

            team_col1, team_col2 = st.columns(2)

            with team_col1:
                teamproj_source = hitterproj.copy()
                if main_slate_check and "MainSlate" in teamproj_source.columns:
                    teamproj_source = teamproj_source[teamproj_source["MainSlate"] == "Main"]

                teamproj = (
                    teamproj_source.groupby(["Team", "Opp", "OppSP"], as_index=False)[["DKPts", "R", "HR", "SB"]]
                    .sum()
                    .sort_values(by="DKPts", ascending=False)
                )

                styled_teamproj = teamproj.style.format({
                    "DKPts": "{:.2f}",
                    "R": "{:.2f}",
                    "HR": "{:.2f}",
                    "SB": "{:.2f}"
                })

                st.markdown("#### Raw Team Totals")
                st.dataframe(styled_teamproj, hide_index=True, use_container_width=True)

            with team_col2:
                team_avg_source = h_vs_avg.copy()

                if main_slate_check and "MainSlate" in hitterproj.columns:
                    mainslate_teams = hitterproj[hitterproj["MainSlate"] == "Main"]["Team"].dropna().unique().tolist()
                    team_avg_source = team_avg_source[team_avg_source["Team"].isin(mainslate_teams)]

                team_v_avg = (
                    team_avg_source.groupby(["Team", "Opp", "OppSP"], as_index=False)[["HR", "Avg HR Proj", "DKPts", "Avg DK Proj"]]
                    .sum()
                )
                team_v_avg.columns = ["Team", "Opp", "OppSP", "Today HR", "Season HR", "Today DK", "Season DK"]

                team_v_avg["Today HR Boost"] = np.where(
                    team_v_avg["Season HR"] != 0,
                    team_v_avg["Today HR"] / team_v_avg["Season HR"],
                    np.nan
                )
                team_v_avg["Today DK Boost"] = np.where(
                    team_v_avg["Season DK"] != 0,
                    team_v_avg["Today DK"] / team_v_avg["Season DK"],
                    np.nan
                )

                team_v_avg = team_v_avg.sort_values(by="Today DK Boost", ascending=False)

                styled_team_v_avg = team_v_avg.style.format({
                    "Today HR": "{:.2f}",
                    "Season HR": "{:.2f}",
                    "Today DK": "{:.2f}",
                    "Season DK": "{:.2f}",
                    "Today HR Boost": "{:.1%}",
                    "Today DK Boost": "{:.1%}"
                })

                st.markdown("#### Today vs Season")
                st.dataframe(styled_team_v_avg, hide_index=True, use_container_width=True)

            st.markdown("---")

        # =========================================================
        # MAIN VIEW SELECTOR
        # =========================================================
        st.markdown("### Full Projections")

        mode_col1, mode_col2 = st.columns([1, 3])
        with mode_col1:
            hproj_option = st.selectbox(
                "What Type To Show",
                ["Todays Projections", "Today vs. Season Avg"],
                index=0,
                key="projtype_hitters"
            )

        # =========================================================
        # TODAYS PROJECTIONS
        # =========================================================
        if hproj_option == "Todays Projections":
            filt1, filt2, filt3, filt4, filt5, filt6 = st.columns(6)

            with filt1:
                slate_option = st.selectbox(
                    "Slate",
                    #["Show All", "Main Slate Only"],
                    slate_options,
                    index=1 if main_slate_check else 0,
                    key="slate_filter_hitters"
                )

            with filt2:
                teams = ["All Teams"] + sorted(hitterproj["Team"].dropna().unique().tolist())
                team_filter = st.selectbox(
                    "Filter by Team",
                    teams,
                    index=0,
                    key="team_filter_hitters"
                )

            with filt3:
                pos_filter = st.text_input(
                    "Filter by Position",
                    placeholder="OF, SS, C, etc.",
                    key="pos_filter_hitters"
                )

            with filt4:
                hitter_search = st.text_input(
                    "Search Hitter",
                    placeholder="Player name",
                    key="hitter_search_name"
                )

            with filt5:
                min_dkpts = st.number_input(
                    "Min DKPts",
                    min_value=0.0,
                    value=0.0,
                    step=0.5,
                    key="min_dkpts_hitters"
                )

            with filt6:
                min_salary = st.number_input(
                    "Min Salary",
                    min_value=0,
                    value=0,
                    step=100,
                    key="min_salary_hitters"
                )

            filt7, filt8, filt9, filt10 = st.columns(4)

            with filt7:
                sort_by = st.selectbox(
                    "Sort By",
                    ["DKPts", "Value", "Sal", "HR", "SB", "Floor", "Ceil", "Own%"],
                    index=0,
                    key="sort_hitters_proj"
                )

            with filt8:
                lineup_filter = st.selectbox(
                    "Lineup Spot",
                    ["All"] + [str(i) for i in range(1, 10)],
                    index=0,
                    key="lineup_spot_filter"
                )

            with filt9:
                park_filter = st.text_input(
                    "Filter by Park",
                    placeholder="Park name",
                    key="park_filter_hitters"
                )

            with filt10:
                top_n = st.selectbox(
                    "Show Top N",
                    ["All", 25, 50, 100],
                    index=0,
                    key="top_n_hitters"
                )

            show_hproj = hitterproj.copy()

            #if slate_option == "Main Slate Only" and "MainSlate" in show_hproj.columns:
            #    show_hproj = show_hproj[show_hproj["MainSlate"] == "Main"]
            if slate_option == "Main":
                show_hproj = show_hproj[show_hproj["MainSlate"] == "Main"]

            if slate_option == "Early":
                show_hproj = show_hproj[show_hproj["MainSlate"] == "Early"]

            if team_filter != "All Teams":
                show_hproj = show_hproj[show_hproj["Team"] == team_filter]

            if pos_filter:
                show_hproj = show_hproj[show_hproj["Pos"].astype(str).str.contains(pos_filter, case=False, na=False)]

            if hitter_search:
                search_col = "Batter" if "Batter" in show_hproj.columns else "Hitter"
                show_hproj = show_hproj[show_hproj[search_col].astype(str).str.contains(hitter_search, case=False, na=False)]

            if "DKPts" in show_hproj.columns:
                show_hproj = show_hproj[show_hproj["DKPts"].fillna(0) >= min_dkpts]

            if "Sal" in show_hproj.columns:
                show_hproj = show_hproj[show_hproj["Sal"].fillna(0) >= min_salary]

            if lineup_filter != "All" and "LU" in show_hproj.columns:
                show_hproj = show_hproj[show_hproj["LU"].astype(str) == lineup_filter]

            if park_filter and "Park" in show_hproj.columns:
                show_hproj = show_hproj[show_hproj["Park"].astype(str).str.contains(park_filter, case=False, na=False)]

            if show_only_confirmed and "LU" in show_hproj.columns:
                show_hproj = show_hproj[show_hproj["LU"].notna()]

            show_hproj = show_hproj.rename({"Ownership": "Own%"}, axis=1)

            desired_cols = [
                "Batter", "Pos", "Team", "Sal", "Opp", "Park", "OppSP", "LU",
                "DKPts", "Value", "HR", "SB", "Floor", "Ceil", "Own%"
            ]
            desired_cols = [c for c in desired_cols if c in show_hproj.columns]
            show_hproj = show_hproj[desired_cols]

            if sort_by in show_hproj.columns:
                show_hproj = show_hproj.sort_values(by=sort_by, ascending=False)

            if top_n != "All":
                show_hproj = show_hproj.head(int(top_n))

            st.markdown("### Table Options")

            default_visible_cols = [c for c in ["Batter", "Pos", "Team", "Sal", "Opp", "OppSP", "LU", "DKPts", "Value", "HR", "SB", "Floor", "Ceil", "Own%"] if c in show_hproj.columns]

            visible_cols = st.multiselect(
                "Choose columns to display",
                options=show_hproj.columns.tolist(),
                default=default_visible_cols,
                key="visible_hitter_columns"
            )

            if visible_cols:
                display_df = show_hproj[visible_cols].copy()
            else:
                display_df = show_hproj.copy()

            @st.cache_data
            def convert_df_to_csv(df):
                return df.to_csv(index=False).encode("utf-8")

            csv_data = convert_df_to_csv(display_df)

            dl_col1, dl_col2 = st.columns([1, 5])
            with dl_col1:
                st.download_button(
                    label="EXPORT TO CSV",
                    data=csv_data,
                    file_name="hitter_projections.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            with dl_col2:
                st.caption("Downloads directly through the browser to the user's computer.")

            numeric_format_dict = {}
            for col in display_df.columns:
                if col in ["DKPts", "Value", "HR", "SB", "Floor", "Ceil"]:
                    numeric_format_dict[col] = "{:.2f}"
                elif col in ["Sal"]:
                    numeric_format_dict[col] = "${:,.0f}"
                elif col in ["Own%"]:
                    numeric_format_dict[col] = "{:.0f}"

            style_subset = [c for c in ["DKPts", "Value", "Sal", "HR", "SB"] if c in display_df.columns]

            if len(display_df) > 0:
                styled_df = (
                    display_df.style
                    .apply(color_cells_HitProj, subset=style_subset, axis=1)
                    .format(numeric_format_dict)
                    .set_table_styles([
                        {"selector": "th", "props": [("text-align", "left"), ("font-weight", "bold")]},
                        {"selector": "td", "props": [("text-align", "left")]}
                    ])
                )

                st.dataframe(
                    styled_df,
                    use_container_width=True,
                    hide_index=True,
                    height=700
                )
            else:
                st.warning("No hitters match the current filters.")

        # =========================================================
        # TODAY VS SEASON AVG
        # =========================================================
        elif hproj_option == "Today vs. Season Avg":
            needed_cols = [c for c in ["Hitter", "Sal", "Pos"] if c in hitterproj.columns]
            needed_proj_data = hitterproj[needed_cols].drop_duplicates(subset=["Hitter"]).copy()

            havg = h_vs_avg.copy()
            havg = pd.merge(havg, needed_proj_data, on="Hitter", how="left")

            if main_slate_check and "MainSlate" in hitterproj.columns:
                mainslate_teams = hitterproj[hitterproj["MainSlate"] == "Main"]["Team"].dropna().unique().tolist()
                havg = havg[havg["Team"].isin(mainslate_teams)]

            filt1, filt2, filt3, filt4, filt5 = st.columns(5)

            with filt1:
                team_options = ["All"] + sorted(havg["Team"].dropna().unique().tolist())
                selected_team = st.selectbox("Select a Team", team_options, key="havg_team_filter")

            with filt2:
                pos_filter_avg = st.text_input(
                    "Filter by Position",
                    placeholder="OF, SS, C, etc.",
                    key="pos_filter_avg_hitters"
                )

            with filt3:
                hitter_search_avg = st.text_input(
                    "Search Hitter",
                    placeholder="Player name",
                    key="hitter_search_avg"
                )

            with filt4:
                sort_avg_by = st.selectbox(
                    "Sort FP Table By",
                    ["DKPts Diff", "DKPts", "Avg DK Proj", "Sal"],
                    index=0,
                    key="sort_avg_hitters_fp"
                )

            with filt5:
                sort_hr_by = st.selectbox(
                    "Sort HR Table By",
                    ["HR Diff", "HR", "Avg HR Proj"],
                    index=0,
                    key="sort_avg_hitters_hr"
                )

            filtered_havg = havg.copy()

            if selected_team != "All":
                filtered_havg = filtered_havg[filtered_havg["Team"] == selected_team]

            if pos_filter_avg and "Pos" in filtered_havg.columns:
                filtered_havg = filtered_havg[filtered_havg["Pos"].astype(str).str.contains(pos_filter_avg, case=False, na=False)]

            if hitter_search_avg:
                filtered_havg = filtered_havg[filtered_havg["Hitter"].astype(str).str.contains(hitter_search_avg, case=False, na=False)]

            fp_cols = [c for c in ["Hitter", "Team", "Sal", "Pos", "Opp", "OppSP", "DKPts", "Avg DK Proj", "DKPts Diff"] if c in filtered_havg.columns]
            show_proj_df = filtered_havg[fp_cols].copy()

            if sort_avg_by in show_proj_df.columns:
                show_proj_df = show_proj_df.sort_values(by=sort_avg_by, ascending=False)

            hr_cols = [c for c in ["Hitter", "Team", "Pos", "Opp", "OppSP", "HR", "Avg HR Proj", "HR Diff"] if c in filtered_havg.columns]
            show_proj_df_hr = filtered_havg[hr_cols].copy()

            if sort_hr_by in show_proj_df_hr.columns:
                show_proj_df_hr = show_proj_df_hr.sort_values(by=sort_hr_by, ascending=False)

            st.markdown("### Fantasy Point Projection")

            fp_csv = convert_df_to_csv(show_proj_df)
            fpdl1, fpdl2 = st.columns([1, 5])
            with fpdl1:
                st.download_button(
                    label="EXPORT FP CSV",
                    data=fp_csv,
                    file_name="hitter_today_vs_avg_fantasy_points.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            with fpdl2:
                st.caption("Downloads the filtered fantasy-point comparison table.")

            styled_fp = show_proj_df.style.apply(
                color_cells_HitProj,
                subset=[c for c in ["DKPts", "Sal", "Avg DK Proj", "DKPts Diff"] if c in show_proj_df.columns],
                axis=1
            ).format({
                "DKPts": "{:.2f}",
                "Sal": "${:,.0f}",
                "Avg DK Proj": "{:.2f}",
                "DKPts Diff": "{:.2f}"
            })

            st.dataframe(
                styled_fp,
                hide_index=True,
                use_container_width=True,
                height=600 if len(show_proj_df) > 20 else None
            )

            st.markdown("### Home Run Projection")

            hr_csv = convert_df_to_csv(show_proj_df_hr)
            hrdl1, hrdl2 = st.columns([1, 5])
            with hrdl1:
                st.download_button(
                    label="EXPORT HR CSV",
                    data=hr_csv,
                    file_name="hitter_today_vs_avg_hr.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            with hrdl2:
                st.caption("Downloads the filtered HR comparison table.")

            styled_hr = show_proj_df_hr.style.apply(
                color_cells_HitProj,
                subset=[c for c in ["HR", "Avg HR Proj", "HR Diff"] if c in show_proj_df_hr.columns],
                axis=1
            ).format({
                "HR": "{:.2f}",
                "Avg HR Proj": "{:.2f}",
                "HR Diff": "{:.2f}"
            })

            st.dataframe(
                styled_hr,
                hide_index=True,
                use_container_width=True,
                height=600 if len(show_proj_df_hr) > 20 else None
            )


    
    if tab == "Matchups":
        require_pro()


        # --- Load only what this page needs ---
        hitterproj_raw, pitcherproj_raw, hitterproj2, gameinfo_raw = load_daily_projections()
        hitter_stats_raw, lineup_stats, pitcher_stats, h_vs_avg, p_vs_avg, h_vs_sim, hotzonedata, posdata = load_player_stats()
        bpreport_raw, rpstats = load_bullpen_data()
        umpire_data, weather_data = load_weather_umps()
        if len(weather_data) < 1:
            weather_data = pd.DataFrame()
        team_vs_sim = h_vs_sim[h_vs_sim['PC'] > 49].groupby('Team', as_index=False)[['xwOBA','SwStr%','AVG','SLG','Brl%','FB%']].mean()
        team_vs_sim['RawRank'] = len(team_vs_sim) - team_vs_sim['xwOBA'].rank() + 1
        team_vs_sim['Rank'] = team_vs_sim['RawRank'].astype(int).astype(str) + '/' + str(len(team_vs_sim))
        (hitterproj, pitcherproj, hitter_stats, gameinfo, bpreport,
         games_df, mainslateteams, main_slate_gamelist,
         confirmed_lus, last_update) = _prepare_projection_data(
            hitterproj_raw, pitcherproj_raw, hitterproj2, gameinfo_raw,
            hitter_stats_raw, h_vs_avg, bpreport_raw)
        st.markdown("<h2><center><br>Projections Detail</h2></center>", unsafe_allow_html=True)

        if st.checkbox("Show Team Ranks"):
            
            st.markdown("<h2>Team Matchups</h2>", unsafe_allow_html=True)

            if st.checkbox("Main Slate Only"):
                show_team_vs_sim = team_vs_sim[team_vs_sim['Team'].isin(mainslateteams)].sort_values(by='RawRank')
                show_team_vs_sim = show_team_vs_sim.drop(['Rank'],axis=1)

                show_team_vs_sim = show_team_vs_sim.rename({'RawRank': 'Rank'},axis=1)

                team_styled_df = show_team_vs_sim.style.apply(color_cells_HitMatchups, subset=['xwOBA', 'AVG', 'SLG',
                                                                                'SwStr%','Brl%','FB%'], axis=1).format({
                    'xwOBA': '{:.3f}', 'xwOBA Con': '{:.3f}','AVG': '{:.3f}',
                    'SwStr%': '{:.1%}', 'Brl%': '{:.1%}', 'SLG': '{:.3f}',
                    'FB%': '{:.1%}', 'Hard%': '{:.1%}', 'Rank': '{:.0f}'
                })
                st.dataframe(team_styled_df, hide_index=True, width=600, height=560)
            else:       
                show_team_vs_sim = team_vs_sim.sort_values(by='RawRank')
                show_team_vs_sim = show_team_vs_sim.drop(['Rank'],axis=1)

                show_team_vs_sim = show_team_vs_sim.rename({'RawRank': 'Rank'},axis=1)

                team_styled_df = show_team_vs_sim.style.apply(color_cells_HitMatchups, subset=['xwOBA', 'AVG', 'SLG',
                                                                                'SwStr%','Brl%','FB%'], axis=1).format({
                    'xwOBA': '{:.3f}', 'xwOBA Con': '{:.3f}','AVG': '{:.3f}',
                    'SwStr%': '{:.1%}', 'Brl%': '{:.1%}', 'SLG': '{:.3f}',
                    'FB%': '{:.1%}', 'Hard%': '{:.1%}', 'Rank': '{:.0f}'
                })
                st.dataframe(team_styled_df, hide_index=True, width=600, height=560)
            
        
        team_options = ['All'] + list(h_vs_sim['Team'].unique())
        col1, col2 = st.columns([1, 3])
        with col1:
            selected_team = st.selectbox('Filter by Team', team_options)

        # Create a single row for sliders
        col_pc, col_xwoba, col_swstr, col_brl = st.columns(4)
        with col_pc:
            pc_min = int(h_vs_sim['PC'].min())
            pc_max = int(h_vs_sim['PC'].max())
            pc_range = st.slider('PC Range', pc_min, pc_max, (pc_min, pc_max))
        with col_xwoba:
            xwoba_min = float(h_vs_sim['xwOBA'].min())
            xwoba_max = float(h_vs_sim['xwOBA'].max())
            xwoba_range = st.slider('xwOBA Range', xwoba_min, xwoba_max, (xwoba_min, xwoba_max), step=0.001)
        with col_swstr:
            swstr_min = float(h_vs_sim['SwStr%'].min())
            swstr_max = float(h_vs_sim['SwStr%'].max())
            swstr_range = st.slider('SwStr% Range', swstr_min, swstr_max, (swstr_min, swstr_max), step=0.001)
        with col_brl:
            brl_min = float(h_vs_sim['Brl%'].min())
            brl_max = float(h_vs_sim['Brl%'].max())
            brl_range = st.slider('Brl% Range', brl_min, brl_max, (brl_min, brl_max), step=0.001)

        # Filter data based on team and slider values
        if selected_team == 'All':
            show_hsim = h_vs_sim[
                (h_vs_sim['PC'].between(pc_range[0], pc_range[1])) &
                (h_vs_sim['xwOBA'].between(xwoba_range[0], xwoba_range[1])) &
                (h_vs_sim['SwStr%'].between(swstr_range[0], swstr_range[1])) &
                (h_vs_sim['Brl%'].between(brl_range[0], brl_range[1]))
            ][['Hitter','Team','OppSP','PC','BIP','xwOBA','xwOBA Con','SwStr%','Brl%','FB%','Hard%']]
        else:
            show_hsim = h_vs_sim[
                (h_vs_sim['Team'] == selected_team) &
                (h_vs_sim['PC'].between(pc_range[0], pc_range[1])) &
                (h_vs_sim['xwOBA'].between(xwoba_range[0], xwoba_range[1])) &
                (h_vs_sim['SwStr%'].between(swstr_range[0], swstr_range[1])) &
                (h_vs_sim['Brl%'].between(brl_range[0], brl_range[1]))
            ][['Hitter','Team','OppSP','PC','BIP','xwOBA','xwOBA Con','SwStr%','Brl%','FB%','Hard%']]

        styled_df = show_hsim.style.apply(color_cells_HitMatchups, subset=['xwOBA','xwOBA Con',
                                                                        'SwStr%','Brl%','FB%',
                                                                        'Hard%'], axis=1).format({
            'xwOBA': '{:.3f}', 'xwOBA Con': '{:.3f}',
            'SwStr%': '{:.1%}', 'Brl%': '{:.1%}',
            'FB%': '{:.1%}', 'Hard%': '{:.1%}'
        })

        if len(show_hsim) > 9:
            st.dataframe(styled_df, hide_index=True, use_container_width=True, height=900)
        else:
            st.dataframe(styled_df, hide_index=True, use_container_width=True)
  
    if tab == "Player Trends":
        work_in_progress()
        # --- Load only what this page needs ---
        trend_h, trend_p = load_trends()
        hitter_stats_raw, lineup_stats, pitcher_stats, h_vs_avg, p_vs_avg, h_vs_sim, hotzonedata, posdata = load_player_stats()
        hitter_stats = hitter_stats_raw.copy()
        st.markdown("<h1><center>Player Trends</center></h1>", unsafe_allow_html=True)

        col1,col2,col3 = st.columns([3,1,3])
        with col2:
            h_p_selection = st.selectbox('Select',['Hitters','Pitchers'])
        
        if h_p_selection == 'Hitters':

            st.markdown('<b><center><i>Determined by comparing xwOBA over expectation from the last 15 days with what each hitter did before these last 15 days', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("<h3><center>🔥 Hottest Hitters 🔥</center></h3>", unsafe_allow_html=True)

                hot_five_ids = trend_h.sort_values(by='Hot Score',ascending=False).head(5)['batter'].unique()
                xcol1,xcol2,xcol3 = st.columns(3)
                picture_width = 105
                with xcol1:
                    st.image(get_player_image(hot_five_ids[0]), width=picture_width)
                with xcol2:
                    st.image(get_player_image(hot_five_ids[1]), width=picture_width)
                with xcol3:
                    st.image(get_player_image(hot_five_ids[2]), width=picture_width)

                hot_five_h = trend_h.sort_values(by='Hot Score',ascending=False).head(10)[['BatterName','xwOBA OE','xwOBA OE L15','Hot Score']]
                styled_hot_five = hot_five_h.style.apply(color_cells_HitMatchups, subset=['xwOBA OE','xwOBA OE L15','Hot Score'], axis=1).format({'xwOBA OE': '{:.3f}', 'xwOBA OE L15': '{:.3f}', 'Hot Score': '{:.3f}'})
                st.dataframe(styled_hot_five, hide_index=True, width=600)
            with col2:
                st.markdown("<h3><center>🧊 Coldest Hitters 🧊</center></h3>", unsafe_allow_html=True)

                cold_five_ids = trend_h.sort_values(by='Hot Score',ascending=True).head(5)['batter'].unique()
                zcol1,zcol2,zcol3 = st.columns(3)
                
                with zcol1:
                    st.image(get_player_image(cold_five_ids[0]), width=picture_width)
                with zcol2:
                    st.image(get_player_image(cold_five_ids[1]), width=picture_width)
                with zcol3:
                    st.image(get_player_image(cold_five_ids[2]), width=picture_width)
                
                col_five_h = trend_h.sort_values(by='Hot Score',ascending=True).head(10)[['BatterName','xwOBA OE','xwOBA OE L15','Hot Score']]
                styled_cold_five = col_five_h.style.apply(color_cells_HitMatchups, subset=['xwOBA OE','xwOBA OE L15','Hot Score'], axis=1).format({'xwOBA OE': '{:.3f}', 'xwOBA OE L15': '{:.3f}', 'Hot Score': '{:.3f}'})
                st.dataframe(styled_cold_five, hide_index=True, width=600)

            st.markdown("<h3><center>Full Table</center></h3>", unsafe_allow_html=True)
            
            bcol1,bcol2,bcol3 = st.columns([1,3,1])
            with bcol2:
                all_trend_h = trend_h.sort_values(by='Hot Score',ascending=False)[['BatterName','xwOBA OE','xwOBA OE L15','Hot Score']]
                styled_all_trend_h = all_trend_h.style.apply(color_cells_HitMatchups, subset=['xwOBA OE','xwOBA OE L15','Hot Score'], axis=1).format({'xwOBA OE': '{:.3f}', 'xwOBA OE L15': '{:.3f}', 'Hot Score': '{:.3f}'})
                st.dataframe(styled_all_trend_h, hide_index=True, width=700,height=900)


        elif h_p_selection == 'Pitchers':
            st.markdown('<b><center><i>Determined by comparing JA ERA the last 20 days with what each pitcher did before these last 20 days', unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("<h3><center>🔥 Hottest Pitchers 🔥</center></h3>", unsafe_allow_html=True)

                hot_five_ids = trend_p.sort_values(by='Hot Score',ascending=False).head(5)['pitcher'].unique()

                xcol1,xcol2,xcol3 = st.columns(3)
                picture_width = 105
                with xcol1:
                    st.image(get_player_image(hot_five_ids[0]), width=picture_width)
                with xcol2:
                    st.image(get_player_image(hot_five_ids[1]), width=picture_width)
                with xcol3:
                    st.image(get_player_image(hot_five_ids[2]), width=picture_width)
                
                hot_five_p = trend_p.sort_values(by='Hot Score',ascending=False).head(10)[['player_name','JA ERA','JA ERA L20','Hot Score']]
                styled_hot_five = hot_five_p.style.apply(color_cells_PitMatchups, subset=['JA ERA','JA ERA L20','Hot Score'], axis=1).format({'JA ERA': '{:.2f}', 'JA ERA L20': '{:.2f}', 'Hot Score': '{:.2f}'})
                st.dataframe(styled_hot_five, hide_index=True, width=600)
        
            with col2:
                st.markdown("<h3><center>🧊 Coldest Pitchers 🧊</center></h3>", unsafe_allow_html=True)

                cold_five_ids = trend_p.sort_values(by='Hot Score',ascending=True).head(5)['pitcher'].unique()

                xcol1,xcol2,xcol3 = st.columns(3)
                picture_width = 105
                with xcol1:
                    st.image(get_player_image(cold_five_ids[0]), width=picture_width)
                with xcol2:
                    st.image(get_player_image(cold_five_ids[1]), width=picture_width)
                with xcol3:
                    st.image(get_player_image(cold_five_ids[2]), width=picture_width)
                
                cold_five_p = trend_p.sort_values(by='Hot Score',ascending=True).head(10)[['player_name','JA ERA','JA ERA L20','Hot Score']]
                styled_cold_five = cold_five_p.style.apply(color_cells_PitMatchups, subset=['JA ERA','JA ERA L20','Hot Score'], axis=1).format({'JA ERA': '{:.2f}', 'JA ERA L20': '{:.2f}', 'Hot Score': '{:.2f}'})
                st.dataframe(styled_cold_five, hide_index=True, width=600)

            st.markdown("<h3><center>Full Table</center></h3>", unsafe_allow_html=True)

            todays_pitchers = list(pitcherproj['Pitcher'])
            today_box = st.checkbox('Show Only Today SP?')
            if today_box:                
                ccol1,ccol2,ccol3 = st.columns([1,3,1])
                with ccol2:
                    all_trend_p = trend_p[trend_p['player_name'].isin(todays_pitchers)].sort_values(by='Hot Score',ascending=False)[['player_name','JA ERA','JA ERA L20','Hot Score']]
                    styled_all_trend_p = all_trend_p.style.apply(color_cells_HitMatchups, subset=['JA ERA','JA ERA L20','Hot Score'], axis=1).format({'JA ERA': '{:.2f}', 'JA ERA L20': '{:.2f}', 'Hot Score': '{:.2f}'})
                    st.dataframe(styled_all_trend_p, hide_index=True, width=700,height=810)
            else:
                bcol1,bcol2,bcol3 = st.columns([1,3,1])
                with bcol2:
                    all_trend_p = trend_p.sort_values(by='Hot Score',ascending=False)[['player_name','JA ERA','JA ERA L20','Hot Score']]
                    styled_all_trend_p = all_trend_p.style.apply(color_cells_HitMatchups, subset=['JA ERA','JA ERA L20','Hot Score'], axis=1).format({'JA ERA': '{:.2f}', 'JA ERA L20': '{:.2f}', 'Hot Score': '{:.2f}'})
                    st.dataframe(styled_all_trend_p, hide_index=True, width=700,height=900)

    if tab == "Air Pull Matchups":
        # --- Load only what this page needs ---
        airpulldata = load_airpull()
        hitterproj_raw, pitcherproj_raw, hitterproj2, gameinfo_raw = load_daily_projections()
        hitter_stats_raw, lineup_stats, pitcher_stats, h_vs_avg, p_vs_avg, h_vs_sim, hotzonedata, posdata = load_player_stats()
        bpreport_raw, rpstats = load_bullpen_data()
        (hitterproj, pitcherproj, hitter_stats, gameinfo, bpreport,
         games_df, mainslateteams, main_slate_gamelist,
         confirmed_lus, last_update) = _prepare_projection_data(
            hitterproj_raw, pitcherproj_raw, hitterproj2, gameinfo_raw,
            hitter_stats_raw, h_vs_avg, bpreport_raw)
        st.markdown("<h2><center><br>Air Pull Matchups</h2></center>", unsafe_allow_html=True)

        #st.write(airpulldata)
        hitters_ap = airpulldata[airpulldata['Sample']=='Hitters'][['BatterName','PA_flag','IsBIP','Air Pull / PA', 'Air Pull / BIP']]
        hitters_ap = hitters_ap.rename({'PA_flag':'Hitter PA', 'BatterName':'Hitter', 'IsBIP': 'Hitter BIP', 'Air Pull / PA': 'Hitter Air Pull / PA', 'Air Pull / BIP': 'Hitter Air Pull / BIP'},axis=1)
        
        pitchers_ap = airpulldata[airpulldata['Sample']=='Pitchers'][['player_name','IsBIP', 'PA_flag','Air Pull / PA', 'Air Pull / BIP']]
        pitchers_ap = pitchers_ap.rename({'PA_flag':'Pitcher PA', 'player_name':'Pitcher',  'IsBIP': 'Pitcher BIP','Air Pull / PA': 'Pitcher Air Pull / PA', 'Air Pull / BIP': 'Pitcher Air Pull / BIP'},axis=1)
        
        todays_matchups = hitterproj2[['Hitter','OppSP']]
        todays_matchups.columns=['Hitter','Pitcher']

        merge1 = pd.merge(todays_matchups,hitters_ap, how='left', on='Hitter')
        merge2 = pd.merge(merge1,pitchers_ap, how='left', on='Pitcher')

        col1, col2 = st.columns([1,5])
        with col1:
            option = st.radio('Select Stat Type', options=['Per PA','Per BIP'], horizontal=True)
        
        if option == 'Per PA':
            show_data = merge2[['Hitter','Pitcher','Hitter PA','Pitcher PA','Hitter Air Pull / PA','Pitcher Air Pull / PA']]

            show_data['Average Air Pull'] = (show_data['Hitter Air Pull / PA'] + show_data['Pitcher Air Pull / PA'])/2
            min_pa = 10
            max_h_pa = int(show_data['Hitter PA'].max()) if not show_data['Hitter PA'].empty else min_pa
            max_p_pa = int(show_data['Pitcher PA'].max()) if not show_data['Pitcher PA'].empty else min_pa
            max_pa = max(max_h_pa, max_p_pa)

            col1, col2 = st.columns([1,3])
            with col1:
               pa_filter = st.slider("Filter by Plate Appearances (PA):",min_value=min_pa,max_value=max_pa,value=(min_pa, max_pa), step=1)

            filtered_df = show_data[(show_data['Hitter PA']>pa_filter[0])&(show_data['Pitcher PA']>pa_filter[0])].sort_values(by='Average Air Pull',ascending=False)

            styled_df = filtered_df.style.apply(
                    color_cells_HitStat, subset=['Hitter Air Pull / PA','Pitcher Air Pull / PA','Average Air Pull'], axis=1
                ).format({'Hitter Air Pull / PA': '{:.1%}','Pitcher Air Pull / PA': '{:.1%}','Average Air Pull': '{:.1%}',
                'Hitter PA': '{:.0f}','Pitcher PA': '{:.0f}'})

            st.dataframe(styled_df, hide_index=True, width=850,height=750)
        
        elif option == 'Per BIP':
            show_data = merge2[['Hitter','Pitcher','Hitter BIP','Pitcher BIP','Hitter Air Pull / BIP','Pitcher Air Pull / BIP']]
            show_data['Average Air Pull'] = (show_data['Hitter Air Pull / BIP'] + show_data['Pitcher Air Pull / BIP'])/2

            min_bip = 50
            max_h_bip = int(show_data['Hitter BIP'].max()) if not show_data['Hitter BIP'].empty else min_pa
            max_p_bip = int(show_data['Pitcher BIP'].max()) if not show_data['Pitcher BIP'].empty else min_pa
            max_bip = max(max_h_bip, max_p_bip)

            col1, col2 = st.columns([1,3])
            with col1:
               bip_filter = st.slider("Filter by Balls In Play (BIP):",min_value=min_bip,max_value=max_bip,value=(min_bip, max_bip), step=1)
            
            filtered_df = show_data[(show_data['Hitter BIP']>bip_filter[0])&(show_data['Pitcher BIP']>bip_filter[0])].sort_values(by='Average Air Pull',ascending=False)

            styled_df = filtered_df.style.apply(
                    color_cells_HitStat, subset=['Hitter Air Pull / BIP','Pitcher Air Pull / BIP','Average Air Pull'], axis=1
                ).format({'Hitter Air Pull / BIP': '{:.1%}','Pitcher Air Pull / BIP': '{:.1%}','Average Air Pull': '{:.1%}',
                'Hitter BIP': '{:.0f}','Pitcher BIP': '{:.0f}'})

            st.dataframe(styled_df, hide_index=True,height=750)
    
    if tab == "Weather & Umps":

        require_pro()
        # --- Load only what this page needs ---
        umpire_data, weather_data = load_weather_umps()
        if len(weather_data) < 1:
            st.info("No weather data available.")
        else:
            weather_show = weather_data[['HomeTeam','Game','Conditions','Temp','Winds','Wind Dir','Rain%']].sort_values(by='Rain%',ascending=False)
            weather_show = pd.merge(weather_show,umpire_data, how='left', on='HomeTeam')
            weather_show = weather_show[['Game','Conditions','Temp','Winds','Wind Dir','Rain%','Umpire','K Boost','BB Boost']]
            styled_df = weather_show.style.apply(
                    color_cells_weatherumps, subset=['Rain%','K Boost','BB Boost'], axis=1).format({'K Boost': '{:.2f}','BB Boost': '{:.2f}'}) 
            st.dataframe(styled_df,hide_index=True,width=900,height=700)
    
    if tab == "Streamers":
        # --- Load only what this page needs ---
        hitterproj_raw, pitcherproj_raw, hitterproj2, gameinfo_raw = load_daily_projections()
        hitter_stats_raw, lineup_stats, pitcher_stats, h_vs_avg, p_vs_avg, h_vs_sim, hotzonedata, posdata = load_player_stats()
        bpreport_raw, rpstats = load_bullpen_data()
        props_df, ownershipdf, allbets, alllines, bet_tracker = load_betting_data()
        base_sched, upcoming_proj, upcoming_p_scores, upcoming_start_grades, mlbplayerinfo, ownershipdict = load_schedule_data()
        (hitterproj, pitcherproj, hitter_stats, gameinfo, bpreport,
         games_df, mainslateteams, main_slate_gamelist,
         confirmed_lus, last_update) = _prepare_projection_data(
            hitterproj_raw, pitcherproj_raw, hitterproj2, gameinfo_raw,
            hitter_stats_raw, h_vs_avg, bpreport_raw)
        ownershipdict = dict(zip(ownershipdf.Player, ownershipdf.Yahoo))

        # hitters or pitchers select
        h_or_p = st.selectbox(options=['Pitchers','Hitters'],label='Select Hitters or Pitchers')
        pitcherproj['Ownership'] = pitcherproj['Pitcher'].map(ownershipdict)

        hitterproj['Hitter'] = hitterproj['Hitter'].str.replace('🔥','').str.strip()
        hitterproj['Hitter'] = hitterproj['Hitter'].str.replace('🥶','').str.strip()
        hitterproj['Ownership'] = hitterproj['Hitter'].map(ownershipdict)

        if h_or_p == 'Hitters':
            show_hitters = hitterproj.copy()
            show_hitters['H'] = show_hitters['1B']+show_hitters['2B']+show_hitters['3B']+show_hitters['HR']
            show_hitters = show_hitters[['Hitter','Pos','Team','Opp','OppSP','Park','Ownership','LU','DKPts','PA','H','R','HR','RBI','SB','1B','2B','3B']]
            
            # Add a slider for Ownership percentage
            col1, col2 = st.columns([1,7])
            with col1:
                ownership_filter = st.slider("Filter by Ownership %", min_value=0, max_value=100, value=(0, 100))
            
            with col2:
                # Filter DataFrame based on slider values
                show_hitters = show_hitters[
                    (show_hitters['Ownership'] >= ownership_filter[0]) & 
                    (show_hitters['Ownership'] <= ownership_filter[1])
                ]
                
                show_hitters = show_hitters.sort_values(by='DKPts', ascending=False)
                #st.dataframe(show_pitchers, hide_index=True, width=850, height=600)

                styled_df = show_hitters.style.apply(
                        color_cells_HitProj, subset=['DKPts','HR','SB'], axis=1
                    ).format({
                        'DKPts': '{:.2f}','PA': '{:.2f}', 
                        'R': '{:.2f}', 'Sal': '${:,.0f}', 
                        'PC': '{:.0f}', 'HR': '{:.2f}', 
                        'H': '{:.2f}', 'RBI': '{:.2f}', 
                        'Ownership': '{:.0f}',
                        'SB': '{:.2f}', 'BB': '{:.2f}', 
                        '1B': '{:.2f}', '2B': '{:.2f}', 
                        '3B': '{:.2f}'
                    }).set_table_styles([
                        {'selector': 'th', 'props': [('text-align', 'left'), ('font-weight', 'bold')]},
                        {'selector': 'td', 'props': [('text-align', 'left')]}
                    ])
                st.dataframe(styled_df, hide_index=True, height=600)
        elif h_or_p == 'Pitchers':
            show_pitchers = pitcherproj.copy()
            show_pitchers = show_pitchers[['Pitcher','Team','Opponent','HomeTeam','Ownership','DKPts','PC','IP','H','ER','SO','BB','W']]
            
            # Add a slider for Ownership percentage
            col1, col2 = st.columns([1,6])
            with col1:
                ownership_filter = st.slider("Filter by Ownership %", min_value=0, max_value=100, value=(0, 100))
            
            with col2:
                # Filter DataFrame based on slider values
                show_pitchers = show_pitchers[
                    (show_pitchers['Ownership'] >= ownership_filter[0]) & 
                    (show_pitchers['Ownership'] <= ownership_filter[1])
                ]
                
                show_pitchers = show_pitchers.sort_values(by='DKPts', ascending=False)
                #st.dataframe(show_pitchers, hide_index=True, width=850, height=600)

                styled_df = show_pitchers.style.apply(
                        color_cells_PitchProj, subset=['DKPts','SO','W','Ownership','BB','PC','IP'], axis=1
                    ).format({
                        'DKPts': '{:.2f}','FDPts': '{:.2f}', 
                        'Val': '{:.2f}', 'Sal': '${:,.0f}', 
                        'PC': '{:.0f}', 'IP': '{:.2f}', 
                        'H': '{:.2f}', 'ER': '{:.2f}', 
                        'Ownership': '{:.0f}',
                        'SO': '{:.2f}', 'BB': '{:.2f}', 
                        'W': '{:.2f}', 'Floor': '{:.2f}', 
                        'Ceil': '{:.2f}', 'Own%': '{:.0f}'
                    }).set_table_styles([
                        {'selector': 'th', 'props': [('text-align', 'left'), ('font-weight', 'bold')]},
                        {'selector': 'td', 'props': [('text-align', 'left')]}
                    ])
                st.dataframe(styled_df, hide_index=True, width=950, height=600)
    
    if tab == "Tableau":
        # --- Load only what this page needs ---
        hitterproj_raw, pitcherproj_raw, hitterproj2, gameinfo_raw = load_daily_projections()
        hitter_stats_raw, lineup_stats, pitcher_stats, h_vs_avg, p_vs_avg, h_vs_sim, hotzonedata, posdata = load_player_stats()
        bpreport_raw, rpstats = load_bullpen_data()
        (hitterproj, pitcherproj, hitter_stats, gameinfo, bpreport,
         games_df, mainslateteams, main_slate_gamelist,
         confirmed_lus, last_update) = _prepare_projection_data(
            hitterproj_raw, pitcherproj_raw, hitterproj2, gameinfo_raw,
            hitter_stats_raw, h_vs_avg, bpreport_raw)
        tableau_choice = st.selectbox(options=['Main','MLB & MiLB Stats'],label='Choose dashboard to display')
        if tableau_choice == 'Main':
            #st.markdown("<h2><center>Main MLB Dashboard</center></h2>", unsafe_allow_html=True)
            st.markdown("<i><center><a href='https://public.tableau.com/app/profile/jon.anderson4212/viz/JonPGHMLB2025Dashboard/Hitters'>Click here to visit full thing</i></a></center>", unsafe_allow_html=True)
            tableau_code_pitchers = """
            <div class='tableauPlaceholder' id='viz1745234354780' style='position: relative'><noscript><a href='#'><img alt=' ' src='https:&#47;&#47;public.tableau.com&#47;static&#47;images&#47;Jo&#47;JonPGHMLB2025Dashboard&#47;Pitchers&#47;1_rss.png' style='border: none' /></a></noscript><object class='tableauViz'  style='display:none;'><param name='host_url' value='https%3A%2F%2Fpublic.tableau.com%2F' /> <param name='embed_code_version' value='3' /> <param name='site_root' value='' /><param name='name' value='JonPGHMLB2025Dashboard&#47;Pitchers' /><param name='tabs' value='yes' /><param name='toolbar' value='yes' /><param name='static_image' value='https:&#47;&#47;public.tableau.com&#47;static&#47;images&#47;Jo&#47;JonPGHMLB2025Dashboard&#47;Pitchers&#47;1.png' /> <param name='animate_transition' value='yes' /><param name='display_static_image' value='yes' /><param name='display_spinner' value='yes' /><param name='display_overlay' value='yes' /><param name='display_count' value='yes' /><param name='language' value='en-US' /></object></div>                <script type='text/javascript'>                    var divElement = document.getElementById('viz1745234354780');                    var vizElement = divElement.getElementsByTagName('object')[0];                    if ( divElement.offsetWidth > 800 ) { vizElement.style.width='1400px';vizElement.style.height='1250px';} else if ( divElement.offsetWidth > 500 ) { vizElement.style.width='1400px';vizElement.style.height='1250px';} else { vizElement.style.width='100%';vizElement.style.height='2350px';}                     var scriptElement = document.createElement('script');                    scriptElement.src = 'https://public.tableau.com/javascripts/api/viz_v1.js';                    vizElement.parentNode.insertBefore(scriptElement, vizElement);                </script>    
            """ 
            components.html(tableau_code_pitchers, height=750, scrolling=True)
        elif tableau_choice == 'MLB & MiLB Stats':
            #st.markdown("<h2><center>Main MLB Dashboard</center></h2>", unsafe_allow_html=True)
            st.markdown("<i><center><a href='https://public.tableau.com/app/profile/jon.anderson4212/viz/MLBMiLBStatsDashboardv3/Hitters-Main#1'>Click here to visit full thing</i></a></center>", unsafe_allow_html=True)
            tableau_code_pitchers = """
            <div class='tableauPlaceholder' id='viz1745237361320' style='position: relative'><noscript><a href='#'><img alt=' ' src='https:&#47;&#47;public.tableau.com&#47;static&#47;images&#47;ML&#47;MLBMiLBStatsDashboardv3&#47;Hitters-Main&#47;1_rss.png' style='border: none' /></a></noscript><object class='tableauViz'  style='display:none;'><param name='host_url' value='https%3A%2F%2Fpublic.tableau.com%2F' /> <param name='embed_code_version' value='3' /> <param name='site_root' value='' /><param name='name' value='MLBMiLBStatsDashboardv3&#47;Hitters-Main' /><param name='tabs' value='yes' /><param name='toolbar' value='yes' /><param name='static_image' value='https:&#47;&#47;public.tableau.com&#47;static&#47;images&#47;ML&#47;MLBMiLBStatsDashboardv3&#47;Hitters-Main&#47;1.png' /> <param name='animate_transition' value='yes' /><param name='display_static_image' value='yes' /><param name='display_spinner' value='yes' /><param name='display_overlay' value='yes' /><param name='display_count' value='yes' /><param name='language' value='en-US' /></object></div>                <script type='text/javascript'>                    var divElement = document.getElementById('viz1745237361320');                    var vizElement = divElement.getElementsByTagName('object')[0];                    if ( divElement.offsetWidth > 800 ) { vizElement.style.width='1400px';vizElement.style.height='850px';} else if ( divElement.offsetWidth > 500 ) { vizElement.style.width='1400px';vizElement.style.height='850px';} else { vizElement.style.width='100%';vizElement.style.height='1800px';}                     var scriptElement = document.createElement('script');                    scriptElement.src = 'https://public.tableau.com/javascripts/api/viz_v1.js';                    vizElement.parentNode.insertBefore(scriptElement, vizElement);                </script>
            """ 
            components.html(tableau_code_pitchers, height=750, scrolling=True)

   
    ## move this later
    def create_speed_gauge(value, min_value=0.05, max_value=0.30):
        fig, ax = plt.subplots(figsize=(6, 3), subplot_kw={'projection': 'polar'})

        # Normalize value to angle (0 to 180 degrees for gauge)
        range_value = max_value - min_value
        normalized_value = (value - min_value) / range_value
        angle = normalized_value * 180
        angle_rad = np.deg2rad(180 - angle)  # Convert to radians, adjust for gauge orientation

        # Create background arc
        theta = np.linspace(np.pi, 0, 100)  # 180-degree arc
        ax.fill_between(theta, 0, range_value, color='lightgray', alpha=0.3)

        # Create colored gauge arc based on value
        gauge_theta = np.linspace(np.pi, np.pi - angle_rad, 50)
        ax.fill_between(gauge_theta, 0, range_value, color='limegreen', alpha=0.7)

        # Plot needle
        needle_length = range_value * 0.9
        ax.plot([np.pi - angle_rad, np.pi - angle_rad], [0, needle_length], color='red', lw=3)

        # Customize gauge
        ax.set_ylim(0, range_value * 1.1)  # Extend slightly beyond max for aesthetics
        ax.set_xticks([])  # Hide angular ticks
        ax.set_yticks([])  # Hide radial ticks
        ax.spines['polar'].set_visible(False)  # Hide polar spine
        ax.grid(False)  # Hide grid

        # Add value label at the bottom
        ax.text(np.pi / 2, -range_value * 0.2, f'{value:.2f}', fontsize=20, ha='center', va='center', color='black')

        # Style
        fig.patch.set_facecolor('white')
        ax.set_facecolor('white')

        return fig


    def plot_bet_value_compare(bet_projodds, bet_lineodds, title="Implied Odds Comparison"):
        labels = ['JA Model', 'Betting Line']
        values = [bet_projodds, bet_lineodds]

        # Create horizontal bar chart
        fig = go.Figure(
            data=[
                go.Bar(
                    y=labels,
                    x=values,
                    orientation='h',
                    marker=dict(color=['#e74c3c', '#3498db']),  # Red, Blue, Green
                    text=[f"{v:.2f}" for v in values],  # Display values on bars
                    textposition='auto',
                )
            ]
        )

        # Customize layout
        fig.update_layout(
            title=dict(
                text=title,
                font=dict(size=18, family="Arial", color="#2c3e50"),
                x=0.5,
                xanchor='center'
            ),
            xaxis_title="Value",
            yaxis_title="",
            height=300,
            margin=dict(l=10, r=10, t=50, b=10),
            showlegend=False,
            plot_bgcolor="#ffffff",
            paper_bgcolor="#ffffff",
            font=dict(family="Arial", size=12, color="#2c3e50"),
            yaxis=dict(automargin=True),
            xaxis=dict(gridcolor="#ecf0f1"),
        )

        # Display the chart in Streamlit
        #st.plotly_chart(fig, use_container_width=True)
        return(fig)

    def plot_bet_projections(bet_line, bet_proj, bat_proj, title="Bet and Projection Comparison"):
        # Data for the bar chart
        labels = ['Bet Line', 'JA Model Projection', 'The Bat X Projection']
        values = [bet_line, bet_proj, bat_proj]

        # Create horizontal bar chart
        fig = go.Figure(
            data=[
                go.Bar(
                    y=labels,
                    x=values,
                    orientation='h',
                    marker=dict(color=['#e74c3c', '#3498db', '#2ecc71']),  # Red, Blue, Green
                    text=[f"{v:.2f}" for v in values],  # Display values on bars
                    textposition='auto',
                )
            ]
        )

        # Customize layout
        fig.update_layout(
            title=dict(
                text=title,
                font=dict(size=18, family="Arial", color="#2c3e50"),
                x=0.5,
                xanchor='center'
            ),
            xaxis_title="Value",
            yaxis_title="",
            height=300,
            margin=dict(l=10, r=10, t=50, b=10),
            showlegend=False,
            plot_bgcolor="#ffffff",
            paper_bgcolor="#ffffff",
            font=dict(family="Arial", size=12, color="#2c3e50"),
            yaxis=dict(automargin=True),
            xaxis=dict(gridcolor="#ecf0f1"),
        )

        # Display the chart in Streamlit
        #st.plotly_chart(fig, use_container_width=True)
        return(fig)
    
    def plotWalks(df,line):
        playername = df['Player'].iloc[0]
        df["Date"] = pd.to_datetime(df["Date"])

        # Create a line graph using Plotly
        fig = px.line(
            df,
            x="Date",
            y="BB",
            title=f"Walks by Start for {playername}",
            markers=True,  # Add markers for each data point
            text="BB",  # Show opponent labels on the points
        )
        
            # Add horizontal line using the 'line' variable
        fig.add_hline(
            y=line,
            line_dash="solid",
            line_color="red",
            line_width=2,
            annotation_text=f"{line}",
            annotation_position="top right"
            )
        
        # Customize the layout for a nicer look
        fig.update_traces(
            line=dict(color="#1f77b4", width=2.5),  # Blue line with a decent thickness
            marker=dict(size=10),  # Larger markers
            textposition="top center",  # Position opponent labels above the points
        )

        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Walks",
            xaxis=dict(
                tickformat="%b %d",  # Format dates as "Mar 31", "Apr 06", etc.
                tickangle=45,  # Rotate x-axis labels for better readability
            ),
            yaxis=dict(
                range=[-0.5, 5],  # Set y-axis range with a little padding
                dtick=1,  # Step of 1 for y-axis ticks
            ),
            title=dict(
                x=0.5,  # Center the title
                font=dict(size=20),
            ),
            showlegend=False,  # No legend needed for a single line
            plot_bgcolor="white",  # White background for the plot
            paper_bgcolor="white",  # White background for the entire figure
            font=dict(size=12),
        )

        return(fig)
    
    def plotStrikeouts(df,line):
        playername = df['Player'].iloc[0]
        df["Date"] = pd.to_datetime(df["Date"])

        df_max = np.max(df['SO']) + 2

        # Create a line graph using Plotly
        fig = px.line(
            df,
            x="Date",
            y="SO",
            title=f"Strikeouts by Start for {playername}",
            markers=True,  # Add markers for each data point
            text="SO",  # Show opponent labels on the points
        )
        
            # Add horizontal line using the 'line' variable
        fig.add_hline(
            y=line,
            line_dash="solid",
            line_color="red",
            line_width=2,
            annotation_text=f"{line}",
            annotation_position="top right"
            )
        
        # Customize the layout for a nicer look
        fig.update_traces(
            line=dict(color="#1f77b4", width=2.5),  # Blue line with a decent thickness
            marker=dict(size=10),  # Larger markers
            textposition="top center",  # Position opponent labels above the points
        )

        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Strikeouts",
            xaxis=dict(
                tickformat="%b %d",  # Format dates as "Mar 31", "Apr 06", etc.
                tickangle=45,  # Rotate x-axis labels for better readability
            ),
            yaxis=dict(
                range=[-0.5, df_max],  # Set y-axis range with a little padding
                dtick=1,  # Step of 1 for y-axis ticks
            ),
            title=dict(
                x=0.5,  # Center the title
                font=dict(size=20),
            ),
            showlegend=False,  # No legend needed for a single line
            plot_bgcolor="white",  # White background for the plot
            paper_bgcolor="white",  # White background for the entire figure
            font=dict(size=12),
        )

        return(fig)

    
    
    if tab == "Prop Bets":
        require_pro()
        import math
        import re
        import unicodedata
        import numpy as np
        import pandas as pd
        import streamlit as st

        st.header("Prop Bets")
        # =========================================================
        # HELPERS
        # =========================================================
        TEAM_FIXES = {
            "SFG": "SF",
            "WSH": "WSN",
            "KCR": "KC",
            "SDP": "SD",
            "TBR": "TB",
            "CHW": "CWS",
        }

        def clean_name(x):
            if pd.isna(x):
                return ""
            x = str(x).strip()
            x = unicodedata.normalize("NFKD", x).encode("ascii", "ignore").decode("utf-8")
            x = x.replace(".", "").replace("'", "").replace("-", " ")
            x = re.sub(r"\s+", " ", x)
            return x.lower().strip()

        def norm_team(x):
            if pd.isna(x):
                return x
            x = str(x).strip()
            return TEAM_FIXES.get(x, x)

        def american_to_implied_prob(price):
            price = float(price)
            if price < 0:
                return (-price) / ((-price) + 100.0)
            return 100.0 / (price + 100.0)

        def implied_prob_to_american(p):
            p = min(max(float(p), 1e-6), 1 - 1e-6)
            if p >= 0.5:
                return int(round(-(100 * p / (1 - p))))
            return int(round((100 * (1 - p) / p)))

        def american_to_decimal(price):
            price = float(price)
            if price > 0:
                return 1 + (price / 100.0)
            return 1 + (100.0 / abs(price))

        def expected_value_per_1u(win_prob, price):
            dec = american_to_decimal(price)
            profit_if_win = dec - 1.0
            return win_prob * profit_if_win - (1 - win_prob)

        def poisson_pmf(k, lam):
            if lam < 0:
                return 0.0
            return math.exp(-lam) * (lam ** k) / math.factorial(k)

        def poisson_cdf(k, lam):
            if k < 0:
                return 0.0
            return sum(poisson_pmf(i, lam) for i in range(int(math.floor(k)) + 1))

        def poisson_prob_over(line, lam):
            threshold = math.floor(line) + 1
            return 1 - poisson_cdf(threshold - 1, lam)

        def poisson_prob_under(line, lam):
            threshold = math.floor(line)
            return poisson_cdf(threshold, lam)

        def normal_cdf(x, mu, sigma):
            if sigma <= 0:
                return 1.0 if x >= mu else 0.0
            z = (x - mu) / (sigma * math.sqrt(2))
            return 0.5 * (1 + math.erf(z))

        def normal_prob_over(line, mu, sigma):
            return 1 - normal_cdf(line, mu, sigma)

        def normal_prob_under(line, mu, sigma):
            return normal_cdf(line, mu, sigma)

        def value_score(ev, edge):
            # looser than before on purpose so consensus can surface more plays
            raw = 50 + (ev * 100 * 0.9) + (edge * 100 * 1.15)
            return max(0.0, min(100.0, raw))

        # =========================================================
        # COPY INPUT DFS SO WE DON'T MUTATE YOUR ORIGINALS
        # =========================================================
        Tableau_DailyHitterProj, Tableau_DailyPitcherProj, bat_hitters, bat_pitchers, AllBooksLines = load_prop_bet_data()
        
        
        mlbdw_h = Tableau_DailyHitterProj.copy()
        mlbdw_p = Tableau_DailyPitcherProj.copy()
        bat_h = bat_hitters.copy()
        bat_p = bat_pitchers.copy()
        lines = AllBooksLines.copy()

        ## code to exclude long shots or over favorites
        lines['Price'] = pd.to_numeric(lines['Price'], errors='coerce')

        lines = lines[
            (
                lines['Price'].between(-300, 300)
            )
            |
            (
                lines['Type'].isin(['pitcher_strikeouts', 'batter_home_runs'])
            )
        ].copy()

        # clean junk cols
        for df in [mlbdw_h, mlbdw_p, bat_h, bat_p, lines]:
            drop_cols = [c for c in df.columns if str(c).lower().startswith("unnamed")]
            if len(drop_cols) > 0:
                df.drop(columns=drop_cols, inplace=True, errors="ignore")

        # bat pitchers sample had a junk/footer row
        if "PLAYER" in bat_p.columns:
            bat_p = bat_p[bat_p["PLAYER"].astype(str).str.contains(r"[A-Za-z]", regex=True)].copy()

        # =========================================================
        # NORMALIZE PROJECTIONS
        # =========================================================
        # MLB DW hitters
        mlbdw_h["player_name"] = mlbdw_h["Hitter"]
        mlbdw_h["player_key"] = mlbdw_h["player_name"].map(clean_name)
        mlbdw_h["team_norm"] = mlbdw_h["Team"].map(norm_team)
        mlbdw_h["opp_norm"] = mlbdw_h["Opp"].map(norm_team)
        mlbdw_h["source"] = "MLB DW"

        # MLB DW pitchers
        mlbdw_p["player_name"] = mlbdw_p["Pitcher"]
        mlbdw_p["player_key"] = mlbdw_p["player_name"].map(clean_name)
        mlbdw_p["team_norm"] = mlbdw_p["Team"].map(norm_team)
        mlbdw_p["opp_norm"] = mlbdw_p["Opponent"].map(norm_team)
        mlbdw_p["source"] = "MLB DW"

        # BAT hitters
        bat_h["player_name"] = bat_h["NAME"]
        bat_h["player_key"] = bat_h["player_name"].map(clean_name)
        bat_h["team_norm"] = bat_h["TEAM"].map(norm_team)
        bat_h["opp_norm"] = bat_h["OPP_TM"].map(norm_team)
        bat_h["source"] = "THE BAT X"

        # BAT pitchers
        bat_p["player_name"] = bat_p["PLAYER"]
        bat_p["player_key"] = bat_p["player_name"].map(clean_name)
        bat_p["team_norm"] = bat_p["TEAM"].map(norm_team)
        bat_p["opp_norm"] = bat_p["OPP"].map(norm_team)
        
        bat_p["source"] = "THE BAT X"

        # derived hitter fields
        if {"1B", "2B", "3B", "HR"}.issubset(mlbdw_h.columns):
            mlbdw_h["H"] = mlbdw_h["1B"].fillna(0) + mlbdw_h["2B"].fillna(0) + mlbdw_h["3B"].fillna(0) + mlbdw_h["HR"].fillna(0)
            mlbdw_h["TB"] = (
                mlbdw_h["1B"].fillna(0)
                + 2 * mlbdw_h["2B"].fillna(0)
                + 3 * mlbdw_h["3B"].fillna(0)
                + 4 * mlbdw_h["HR"].fillna(0)
            )

        if "K" in bat_h.columns and "SO" not in bat_h.columns:
            bat_h["SO"] = bat_h["K"]

        # standard hitter schema
        hitter_cols = [
            "player_name", "player_key", "team_norm", "opp_norm", "source",
            "PA", "R", "HR", "RBI", "SB", "SO", "BB", "HBP", "1B", "2B", "3B", "H", "TB"
        ]
        for col in hitter_cols:
            if col not in mlbdw_h.columns:
                mlbdw_h[col] = np.nan
            if col not in bat_h.columns:
                bat_h[col] = np.nan

        hitters_all = pd.concat(
            [mlbdw_h[hitter_cols], bat_h[hitter_cols]],
            ignore_index=True
        )

        # standard pitcher schema
        pitcher_cols = [
            "player_name", "player_key", "team_norm", "opp_norm", "source",
            "IP", "SO", "BB", "H", "HR", "ER", "W"
        ]
        for col in pitcher_cols:
            if col not in mlbdw_p.columns:
                mlbdw_p[col] = np.nan
            if col not in bat_p.columns:
                bat_p[col] = np.nan

        pitchers_all = pd.concat(
            [mlbdw_p[pitcher_cols], bat_p[pitcher_cols]],
            ignore_index=True
        )

        # =========================================================
        # CLEAN LINES
        # =========================================================
        lines["player_key"] = lines["Player"].map(clean_name)
        lines["Book"] = lines["Book"].astype(str).str.strip()
        lines["Type"] = lines["Type"].astype(str).str.strip()
        lines["OU"] = lines["OU"].astype(str).str.strip().str.title()
        lines["StartTime"] = pd.to_datetime(lines["StartTime"], errors="coerce")

        # =========================================================
        # PROP MAP
        # =========================================================
        HITTER_BET_MAP = {
            "batter_home_runs": {"stat": "HR", "dist": "poisson"},
            "batter_hits": {"stat": "H", "dist": "poisson"},
            "batter_runs_scored": {"stat": "R", "dist": "poisson"},
            "batter_walks": {"stat": "BB", "dist": "poisson"},
            "batter_strikeouts": {"stat": "SO", "dist": "poisson"},
            "batter_stolen_bases": {"stat": "SB", "dist": "poisson"},
            "batter_doubles": {"stat": "2B", "dist": "poisson"},
            "batter_singles": {"stat": "1B", "dist": "poisson"},
            "batter_hits_runs_rbis": {"stat": "H+R+RBI", "dist": "combo"},
        }

        PITCHER_BET_MAP = {
            "pitcher_strikeouts": {"stat": "SO", "dist": "poisson"},
            "pitcher_walks": {"stat": "BB", "dist": "poisson"},
            "pitcher_hits_allowed": {"stat": "H", "dist": "poisson"},
            "pitcher_outs": {"stat": "OUTS", "dist": "normal"},
        }

        SUPPORTED_TYPES = set(HITTER_BET_MAP.keys()) | set(PITCHER_BET_MAP.keys())

        hitter_lookup = {
            (r["player_key"], r["source"]): r
            for _, r in hitters_all.drop_duplicates(["player_key", "source"]).iterrows()
        }
        pitcher_lookup = {
            (r["player_key"], r["source"]): r
            for _, r in pitchers_all.drop_duplicates(["player_key", "source"]).iterrows()
        }

        def get_proj_mean(line_row, source_name):
            bet_type = line_row["Type"]
            player_key = line_row["player_key"]

            if bet_type in HITTER_BET_MAP:
                proj = hitter_lookup.get((player_key, source_name))
                if proj is None:
                    return None, None, None

                stat = HITTER_BET_MAP[bet_type]["stat"]
                dist = HITTER_BET_MAP[bet_type]["dist"]

                if stat == "H+R+RBI":
                    vals = [proj.get("H", np.nan), proj.get("R", np.nan), proj.get("RBI", np.nan)]
                    if any(pd.isna(v) for v in vals):
                        return None, None, None
                    mean = float(vals[0]) + float(vals[1]) + float(vals[2])
                else:
                    mean = proj.get(stat, np.nan)
                    if pd.isna(mean):
                        return None, None, None
                    mean = float(mean)

                return mean, dist, "hitter"

            if bet_type in PITCHER_BET_MAP:
                proj = pitcher_lookup.get((player_key, source_name))
                if proj is None:
                    return None, None, None

                stat = PITCHER_BET_MAP[bet_type]["stat"]
                dist = PITCHER_BET_MAP[bet_type]["dist"]

                if stat == "OUTS":
                    ip = proj.get("IP", np.nan)
                    if pd.isna(ip):
                        return None, None, None
                    mean = float(ip) * 3
                else:
                    mean = proj.get(stat, np.nan)
                    if pd.isna(mean):
                        return None, None, None
                    mean = float(mean)

                return mean, dist, "pitcher"

            return None, None, None

        def model_prob(line, ou, mean, dist, market_type):
            if dist == "poisson":
                return poisson_prob_over(line, mean) if ou == "Over" else poisson_prob_under(line, mean)

            if dist == "combo":
                # variance inflated for combo props
                sigma = max(math.sqrt(max(mean, 0.01)) * 1.25, 0.9)
                return normal_prob_over(line, mean, sigma) if ou == "Over" else normal_prob_under(line, mean, sigma)

            if dist == "normal":
                sigma = 3.5 if market_type == "pitcher" else 1.25
                return normal_prob_over(line, mean, sigma) if ou == "Over" else normal_prob_under(line, mean, sigma)

            return np.nan

        # =========================================================
        # GRADE ALL BETS
        # =========================================================
        supported_lines = lines[lines["Type"].isin(SUPPORTED_TYPES)].copy()

        graded_rows = []
        for _, row in supported_lines.iterrows():
            for source_name in ["MLB DW", "THE BAT X"]:
                proj_mean, dist, market_type = get_proj_mean(row, source_name)
                if proj_mean is None:
                    continue

                win_prob = model_prob(row["Line"], row["OU"], proj_mean, dist, market_type)
                market_prob = american_to_implied_prob(row["Price"])
                edge = win_prob - market_prob
                ev = expected_value_per_1u(win_prob, row["Price"])
                fair_price = implied_prob_to_american(win_prob)
                score = value_score(ev, edge)

                out = row.to_dict()
                out["ProjectionSource"] = source_name
                out["ProjMean"] = proj_mean
                out["ModelProb"] = win_prob
                out["MarketProb"] = market_prob
                out["Edge"] = edge
                out["EV_1u"] = ev
                out["FairPrice"] = fair_price
                out["ValueScore"] = score
                graded_rows.append(out)

        graded = pd.DataFrame(graded_rows)




        if graded.empty:
            st.warning("No supported prop bets could be graded from the current files.")
        else:
            # =====================================================
            # BEST-LINE / BEST-PRICE SUMMARIES
            # =====================================================
            # best price by side across all books
            best_price = (
                graded.sort_values("Price", ascending=False)
                .drop_duplicates(["Player", "Type", "OU", "Line", "ProjectionSource"])
                .copy()
            )
            best_price["BestAcrossBooks"] = "Y"

            # loose consensus = both systems are at least mildly positive
            consensus = (
                graded.pivot_table(
                    index=["Player", "Type", "OU", "Line", "Game"],
                    columns="ProjectionSource",
                    values=["ValueScore", "EV_1u", "Edge", "ProjMean", "ModelProb"],
                    aggfunc="max"   # use best score/price found among all books
                )
                .reset_index()
            )
            consensus.columns = [
                "_".join([str(x) for x in col if str(x) != ""]).strip("_")
                if isinstance(col, tuple) else col
                for col in consensus.columns
            ]

            # looser than "both positive EV"
            if ("ValueScore_MLB DW" in consensus.columns) and ("ValueScore_THE BAT X" in consensus.columns):
                consensus["ConsensusScore"] = (
                    consensus["ValueScore_MLB DW"].fillna(0) +
                    consensus["ValueScore_THE BAT X"].fillna(0)
                ) / 2

                consensus["BothLikeIt"] = (
                    ((consensus["ValueScore_MLB DW"].fillna(0) >= 52) & (consensus["ValueScore_THE BAT X"].fillna(0) >= 52))
                    |
                    ((consensus["Edge_MLB DW"].fillna(0) >= 0.01) & (consensus["Edge_THE BAT X"].fillna(0) >= 0.01))
                )

            # best shopping edge: compare books for same exact bet
            line_shop = (
                graded.groupby(["Player", "Type", "OU", "Line", "ProjectionSource"], as_index=False)
                .agg(
                    BestPrice=("Price", "max"),
                    WorstPrice=("Price", "min"),
                    BestBook=("Book", lambda s: s.iloc[s.index.get_loc(s.idxmax())] if len(s) > 0 else None),
                    NumBooks=("Book", "nunique"),
                    BestValueScore=("ValueScore", "max"),
                    BestEV=("EV_1u", "max"),
                )
            )
            line_shop["PriceGap"] = line_shop["BestPrice"] - line_shop["WorstPrice"]

            # arbitrage
            over_best = (
                lines[lines["OU"] == "Over"]
                .sort_values("Price", ascending=False)
                .drop_duplicates(["Player", "Type", "Line", "Game"])
                .rename(columns={"Book": "OverBook", "Price": "OverPrice"})
            )
            under_best = (
                lines[lines["OU"] == "Under"]
                .sort_values("Price", ascending=False)
                .drop_duplicates(["Player", "Type", "Line", "Game"])
                .rename(columns={"Book": "UnderBook", "Price": "UnderPrice"})
            )
            arb = pd.merge(
                over_best[["Player", "Type", "Line", "Game", "OverBook", "OverPrice"]],
                under_best[["Player", "Type", "Line", "Game", "UnderBook", "UnderPrice"]],
                on=["Player", "Type", "Line", "Game"],
                how="inner"
            )
            if len(arb) > 0:
                arb["OverDec"] = arb["OverPrice"].map(american_to_decimal)
                arb["UnderDec"] = arb["UnderPrice"].map(american_to_decimal)
                arb["ArbIndex"] = 1 / arb["OverDec"] + 1 / arb["UnderDec"]
                arb["ArbPct"] = np.where(arb["ArbIndex"] < 1, (1 - arb["ArbIndex"]) * 100, 0)
                arb["Arbitrage"] = arb["ArbIndex"] < 1
                arb = arb.sort_values(["Arbitrage", "ArbPct"], ascending=[False, False]).reset_index(drop=True)

            # =====================================================
            # TOP CONTROLS - NO SIDEBAR
            # =====================================================
            c1, c2, c3, c4, c5 = st.columns([1.2, 1.2, 1.2, 1.0, 1.0])

            view_mode = c1.selectbox(
                "View",
                ["Top Bets", "Consensus", "Player Search", "Price Shopping", "Arbitrage"]
            )

            proj_choice = c2.selectbox(
                "Projection System",
                ["MLB DW", "THE BAT X", "Both Systems"],
                index=2
            )

            bet_type_list = sorted(graded["Type"].dropna().unique())
            bet_types = c3.multiselect(
                "Bet Types",
                bet_type_list,
                default=bet_type_list
            )

            game_list = sorted([g for g in graded["Game"].dropna().unique()])
            game_options = ["All Games"] + game_list
            selected_game = c1.selectbox("Game", game_options)

            min_score = c4.slider("Min Score", 0, 100, 55)
            min_edge = c5.slider("Min Edge %", 0.0, 25.0, 1.0, 0.5) / 100.0

            # =====================================================
            # TOP BETS
            # =====================================================
            if view_mode == "Top Bets":
                top_bets = graded[graded["Type"].isin(bet_types)].copy()
                top_bets = top_bets[top_bets["ValueScore"] >= min_score].copy()
                top_bets = top_bets[top_bets["Edge"] >= min_edge].copy()

                if selected_game != "All Games":
                    top_bets = top_bets[top_bets["Game"] == selected_game].copy()

                if proj_choice != "Both Systems":
                    top_bets = top_bets[top_bets["ProjectionSource"] == proj_choice].copy()

                top_bets = top_bets.sort_values(
                    ["ValueScore", "EV_1u", "Edge", "Price"],
                    ascending=[False, False, False, False]
                )

                st.subheader("Top Bets")
                st.dataframe(
                    top_bets[["Player", "Book", "Type", "OU", "Line", "Price",
                            "ProjectionSource", "ProjMean", "ModelProb", "MarketProb",
                            "Edge", "EV_1u", "FairPrice", "ValueScore", "Game"]],
                    use_container_width=True,
                    height=700, hide_index=True
                )
                export_button(top_bets[[
                            "Player", "Book", "Type", "OU", "Line", "Price",
                            "ProjectionSource", "ProjMean", "ModelProb", "MarketProb",
                            "Edge", "EV_1u", "FairPrice", "ValueScore", "Game"
                        ]], f"top_bets.csv")

            # =====================================================
            # CONSENSUS
            # =====================================================
            elif view_mode == "Consensus":
                st.subheader("Consensus Bets")

                c1, c2 = st.columns(2)
                only_both_like = c1.checkbox("Only show bets both systems like", value=True)
                min_consensus = c2.slider("Min Consensus Score", 0, 100, 55)

                cdf = consensus.copy()
                cdf = cdf[cdf["Type"].isin(bet_types)].copy()

                if "ConsensusScore" in cdf.columns:
                    cdf = cdf[cdf["ConsensusScore"] >= min_consensus].copy()

                if only_both_like and "BothLikeIt" in cdf.columns:
                    cdf = cdf[cdf["BothLikeIt"] == True].copy()

                cdf = cdf.sort_values(["ConsensusScore"], ascending=False)

                if selected_game != "All Games":
                    cdf = cdf[cdf["Game"] == selected_game].copy()

                st.dataframe(cdf, use_container_width=True, height=700, hide_index=True)

            # =====================================================
            # PLAYER SEARCH
            # =====================================================
            elif view_mode == "Player Search":
                player_list = sorted(graded["Player"].dropna().unique())
                selected_player = st.selectbox("Player", player_list)

                p1, p2 = st.columns(2)

                player_bets = graded[(graded["Player"] == selected_player) & (graded["Type"].isin(bet_types))].copy()
                if proj_choice != "Both Systems":
                    player_bets = player_bets[player_bets["ProjectionSource"] == proj_choice].copy()

                player_bets = player_bets.sort_values(
                    ["ValueScore", "EV_1u", "Price"],
                    ascending=[False, False, False]
                )

                p1.markdown("### All Bets")
                p1.dataframe(
                    player_bets[
                        [
                            "Player", "Book", "Type", "OU", "Line", "Price",
                            "ProjectionSource", "ProjMean", "ModelProb", "MarketProb",
                            "Edge", "EV_1u", "FairPrice", "ValueScore"
                        ]
                    ],
                    use_container_width=True,
                    height=650, hide_index=True
                )

                p2.markdown("### Consensus / Best-Line View")
                player_consensus = consensus[consensus["Player"] == selected_player].copy()
                player_consensus = player_consensus[player_consensus["Type"].isin(bet_types)].copy()
                if len(player_consensus) > 0 and "ConsensusScore" in player_consensus.columns:
                    player_consensus = player_consensus.sort_values("ConsensusScore", ascending=False)
                    p2.dataframe(player_consensus, use_container_width=True, height=650, hide_index=True)
                else:
                    p2.info("No consensus rows for this player.")

            # =====================================================
            # PRICE SHOPPING
            # =====================================================
            elif view_mode == "Price Shopping":
                st.subheader("Best Prices Across Books")

                c1, c2 = st.columns(2)
                min_gap = c1.slider("Minimum Price Gap", 0, 100, 10)
                min_books = c2.slider("Minimum Books", 1, int(max(1, line_shop["NumBooks"].max())), 2)

                sdf = line_shop[line_shop["Type"].isin(bet_types)].copy()
                sdf = sdf[(sdf["PriceGap"] >= min_gap) & (sdf["NumBooks"] >= min_books)].copy()

                if proj_choice != "Both Systems":
                    sdf = sdf[sdf["ProjectionSource"] == proj_choice].copy()

                sdf = sdf.sort_values(["PriceGap", "BestValueScore", "BestEV"], ascending=[False, False, False])
                #if selected_game != "All Games":
                    #sdf = sdf[sdf["Game"] == selected_game].copy()
                st.dataframe(
                    sdf[
                        [
                            "Player", "Type", "OU", "Line", "ProjectionSource",
                            "BestBook", "BestPrice", "WorstPrice", "PriceGap",
                            "NumBooks", "BestValueScore", "BestEV"
                        ]
                    ],
                    use_container_width=True,
                    height=700, hide_index=True)

            # =====================================================
            # ARBITRAGE
            # =====================================================
            elif view_mode == "Arbitrage":
                st.subheader("Arbitrage Hunting")

                if len(arb) == 0:
                    st.info("No over/under pairs found for arbitrage check.")
                else:
                    min_arb = st.slider("Minimum Arb %", 0.0, 10.0, 0.0, 0.1)
                    adf = arb[(arb["Arbitrage"] == True) & (arb["ArbPct"] >= min_arb)].copy()
                    adf = adf[adf["Type"].isin(bet_types)].copy()

                    st.dataframe(
                        adf[
                            [
                                "Player", "Game", "Type", "Line",
                                "OverBook", "OverPrice",
                                "UnderBook", "UnderPrice",
                                "ArbIndex", "ArbPct"
                            ]
                        ],
                        use_container_width=True,
                        height=700, hide_index=True)

            st.markdown("---")
            st.markdown(
                """
                **Notes**
                - All books are evaluated together.
                - Consensus is intentionally looser: a bet can qualify when both systems show at least mild support.
                - Count props are modeled with projection means using Poisson-style assumptions.
                - Combo props use a variance-inflated approximation.
                - Pitcher outs use a normal approximation around projected outs.
                """
            )


    def sp_grade_color_score(val):
        try:
            score = float(val)
            if score > 100:
                intensity = min((score - 100) / 40, 1)  # Normalize to 0-1 scale, cap at 50 points above 100
                color = f'rgba(144, 238, 144, {0.3 + 0.7 * intensity})'  # Light green with varying opacity
            elif score < 90:
                intensity = min((100 - score) / 50, 1)  # Normalize to 0-1 scale, cap at 50 points below 100
                color = f'rgba(255, 182, 193, {0.3 + 0.7 * intensity})'  # Light pink/red with varying opacity
            else:
                color = 'rgba(245, 245, 245, 1)'  # Neutral light gray for 100
            
            return f'background-color: {color}; color: black;'
        except:
            return ''  # Return empty string for non-numeric values

    if tab == "Upcoming Projections":
        import streamlit as st
        import pandas as pd
        import numpy as np

        st.markdown("## Upcoming Projections")
        st.caption("View projected hitter and pitcher lines for the next 10 days, with ownership and next scoring period filters.")

        base_sched, upcoming_proj, ownershipdict = load_next_ten_proj()

        # -----------------------------
        # Basic cleanup
        # -----------------------------
        df = upcoming_proj.copy()

        if 'Unnamed: 0' in df.columns:
            df = df.drop(columns=['Unnamed: 0'])

        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

        if 'Ownership' in df.columns:
            df['Ownership'] = pd.to_numeric(df['Ownership'], errors='coerce')

        if 'Next FWeek' in df.columns:
            df['Next FWeek'] = pd.to_numeric(df['Next FWeek'], errors='coerce').fillna(0).astype(int)

        df['Category'] = df['Category'].astype(str).str.strip()
        df['Pos'] = df['Pos'].astype(str).str.strip()

        # Fill ownership from dict if needed
        if 'Ownership' in df.columns and isinstance(ownershipdict, dict):
            missing_own = df['Ownership'].isna()
            if missing_own.any():
                df.loc[missing_own, 'Ownership'] = df.loc[missing_own, 'Player'].map(ownershipdict)

        df['Ownership'] = pd.to_numeric(df['Ownership'], errors='coerce').fillna(0)

        upcoming_hitter_proj = df[df['Category'] == 'Hitters'].copy()
        upcoming_pitcher_proj = df[df['Category'] == 'Pitchers'].copy()

        # -----------------------------
        # Top controls
        # -----------------------------
        c1, c2, c3, c4 = st.columns([1.1, 1.0, 1.2, 1.7])

        with c1:
            only_next_week = st.toggle(
                "Only Next Fantasy Week",
                value=False,
                help="Show only games in the next Monday-Sunday fantasy scoring period."
            )

        with c2:
            player_view = st.radio("Show", ["Hitters", "Pitchers"], horizontal=True)

        with c3:
            own_mode = st.selectbox(
                "Ownership Filter",
                [
                    "All Players",
                    "Available Players Only (< 50%)",
                    "Widely Available (< 25%)",
                    "Deep League Targets (< 10%)",
                    "Highly Owned (>= 50%)"
                ]
            )

        with c4:
            player_search = st.text_input("Player Search", placeholder="Search player name...")

        c5, c6, c7 = st.columns([1, 1, 1])

        with c5:
            team_options = ["All Teams"] + sorted(df['Team'].dropna().astype(str).unique().tolist())
            selected_team = st.selectbox("Team", team_options)

        with c6:
            pos_options = ["All Positions"] + sorted(df['Pos'].dropna().astype(str).unique().tolist())
            selected_pos = st.selectbox("Pos", pos_options)

        with c7:
            game_sort_desc = st.toggle("Game Table Sort Descending", value=True)

        # -----------------------------
        # Common filters
        # -----------------------------
        def apply_common_filters(data):
            out = data.copy()

            if only_next_week:
                out = out[out['Next FWeek'] == 1]

            if selected_team != "All Teams":
                out = out[out['Team'] == selected_team]

            if selected_pos != "All Positions":
                out = out[out['Pos'].astype(str).str.contains(selected_pos, case=False, na=False)]

            if player_search.strip():
                out = out[out['Player'].astype(str).str.contains(player_search.strip(), case=False, na=False)]

            if own_mode == "Available Players Only (< 50%)":
                out = out[out['Ownership'] < 50]
            elif own_mode == "Widely Available (< 25%)":
                out = out[out['Ownership'] < 25]
            elif own_mode == "Deep League Targets (< 10%)":
                out = out[out['Ownership'] < 10]
            elif own_mode == "Highly Owned (>= 50%)":
                out = out[out['Ownership'] >= 50]

            return out

        hitter_view = apply_common_filters(upcoming_hitter_proj)
        pitcher_view = apply_common_filters(upcoming_pitcher_proj)

        # -----------------------------
        # Date range helper
        # -----------------------------
        def get_date_range_text(data):
            if data.empty or 'Date' not in data.columns:
                return "No dates available"

            valid_dates = pd.to_datetime(data['Date'], errors='coerce').dropna()
            if valid_dates.empty:
                return "No dates available"

            min_date = valid_dates.min()
            max_date = valid_dates.max()

            return f"{min_date.strftime('%b %d, %Y')} to {max_date.strftime('%b %d, %Y')}"

        hitter_date_range = get_date_range_text(hitter_view)
        pitcher_date_range = get_date_range_text(pitcher_view)

        # -----------------------------
        # Summary helpers
        # -----------------------------
        def build_hitter_summary(data):
            if data.empty:
                return pd.DataFrame()

            group_cols = [c for c in ['Player', 'Team', 'Pos', 'Ownership'] if c in data.columns]

            sum_cols = [
                'FPts', 'PA', 'R', 'HR', 'RBI', 'SB',
                'SO', 'BB', 'HBP', '1B', '2B', '3B'
            ]
            sum_cols = [c for c in sum_cols if c in data.columns]

            summary = (
                data.groupby(group_cols, dropna=False)[sum_cols]
                .sum()
                .reset_index()
            )

            if 'Date' in data.columns:
                games_ct = data.groupby(group_cols, dropna=False)['Date'].count().reset_index(name='Games')
                summary = summary.merge(games_ct, on=group_cols, how='left')

            if 'FPts' in summary.columns:
                summary = summary.sort_values(['FPts', 'Ownership', 'Player'], ascending=[False, True, True])

            ordered_cols = [c for c in [
                'Player', 'Ownership', 'Team', 'Pos', 'Games', 'FPts', 'PA', 'R',
                'HR', 'RBI', 'SB', 'SO', 'BB', 'HBP', '1B', '2B', '3B'
            ] if c in summary.columns]

            return summary[ordered_cols]

        def build_pitcher_summary(data):
            if data.empty:
                return pd.DataFrame()

            group_cols = [c for c in ['Player', 'Team', 'Pos', 'Ownership'] if c in data.columns]

            sum_cols = [
                'FPts', 'PC', 'IP', 'W', 'SO', 'BB',
                'HBP', 'H', 'ER'
            ]
            sum_cols = [c for c in sum_cols if c in data.columns]

            summary = (
                data.groupby(group_cols, dropna=False)[sum_cols]
                .sum()
                .reset_index()
            )

            if 'Date' in data.columns:
                games_ct = data.groupby(group_cols, dropna=False)['Date'].count().reset_index(name='Games')
                summary = summary.merge(games_ct, on=group_cols, how='left')

            if 'FPts' in summary.columns:
                summary = summary.sort_values(['FPts', 'Ownership', 'Player'], ascending=[False, True, True])

            ordered_cols = [c for c in [
                'Player', 'Ownership', 'Team', 'Pos', 'Games', 'FPts', 'PC', 'IP',
                'W', 'SO', 'BB', 'HBP', 'H', 'ER'
            ] if c in summary.columns]

            return summary[ordered_cols]

        hitter_summary = build_hitter_summary(hitter_view)
        pitcher_summary = build_pitcher_summary(pitcher_view)

        # -----------------------------
        # Exports
        # -----------------------------
        export_hitters = hitter_view.copy()
        export_pitchers = pitcher_view.copy()

        hitter_export_cols = [
            'Date', 'Player', 'Team', 'Opp', 'Pos', 'Park', 'OppSP', 'LU',
            'Ownership', 'Next FWeek', 'FPts', 'PA', 'R', 'HR', 'RBI', 'SB',
            'SO', 'BB', 'HBP', '1B', '2B', '3B', 'ID'
        ]
        pitcher_export_cols = [
            'Date', 'Player', 'Team', 'Opp', 'Pos', 'Park',
            'Ownership', 'Next FWeek', 'FPts', 'PC', 'IP', 'W', 'SO', 'BB',
            'HBP', 'H', 'ER', 'ID'
        ]

        hitter_export_cols = [c for c in hitter_export_cols if c in export_hitters.columns]
        pitcher_export_cols = [c for c in pitcher_export_cols if c in export_pitchers.columns]

        export_hitters = export_hitters[hitter_export_cols]
        export_pitchers = export_pitchers[pitcher_export_cols]

        d1, d2 = st.columns(2)
        with d1:
            st.download_button(
                "Export Hitters Projections",
                data=export_hitters.to_csv(index=False).encode("utf-8"),
                file_name="upcoming_hitter_projections.csv",
                mime="text/csv",
                use_container_width=True
            )
        with d2:
            st.download_button(
                "Export Pitchers Projections",
                data=export_pitchers.to_csv(index=False).encode("utf-8"),
                file_name="upcoming_pitcher_projections.csv",
                mime="text/csv",
                use_container_width=True
            )

        st.markdown("---")

        # -----------------------------
        # Display helpers
        # -----------------------------
        def format_dates_for_display(data):
            out = data.copy()
            if 'Date' in out.columns:
                out['Date'] = pd.to_datetime(out['Date'], errors='coerce').dt.strftime('%Y-%m-%d')
            return out

        def sort_game_table(data):
            out = data.copy()
            sort_candidates = [c for c in ['Date', 'FPts', 'Player'] if c in out.columns]
            if sort_candidates:
                ascending_flags = []
                for c in sort_candidates:
                    if c == 'Date':
                        ascending_flags.append(True)
                    elif c == 'Player':
                        ascending_flags.append(True)
                    else:
                        ascending_flags.append(not game_sort_desc)
                out = out.sort_values(sort_candidates, ascending=ascending_flags, na_position='last')
            return out

        # -----------------------------
        # Hitters
        # -----------------------------
        if player_view == "Hitters":
            summary_title = "### Hitter Summary Projections"
            if only_next_week:
                summary_title = "### Hitter Summary Projections - Next Fantasy Week"

            st.markdown(summary_title)
            st.caption(f"Summary date range: **{hitter_date_range}**")

            hitter_summary_display = hitter_summary.copy()

            st.dataframe(
                hitter_summary_display,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Ownership": st.column_config.NumberColumn("Own%", format="%.0f"),
                    "Games": st.column_config.NumberColumn("G", format="%d"),
                    "FPts": st.column_config.NumberColumn("FPts", format="%.2f"),
                    "PA": st.column_config.NumberColumn("PA", format="%.2f"),
                    "R": st.column_config.NumberColumn("R", format="%.2f"),
                    "HR": st.column_config.NumberColumn("HR", format="%.2f"),
                    "RBI": st.column_config.NumberColumn("RBI", format="%.2f"),
                    "SB": st.column_config.NumberColumn("SB", format="%.2f"),
                    "SO": st.column_config.NumberColumn("SO", format="%.2f"),
                    "BB": st.column_config.NumberColumn("BB", format="%.2f"),
                    "HBP": st.column_config.NumberColumn("HBP", format="%.2f"),
                    "1B": st.column_config.NumberColumn("1B", format="%.2f"),
                    "2B": st.column_config.NumberColumn("2B", format="%.2f"),
                    "3B": st.column_config.NumberColumn("3B", format="%.2f"),
                }
            )

            st.markdown("### Hitter Game-by-Game Projections")

            hitter_cols = [
                'Date', 'Player', 'Ownership', 'Team', 'Opp', 'Pos', 'Park', 'OppSP', 'LU',
                'FPts', 'PA', 'R', 'HR', 'RBI', 'SB', 'SO', 'BB', 'HBP', '1B', '2B', '3B'
            ]
            hitter_cols = [c for c in hitter_cols if c in hitter_view.columns]

            hitter_display = sort_game_table(hitter_view[hitter_cols].copy())
            hitter_display = format_dates_for_display(hitter_display)

            st.dataframe(
                hitter_display,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Ownership": st.column_config.NumberColumn("Own%", format="%.0f"),
                    "FPts": st.column_config.NumberColumn("FPts", format="%.2f"),
                    "PA": st.column_config.NumberColumn("PA", format="%.2f"),
                    "R": st.column_config.NumberColumn("R", format="%.2f"),
                    "HR": st.column_config.NumberColumn("HR", format="%.2f"),
                    "RBI": st.column_config.NumberColumn("RBI", format="%.2f"),
                    "SB": st.column_config.NumberColumn("SB", format="%.2f"),
                    "LU": st.column_config.NumberColumn("LU", format="%d"),
                }
            )

        # -----------------------------
        # Pitchers
        # -----------------------------
        else:
            summary_title = "### Pitcher Summary Projections"
            if only_next_week:
                summary_title = "### Pitcher Summary Projections - Next Fantasy Week"

            st.markdown(summary_title)
            st.caption(f"Summary date range: **{pitcher_date_range}**")

            pitcher_summary_display = pitcher_summary.copy()

            st.dataframe(
                pitcher_summary_display,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Ownership": st.column_config.NumberColumn("Own%", format="%.0f"),
                    "Games": st.column_config.NumberColumn("G", format="%d"),
                    "FPts": st.column_config.NumberColumn("FPts", format="%.2f"),
                    "PC": st.column_config.NumberColumn("PC", format="%.0f"),
                    "IP": st.column_config.NumberColumn("IP", format="%.2f"),
                    "W": st.column_config.NumberColumn("W", format="%.2f"),
                    "SO": st.column_config.NumberColumn("SO", format="%.2f"),
                    "BB": st.column_config.NumberColumn("BB", format="%.2f"),
                    "HBP": st.column_config.NumberColumn("HBP", format="%.2f"),
                    "H": st.column_config.NumberColumn("H", format="%.2f"),
                    "ER": st.column_config.NumberColumn("ER", format="%.2f"),
                }
            )

            st.markdown("### Pitcher Game-by-Game Projections")

            pitcher_cols = [
                'Date', 'Player', 'Ownership', 'Team', 'Opp', 'Pos', 'Park',
                'FPts', 'PC', 'IP', 'W', 'SO', 'BB', 'HBP', 'H', 'ER'
            ]
            pitcher_cols = [c for c in pitcher_cols if c in pitcher_view.columns]

            pitcher_display = sort_game_table(pitcher_view[pitcher_cols].copy())
            pitcher_display = format_dates_for_display(pitcher_display)

            st.dataframe(
                pitcher_display,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Ownership": st.column_config.NumberColumn("Own%", format="%.0f"),
                    "FPts": st.column_config.NumberColumn("FPts", format="%.2f"),
                    "PC": st.column_config.NumberColumn("PC", format="%.0f"),
                    "IP": st.column_config.NumberColumn("IP", format="%.2f"),
                    "W": st.column_config.NumberColumn("W", format="%.2f"),
                    "SO": st.column_config.NumberColumn("SO", format="%.2f"),
                    "BB": st.column_config.NumberColumn("BB", format="%.2f"),
                    "H": st.column_config.NumberColumn("H", format="%.2f"),
                    "ER": st.column_config.NumberColumn("ER", format="%.2f"),
                }
            )
    if tab == "SP Planner":
        # --- Load only what this page needs ---
        base_sched, upcoming_proj, upcoming_p_scores, upcoming_start_grades, mlbplayerinfo, ownershipdict = load_schedule_data()
        hitterproj_raw, pitcherproj_raw, hitterproj2, gameinfo_raw = load_daily_projections()
        hitter_stats_raw, lineup_stats, pitcher_stats, h_vs_avg, p_vs_avg, h_vs_sim, hotzonedata, posdata = load_player_stats()
        bpreport_raw, rpstats = load_bullpen_data()
        (hitterproj, pitcherproj, hitter_stats, gameinfo, bpreport,
         games_df, mainslateteams, main_slate_gamelist,
         confirmed_lus, last_update) = _prepare_projection_data(
            hitterproj_raw, pitcherproj_raw, hitterproj2, gameinfo_raw,
            hitter_stats_raw, h_vs_avg, bpreport_raw
        )

        st.markdown("&nbsp;<h1><center>Upcoming Strength of Schedule Analysis</h1></center>&nbsp;", unsafe_allow_html=True)

        # ------------------------------------------------------------------
        # Helpers
        # ------------------------------------------------------------------
        owndict = ownershipdict.copy() if isinstance(ownershipdict, dict) else {}

        def _map_own_col(df, player_col="Pitcher", new_col="Own%"):
            out = df.copy()
            out[new_col] = out[player_col].map(owndict)
            out[new_col] = pd.to_numeric(out[new_col], errors="coerce").round(0)
            return out

        def _parse_sched_date(series):
            """
            Robust date parser for base_sched DATE values.
            Handles:
            - full dates already parseable
            - MM-DD strings (assumes current year)
            - MM/DD strings (assumes current year)
            """
            s = series.astype(str).str.strip()

            parsed = pd.to_datetime(s, errors="coerce")

            # If some are still NaT, try adding current year to mm-dd / mm/dd strings
            mask = parsed.isna()
            if mask.any():
                current_year = pd.Timestamp.today().year

                s2 = s.copy()
                s2 = s2.str.replace("/", "-", regex=False)

                # only append year for things like 3-30 / 03-30
                mmdd_mask = s2.str.match(r"^\d{1,2}-\d{1,2}$", na=False)
                s2.loc[mmdd_mask] = s2.loc[mmdd_mask] + f"-{current_year}"

                parsed2 = pd.to_datetime(s2, errors="coerce")
                parsed.loc[mask] = parsed2.loc[mask]

            return parsed.dt.date

        def _next_scoring_period():
            """
            Returns next Monday -> next Sunday.
            If today is Monday, this returns the Monday/Sunday of NEXT week.
            """
            today = pd.Timestamp.today().normalize().date()
            days_until_next_monday = (7 - today.weekday()) % 7
            if days_until_next_monday == 0:
                days_until_next_monday = 7

            next_monday = today + pd.Timedelta(days=days_until_next_monday)
            next_sunday = next_monday + pd.Timedelta(days=6)
            return next_monday, next_sunday

        def _build_two_start_sp_table(base_sched_df):
            """
            Build table of projected two-start SPs for next scoring period.
            Only returns results if we have projected probable starters through next Sunday.
            """
            sched = base_sched_df.copy()

            # Parse date
            sched["DATE_PARSED"] = _parse_sched_date(sched["DATE"])

            next_monday, next_sunday = _next_scoring_period()

            # Must have schedule/probables through next Sunday
            max_sched_date = sched["DATE_PARSED"].dropna().max()

            if pd.isna(max_sched_date) or (max_sched_date < next_sunday):
                return None, next_monday, next_sunday, max_sched_date

            wk = sched[
                (sched["DATE_PARSED"] >= next_monday) &
                (sched["DATE_PARSED"] <= next_sunday)
            ].copy()

            # Need pitcher names populated
            wk["Pitcher"] = wk["Pitcher"].astype(str).str.strip()
            wk = wk[
                wk["Pitcher"].notna() &
                (wk["Pitcher"] != "") &
                (wk["Pitcher"].str.lower() != "nan") &
                (wk["Pitcher"].str.lower() != "tbd")
            ].copy()

            if wk.empty:
                return pd.DataFrame(), next_monday, next_sunday, max_sched_date

            wk["Own%"] = wk["Pitcher"].map(owndict)
            wk["Own%"] = pd.to_numeric(wk["Own%"], errors="coerce").round(0)

            # Keep one row per pitcher's start
            wk = wk[["DATE_PARSED", "Pitcher", "Own%", "TEAM", "OPP", "GAME", "TIME"]].drop_duplicates()

            # Count starts
            sp_counts = (
                wk.groupby(["Pitcher", "TEAM"], dropna=False)
                  .agg(
                      Starts=("DATE_PARSED", "count"),
                      OwnPct=("Own%", "max")
                  )
                  .reset_index()
            )

            two_start = sp_counts[sp_counts["Starts"] >= 2].copy()

            if two_start.empty:
                return pd.DataFrame(), next_monday, next_sunday, max_sched_date

            # Build matchup/date strings
            matchup_map = (
                wk.sort_values(["Pitcher", "DATE_PARSED"])
                  .groupby(["Pitcher", "TEAM"], dropna=False)
                  .apply(lambda x: " | ".join(
                      [f"{d.strftime('%a %m/%d')} vs {opp}" for d, opp in zip(x["DATE_PARSED"], x["OPP"])]
                  ))
                  .reset_index(name="Matchups")
            )

            two_start = two_start.merge(matchup_map, on=["Pitcher", "TEAM"], how="left")
            two_start = two_start.rename(columns={"OwnPct": "Own%"})
            two_start["Own%"] = pd.to_numeric(two_start["Own%"], errors="coerce").round(0)

            two_start = two_start[["Pitcher", "Own%", "TEAM", "Starts", "Matchups"]]
            two_start = two_start.sort_values(["Starts", "Own%", "Pitcher"], ascending=[False, False, True]).reset_index(drop=True)

            return two_start, next_monday, next_sunday, max_sched_date

        # ------------------------------------------------------------------
        # Two-start SP pop-up
        # ------------------------------------------------------------------
        with st.popover("Two-Start SPs (Next Scoring Period)"):
            two_start_df, next_monday, next_sunday, max_sched_date = _build_two_start_sp_table(base_sched)

            st.markdown(
                f"**Scoring period checked:** {pd.to_datetime(next_monday).strftime('%a %m/%d/%Y')} "
                f"through {pd.to_datetime(next_sunday).strftime('%a %m/%d/%Y')}"
            )

            if two_start_df is None:
                st.warning(
                    f"Projected probable pitchers do not extend far enough yet. "
                    f"I need projected probables through **{pd.to_datetime(next_sunday).strftime('%A %m/%d/%Y')}** "
                    f"for this to work."
                )
                if pd.notna(max_sched_date):
                    st.caption(f"Latest projected probable date currently available: {pd.to_datetime(max_sched_date).strftime('%a %m/%d/%Y')}")
            elif two_start_df.empty:
                st.info("No projected two-start SPs found for that scoring period yet.")
            else:
                st.dataframe(
                    two_start_df.style.format({"Own%": "{:.0f}"}),
                    hide_index=True,
                    width=1000,
                    height=450
                )

        # ------------------------------------------------------------------
        # Daily planner
        # ------------------------------------------------------------------
        dpcheck = st.checkbox("Show Daily Planner?")
        if dpcheck:
            st.markdown("<h3><center>Upcoming Starting Pitcher Matchup Grades</h3></center>", unsafe_allow_html=True)

            upcoming_start_grades = upcoming_start_grades.copy()

            # Robust date handling
            if not pd.api.types.is_datetime64_any_dtype(upcoming_start_grades["Date"]):
                temp_dates = upcoming_start_grades["Date"].astype(str).str.strip().str.replace("/", "-", regex=False)

                # If it looks like mm-dd, append current year
                mmdd_mask = temp_dates.str.match(r"^\d{1,2}-\d{1,2}$", na=False)
                temp_dates.loc[mmdd_mask] = temp_dates.loc[mmdd_mask] + f"-{pd.Timestamp.today().year}"

                upcoming_start_grades["Date"] = pd.to_datetime(temp_dates, errors="coerce")

            upcoming_start_grades["Date"] = upcoming_start_grades["Date"].dt.date

            # Use owndict so ownership sits right next to pitcher name
            upcoming_start_grades["Own%"] = upcoming_start_grades["Pitcher"].map(owndict)
            upcoming_start_grades["Own%"] = pd.to_numeric(upcoming_start_grades["Own%"], errors="coerce").round(0)

            upcoming_start_grades = upcoming_start_grades[
                ["Date", "Pitcher", "Own%", "Team", "Opp", "Home", "Start Grade", "Day Rank"]
            ]

            dates = upcoming_start_grades["Date"].dropna().unique()
            ownerships = upcoming_start_grades["Own%"].dropna().unique()

            col1, col2 = st.columns([1, 4])

            with col1:
                if len(dates) > 0:
                    date_range = st.slider(
                        "Select a Date Range",
                        min_value=min(dates),
                        max_value=max(dates),
                        value=(min(dates), max(dates)),
                        format="YYYY-MM-DD"
                    )
                else:
                    date_range = (pd.Timestamp.today().date(), pd.Timestamp.today().date())

                if len(ownerships) > 0:
                    own_range = st.slider(
                        "Select an Ownership Range",
                        min_value=float(min(ownerships)),
                        max_value=float(max(ownerships)),
                        value=(float(min(ownerships)), float(max(ownerships)))
                    )
                else:
                    own_range = (0.0, 100.0)

            with col2:
                sg_filtered_df = upcoming_start_grades[
                    (upcoming_start_grades["Date"] >= date_range[0]) &
                    (upcoming_start_grades["Date"] <= date_range[1])
                ]
                sg_filtered_df = sg_filtered_df[
                    (sg_filtered_df["Own%"].fillna(-1) >= own_range[0]) &
                    (sg_filtered_df["Own%"].fillna(-1) <= own_range[1])
                ]

                sg_display = (
                    sg_filtered_df.style
                    .applymap(sp_grade_color_score, subset=["Start Grade"])
                    .format({"Start Grade": "{:.0f}", "Own%": "{:.0f}"})
                )

                st.dataframe(sg_display, width=900, height=500, hide_index=True)

        # ------------------------------------------------------------------
        # Softest / toughest
        # ------------------------------------------------------------------
        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown("<h3>Softest Upcoming Schedules</h3>", unsafe_allow_html=True)

            top_hits = upcoming_p_scores[upcoming_p_scores["Score"] >= 110].copy()
            top_hits["Own%"] = top_hits["Pitcher"].map(owndict)
            top_hits["Own%"] = pd.to_numeric(top_hits["Own%"], errors="coerce").round(0)
            top_hits = top_hits[["Pitcher", "Own%", "Team", "GS", "Score", "Matchups"]]
            top_hits["Score"] = top_hits["Score"].astype(float).astype(int)

            styled_top_hits = (
                top_hits.style
                .applymap(sp_grade_color_score, subset=["Score"])
                .format({"Own%": "{:.0f}"})
            )

            st.dataframe(styled_top_hits, hide_index=True, height=400, width=900)

        with col2:
            st.markdown("<h3>Toughest Upcoming Schedules</h3>", unsafe_allow_html=True)

            bot_hits = upcoming_p_scores[upcoming_p_scores["Score"] <= 90].copy()
            bot_hits["Own%"] = bot_hits["Pitcher"].map(owndict)
            bot_hits["Own%"] = pd.to_numeric(bot_hits["Own%"], errors="coerce").round(0)
            bot_hits = bot_hits[["Pitcher", "Own%", "Team", "GS", "Score", "Matchups"]].sort_values(by="Score")
            bot_hits["Score"] = bot_hits["Score"].astype(float).astype(int)

            styled_bot_hits = (
                bot_hits.style
                .applymap(sp_grade_color_score, subset=["Score"])
                .format({"Own%": "{:.0f}"})
            )

            st.dataframe(styled_bot_hits, hide_index=True, height=400, width=900)

        # ------------------------------------------------------------------
        # Search + opponent filter
        # ------------------------------------------------------------------
        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown("<h3>Search for a Pitcher</h3>", unsafe_allow_html=True)
            pitcher_name = st.text_input("Enter Pitcher Name:")

            if pitcher_name:
                search_result = upcoming_p_scores[
                    upcoming_p_scores["Pitcher"].str.contains(pitcher_name, case=False, na=False)
                ].copy()

                if not search_result.empty:
                    search_result["Own%"] = search_result["Pitcher"].map(owndict)
                    search_result["Own%"] = pd.to_numeric(search_result["Own%"], errors="coerce").round(0)
                    search_result = search_result[["Pitcher", "Own%", "Team", "GS", "Score", "Matchups"]]
                    search_result["Score"] = search_result["Score"].astype(float).astype(int)

                    styled_search_result = (
                        search_result.style
                        .applymap(sp_grade_color_score, subset=["Score"])
                        .format({"Own%": "{:.0f}"})
                    )

                    st.dataframe(styled_search_result, hide_index=True, width=900)
                else:
                    st.write("No matching pitcher found.")

        with col2:
            p_hand_dict = dict(zip(mlbplayerinfo.Player, mlbplayerinfo.PitchSide))
            st.markdown("<h3>Filter by Opponent</h3>", unsafe_allow_html=True)

            opp_options = sorted(base_sched["OPP"].dropna().unique())
            selected_opp = st.selectbox("Select Opponent:", opp_options)

            filtered_sched = base_sched.copy()
            filtered_sched["Hand"] = filtered_sched["Pitcher"].map(p_hand_dict)
            filtered_sched["Own%"] = filtered_sched["Pitcher"].map(owndict)
            filtered_sched["Own%"] = pd.to_numeric(filtered_sched["Own%"], errors="coerce").round(0)

            filtered_sched = filtered_sched[
                filtered_sched["OPP"] == selected_opp
            ][["DATE", "GAME", "TIME", "Pitcher", "Own%", "Hand", "TEAM", "OPP"]]

            st.dataframe(
                filtered_sched.style.format({"Own%": "{:.0f}"}),
                hide_index=True,
                width=900
            )

    if tab == "Transactions Tracker":
        st.subheader("MLB Transactions Tracker")

        # =========================
        # Load data
        # =========================
        @st.cache_data(ttl=3600, show_spinner=False)
        def load_transactions():
            base_dir = os.path.dirname(__file__)
            data_dir = os.path.join(base_dir, "Data")
            path = os.path.join(data_dir, "mlb_transactions.parquet")
            df = pd.read_parquet(path)

            # Standardize
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                df["date_only"] = df["date"].dt.date
            else:
                df["date"] = pd.NaT
                df["date_only"] = pd.NaT

            if "effectiveDate" in df.columns:
                df["effectiveDate"] = pd.to_datetime(df["effectiveDate"], errors="coerce")

            # Safe description
            if "description" not in df.columns:
                df["description"] = ""
            df["description"] = df["description"].astype(str)

            # Common friendly columns if not already present
            if "player_name" not in df.columns and "person.fullName" in df.columns:
                df["player_name"] = df["person.fullName"]
            if "player_id" not in df.columns and "person.id" in df.columns:
                df["player_id"] = df["person.id"]

            if "to_team" not in df.columns and "toTeam.name" in df.columns:
                df["to_team"] = df["toTeam.name"]
            if "from_team" not in df.columns and "fromTeam.name" in df.columns:
                df["from_team"] = df["fromTeam.name"]

            if "typeDesc" not in df.columns:
                df["typeDesc"] = df.get("type", "")

            # IL flag (ensure exists)
            if "is_il" not in df.columns:
                df["is_il"] = df["description"].str.contains(r"\binjured list\b", case=False, na=False)

            df = df[df['typeDesc']!='Number Change']
            return df

        transactions_df = load_transactions()

        # =========================
        # Compute date bounds
        # =========================
        if transactions_df["date"].notna().any():
            min_date = transactions_df["date"].min().date()
            max_date = transactions_df["date"].max().date()
        else:
            min_date = datetime(2025, 1, 1).date()
            max_date = datetime.today().date()

        default_start = max(min_date, max_date - timedelta(days=14))

        # =========================
        # TOP CONTROLS (on main page)
        # =========================
        # Row 1: search + quick range + IL only + max rows
        c1, c2, c3, c4 = st.columns([3, 1.4, 1, 1.2])
        with c1:
            q = st.text_input(
                "Search (player, team, transaction text)",
                value="",
                placeholder="Castellanos, DFA, 60-day, hamstring, Yankees..."
            )
        with c2:
            preset = st.selectbox(
                "Quick range",
                ["Last 14 days", "Today", "Last 3 days", "Last 7 days", "Last 30 days", "Season-to-date", "Custom"],
                index=0
            )
        with c3:
            il_only = st.toggle("IL only", value=False) if "is_il" in transactions_df.columns else False
        with c4:
            max_rows = st.number_input("Max rows", min_value=100, max_value=20000, value=1500, step=100)

        # Row 2: date range + sorting
        c5, c6 = st.columns([2.2, 1])
        with c5:
            # Apply preset → default date range
            if preset == "Today":
                date_range_default = (max_date, max_date)
            elif preset == "Last 3 days":
                date_range_default = (max(min_date, max_date - timedelta(days=2)), max_date)
            elif preset == "Last 7 days":
                date_range_default = (max(min_date, max_date - timedelta(days=6)), max_date)
            elif preset == "Last 30 days":
                date_range_default = (max(min_date, max_date - timedelta(days=29)), max_date)
            elif preset == "Season-to-date":
                date_range_default = (min_date, max_date)
            elif preset == "Custom":
                date_range_default = (default_start, max_date)
            else:  # Last 14 days
                date_range_default = (default_start, max_date)

            date_range = st.date_input(
                "Date range",
                value=date_range_default,
                min_value=min_date,
                max_value=max_date
            )
            if isinstance(date_range, tuple) and len(date_range) == 2:
                start_d, end_d = date_range
            else:
                start_d, end_d = date_range_default

        with c6:
            sort_choice = st.selectbox(
                "Sort",
                ["Newest first", "Oldest first", "Player A→Z", "Team A→Z"],
                index=0
            )

        # Row 3: Team / Type / Player filters
        c7, c8, c9, c10 = st.columns([1.2, 2.2, 2.2, 2.4])

        # Team options
        team_opts = sorted(pd.unique(
            pd.concat([
                transactions_df.get("to_team", pd.Series(dtype=str)).dropna().astype(str),
                transactions_df.get("from_team", pd.Series(dtype=str)).dropna().astype(str),
            ], ignore_index=True)
        ).tolist())

        with c7:
            team_mode = st.radio("Team match", ["Any", "To", "From"], horizontal=True)

        with c8:
            selected_teams = st.multiselect("Team(s)", options=team_opts, default=[])

        # Type options (top N)
        type_opts = []
        if "typeDesc" in transactions_df.columns:
            type_opts = (
                transactions_df["typeDesc"]
                .fillna("")
                .astype(str)
                .value_counts()
                .head(40)
                .index
                .tolist()
            )

        with c9:
            selected_types = st.multiselect("Type(s)", options=type_opts, default=[])

        # Player options (top 1000 for speed)
        player_opts = (
            transactions_df.get("player_name", pd.Series(dtype=str))
            .dropna()
            .astype(str)
            .value_counts()
            .head(1000)
            .index
            .tolist()
        )

        with c10:
            selected_players = st.multiselect("Player(s) (top 1000)", options=player_opts, default=[])

        # Row 4: Column chooser + reset
        c11, c12 = st.columns([3.2, 1])

        available_cols = [c for c in [
            "date", "effectiveDate", "player_name", "to_team", "from_team", "typeDesc",
            "is_il", "il_days", "retroactive", "injury_detail", "body_part", "injury_type",
            "description"
        ] if c in transactions_df.columns]

        default_cols = [c for c in ["date", "player_name", "to_team", "typeDesc", "description"] if c in available_cols]

        with c11:
            show_cols = st.multiselect(
                "Columns",
                options=available_cols,
                default=default_cols
            )

        with c12:
            st.write("")  # spacer
            st.write("")
            if st.button("Reset filters", use_container_width=True):
                st.rerun()

        st.divider()

        # =========================
        # Apply filters (safe)
        # =========================
        df = transactions_df.copy()

        # Date filter
        if "date_only" in df.columns:
            df = df[(df["date_only"] >= start_d) & (df["date_only"] <= end_d)]

        # IL only
        if il_only and "is_il" in df.columns:
            df = df[df["is_il"] == True]

        # Type filter
        if selected_types and "typeDesc" in df.columns:
            df = df[df["typeDesc"].astype(str).isin(selected_types)]

        # Team filter
        if selected_teams:
            if team_mode == "To" and "to_team" in df.columns:
                df = df[df["to_team"].astype(str).isin(selected_teams)]
            elif team_mode == "From" and "from_team" in df.columns:
                df = df[df["from_team"].astype(str).isin(selected_teams)]
            else:
                to_match = df["to_team"].astype(str).isin(selected_teams) if "to_team" in df.columns else False
                from_match = df["from_team"].astype(str).isin(selected_teams) if "from_team" in df.columns else False
                df = df[to_match | from_match]

        # Player filter
        if selected_players and "player_name" in df.columns:
            df = df[df["player_name"].astype(str).isin(selected_players)]

        # Global search
        if q.strip():
            needle = q.strip()
            search_cols = [c for c in ["player_name", "to_team", "from_team", "typeDesc", "description"] if c in df.columns]
            if search_cols:
                mask = False
                for c in search_cols:
                    mask = mask | df[c].astype(str).str.contains(needle, case=False, na=False)
                df = df[mask]

        # Sort
        if sort_choice == "Newest first" and "date" in df.columns:
            df = df.sort_values("date", ascending=False)
        elif sort_choice == "Oldest first" and "date" in df.columns:
            df = df.sort_values("date", ascending=True)
        elif sort_choice == "Player A→Z" and "player_name" in df.columns:
            df = df.sort_values("player_name", ascending=True)
        elif sort_choice == "Team A→Z" and "to_team" in df.columns:
            df = df.sort_values("to_team", ascending=True)

        # =========================
        # Metrics + quick insights
        # =========================
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Rows (filtered)", f"{len(df):,}")
        m2.metric("Date range", f"{start_d} → {end_d}")
        m3.metric("IL moves", f"{int(df['is_il'].sum()):,}" if "is_il" in df.columns else "—")
        m4.metric("Showing", f"{min(len(df), int(max_rows)):,} / {len(df):,}")

        with st.expander("🔎 Quick summary (auto)", expanded=True):
            if "typeDesc" in df.columns:
                top_types = df["typeDesc"].fillna("").astype(str).value_counts().head(10)
                if len(top_types):
                    st.write("**Top transaction types:** " + ", ".join([f"{k} ({v})" for k, v in top_types.items() if k]))
            if "is_il" in df.columns and df["is_il"].any() and "injury_detail" in df.columns:
                il_snips = (
                    df[df["is_il"] == True]["injury_detail"]
                    .dropna()
                    .astype(str)
                    .value_counts()
                    .head(10)
                )
                if len(il_snips):
                    st.write("**Most common injury details (when provided):** " + ", ".join([f"{k} ({v})" for k, v in il_snips.items()]))

        st.divider()

        # =========================
        # Display
        # =========================
        if not show_cols:
            st.warning("Select at least one column to display.")
        else:
            df_view = df.head(int(max_rows)).copy()
            display_df = df_view[show_cols].copy()

            # ── Strip timestamps: show only YYYY-MM-DD ──
            for dcol in ["date", "effectiveDate", "il_start_date"]:
                if dcol in display_df.columns:
                    display_df[dcol] = (
                        pd.to_datetime(display_df[dcol], errors="coerce")
                        .dt.strftime("%Y-%m-%d")
                        .fillna("")
                    )

            # ── Badge helper for typeDesc ──
            def _txn_badge(val):
                s = str(val).strip()
                sl = s.lower()
                if "trade" in sl:
                    cls = "badge-trade"
                elif "il" in sl or "injured" in sl or "disabled" in sl:
                    cls = "badge-il"
                elif "assign" in sl:
                    cls = "badge-assigned"
                elif "dfa" in sl or "designated" in sl:
                    cls = "badge-dfa"
                else:
                    cls = "badge-other"
                return f'<span class="txn-badge {cls}">{s}</span>'

            # ── Build HTML table ──
            header_cells = "".join(
                f"<th>{c.replace('_', ' ').title()}</th>" for c in display_df.columns
            )
            rows_html = []
            for _, row in display_df.iterrows():
                cells = []
                for col in display_df.columns:
                    val = row[col]
                    s_val = "" if (val is None or (isinstance(val, float) and val != val)) else str(val)
                    if col == "description":
                        cells.append(f'<td class="desc">{s_val}</td>')
                    elif col in ("date", "effectiveDate", "il_start_date"):
                        cells.append(f'<td class="date">{s_val}</td>')
                    elif col == "typeDesc":
                        cells.append(f'<td>{_txn_badge(s_val)}</td>')
                    else:
                        cells.append(f"<td>{s_val}</td>")
                rows_html.append("<tr>" + "".join(cells) + "</tr>")

            table_html = f"""
            <div style="overflow-x:auto; border-radius:10px; border:1px solid #dce2ed;">
            <table class="txn-table">
                <thead><tr>{header_cells}</tr></thead>
                <tbody>{"".join(rows_html)}</tbody>
            </table>
            </div>
            """
            st.markdown(table_html, unsafe_allow_html=True)

        # =========================
        # Downloads
        # =========================
        d1, d2, d3 = st.columns([1.2, 1.2, 2.6])

        with d1:
            st.download_button(
                "⬇️ Download filtered CSV",
                data=df[show_cols].to_csv(index=False).encode("utf-8") if show_cols else df.to_csv(index=False).encode("utf-8"),
                file_name=f"mlb_transactions_filtered_{start_d}_to_{end_d}.csv",
                mime="text/csv",
                use_container_width=True
            )

        with d2:
            if "is_il" in df.columns:
                il_only_df = df[df["is_il"] == True]
                st.download_button(
                    "🏥 Download IL-only CSV",
                    data=il_only_df[show_cols].to_csv(index=False).encode("utf-8") if show_cols else il_only_df.to_csv(index=False).encode("utf-8"),
                    file_name=f"mlb_transactions_IL_{start_d}_to_{end_d}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

        with d3:
            st.caption(
                "Tips: search `DFA`, `optioned`, `selected`, `activated`, `60-day`, `retroactive`, `hamstring`, etc. "
                "All text matching uses `na=False` so null descriptions won't crash filters."
            )
    
    
    if tab == "Tim Kanak fScores":
        # --- Load only what this page needs ---
        hitterranks, pitcherranks, fscores_mlb_hit, fscores_milb_hit, fscores_mlb_pitch, fscores_milb_pitch, pitchers_fscores, hitters_fscores, timrank_hitters, timrank_pitchers, posdata = load_rankings()
        import streamlit as st
        import pandas as pd
        import numpy as np

        # =========================================================
        # EXPECTED DATAFRAMES
        # You said you'll handle loading them.
        #
        # hitters_fscores expected columns:
        # Player, ID, Level, MLB Team, HitTool, Power, Speed,
        # Discipline, Durability, Hitter Grade
        #
        # pitchers_fscores expected columns:
        # Player, ID, Level, MLB Team, ERA, Control, Stuff,
        # Durability, Pitcher Grade
        # =========================================================

        # -----------------------------
        # Page styling
        # -----------------------------
        st.markdown("""
        <style>
        .fscore-hero {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 60%, #334155 100%);
            padding: 24px 28px;
            border-radius: 18px;
            margin-bottom: 18px;
            border: 1px solid rgba(255,255,255,0.08);
            box-shadow: 0 10px 24px rgba(0,0,0,0.16);
        }
        .fscore-title {
            color: white;
            font-size: 2rem;
            font-weight: 800;
            margin-bottom: 6px;
            letter-spacing: -0.02em;
        }
        .fscore-sub {
            color: #dbeafe;
            font-size: 0.98rem;
            margin-bottom: 6px;
        }
        .fscore-note {
            color: #cbd5e1;
            font-size: 0.92rem;
        }
        </style>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="fscore-hero">
            <div class="fscore-title">Tim Kanak fScores</div>
            <div class="fscore-sub">
                fScores created by <b>Tim Kanak</b> (@fantasyaceball on X) and programmed by
                <b>Jon Anderson</b> (@JonPGH on X)
            </div>
            <div class="fscore-note">
                All fScores are built on a 100-average scale. Higher = green. Lower = red.
            </div>
        </div>
        """, unsafe_allow_html=True)

        # -----------------------------
        # Helper functions
        # -----------------------------
        @st.cache_data(show_spinner=False)
        def prep_hitter_data(df):
            df = df.copy()
            df = df.loc[:, ~df.columns.astype(str).str.contains("^Unnamed")]

            for c in ["Player", "Level", "MLB Team"]:
                if c in df.columns:
                    df[c] = df[c].astype(str).str.strip()

            if "ID" in df.columns:
                df["ID"] = pd.to_numeric(df["ID"], errors="coerce").astype("Int64")

            if "Level" in df.columns:
                df["LevelGroup"] = np.where(
                    df["Level"].astype(str).str.upper() == "MLB",
                    "Majors",
                    "Minors"
                )
            else:
                df["LevelGroup"] = "Unknown"

            return df

        @st.cache_data(show_spinner=False)
        def prep_pitcher_data(df):
            df = df.copy()
            df = df.loc[:, ~df.columns.astype(str).str.contains("^Unnamed")]

            for c in ["Player", "Level", "MLB Team"]:
                if c in df.columns:
                    df[c] = df[c].astype(str).str.strip()

            if "ID" in df.columns:
                df["ID"] = pd.to_numeric(df["ID"], errors="coerce").astype("Int64")

            if "Level" in df.columns:
                df["LevelGroup"] = np.where(
                    df["Level"].astype(str).str.upper() == "MLB",
                    "Majors",
                    "Minors"
                )
            else:
                df["LevelGroup"] = "Unknown"

            return df

        hitters = prep_hitter_data(hitters_fscores)
        pitchers = prep_pitcher_data(pitchers_fscores)

        HITTER_SCORE_COLS = [
            "HitTool", "Power", "Speed", "Discipline", "Durability", "Hitter Grade"
        ]
        PITCHER_SCORE_COLS = [
            "ERA", "Control", "Stuff", "Durability", "Pitcher Grade"
        ]

        HITTER_DISPLAY_COLS = ["Player", "MLB Team", "Level"] + HITTER_SCORE_COLS
        PITCHER_DISPLAY_COLS = ["Player", "MLB Team", "Level"] + PITCHER_SCORE_COLS

        def filter_level(df, level_choice):
            if level_choice == "Majors":
                return df[df["LevelGroup"] == "Majors"].copy()
            elif level_choice == "Minors":
                return df[df["LevelGroup"] == "Minors"].copy()
            return df.copy()

        def apply_score_gradient(val):
            try:
                v = float(val)
            except:
                return ""

            if pd.isna(v):
                return ""

            if v >= 100:
                intensity = min((v - 100) / 60, 1.0)
                return f"background-color: rgba(34, 197, 94, {0.12 + 0.33*intensity:.3f});"
            else:
                intensity = min((100 - v) / 60, 1.0)
                return f"background-color: rgba(239, 68, 68, {0.12 + 0.33*intensity:.3f});"

        def render_table(df, score_cols, csv_name):
            if df.empty:
                st.info("No matching fScores found.")
                return

            working = df.copy()

            search_text = st.text_input("Search within table", key=f"search_{csv_name}")
            if search_text:
                mask = working.astype(str).apply(
                    lambda col: col.str.contains(search_text, case=False, na=False)
                ).any(axis=1)
                working = working[mask].copy()

            sort_options = [c for c in working.columns if c in score_cols] + [
                c for c in working.columns if c not in score_cols
            ]
            default_sort = score_cols[-1] if score_cols[-1] in working.columns else working.columns[0]

            c1, c2 = st.columns([1, 1])
            with c1:
                sort_col = st.selectbox(
                    "Sort by",
                    options=sort_options,
                    index=sort_options.index(default_sort) if default_sort in sort_options else 0,
                    key=f"sortcol_{csv_name}"
                )
            with c2:
                sort_order = st.radio(
                    "Order",
                    ["Descending", "Ascending"],
                    horizontal=True,
                    key=f"sortorder_{csv_name}"
                )

            working = working.sort_values(
                sort_col,
                ascending=(sort_order == "Ascending")
            ).reset_index(drop=True)

            styled = (
                working.style
                .applymap(apply_score_gradient, subset=[c for c in score_cols if c in working.columns])
                .format({c: "{:.0f}" for c in score_cols if c in working.columns})
            )

            st.dataframe(
                styled,
                use_container_width=True,
                height=650
            )

            st.download_button(
                "Download CSV",
                data=working.to_csv(index=False).encode("utf-8"),
                file_name=csv_name,
                mime="text/csv",
                key=f"download_{csv_name}"
            )

        # -----------------------------
        # Main controls
        # -----------------------------
        st.markdown("### fScore Search")

        c1, c2, c3 = st.columns([1, 1, 1])

        with c1:
            score_side = st.radio("Show fScores for", ["Hitters", "Pitchers"], horizontal=True)

        with c2:
            search_mode = st.radio("Search type", ["Player", "Team"], horizontal=True)

        with c3:
            level_choice = st.radio("Level", ["All", "Majors", "Minors"], horizontal=True)

        # -----------------------------
        # Hitters
        # -----------------------------
        if score_side == "Hitters":
            df = hitters.copy()
            df = filter_level(df, level_choice)

            df = df.dropna(
                subset=[c for c in HITTER_SCORE_COLS if c in df.columns],
                how="all"
            ).copy()

            if search_mode == "Player":
                player_list = sorted(df["Player"].dropna().unique().tolist())
                selected_player = st.selectbox("Choose a player", player_list)

                result = df[df["Player"] == selected_player].copy()

                # If MLB exists, prioritize it and hide minors
                if level_choice == "All" and not result.empty and (result["LevelGroup"] == "Majors").any():
                    result = result[result["LevelGroup"] == "Majors"].copy()

                result = result[[c for c in HITTER_DISPLAY_COLS if c in result.columns]]

                st.markdown(f"#### {selected_player} Hitting fScores")
                render_table(
                    result,
                    score_cols=HITTER_SCORE_COLS,
                    csv_name=f"{selected_player.replace(' ', '_')}_hitting_fscores.csv"
                )

            else:
                team_list = sorted(df["MLB Team"].dropna().unique().tolist())
                team_list = ["All"] + team_list
                selected_team = st.selectbox("Choose an organization / MLB team", team_list)

                if selected_team == "All":
                    result = df.copy()
                else:
                    result = df[df["MLB Team"] == selected_team].copy()

                result = result[[c for c in HITTER_DISPLAY_COLS if c in result.columns]]

                title_team = "All Teams" if selected_team == "All" else selected_team
                st.markdown(f"#### {title_team} Hitting fScores")
                render_table(
                    result,
                    score_cols=HITTER_SCORE_COLS,
                    csv_name=f"{selected_team}_{level_choice.lower()}_hitting_fscores.csv"
                )

        # -----------------------------
        # Pitchers
        # -----------------------------
        else:
            df = pitchers.copy()
            df = filter_level(df, level_choice)

            df = df.dropna(
                subset=[c for c in PITCHER_SCORE_COLS if c in df.columns],
                how="all"
            ).copy()

            if search_mode == "Player":
                player_list = sorted(df["Player"].dropna().unique().tolist())
                selected_player = st.selectbox("Choose a player", player_list)

                result = df[df["Player"] == selected_player].copy()

                # If MLB exists, prioritize it and hide minors
                if level_choice == "All" and not result.empty and (result["LevelGroup"] == "Majors").any():
                    result = result[result["LevelGroup"] == "Majors"].copy()

                result = result[[c for c in PITCHER_DISPLAY_COLS if c in result.columns]]

                st.markdown(f"#### {selected_player} Pitching fScores")
                render_table(
                    result,
                    score_cols=PITCHER_SCORE_COLS,
                    csv_name=f"{selected_player.replace(' ', '_')}_pitching_fscores.csv"
                )

            else:
                team_list = sorted(df["MLB Team"].dropna().unique().tolist())
                team_list = ["All"] + team_list
                selected_team = st.selectbox("Choose an organization / MLB team", team_list)

                if selected_team == "All":
                    result = df.copy()
                else:
                    result = df[df["MLB Team"] == selected_team].copy()

                result = result[[c for c in PITCHER_DISPLAY_COLS if c in result.columns]]

                title_team = "All Teams" if selected_team == "All" else selected_team
                st.markdown(f"#### {title_team} Pitching fScores")
                render_table(
                    result,
                    score_cols=PITCHER_SCORE_COLS,
                    csv_name=f"{selected_team}_{level_choice.lower()}_pitching_fscores.csv"
                )

    if tab == "Games & Lineups _ Old":
        import pandas as pd
        import numpy as np
        import streamlit as st
        import textwrap

        def load_games_and_lus_data():
            fp = _DATA_DIR
            daily_weather_report  = pd.read_csv(f'{fp}/daily_weather_2026.csv')
            dfs_pitcher_proj = pd.read_csv(f'{fp}/Tableau_DailyPitcherProj.csv')
            dfs_hitter_proj = pd.read_csv(f'{fp}/Tableau_DailyHitterProj.csv')
            game_info = pd.read_csv(f'{fp}/gameinfo.csv')
            return dfs_hitter_proj, dfs_pitcher_proj, daily_weather_report, game_info

        dfs_hitter_proj, dfs_pitcher_proj, daily_weather_report, game_info = load_games_and_lus_data()

        # -----------------------------
        # basic cleanup
        # -----------------------------
        for df in [dfs_hitter_proj, dfs_pitcher_proj, daily_weather_report, game_info]:
            drop_cols = [c for c in df.columns if str(c).startswith("Unnamed")]
            if drop_cols:
                df.drop(columns=drop_cols, inplace=True, errors="ignore")

        dfs_hitter_proj["Team"] = dfs_hitter_proj["Team"].astype(str).str.upper().str.strip()
        dfs_hitter_proj["Opp"] = dfs_hitter_proj["Opp"].astype(str).str.upper().str.strip()

        dfs_pitcher_proj["Team"] = dfs_pitcher_proj["Team"].astype(str).str.upper().str.strip()
        dfs_pitcher_proj["Opponent"] = dfs_pitcher_proj["Opponent"].astype(str).str.upper().str.strip()
        dfs_pitcher_proj["HomeTeam"] = dfs_pitcher_proj["HomeTeam"].astype(str).str.upper().str.strip()

        game_info["team"] = game_info["team"].astype(str).str.upper().str.strip()
        game_info["opponent"] = game_info["opponent"].astype(str).str.upper().str.strip()
        game_info["Park"] = game_info["Park"].astype(str).str.upper().str.strip()

        if "away_team" in daily_weather_report.columns:
            daily_weather_report["away_team"] = daily_weather_report["away_team"].astype(str).str.upper().str.strip()
        if "home_team" in daily_weather_report.columns:
            daily_weather_report["home_team"] = daily_weather_report["home_team"].astype(str).str.upper().str.strip()

        dfs_hitter_proj["LU"] = pd.to_numeric(dfs_hitter_proj["LU"], errors="coerce")
        dfs_hitter_proj["Sal"] = pd.to_numeric(dfs_hitter_proj["Sal"], errors="coerce")
        dfs_pitcher_proj["Sal"] = pd.to_numeric(dfs_pitcher_proj["Sal"], errors="coerce")

        def clean_html(s: str) -> str:
            return textwrap.dedent(s).strip()

        def fmt_odds(x):
            if pd.isna(x):
                return "—"
            x = int(round(float(x)))
            return f"+{x}" if x > 0 else str(x)

        def fmt_moneyline_with_total(row):
            ml = fmt_odds(row.get("moneyline"))
            proj = row.get("projected", np.nan)
            proj_txt = f"{proj:.2f}" if pd.notna(proj) else "—"
            return ml, proj_txt

        def fmt_ou(x):
            if pd.isna(x):
                return "—"
            return f"{float(x):.1f}"

        def fmt_temp(x):
            if pd.isna(x):
                return "—"
            return f"{int(round(float(x)))}°"

        def fmt_rain(x):
            if pd.isna(x):
                return "—"
            return f"{int(round(float(x)))}%"

        def fmt_salary(x):
            if pd.isna(x) or float(x) <= 0:
                return ""
            val = float(x)
            return f"${val/1000:.1f}K" if val >= 1000 else f"${val:,.0f}"

        def lineup_status(team_df):
            vals = (
                team_df["Confirmed LU"]
                .astype(str)
                .str.upper()
                .str.strip()
                .replace({"YES": "Y", "NO": "N", "TRUE": "Y", "FALSE": "N"})
            )
            if (vals == "Y").any():
                return "CONFIRMED", "confirmed"
            return "NOT CONFIRMED", "not-confirmed"

        def get_lineup(team):
            df = dfs_hitter_proj[dfs_hitter_proj["Team"] == team].copy()
            if df.empty:
                return df
            return df.sort_values(["LU", "Hitter"], na_position="last")

        def get_pitcher_for_team(team):
            pdf = dfs_pitcher_proj[dfs_pitcher_proj["Team"] == team].copy()
            if pdf.empty:
                return {"Pitcher": "TBD", "Sal": np.nan}
            row = pdf.sort_values(["DKPts", "Sal"], ascending=[False, False]).iloc[0]
            return {"Pitcher": row.get("Pitcher", "TBD"), "Sal": row.get("Sal", np.nan)}

        def get_weather(away_team, home_team):
            if daily_weather_report.empty:
                return None

            w = daily_weather_report[
                (daily_weather_report["away_team"] == away_team) &
                (daily_weather_report["home_team"] == home_team)
            ].copy()

            if w.empty:
                w = daily_weather_report[daily_weather_report["home_team"] == home_team].copy()

            if w.empty:
                return None

            row = w.iloc[0]
            return {
                "temp": fmt_temp(row.get("temp_f")),
                "rain": fmt_rain(row.get("rain_prob_pct")),
                "wind": row.get("wind_summary", "—")
            }

        def build_games():
            games = []
            used = set()

            for _, row in game_info.iterrows():
                team = row["team"]
                opp = row["opponent"]
                pair_key = tuple(sorted([team, opp]))
                if pair_key in used:
                    continue

                pair_rows = game_info[
                    ((game_info["team"] == team) & (game_info["opponent"] == opp)) |
                    ((game_info["team"] == opp) & (game_info["opponent"] == team))
                ].copy()

                if pair_rows.empty or len(pair_rows) < 2:
                    continue

                home_rows = pair_rows[pair_rows["team"] == pair_rows["Park"]]
                home_row = home_rows.iloc[0] if not home_rows.empty else pair_rows.iloc[0]

                away_rows = pair_rows[pair_rows["team"] != pair_rows["Park"]]
                away_row = away_rows.iloc[0] if not away_rows.empty else pair_rows[pair_rows["team"] != home_row["team"]].iloc[0]

                games.append({
                    "away_team": away_row["team"],
                    "home_team": home_row["team"],
                    "away_row": away_row,
                    "home_row": home_row,
                    "game_time": home_row.get("game_time", away_row.get("game_time", "")),
                    "game_date": home_row.get("game_date", away_row.get("game_date", "")),
                    "park": home_row.get("Park", ""),
                    "overunder": home_row.get("overunder", away_row.get("overunder", np.nan)),
                })
                used.add(pair_key)

            return games

        games = build_games()

        if main_slate_only and len(main_slate_teams) > 0:
            games = [
                g for g in games
                if g["away_team"] in main_slate_teams and g["home_team"] in main_slate_teams
            ]

        try:
            games = sorted(
                games,
                key=lambda x: pd.to_datetime(f"{x['game_date']} {x['game_time']}", errors="coerce")
            )
        except Exception:
            pass

        def build_game_table(games):
            rows = []
            for g in games:
                away_row = g["away_row"]
                home_row = g["home_row"]

                weather = get_weather(g["away_team"], g["home_team"])

                away_pitcher = get_pitcher_for_team(g["away_team"])
                home_pitcher = get_pitcher_for_team(g["home_team"])

                rows.append({
                    "Time": g.get("game_time", ""),
                    "Away": g["away_team"],
                    "Home": g["home_team"],
                    "Matchup": f"{g['away_team']} @ {g['home_team']}",
                    "Park": g.get("park", ""),
                    "Away SP": away_pitcher.get("Pitcher", "TBD"),
                    "Home SP": home_pitcher.get("Pitcher", "TBD"),
                    "Away ML": away_row.get("moneyline", np.nan),
                    "Home ML": home_row.get("moneyline", np.nan),
                    "O/U": g.get("overunder", np.nan),
                    "Away IRT": away_row.get("projected", np.nan),
                    "Home IRT": home_row.get("projected", np.nan),
                    "Temp": weather["temp"] if weather else "—",
                    "Rain": weather["rain"] if weather else "—",
                    "Wind": weather["wind"] if weather else "—",
                })

            game_table = pd.DataFrame(rows)

            if not game_table.empty:
                if "Away ML" in game_table.columns:
                    game_table["Away ML"] = pd.to_numeric(game_table["Away ML"], errors="coerce")
                if "Home ML" in game_table.columns:
                    game_table["Home ML"] = pd.to_numeric(game_table["Home ML"], errors="coerce")
                if "O/U" in game_table.columns:
                    game_table["O/U"] = pd.to_numeric(game_table["O/U"], errors="coerce")
                if "Away IRT" in game_table.columns:
                    game_table["Away IRT"] = pd.to_numeric(game_table["Away IRT"], errors="coerce")
                if "Home IRT" in game_table.columns:
                    game_table["Home IRT"] = pd.to_numeric(game_table["Home IRT"], errors="coerce")

            return game_table

        game_table = build_game_table(games)

        if show_game_table:
            st.markdown("### Game Info Table")
            st.dataframe(
                game_table,
                use_container_width=True,
                hide_index=True
            )

        st.markdown("""
        <style>
        .slate-card {
            border: 1px solid #d9d9d9;
            border-radius: 14px;
            background: white;
            margin-bottom: 18px;
            overflow: hidden;
            box-shadow: 0 1px 4px rgba(0,0,0,.06);
        }
        .slate-header {
            background: #f7f7f7;
            padding: 12px 14px 8px 14px;
            border-bottom: 1px solid #e6e6e6;
        }
        .slate-time {
            font-size: 0.85rem;
            color: #666;
            font-weight: 600;
            margin-bottom: 6px;
        }
        .slate-matchup {
            display: flex;
            justify-content: space-between;
            gap: 10px;
            font-weight: 700;
            font-size: 1.05rem;
        }
        .slate-weather {
            background: #eef8ee;
            padding: 10px 14px;
            border-bottom: 1px solid #e6e6e6;
            font-size: 0.9rem;
            line-height: 1.35;
        }
        .slate-betting {
            display: grid;
            grid-template-columns: 1fr 0.9fr 1fr;
            text-align: center;
            border-bottom: 1px solid #e6e6e6;
            background: #fbfbfb;
        }
        .bet-box { padding: 12px 8px; }
        .bet-main {
            font-weight: 800;
            font-size: 1.25rem;
            color: #164a9c;
        }
        .bet-sub {
            font-size: 0.84rem;
            color: #666;
        }
        .team-sections {
            display: grid;
            grid-template-columns: 1fr 1fr;
        }
        .team-col { border-right: 1px solid #ededed; }
        .team-col:last-child { border-right: none; }
        .pitcher-box {
            text-align: center;
            padding: 14px 10px 10px 10px;
            min-height: 78px;
        }
        .pitcher-name {
            font-size: 1.05rem;
            font-weight: 700;
            color: #444;
        }
        .pitcher-meta {
            font-size: 0.9rem;
            color: #666;
        }
        .lineup-status-confirmed {
            background: #1f8f4e;
            color: white;
            font-weight: 700;
            font-size: 0.85rem;
            padding: 7px 12px;
        }
        .lineup-status-not-confirmed {
            background: #e05353;
            color: white;
            font-weight: 700;
            font-size: 0.85rem;
            padding: 7px 12px;
        }
        .lineup-list {
            background: #faeded;
            padding: 10px 14px 14px 14px;
            min-height: 290px;
        }
        .lineup-list.confirmed-bg { background: #eef7ef; }
        .line-row {
            display: flex;
            gap: 8px;
            align-items: baseline;
            margin-bottom: 5px;
            font-size: 0.95rem;
        }
        .line-spot {
            width: 16px;
            color: #666;
            flex-shrink: 0;
        }
        .line-player {
            font-weight: 600;
            color: #444;
        }
        .line-pos {
            color: #777;
            font-size: 0.84rem;
        }
        .line-sal {
            color: #17853a;
            font-weight: 700;
            font-size: 0.88rem;
            margin-left: auto;
        }
        .small-muted {
            color: #777;
            font-size: 0.83rem;
        }
        </style>
        """, unsafe_allow_html=True)

        def get_main_slate_teams():
            teams = set()

            if "MainSlate" in dfs_hitter_proj.columns:
                hit_main = dfs_hitter_proj[
                    dfs_hitter_proj["MainSlate"].astype(str).str.upper().isin(["Y","MAIN", "YES", "TRUE", "1"])
                ]["Team"].dropna().astype(str).str.upper().unique().tolist()
                teams.update(hit_main)

            if "MainSlate" in dfs_pitcher_proj.columns:
                pit_main = dfs_pitcher_proj[
                    dfs_pitcher_proj["MainSlate"].astype(str).str.upper().isin(["Y","MAIN", "YES", "TRUE", "1"])
                ]["Team"].dropna().astype(str).str.upper().unique().tolist()
                teams.update(pit_main)

            return teams

        main_slate_teams = get_main_slate_teams()

        st.subheader("Slate Preview")

        top_c1, top_c2 = st.columns([1, 1])

        with top_c1:
            show_game_table = st.toggle("Show game info table", value=False)

        with top_c2:
            main_slate_only = st.toggle("Main slate only", value=False)

        if len(games) == 0:
            st.warning("No games found.")
        else:
            #for i in range(0, len(games), 3):
            #    row_games = games[i:i+3]
            #    cols = st.columns(3)
            for i in range(0, len(games), 2):
                row_games = games[i:i+2]
                cols = st.columns(2)

                for col_idx, game in enumerate(row_games):
                    away_team = game["away_team"]
                    home_team = game["home_team"]

                    away_lineup = get_lineup(away_team)
                    home_lineup = get_lineup(home_team)

                    away_pitcher = get_pitcher_for_team(away_team)
                    home_pitcher = get_pitcher_for_team(home_team)

                    away_status_text, away_status_class = lineup_status(away_lineup) if not away_lineup.empty else ("NOT CONFIRMED", "not-confirmed")
                    home_status_text, home_status_class = lineup_status(home_lineup) if not home_lineup.empty else ("NOT CONFIRMED", "not-confirmed")

                    weather = get_weather(away_team, home_team)
                    away_row = game["away_row"]
                    home_row = game["home_row"]

                    away_ml, away_proj = fmt_moneyline_with_total(away_row)
                    home_ml, home_proj = fmt_moneyline_with_total(home_row)
                    ou_txt = fmt_ou(game["overunder"])

                    with cols[col_idx]:
                        if weather is not None:
                            weather_html = clean_html(f"""
                                <div class="slate-weather">
                                    <div><b>Temp:</b> {weather['temp']} &nbsp;&nbsp; <b>Rain:</b> {weather['rain']}</div>
                                    <div><b>Wind:</b> {weather['wind']}</div>
                                </div>
                            """)
                        else:
                            weather_html = clean_html("""
                                <div class="slate-weather">
                                    <div><b>Temp:</b> — &nbsp;&nbsp; <b>Rain:</b> —</div>
                                    <div><b>Wind:</b> —</div>
                                </div>
                            """)

                        away_bg_class = "confirmed-bg" if away_status_class == "confirmed" else ""
                        home_bg_class = "confirmed-bg" if home_status_class == "confirmed" else ""

                        away_rows_html = ""
                        if away_lineup.empty:
                            away_rows_html = '<div class="small-muted">No lineup available.</div>'
                        else:
                            for _, r in away_lineup.sort_values("LU").iterrows():
                                spot = "" if pd.isna(r.get("LU")) else int(r["LU"])
                                sal_txt = fmt_salary(r.get("Sal"))
                                away_rows_html += clean_html(f"""
                                    <div class="line-row">
                                        <div class="line-spot">{spot}</div>
                                        <div class="line-player">{r.get('Hitter','')}</div>
                                        <div class="line-pos">{r.get('Pos','')}</div>
                                        <div class="line-sal">{sal_txt}</div>
                                    </div>
                                """)

                        home_rows_html = ""
                        if home_lineup.empty:
                            home_rows_html = '<div class="small-muted">No lineup available.</div>'
                        else:
                            for _, r in home_lineup.sort_values("LU").iterrows():
                                spot = "" if pd.isna(r.get("LU")) else int(r["LU"])
                                sal_txt = fmt_salary(r.get("Sal"))
                                home_rows_html += clean_html(f"""
                                    <div class="line-row">
                                        <div class="line-spot">{spot}</div>
                                        <div class="line-player">{r.get('Hitter','')}</div>
                                        <div class="line-pos">{r.get('Pos','')}</div>
                                        <div class="line-sal">{sal_txt}</div>
                                    </div>
                                """)

                        card_html = f"""
                        <html>
                        <head>
                        <style>
                            body {{
                                margin: 0;
                                padding: 0;
                                background: white;
                                font-family: Arial, sans-serif;
                            }}
                            .slate-card {{
                                border: 1px solid #d9d9d9;
                                border-radius: 14px;
                                background: white;
                                overflow: hidden;
                                box-shadow: 0 1px 4px rgba(0,0,0,.06);
                            }}
                            .slate-header {{
                                background: #f7f7f7;
                                padding: 12px 14px 8px 14px;
                                border-bottom: 1px solid #e6e6e6;
                            }}
                            .slate-time {{
                                font-size: 13px;
                                color: #666;
                                font-weight: 600;
                                margin-bottom: 8px;
                            }}
                            .slate-matchup {{
                                display: grid;
                                grid-template-columns: 1fr 40px 1fr;
                                align-items: center;
                                font-weight: 700;
                                font-size: 18px;
                            }}
                            .away-team {{
                                text-align: left;
                            }}
                            .at-sign {{
                                text-align: center;
                            }}
                            .home-team {{
                                text-align: right;
                            }}
                            .slate-weather {{
                                background: #eef8ee;
                                padding: 10px 14px;
                                border-bottom: 1px solid #e6e6e6;
                                font-size: 14px;
                                line-height: 1.4;
                            }}
                            .slate-betting {{
                                display: grid;
                                grid-template-columns: 1fr 0.9fr 1fr;
                                text-align: center;
                                border-bottom: 1px solid #e6e6e6;
                                background: #fbfbfb;
                            }}
                            .bet-box {{
                                padding: 12px 8px;
                            }}
                            .bet-main {{
                                font-weight: 800;
                                font-size: 28px;
                                color: #164a9c;
                                line-height: 1.1;
                            }}
                            .bet-sub {{
                                font-size: 13px;
                                color: #666;
                            }}
                            .team-sections {{
                                display: grid;
                                grid-template-columns: 1fr 1fr;
                            }}
                            .team-col {{
                                border-right: 1px solid #ededed;
                            }}
                            .team-col:last-child {{
                                border-right: none;
                            }}
                            .pitcher-box {{
                                text-align: center;
                                padding: 14px 10px 10px 10px;
                                min-height: 78px;
                            }}
                            .pitcher-name {{
                                font-size: 17px;
                                font-weight: 700;
                                color: #444;
                            }}
                            .pitcher-meta {{
                                font-size: 14px;
                                color: #666;
                            }}
                            .lineup-status-confirmed {{
                                background: #1f8f4e;
                                color: white;
                                font-weight: 700;
                                font-size: 13px;
                                padding: 7px 12px;
                            }}
                            .lineup-status-not-confirmed {{
                                background: #e05353;
                                color: white;
                                font-weight: 700;
                                font-size: 13px;
                                padding: 7px 12px;
                            }}
                            .lineup-list {{
                                background: #faeded;
                                padding: 10px 14px 14px 14px;
                                min-height: 310px;
                            }}
                            .lineup-list.confirmed-bg {{
                                background: #eef7ef;
                            }}
                            .line-row {{
                                display: grid;
                                grid-template-columns: 20px 1fr auto auto;
                                gap: 8px;
                                align-items: baseline;
                                margin-bottom: 6px;
                                font-size: 15px;
                            }}
                            .line-spot {{
                                color: #666;
                            }}
                            .line-player {{
                                font-weight: 600;
                                color: #444;
                            }}
                            .line-pos {{
                                color: #777;
                                font-size: 13px;
                            }}
                            .line-sal {{
                                color: #17853a;
                                font-weight: 700;
                                font-size: 13px;
                            }}
                            .small-muted {{
                                color: #777;
                                font-size: 13px;
                            }}
                        </style>
                        </head>
                        <body>
                        <div class="slate-card">
                            <div class="slate-header">
                                <div class="slate-time">{game.get('game_time','')} ET | {game.get('park','')}</div>
                                <div class="slate-matchup">
                                    <div class="away-team">{away_team}</div>
                                    <div class="at-sign">@</div>
                                    <div class="home-team">{home_team}</div>
                                </div>
                            </div>

                            {weather_html}

                            <div class="slate-betting">
                                <div class="bet-box">
                                    <div class="bet-main">{away_proj}</div>
                                    <div class="bet-sub">{away_ml} ML</div>
                                </div>
                                <div class="bet-box">
                                    <div class="bet-main">{ou_txt}</div>
                                    <div class="bet-sub">O/U</div>
                                </div>
                                <div class="bet-box">
                                    <div class="bet-main">{home_proj}</div>
                                    <div class="bet-sub">{home_ml} ML</div>
                                </div>
                            </div>

                            <div class="team-sections">
                                <div class="team-col">
                                    <div class="pitcher-box">
                                        <div class="pitcher-name">{away_pitcher['Pitcher']}</div>
                                        <div class="pitcher-meta">Probable SP &nbsp;&nbsp; {fmt_salary(away_pitcher['Sal'])}</div>
                                    </div>
                                    <div class="lineup-status-{away_status_class}">{away_status_text}</div>
                                    <div class="lineup-list {away_bg_class}">
                                        {away_rows_html}
                                    </div>
                                </div>

                                <div class="team-col">
                                    <div class="pitcher-box">
                                        <div class="pitcher-name">{home_pitcher['Pitcher']}</div>
                                        <div class="pitcher-meta">Probable SP &nbsp;&nbsp; {fmt_salary(home_pitcher['Sal'])}</div>
                                    </div>
                                    <div class="lineup-status-{home_status_class}">{home_status_text}</div>
                                    <div class="lineup-list {home_bg_class}">
                                        {home_rows_html}
                                    </div>
                                </div>
                            </div>
                        </div>
                        </body>
                        </html>
                        """

                        components.html(card_html, height=760, scrolling=False)

                        #st.markdown(card_html, unsafe_allow_html=True)
                        components.html(card_html, height=760, scrolling=False)

    if tab == "DFS Optimizer":
        import io
        import math
        import random
        import numpy as np
        import pandas as pd
        import streamlit as st


        require_pro()

        def load_daily_projections_data_optimizer():
            fp = _DATA_DIR
            daily_weather_report  = pd.read_csv(f'{fp}/daily_weather_2026.csv')
            dfs_pitcher_proj = pd.read_csv(f'{fp}/Tableau_DailyPitcherProj.csv')
            dfs_hitter_proj = pd.read_csv(f'{fp}/Tableau_DailyHitterProj.csv')
            return dfs_hitter_proj, dfs_pitcher_proj, daily_weather_report

        dfs_hitter_proj, dfs_pitcher_proj, daily_weather_report = load_daily_projections_data_optimizer()

        slate_options = list(dfs_hitter_proj['MainSlate'].unique())
        ##

        try:
            import pulp
        except Exception:
            st.error("The DFS Optimizer requires the 'pulp' package. Install it with: pip install pulp")
            st.stop()

        # =========================================================
        # CONFIG / HELPERS
        # =========================================================
        DK_SALARY_CAP = 50000
        DEFAULT_MIN_SALARY = 49000
        DEFAULT_MAX_SALARY = 50000
        DEFAULT_VARIANCE = 5.0
        DEFAULT_GLOBAL_MAX = 40
        DEFAULT_NUM_LINEUPS = 20
        DEFAULT_UNIQUE_PLAYERS = 2
        DEFAULT_MAX_HITTERS_PER_TEAM = 5

        ROSTER_SLOTS = ["P1", "P2", "C", "1B", "2B", "3B", "SS", "OF1", "OF2", "OF3"]
        HITTER_SLOTS = ["C", "1B", "2B", "3B", "SS", "OF1", "OF2", "OF3"]

        def _safe_int(x, default=0):
            try:
                if pd.isna(x):
                    return default
                return int(float(x))
            except Exception:
                return default

        def _safe_float(x, default=0.0):
            try:
                if pd.isna(x):
                    return default
                return float(x)
            except Exception:
                return default

        def _norm_team(x):
            if pd.isna(x):
                return ""
            return str(x).strip().upper()

        def _split_positions(pos_str):
            if pd.isna(pos_str):
                return []
            s = str(pos_str).strip().upper().replace(" ", "")
            return [x for x in s.split("/") if x]

        def _eligible_slots(pos_list, is_pitcher=False):
            if is_pitcher:
                return ["P1", "P2"]
            slots = []
            if "C" in pos_list:
                slots.append("C")
            if "1B" in pos_list:
                slots.append("1B")
            if "2B" in pos_list:
                slots.append("2B")
            if "3B" in pos_list:
                slots.append("3B")
            if "SS" in pos_list:
                slots.append("SS")
            if "OF" in pos_list:
                slots.extend(["OF1", "OF2", "OF3"])
            return slots

        def _rain_style(val):
            try:
                v = float(val)
            except Exception:
                return ""
            if v > 40:
                return "background-color: #ffcccc; color: #8b0000; font-weight: bold;"
            return ""

        def _weather_row_label(row):
            return f"{row['away_team']} @ {row['home_team']}"

        @st.cache_data(ttl=300, show_spinner=False)
        def prep_optimizer_data(dfs_hitter_proj, dfs_pitcher_proj, daily_weather_report):
            h = dfs_hitter_proj.copy()
            p = dfs_pitcher_proj.copy()
            w = daily_weather_report.copy()

            # -------------------------
            # HITTERS
            # -------------------------
            if "Unnamed: 0" in h.columns:
                h = h.drop(columns=["Unnamed: 0"], errors="ignore")

            h["Player"] = h["Hitter"].astype(str)
            h["Team"] = h["Team"].apply(_norm_team)
            h["OppTeam"] = h["Opp"].apply(_norm_team)
            h["Salary"] = pd.to_numeric(h["Sal"], errors="coerce").fillna(0).astype(int)
            h["Proj"] = pd.to_numeric(h["DKPts"], errors="coerce").fillna(0.0)
            h["Floor"] = pd.to_numeric(h["Floor"], errors="coerce").fillna(0.0)
            h["Ceil"] = pd.to_numeric(h["Ceil"], errors="coerce").fillna(0.0)
            h["Ownership"] = pd.to_numeric(h.get("Ownership", 0), errors="coerce").fillna(0.0)
            h["TopPlayScore"] = pd.to_numeric(h.get("TopPlayScore", 0), errors="coerce").fillna(0.0)
            h["DKID"] = pd.to_numeric(h.get("DKID", np.nan), errors="coerce")
            h["MainSlate"] = h.get("MainSlate", "").astype(str)
            h["Confirmed LU"] = h.get("Confirmed LU", "").astype(str)
            h["Positions"] = h["Pos"].apply(_split_positions)
            h["EligibleSlots"] = h["Positions"].apply(lambda x: _eligible_slots(x, False))
            h["IsPitcher"] = 0
            h["Game"] = h["Team"] + " @ " + h["OppTeam"]

            # only usable hitters with at least one legal DK slot
            h = h[h["EligibleSlots"].apply(len) > 0].copy()

            # -------------------------
            # PITCHERS
            # -------------------------
            if "Unnamed: 0" in p.columns:
                p = p.drop(columns=["Unnamed: 0"], errors="ignore")

            p["Player"] = p["Pitcher"].astype(str)
            p["Team"] = p["Team"].apply(_norm_team)
            p["OppTeam"] = p["Opponent"].apply(_norm_team)
            p["Salary"] = pd.to_numeric(p["Sal"], errors="coerce").fillna(0).astype(int)
            p["Proj"] = pd.to_numeric(p["DKPts"], errors="coerce").fillna(0.0)
            p["Floor"] = pd.to_numeric(p["Floor"], errors="coerce").fillna(0.0)
            p["Ceil"] = pd.to_numeric(p["Ceil"], errors="coerce").fillna(0.0)
            p["Ownership"] = pd.to_numeric(p.get("Ownership", 0), errors="coerce").fillna(0.0)
            p["TopPlayScore"] = pd.to_numeric(p.get("Pitcher_Ownership", 0), errors="coerce").fillna(0.0)
            p["DKID"] = pd.to_numeric(p.get("DKID", np.nan), errors="coerce")
            p["MainSlate"] = p.get("MainSlate", "").astype(str)
            p["Positions"] = [["P"]] * len(p)
            p["EligibleSlots"] = [["P1", "P2"]] * len(p)
            p["IsPitcher"] = 1
            p["Game"] = p["Team"] + " @ " + p["OppTeam"]

            # -------------------------
            # WEATHER
            # -------------------------
            if "Unnamed: 0" in w.columns:
                w = w.drop(columns=["Unnamed: 0"], errors="ignore")

            for c in ["away_team", "home_team"]:
                if c in w.columns:
                    w[c] = w[c].apply(_norm_team)

            if "rain_prob_pct" in w.columns:
                w["rain_prob_pct"] = pd.to_numeric(w["rain_prob_pct"], errors="coerce").fillna(0)

            if "temp_f" in w.columns:
                w["temp_f"] = pd.to_numeric(w["temp_f"], errors="coerce")

            # add opponent weather tags
            w["GameLabel"] = w.apply(_weather_row_label, axis=1)

            keep_cols_hit = [
                "Player", "Team", "OppTeam", "Salary", "Proj", "Floor", "Ceil", "Ownership",
                "TopPlayScore", "DKID", "MainSlate", "Positions", "EligibleSlots", "IsPitcher",
                "Game", "Pos", "LU", "OppSP", "Park", "Confirmed LU"
            ]
            keep_cols_pitch = [
                "Player", "Team", "OppTeam", "Salary", "Proj", "Floor", "Ceil", "Ownership",
                "TopPlayScore", "DKID", "MainSlate", "Positions", "EligibleSlots", "IsPitcher",
                "Game", "PC", "HomeTeam"
            ]

            h = h[[c for c in keep_cols_hit if c in h.columns]].copy()
            p = p[[c for c in keep_cols_pitch if c in p.columns]].copy()

            h["SourceType"] = "H"
            p["SourceType"] = "P"

            h["DefaultLike"] = False
            p["DefaultLike"] = False
            h["DefaultLock"] = False
            p["DefaultLock"] = False
            h["DefaultExclude"] = False
            p["DefaultExclude"] = False

            return h, p, w

        hitter_base, pitcher_base, weather_df = prep_optimizer_data(
            dfs_hitter_proj=dfs_hitter_proj,
            dfs_pitcher_proj=dfs_pitcher_proj,
            daily_weather_report=daily_weather_report
        )

        # =========================================================
        # HEADER
        # =========================================================
        st.subheader("MLB DFS Optimizer")
        st.caption("DraftKings MLB optimizer with stacking, exposures, randomization, weather, and CSV export.")

        # =========================================================
        # SLATE FILTERING
        # =========================================================
        all_teams = sorted(set(hitter_base["Team"].dropna().unique()).union(set(pitcher_base["Team"].dropna().unique())))

        top1, top2, top3, top4 = st.columns([1.2, 1.2, 1.2, 1.2])

        with top1:
            slate_mode = st.selectbox(
                "Slate Filter",
                #["Main", "All", "Custom Team List"],
                slate_options+['Custom Team List'],
                index=0,
                key="dfs_opto_slate_mode"
            )

        selected_slate_teams = []
        if slate_mode == "Custom Team List":
            with top2:
                selected_slate_teams = st.multiselect(
                    "Teams In Slate",
                    options=all_teams,
                    default=all_teams[:10] if len(all_teams) >= 10 else all_teams,
                    key="dfs_opto_custom_slate_teams"
                )

        def apply_slate_filter(df):
            out = df.copy()
            if slate_mode == "Main":
                out = out[out["MainSlate"].astype(str).str.upper().eq("MAIN")].copy()
            elif slate_mode == "Early":
                out = out[out["MainSlate"].astype(str).str.upper().eq("EARLY")].copy()
            elif slate_mode == "Custom Team List":
                if selected_slate_teams:
                    out = out[out["Team"].isin(selected_slate_teams)].copy()
                else:
                    out = out.iloc[0:0].copy()
            return out

        hitters = apply_slate_filter(hitter_base)
        pitchers = apply_slate_filter(pitcher_base)

        st.markdown(f"Teams on slate: {list(hitters['Team'].unique())}", unsafe_allow_html=True)

        if len(hitters) == 0 or len(pitchers) == 0:
            st.warning("No players available after slate filtering.")
            st.stop()

        available_hitter_teams = sorted(hitters["Team"].dropna().unique().tolist())
        available_pitcher_teams = sorted(pitchers["Team"].dropna().unique().tolist())
        available_teams = sorted(set(available_hitter_teams).union(set(available_pitcher_teams)))

        # =========================================================
        # WEATHER
        # =========================================================
        with st.expander("Weather Report", expanded=False):
            if len(weather_df) == 0:
                st.info("No weather report loaded.")
            else:
                weather_show = weather_df.copy()

                if slate_mode == "Main":
                    slate_teams_for_weather = set(available_teams)
                    weather_show = weather_show[
                        weather_show["away_team"].isin(slate_teams_for_weather) |
                        weather_show["home_team"].isin(slate_teams_for_weather)
                    ].copy()
                elif slate_mode == "Custom Team List":
                    slate_teams_for_weather = set(selected_slate_teams)
                    weather_show = weather_show[
                        weather_show["away_team"].isin(slate_teams_for_weather) |
                        weather_show["home_team"].isin(slate_teams_for_weather)
                    ].copy()

                if len(weather_show) > 0:
                    weather_show = weather_show[
                        ["away_team", "home_team", "venue_name", "game_time", "temp_f", "rain_prob_pct", "wind_summary", "wind_effect", "out_component_mph"]
                    ].copy()

                    st.dataframe(
                        weather_show.style.map(
                            _rain_style, subset=["rain_prob_pct"]
                        ),
                        use_container_width=True,
                        hide_index=True
                    )
                    risky = weather_show[weather_show["rain_prob_pct"] > 40]
                    if len(risky) > 0:
                        st.error("Heavy rain risk (>40%) detected for: " + ", ".join([f"{r.away_team}@{r.home_team}" for _, r in risky.iterrows()]))
                else:
                    st.info("No weather rows matched the current slate filter.")

        # =========================================================
        # GLOBAL SETTINGS
        # =========================================================
        st.markdown("### Build Settings")
        c1, c2, c3, c4, c5, c6 = st.columns(6)

        with c1:
            num_lineups = st.number_input("Lineups", min_value=1, max_value=150, value=DEFAULT_NUM_LINEUPS, step=1)
        with c2:
            variance_pct = st.number_input("Projection Variance %", min_value=0.0, max_value=50.0, value=DEFAULT_VARIANCE, step=0.5)
        with c3:
            global_max_exp = st.number_input("Global Max Exposure %", min_value=1, max_value=100, value=DEFAULT_GLOBAL_MAX, step=1)
        with c4:
            min_unique_players = st.number_input("Unique Players Across Lineups", min_value=1, max_value=9, value=DEFAULT_UNIQUE_PLAYERS, step=1)
        with c5:
            min_salary = st.number_input("Minimum Salary", min_value=0, max_value=DK_SALARY_CAP, value=DEFAULT_MIN_SALARY, step=100)
        with c6:
            max_salary = st.number_input("Maximum Salary", min_value=0, max_value=DK_SALARY_CAP, value=DEFAULT_MAX_SALARY, step=100)

        c7, c8, c9, c10 = st.columns(4)
        with c7:
            block_batters_vs_pitchers = st.checkbox("Block Hitters vs Opposing Pitchers", value=True)
        with c8:
            max_hitters_per_team = st.number_input("Max Hitters Per Team", min_value=3, max_value=5, value=DEFAULT_MAX_HITTERS_PER_TEAM, step=1)
        with c9:
            allow_unconfirmed_lineups = st.checkbox("Allow Unconfirmed Hitters", value=True)
        with c10:
            random_seed = st.number_input("Random Seed", min_value=0, max_value=999999, value=42, step=1)

        # =========================================================
        # STACK SETTINGS
        # =========================================================
        st.markdown("### Stacking Preferences")
        s1, s2 = st.columns(2)

        with s1:
            st.markdown("**Primary Stack**")
            use_primary_stack = st.checkbox("Use Primary Stack", value=False, key="use_primary_stack")
            primary_stack_size = st.selectbox("Primary Stack Size", [4, 5], index=1, key="primary_stack_size")
            primary_stack_teams = st.multiselect(
                "Eligible Primary Stack Teams",
                options=available_hitter_teams,
                default=[],
                key="primary_stack_teams"
            )

        with s2:
            st.markdown("**Secondary Stack**")
            use_secondary_stack = st.checkbox("Use Secondary Stack", value=False, key="use_secondary_stack")
            secondary_stack_size = st.selectbox("Secondary Stack Size", [2, 3, 4], index=1, key="secondary_stack_size")
            secondary_stack_teams = st.multiselect(
                "Eligible Secondary Stack Teams",
                options=available_hitter_teams,
                default=[],
                key="secondary_stack_teams"
            )

        team_offense_excludes = st.multiselect(
            "Exclude Team Offenses",
            options=available_hitter_teams,
            default=[],
            help="Excludes hitters only. Pitchers from those teams can still be used."
        )

        # =========================================================
        # PITCHER CONTROL SCREEN
        # =========================================================
        st.markdown("### Pitcher Controls")
        pitcher_control_df = pitchers[[
            "Player", "Team", "OppTeam", "Salary", "Proj", "Floor", "Ceil", "Ownership", "DKID"
        ]].copy()

        pitcher_control_df["Lock"] = False
        pitcher_control_df["Exclude"] = False
        pitcher_control_df["Like"] = False
        pitcher_control_df["MaxExp%"] = global_max_exp

        pitcher_control_df = st.data_editor(
            pitcher_control_df,
            use_container_width=True,
            hide_index=True,
            key="pitcher_control_editor",
            num_rows="fixed",
            disabled=["Player", "Team", "OppTeam", "Salary", "Proj", "Floor", "Ceil", "Ownership", "DKID"],
            column_config={
                "MaxExp%": st.column_config.NumberColumn(min_value=0, max_value=100, step=1),
                "Lock": st.column_config.CheckboxColumn(),
                "Exclude": st.column_config.CheckboxColumn(),
                "Like": st.column_config.CheckboxColumn(),
            }
        )

        # =========================================================
        # HITTER / PLAYER CONTROL SCREEN
        # =========================================================
        st.markdown("### Hitter Controls")
        hleft, hright = st.columns([1, 2])

        with hleft:
            hitter_team_view = st.selectbox("Team View", options=["ALL"] + available_hitter_teams, index=0)
            hitter_search = st.text_input("Search Hitters", value="")
            exclude_all_unconfirmed = st.checkbox("Exclude All Unconfirmed Hitters", value=False)
            sort_hitters_by = st.selectbox("Sort Hitters By", ["Proj", "TopPlayScore", "Salary", "Ownership", "Ceil"], index=0)

        hitter_control_df = hitters[[
            "Player", "Team", "OppTeam", "Salary", "Proj", "Floor", "Ceil", "Ownership", "TopPlayScore", "DKID", "Pos", "LU", "Confirmed LU"
        ]].copy()

        if hitter_team_view != "ALL":
            hitter_control_df = hitter_control_df[hitter_control_df["Team"] == hitter_team_view].copy()

        if hitter_search.strip():
            hitter_control_df = hitter_control_df[hitter_control_df["Player"].str.contains(hitter_search, case=False, na=False)].copy()

        hitter_control_df = hitter_control_df.sort_values(sort_hitters_by, ascending=False).copy()

        hitter_control_df["Lock"] = False
        hitter_control_df["Exclude"] = False
        hitter_control_df["Like"] = False
        hitter_control_df["MaxExp%"] = global_max_exp

        hitter_control_df = st.data_editor(
            hitter_control_df,
            use_container_width=True,
            hide_index=True,
            key="hitter_control_editor",
            num_rows="fixed",
            disabled=["Player", "Team", "OppTeam", "Salary", "Proj", "Floor", "Ceil", "Ownership", "TopPlayScore", "DKID", "Pos", "LU", "Confirmed LU"],
            column_config={
                "MaxExp%": st.column_config.NumberColumn(min_value=0, max_value=100, step=1),
                "Lock": st.column_config.CheckboxColumn(),
                "Exclude": st.column_config.CheckboxColumn(),
                "Like": st.column_config.CheckboxColumn(),
            }
        )

        # =========================================================
        # BUILD PLAYER MASTER
        # =========================================================
        player_rows = []

        # hitters
        #hitter_edit_lookup = hitter_control_df.set_index("Player")[["Lock", "Exclude", "Like", "MaxExp%"]].to_dict("index") if len(hitter_control_df) > 0 else {}
        hitter_edit_lookup = (
            hitter_control_df
            .drop_duplicates(subset=["Player"], keep="last")
            .set_index("Player")[["Lock", "Exclude", "Like", "MaxExp%"]]
            .to_dict("index")
        ) if len(hitter_control_df) > 0 else {}
        # for hitters not visible in filtered editor, keep defaults
        for _, r in hitters.iterrows():
            edit = hitter_edit_lookup.get(r["Player"], {"Lock": False, "Exclude": False, "Like": False, "MaxExp%": global_max_exp})
            is_excluded = bool(edit["Exclude"])
            if r["Team"] in team_offense_excludes:
                is_excluded = True
            if exclude_all_unconfirmed and str(r.get("Confirmed LU", "")).upper() != "Y":
                is_excluded = True
            player_rows.append({
                "Player": r["Player"],
                "Team": r["Team"],
                "OppTeam": r["OppTeam"],
                "IsPitcher": 0,
                "Salary": _safe_int(r["Salary"]),
                "Proj": _safe_float(r["Proj"]),
                "Floor": _safe_float(r["Floor"]),
                "Ceil": _safe_float(r["Ceil"]),
                "Ownership": _safe_float(r["Ownership"]),
                "TopPlayScore": _safe_float(r["TopPlayScore"]),
                "DKID": r["DKID"],
                "EligibleSlots": r["EligibleSlots"],
                "Lock": bool(edit["Lock"]),
                "Exclude": bool(is_excluded),
                "Like": bool(edit["Like"]),
                "MaxExpPct": _safe_int(edit["MaxExp%"], global_max_exp),
                "PosStr": r.get("Pos", ""),
                "Order": r.get("LU", np.nan),
                "ConfirmedLU": r.get("Confirmed LU", "")
            })

        # pitchers
        #pitcher_edit_lookup = pitcher_control_df.set_index("Player")[["Lock", "Exclude", "Like", "MaxExp%"]].to_dict("index") if len(pitcher_control_df) > 0 else {}
        pitcher_edit_lookup = (
            pitcher_control_df
            .drop_duplicates(subset=["Player"], keep="last")
            .set_index("Player")[["Lock", "Exclude", "Like", "MaxExp%"]]
            .to_dict("index")
        ) if len(pitcher_control_df) > 0 else {}
        for _, r in pitchers.iterrows():
            edit = pitcher_edit_lookup.get(r["Player"], {"Lock": False, "Exclude": False, "Like": False, "MaxExp%": global_max_exp})
            player_rows.append({
                "Player": r["Player"],
                "Team": r["Team"],
                "OppTeam": r["OppTeam"],
                "IsPitcher": 1,
                "Salary": _safe_int(r["Salary"]),
                "Proj": _safe_float(r["Proj"]),
                "Floor": _safe_float(r["Floor"]),
                "Ceil": _safe_float(r["Ceil"]),
                "Ownership": _safe_float(r["Ownership"]),
                "TopPlayScore": _safe_float(r["TopPlayScore"]),
                "DKID": r["DKID"],
                "EligibleSlots": r["EligibleSlots"],
                "Lock": bool(edit["Lock"]),
                "Exclude": bool(edit["Exclude"]),
                "Like": bool(edit["Like"]),
                "MaxExpPct": _safe_int(edit["MaxExp%"], global_max_exp),
                "PosStr": "P",
                "Order": np.nan,
                "ConfirmedLU": ""
            })

        pool = pd.DataFrame(player_rows).drop_duplicates(subset=["Player", "Team", "IsPitcher"]).reset_index(drop=True)

        # remove excluded and invalid salary/proj rows
        pool = pool[~pool["Exclude"]].copy()
        pool = pool[(pool["Salary"] > 0) & (pool["Proj"] > 0)].copy()

        # projection boost for Like
        pool["BaseProj"] = np.where(pool["Like"], pool["Proj"] * 1.10, pool["Proj"])

        # warning area for missing DKIDs
        missing_dkid_pool = pool[pool["DKID"].isna()].copy()
        if len(missing_dkid_pool) > 0:
            st.warning(
                "MISSING DK IDs for: "
                + ", ".join(sorted(missing_dkid_pool["Player"].tolist()))
                + ". THESE WILL NOT BE ABLE TO BE USED IN EXPORTED LINEUPS."
            )

        if len(pool) == 0:
            st.warning("No players left after applying your filters and excludes.")
            st.stop()

        # =========================================================
        # PRECHECKS
        # =========================================================
        locked_players = pool[pool["Lock"]].copy()
        if len(locked_players) > 10:
            st.error("You have more than 10 locked players.")
            st.stop()

        locked_pitchers = locked_players[locked_players["IsPitcher"] == 1]
        if len(locked_pitchers) > 2:
            st.error("You cannot lock more than 2 pitchers.")
            st.stop()

        # =========================================================
        # OPTIMIZER
        # =========================================================
        def build_single_lineup(
            pool_df,
            lineup_idx,
            existing_lineups,
            current_counts,
            total_lineups,
            global_max_exp,
            variance_pct,
            min_salary,
            max_salary,
            min_unique_players,
            max_hitters_per_team,
            block_batters_vs_pitchers,
            use_primary_stack,
            primary_stack_size,
            primary_stack_teams,
            use_secondary_stack,
            secondary_stack_size,
            secondary_stack_teams,
            seed_base=42
        ):
            rng = np.random.default_rng(seed_base + lineup_idx + 1000)

            df = pool_df.copy()

            # randomized projections
            v = max(0.0, variance_pct) / 100.0
            noise = rng.uniform(1 - v, 1 + v, size=len(df))
            df["OptProj"] = df["BaseProj"] * noise

            # locked players should not get randomized downward in a way that hurts them
            df.loc[df["Lock"], "OptProj"] = df.loc[df["Lock"], "BaseProj"]

            # exposure caps
            df["MaxAppearances"] = np.where(
                df["Lock"],
                total_lineups,
                np.ceil(np.minimum(df["MaxExpPct"], global_max_exp) / 100.0 * total_lineups).astype(int)
            )
            df["CurrentCount"] = df["Player"].map(current_counts).fillna(0).astype(int)

            # players already maxed out are unavailable
            df = df[df["CurrentCount"] < df["MaxAppearances"]].copy()

            if len(df) == 0:
                return None, "No players available after exposure caps."

            # enough pitchers/hitters?
            if (df["IsPitcher"] == 1).sum() < 2:
                return None, "Not enough pitchers available."
            if (df["IsPitcher"] == 0).sum() < 8:
                return None, "Not enough hitters available."

            # player ids
            player_ids = df.index.tolist()

            # assignment vars
            x = {}
            prob = pulp.LpProblem(f"DK_MLB_Lineup_{lineup_idx}", pulp.LpMaximize)

            for i in player_ids:
                for slot in df.loc[i, "EligibleSlots"]:
                    x[(i, slot)] = pulp.LpVariable(f"x_{i}_{slot}", lowBound=0, upBound=1, cat="Binary")

            # objective
            prob += pulp.lpSum(df.loc[i, "OptProj"] * x[(i, slot)] for (i, slot) in x.keys())

            # exactly one player per roster slot
            for slot in ROSTER_SLOTS:
                slot_vars = [x[(i, slot)] for i in player_ids if (i, slot) in x]
                prob += pulp.lpSum(slot_vars) == 1, f"fill_{slot}"

            # each player at most once
            for i in player_ids:
                i_vars = [x[(i, slot)] for slot in df.loc[i, "EligibleSlots"] if (i, slot) in x]
                prob += pulp.lpSum(i_vars) <= 1, f"one_slot_per_player_{i}"

            # salary
            prob += pulp.lpSum(df.loc[i, "Salary"] * x[(i, slot)] for (i, slot) in x.keys()) <= max_salary, "max_salary"
            prob += pulp.lpSum(df.loc[i, "Salary"] * x[(i, slot)] for (i, slot) in x.keys()) >= min_salary, "min_salary"

            # exactly 2 pitchers / 8 hitters implicit via slots, but can still reinforce hitter team limits
            hitter_ids = [i for i in player_ids if df.loc[i, "IsPitcher"] == 0]
            pitcher_ids = [i for i in player_ids if df.loc[i, "IsPitcher"] == 1]

            # locked players
            for i in player_ids:
                if bool(df.loc[i, "Lock"]):
                    prob += pulp.lpSum([x[(i, s)] for s in df.loc[i, "EligibleSlots"] if (i, s) in x]) == 1, f"lock_{i}"

            # max hitters per team
            hitter_teams = sorted(df.loc[hitter_ids, "Team"].dropna().unique().tolist())
            for team in hitter_teams:
                team_hitter_vars = []
                for i in hitter_ids:
                    if df.loc[i, "Team"] == team:
                        for s in df.loc[i, "EligibleSlots"]:
                            if (i, s) in x:
                                team_hitter_vars.append(x[(i, s)])
                if team_hitter_vars:
                    prob += pulp.lpSum(team_hitter_vars) <= max_hitters_per_team, f"max_hitters_{team}"

            # no hitters against selected pitchers
            if block_batters_vs_pitchers:
                for p_i in pitcher_ids:
                    opp_team = df.loc[p_i, "OppTeam"]
                    p_var_sum = pulp.lpSum([x[(p_i, s)] for s in df.loc[p_i, "EligibleSlots"] if (p_i, s) in x])

                    opp_hitters = [i for i in hitter_ids if df.loc[i, "Team"] == opp_team]
                    if opp_hitters:
                        opp_vars = []
                        for h_i in opp_hitters:
                            for s in df.loc[h_i, "EligibleSlots"]:
                                if (h_i, s) in x:
                                    opp_vars.append(x[(h_i, s)])
                        if opp_vars:
                            prob += pulp.lpSum(opp_vars) <= 8 * (1 - p_var_sum), f"block_opp_hitters_vs_pitcher_{p_i}"

            # stack constraints
            # primary stack
            primary_team_vars = {}
            if use_primary_stack and len(primary_stack_teams) > 0:
                eligible_primary_teams = [t for t in primary_stack_teams if t in hitter_teams]
                if len(eligible_primary_teams) > 0:
                    for t in eligible_primary_teams:
                        primary_team_vars[t] = pulp.LpVariable(f"primary_{t}_{lineup_idx}", lowBound=0, upBound=1, cat="Binary")
                    prob += pulp.lpSum(primary_team_vars.values()) == 1, f"choose_primary_stack_{lineup_idx}"

                    for t in eligible_primary_teams:
                        team_vars = []
                        for i in hitter_ids:
                            if df.loc[i, "Team"] == t:
                                for s in df.loc[i, "EligibleSlots"]:
                                    if (i, s) in x:
                                        team_vars.append(x[(i, s)])
                        if team_vars:
                            prob += pulp.lpSum(team_vars) >= primary_stack_size * primary_team_vars[t], f"primary_stack_min_{t}_{lineup_idx}"

            # secondary stack
            secondary_team_vars = {}
            if use_secondary_stack and len(secondary_stack_teams) > 0:
                eligible_secondary_teams = [t for t in secondary_stack_teams if t in hitter_teams]
                if len(eligible_secondary_teams) > 0:
                    for t in eligible_secondary_teams:
                        secondary_team_vars[t] = pulp.LpVariable(f"secondary_{t}_{lineup_idx}", lowBound=0, upBound=1, cat="Binary")
                    prob += pulp.lpSum(secondary_team_vars.values()) == 1, f"choose_secondary_stack_{lineup_idx}"

                    for t in eligible_secondary_teams:
                        team_vars = []
                        for i in hitter_ids:
                            if df.loc[i, "Team"] == t:
                                for s in df.loc[i, "EligibleSlots"]:
                                    if (i, s) in x:
                                        team_vars.append(x[(i, s)])
                        if team_vars:
                            prob += pulp.lpSum(team_vars) >= secondary_stack_size * secondary_team_vars[t], f"secondary_stack_min_{t}_{lineup_idx}"

            # no overlap between primary and secondary stack team
            if len(primary_team_vars) > 0 and len(secondary_team_vars) > 0:
                shared_teams = set(primary_team_vars.keys()).intersection(set(secondary_team_vars.keys()))
                for t in shared_teams:
                    prob += primary_team_vars[t] + secondary_team_vars[t] <= 1, f"no_stack_overlap_{t}_{lineup_idx}"

            # uniqueness vs prior lineups
            # require overlap <= 10 - min_unique_players
            for old_idx, old_lineup in enumerate(existing_lineups):
                old_players = set(old_lineup["Player"].tolist())
                overlap_vars = []
                for i in player_ids:
                    if df.loc[i, "Player"] in old_players:
                        for s in df.loc[i, "EligibleSlots"]:
                            if (i, s) in x:
                                overlap_vars.append(x[(i, s)])
                if overlap_vars:
                    prob += pulp.lpSum(overlap_vars) <= 10 - min_unique_players, f"uniq_vs_{old_idx}_{lineup_idx}"

            # solve
            solver = pulp.PULP_CBC_CMD(msg=False, warmStart=True)
            result = prob.solve(solver)

            if pulp.LpStatus[prob.status] != "Optimal":
                return None, f"Solver status: {pulp.LpStatus[prob.status]}"

            # read solution
            chosen = []
            for slot in ROSTER_SLOTS:
                found = None
                for i in player_ids:
                    if (i, slot) in x and pulp.value(x[(i, slot)]) == 1:
                        found = {
                            "Slot": slot,
                            "Player": df.loc[i, "Player"],
                            "Team": df.loc[i, "Team"],
                            "OppTeam": df.loc[i, "OppTeam"],
                            "IsPitcher": int(df.loc[i, "IsPitcher"]),
                            "Salary": int(df.loc[i, "Salary"]),
                            "Proj": float(df.loc[i, "BaseProj"]),
                            "OptProj": float(df.loc[i, "OptProj"]),
                            "DKID": df.loc[i, "DKID"],
                            "PosStr": df.loc[i, "PosStr"],
                        }
                        break
                if found is None:
                    return None, f"Could not assign slot {slot}."
                chosen.append(found)

            lineup_df = pd.DataFrame(chosen)
            return lineup_df, None

        # =========================================================
        # RUN OPTIMIZER
        # =========================================================
        st.markdown("### Build Lineups")
        run_build = st.button("Build DFS Lineups", type="primary", use_container_width=True)

        if run_build:
            random.seed(random_seed)
            np.random.seed(random_seed)

            results = []
            failures = []
            exposure_counts = {p: 0 for p in pool["Player"].tolist()}

            progress = st.progress(0, text="Starting optimizer...")
            status_box = st.empty()

            for i in range(num_lineups):
                status_box.info(f"Building lineup {i+1} of {num_lineups}...")

                lineup_df, err = build_single_lineup(
                    pool_df=pool,
                    lineup_idx=i,
                    existing_lineups=results,
                    current_counts=exposure_counts,
                    total_lineups=num_lineups,
                    global_max_exp=global_max_exp,
                    variance_pct=variance_pct,
                    min_salary=min_salary,
                    max_salary=max_salary,
                    min_unique_players=min_unique_players,
                    max_hitters_per_team=max_hitters_per_team,
                    block_batters_vs_pitchers=block_batters_vs_pitchers,
                    use_primary_stack=use_primary_stack,
                    primary_stack_size=primary_stack_size,
                    primary_stack_teams=primary_stack_teams,
                    use_secondary_stack=use_secondary_stack,
                    secondary_stack_size=secondary_stack_size,
                    secondary_stack_teams=secondary_stack_teams,
                    seed_base=random_seed
                )

                if lineup_df is None:
                    failures.append(f"Lineup {i+1}: {err}")
                    progress.progress((i + 1) / num_lineups, text=f"Failed lineup {i+1}/{num_lineups}")
                    continue

                results.append(lineup_df)
                for p_name in lineup_df["Player"].tolist():
                    exposure_counts[p_name] = exposure_counts.get(p_name, 0) + 1

                progress.progress((i + 1) / num_lineups, text=f"Built lineup {i+1}/{num_lineups}")

            status_box.empty()

            if len(results) == 0:
                st.error("No valid lineups were built.")
                if failures:
                    with st.expander("Failure Details"):
                        for f in failures[:50]:
                            st.write(f)
                st.stop()

            st.success(f"Built {len(results)} lineup(s).")

            if len(failures) > 0:
                st.warning(f"{len(failures)} lineup(s) failed to build.")
                with st.expander("Failure Details"):
                    for f in failures[:50]:
                        st.write(f)

            # =====================================================
            # DISPLAY LINEUPS
            # =====================================================
            display_rows = []
            export_rows = []
            lineups_with_missing_ids = []

            for idx, lu in enumerate(results, start=1):
                lu = lu.copy()
                lu["LineupNum"] = idx

                total_salary = int(lu["Salary"].sum())
                total_proj = round(lu["Proj"].sum(), 2)
                total_opt_proj = round(lu["OptProj"].sum(), 2)

                hitter_counts = lu[lu["IsPitcher"] == 0].groupby("Team").size().sort_values(ascending=False)
                stack_summary = " / ".join([f"{team} {cnt}" for team, cnt in hitter_counts.items()])

                for _, r in lu.iterrows():
                    display_rows.append({
                        "Lineup": idx,
                        "Slot": r["Slot"],
                        "Player": r["Player"],
                        "Team": r["Team"],
                        "Opp": r["OppTeam"],
                        "Salary": r["Salary"],
                        "Proj": round(r["Proj"], 2),
                        "OptProj": round(r["OptProj"], 2),
                        "DKID": r["DKID"],
                        "StackSummary": stack_summary,
                        "LineupSalary": total_salary,
                        "LineupProj": total_proj
                    })

                # DK export row in exact order P, P, C, 1B, 2B, 3B, SS, OF, OF, OF
                slot_map = {
                    "P1": None, "P2": None, "C": None, "1B": None, "2B": None, "3B": None, "SS": None,
                    "OF1": None, "OF2": None, "OF3": None
                }
                for _, r in lu.iterrows():
                    slot_map[r["Slot"]] = r["DKID"]

                if any(pd.isna(slot_map[s]) for s in slot_map):
                    lineups_with_missing_ids.append(idx)

                export_rows.append({
                    "P": slot_map["P1"],
                    "P_2": slot_map["P2"],
                    "C": slot_map["C"],
                    "1B": slot_map["1B"],
                    "2B": slot_map["2B"],
                    "3B": slot_map["3B"],
                    "SS": slot_map["SS"],
                    "OF": slot_map["OF1"],
                    "OF_2": slot_map["OF2"],
                    "OF_3": slot_map["OF3"],
                })

            lineup_display_df = pd.DataFrame(display_rows)
            export_df = pd.DataFrame(export_rows)

            st.markdown("### Built Lineups")
            lineup_summary_df = (
                lineup_display_df[["Lineup", "LineupSalary", "LineupProj", "StackSummary"]]
                .drop_duplicates()
                .sort_values(["Lineup"])
                .reset_index(drop=True)
            )
            st.dataframe(lineup_summary_df, use_container_width=True, hide_index=True)

            chosen_lineup_to_view = st.selectbox("View Lineup Details", options=sorted(lineup_display_df["Lineup"].unique().tolist()))
            st.dataframe(
                lineup_display_df[lineup_display_df["Lineup"] == chosen_lineup_to_view][
                    ["Slot", "Player", "Team", "Opp", "Salary", "Proj", "OptProj", "DKID"]
                ].sort_values("Slot"),
                use_container_width=True,
                hide_index=True
            )

            # =====================================================
            # EXPOSURES
            # =====================================================
            st.markdown("### Exposure Report")
            exposure_df = pd.DataFrame({
                "Player": list(exposure_counts.keys()),
                "Appearances": list(exposure_counts.values())
            })
            exposure_df = exposure_df.merge(
                pool[["Player", "Team", "IsPitcher", "BaseProj", "Salary", "DKID"]],
                on="Player",
                how="left"
            )
            exposure_df["Exposure%"] = np.where(len(results) > 0, (exposure_df["Appearances"] / len(results) * 100).round(1), 0.0)
            exposure_df = exposure_df[exposure_df["Appearances"] > 0].sort_values(["Exposure%", "BaseProj"], ascending=[False, False])
            st.dataframe(exposure_df, use_container_width=True, hide_index=True)

            # =====================================================
            # DKID WARNINGS / EXPORT
            # =====================================================
            export_has_missing = export_df.isna().any(axis=1).any()

            if len(lineups_with_missing_ids) > 0:
                st.warning(
                    "Some built lineups contain missing DK IDs and cannot be safely exported. "
                    f"Affected lineup numbers: {lineups_with_missing_ids}"
                )

            st.markdown("### Export")
            if export_has_missing:
                st.error("Export blocked because one or more lineups contain missing DK IDs.")
            else:
                csv_buffer = io.StringIO()
                export_df.to_csv(csv_buffer, index=False)

                st.download_button(
                    label="Download DraftKings Upload CSV",
                    data=csv_buffer.getvalue(),
                    file_name="dk_mlb_lineups.csv",
                    mime="text/csv",
                    use_container_width=True
                )

            # raw export preview
            with st.expander("Show DraftKings Export Preview", expanded=False):
                st.dataframe(export_df, use_container_width=True, hide_index=True)

    if tab == "Games & Lineups":
        import pandas as pd
        import numpy as np
        import streamlit as st
        import streamlit.components.v1 as components

        def load_games_and_lus_data():
            fp = _DATA_DIR
            daily_weather_report = pd.read_csv(f'{fp}/daily_weather_2026.csv')
            dfs_pitcher_proj = pd.read_csv(f'{fp}/Tableau_DailyPitcherProj.csv')
            dfs_hitter_proj = pd.read_csv(f'{fp}/Tableau_DailyHitterProj.csv')
            game_info = pd.read_csv(f'{fp}/gameinfo.csv')
            return dfs_hitter_proj, dfs_pitcher_proj, daily_weather_report, game_info

        dfs_hitter_proj, dfs_pitcher_proj, daily_weather_report, game_info = load_games_and_lus_data()

        # -----------------------------
        # cleanup
        # -----------------------------
        for df in [dfs_hitter_proj, dfs_pitcher_proj, daily_weather_report, game_info]:
            drop_cols = [c for c in df.columns if str(c).startswith("Unnamed")]
            if drop_cols:
                df.drop(columns=drop_cols, inplace=True, errors="ignore")

        # hitter file
        if "Team" in dfs_hitter_proj.columns:
            dfs_hitter_proj["Team"] = dfs_hitter_proj["Team"].astype(str).str.upper().str.strip()
        if "Opp" in dfs_hitter_proj.columns:
            dfs_hitter_proj["Opp"] = dfs_hitter_proj["Opp"].astype(str).str.upper().str.strip()
        if "LU" in dfs_hitter_proj.columns:
            dfs_hitter_proj["LU"] = pd.to_numeric(dfs_hitter_proj["LU"], errors="coerce")
        if "Sal" in dfs_hitter_proj.columns:
            dfs_hitter_proj["Sal"] = pd.to_numeric(dfs_hitter_proj["Sal"], errors="coerce")

        # pitcher file
        if "Team" in dfs_pitcher_proj.columns:
            dfs_pitcher_proj["Team"] = dfs_pitcher_proj["Team"].astype(str).str.upper().str.strip()
        if "Opponent" in dfs_pitcher_proj.columns:
            dfs_pitcher_proj["Opponent"] = dfs_pitcher_proj["Opponent"].astype(str).str.upper().str.strip()
        if "HomeTeam" in dfs_pitcher_proj.columns:
            dfs_pitcher_proj["HomeTeam"] = dfs_pitcher_proj["HomeTeam"].astype(str).str.upper().str.strip()
        if "Sal" in dfs_pitcher_proj.columns:
            dfs_pitcher_proj["Sal"] = pd.to_numeric(dfs_pitcher_proj["Sal"], errors="coerce")
        if "DKPts" in dfs_pitcher_proj.columns:
            dfs_pitcher_proj["DKPts"] = pd.to_numeric(dfs_pitcher_proj["DKPts"], errors="coerce")

        # weather
        if "away_team" in daily_weather_report.columns:
            daily_weather_report["away_team"] = daily_weather_report["away_team"].astype(str).str.upper().str.strip()
        if "home_team" in daily_weather_report.columns:
            daily_weather_report["home_team"] = daily_weather_report["home_team"].astype(str).str.upper().str.strip()

        # game info
        if "team" in game_info.columns:
            game_info["team"] = game_info["team"].astype(str).str.upper().str.strip()
        if "opponent" in game_info.columns:
            game_info["opponent"] = game_info["opponent"].astype(str).str.upper().str.strip()
        if "Park" in game_info.columns:
            game_info["Park"] = game_info["Park"].astype(str).str.upper().str.strip()
        for c in ["moneyline", "overunder", "projected"]:
            if c in game_info.columns:
                game_info[c] = pd.to_numeric(game_info[c], errors="coerce")

        # -----------------------------
        # helpers
        # -----------------------------
        def is_yes_series(series):
            return series.astype(str).str.upper().str.strip().isin(["Y", "YES", "TRUE", "1"])

        def fmt_odds(x):
            if pd.isna(x):
                return "—"
            x = int(round(float(x)))
            return f"+{x}" if x > 0 else str(x)

        def fmt_ou(x):
            if pd.isna(x):
                return "—"
            return f"{float(x):.1f}"

        def fmt_temp(x):
            if pd.isna(x):
                return "—"
            try:
                return f"{int(round(float(x)))}°"
            except:
                return str(x)

        def fmt_rain(x):
            if pd.isna(x):
                return "—"
            try:
                return f"{int(round(float(x)))}%"
            except:
                return str(x)

        def fmt_salary(x):
            if pd.isna(x):
                return ""
            try:
                x = float(x)
                if x <= 0:
                    return ""
                if x >= 1000:
                    return f"${x/1000:.1f}K"
                return f"${x:,.0f}"
            except:
                return ""

        def fmt_proj(x):
            if pd.isna(x):
                return "—"
            return f"{float(x):.2f}"

        def get_main_slate_teams():
            teams = set()

            if "MainSlate" in dfs_hitter_proj.columns:
                hit_main = dfs_hitter_proj.loc[is_yes_series(dfs_hitter_proj["MainSlate"]), "Team"].dropna().tolist()
                teams.update(hit_main)

            if "MainSlate" in dfs_pitcher_proj.columns:
                pit_main = dfs_pitcher_proj.loc[is_yes_series(dfs_pitcher_proj["MainSlate"]), "Team"].dropna().tolist()
                teams.update(pit_main)

            return teams

        def lineup_status(team_df):
            if team_df.empty or "Confirmed LU" not in team_df.columns:
                return "NOT CONFIRMED", "not-confirmed"

            vals = (
                team_df["Confirmed LU"]
                .astype(str)
                .str.upper()
                .str.strip()
                .replace({"YES": "Y", "NO": "N", "TRUE": "Y", "FALSE": "N"})
            )

            if (vals == "Y").any():
                return "CONFIRMED", "confirmed"
            return "NOT CONFIRMED", "not-confirmed"

        def get_lineup(team):
            df = dfs_hitter_proj[dfs_hitter_proj["Team"] == team].copy()
            if df.empty:
                return df

            sort_cols = [c for c in ["LU", "Order", "BatOrder", "Hitter"] if c in df.columns]
            if "LU" in df.columns:
                df = df.sort_values(["LU", "Hitter"], na_position="last")
            elif len(sort_cols) > 0:
                df = df.sort_values(sort_cols, na_position="last")

            return df

        def get_pitcher_for_team(team):
            pdf = dfs_pitcher_proj[dfs_pitcher_proj["Team"] == team].copy()
            if pdf.empty:
                return {"Pitcher": "TBD", "Sal": np.nan}

            sort_cols = []
            ascending = []
            if "DKPts" in pdf.columns:
                sort_cols.append("DKPts")
                ascending.append(False)
            if "Sal" in pdf.columns:
                sort_cols.append("Sal")
                ascending.append(False)

            if len(sort_cols) > 0:
                pdf = pdf.sort_values(sort_cols, ascending=ascending, na_position="last")

            row = pdf.iloc[0]
            return {
                "Pitcher": row.get("Pitcher", "TBD"),
                "Sal": row.get("Sal", np.nan)
            }

        def get_weather(away_team, home_team):
            if daily_weather_report.empty:
                return None

            w = daily_weather_report[
                (daily_weather_report["away_team"] == away_team) &
                (daily_weather_report["home_team"] == home_team)
            ].copy()

            if w.empty:
                w = daily_weather_report[daily_weather_report["home_team"] == home_team].copy()

            if w.empty:
                return None

            row = w.iloc[0]

            temp_val = None
            for c in ["temp_f", "Temp", "temperature", "temp"]:
                if c in row.index:
                    temp_val = row.get(c)
                    break

            rain_val = None
            for c in ["rain_prob_pct", "Rain", "rain", "precip_pct", "precip"]:
                if c in row.index:
                    rain_val = row.get(c)
                    break

            wind_val = "—"
            for c in ["wind_summary", "Wind", "wind", "Winds", "Wind Dir"]:
                if c in row.index and pd.notna(row.get(c)):
                    wind_val = row.get(c)
                    break

            return {
                "temp": fmt_temp(temp_val),
                "rain": fmt_rain(rain_val),
                "wind": wind_val if pd.notna(wind_val) else "—"
            }

        def build_games():
            games = []
            used = set()

            for _, row in game_info.iterrows():
                team = row["team"]
                opp = row["opponent"]

                pair_key = tuple(sorted([team, opp]))
                if pair_key in used:
                    continue

                pair_rows = game_info[
                    ((game_info["team"] == team) & (game_info["opponent"] == opp)) |
                    ((game_info["team"] == opp) & (game_info["opponent"] == team))
                ].copy()

                if pair_rows.empty:
                    continue

                # prefer exactly 2 rows, but still try to recover if data is messy
                home_rows = pair_rows[pair_rows["team"] == pair_rows["Park"]] if "Park" in pair_rows.columns else pd.DataFrame()
                away_rows = pair_rows[pair_rows["team"] != pair_rows["Park"]] if "Park" in pair_rows.columns else pd.DataFrame()

                if not home_rows.empty:
                    home_row = home_rows.iloc[0]
                else:
                    home_row = pair_rows.iloc[0]

                if not away_rows.empty:
                    away_row = away_rows.iloc[0]
                else:
                    alt = pair_rows[pair_rows["team"] != home_row["team"]]
                    away_row = alt.iloc[0] if not alt.empty else pair_rows.iloc[0]

                games.append({
                    "away_team": away_row["team"],
                    "home_team": home_row["team"],
                    "away_row": away_row,
                    "home_row": home_row,
                    "game_time": home_row.get("game_time", away_row.get("game_time", "")),
                    "game_date": home_row.get("game_date", away_row.get("game_date", "")),
                    "park": home_row.get("Park", ""),
                    "overunder": home_row.get("overunder", away_row.get("overunder", np.nan)),
                })

                used.add(pair_key)

            return games

        def build_game_table(games):
            rows = []
            for g in games:
                away_row = g["away_row"]
                home_row = g["home_row"]
                weather = get_weather(g["away_team"], g["home_team"])
                away_pitcher = get_pitcher_for_team(g["away_team"])
                home_pitcher = get_pitcher_for_team(g["home_team"])

                rows.append({
                    "Time": g.get("game_time", ""),
                    "Matchup": f"{g['away_team']} @ {g['home_team']}",
                    "Away": g["away_team"],
                    "Home": g["home_team"],
                    "Park": g.get("park", ""),
                    "Away SP": away_pitcher.get("Pitcher", "TBD"),
                    "Home SP": home_pitcher.get("Pitcher", "TBD"),
                    "Away ML": away_row.get("moneyline", np.nan),
                    "Home ML": home_row.get("moneyline", np.nan),
                    "O/U": g.get("overunder", np.nan),
                    "Away IRT": away_row.get("projected", np.nan),
                    "Home IRT": home_row.get("projected", np.nan),
                    "Temp": weather["temp"] if weather else "—",
                    "Rain": weather["rain"] if weather else "—",
                    "Wind": weather["wind"] if weather else "—",
                })

            game_table = pd.DataFrame(rows)

            if not game_table.empty:
                for c in ["Away ML", "Home ML", "O/U", "Away IRT", "Home IRT"]:
                    if c in game_table.columns:
                        game_table[c] = pd.to_numeric(game_table[c], errors="coerce")

                desired_order = [
                    "Time", "Matchup", "Park",
                    "Away SP", "Home SP",
                    "Away ML", "Home ML", "O/U",
                    "Away IRT", "Home IRT",
                    "Temp", "Rain", "Wind"
                ]
                game_table = game_table[[c for c in desired_order if c in game_table.columns]]

            return game_table

        # -----------------------------
        # top controls
        # -----------------------------
        st.subheader("Slate Preview")

        top_c1, top_c2 = st.columns([1, 1])

        with top_c1:
            show_game_table = st.toggle("Show game info table", value=False)

        with top_c2:
            main_slate_only = st.toggle("Main slate only", value=False)

        main_slate_teams = get_main_slate_teams()
        games = build_games()

        if main_slate_only and len(main_slate_teams) > 0:
            games = [
                g for g in games
                if g["away_team"] in main_slate_teams and g["home_team"] in main_slate_teams
            ]

        try:
            games = sorted(
                games,
                key=lambda x: pd.to_datetime(f"{x.get('game_date', '')} {x.get('game_time', '')}", errors="coerce")
            )
        except:
            pass

        game_table = build_game_table(games)

        if show_game_table:
            st.markdown("### Game Info Table")
            st.dataframe(game_table, use_container_width=True, hide_index=True)

        # -----------------------------
        # cards
        # -----------------------------
        if len(games) == 0:
            st.warning("No games found.")
        else:
            for i in range(0, len(games), 2):
                row_games = games[i:i+2]
                cols = st.columns(2)

                for col_idx, game in enumerate(row_games):
                    away_team = game["away_team"]
                    home_team = game["home_team"]

                    away_lineup = get_lineup(away_team)
                    home_lineup = get_lineup(home_team)

                    away_pitcher = get_pitcher_for_team(away_team)
                    home_pitcher = get_pitcher_for_team(home_team)

                    away_status_text, away_status_class = lineup_status(away_lineup)
                    home_status_text, home_status_class = lineup_status(home_lineup)

                    away_bg_class = "confirmed-bg" if away_status_class == "confirmed" else ""
                    home_bg_class = "confirmed-bg" if home_status_class == "confirmed" else ""

                    weather = get_weather(away_team, home_team)
                    away_row = game["away_row"]
                    home_row = game["home_row"]

                    away_ml = fmt_odds(away_row.get("moneyline"))
                    home_ml = fmt_odds(home_row.get("moneyline"))
                    away_proj = fmt_proj(away_row.get("projected"))
                    home_proj = fmt_proj(home_row.get("projected"))
                    ou_txt = fmt_ou(game.get("overunder"))

                    if weather is not None:
                        weather_html = f"""
                        <div class="slate-weather">
                            <div><b>Temp:</b> {weather['temp']} &nbsp;&nbsp; <b>Rain:</b> {weather['rain']}</div>
                            <div><b>Wind:</b> {weather['wind']}</div>
                        </div>
                        """
                    else:
                        weather_html = """
                        <div class="slate-weather">
                            <div><b>Temp:</b> — &nbsp;&nbsp; <b>Rain:</b> —</div>
                            <div><b>Wind:</b> —</div>
                        </div>
                        """

                    away_rows_html = ""
                    if away_lineup.empty:
                        away_rows_html = '<div class="small-muted">No lineup available.</div>'
                    else:
                        for _, r in away_lineup.iterrows():
                            spot = ""
                            if "LU" in away_lineup.columns and pd.notna(r.get("LU")):
                                try:
                                    spot = int(r.get("LU"))
                                except:
                                    spot = r.get("LU")

                            player_name = r.get("Hitter", r.get("Player", ""))
                            pos = r.get("Pos", r.get("Position", ""))
                            sal_txt = fmt_salary(r.get("Sal"))

                            away_rows_html += f"""
                            <div class="line-row">
                                <div class="line-spot">{spot}</div>
                                <div class="line-player">{player_name}</div>
                                <div class="line-pos">{pos}</div>
                                <div class="line-sal">{sal_txt}</div>
                            </div>
                            """

                    home_rows_html = ""
                    if home_lineup.empty:
                        home_rows_html = '<div class="small-muted">No lineup available.</div>'
                    else:
                        for _, r in home_lineup.iterrows():
                            spot = ""
                            if "LU" in home_lineup.columns and pd.notna(r.get("LU")):
                                try:
                                    spot = int(r.get("LU"))
                                except:
                                    spot = r.get("LU")

                            player_name = r.get("Hitter", r.get("Player", ""))
                            pos = r.get("Pos", r.get("Position", ""))
                            sal_txt = fmt_salary(r.get("Sal"))

                            home_rows_html += f"""
                            <div class="line-row">
                                <div class="line-spot">{spot}</div>
                                <div class="line-player">{player_name}</div>
                                <div class="line-pos">{pos}</div>
                                <div class="line-sal">{sal_txt}</div>
                            </div>
                            """

                    card_html = f"""
                    <html>
                    <head>
                    <style>
                        body {{
                            margin: 0;
                            padding: 8px;
                            background: white;
                            font-family: Arial, sans-serif;
                        }}
                        .slate-card {{
                            border: 1px solid #d9d9d9;
                            border-radius: 14px;
                            background: white;
                            overflow: hidden;
                            box-shadow: 0 1px 4px rgba(0,0,0,.06);
                        }}
                        .slate-header {{
                            background: #f7f7f7;
                            padding: 12px 14px 8px 14px;
                            border-bottom: 1px solid #e6e6e6;
                        }}
                        .slate-time {{
                            font-size: 13px;
                            color: #666;
                            font-weight: 600;
                            margin-bottom: 8px;
                        }}
                        .slate-matchup {{
                            display: grid;
                            grid-template-columns: 1fr 40px 1fr;
                            align-items: center;
                            font-weight: 700;
                            font-size: 18px;
                        }}
                        .away-team {{
                            text-align: left;
                        }}
                        .at-sign {{
                            text-align: center;
                        }}
                        .home-team {{
                            text-align: right;
                        }}
                        .slate-weather {{
                            background: #eef8ee;
                            padding: 10px 14px;
                            border-bottom: 1px solid #e6e6e6;
                            font-size: 14px;
                            line-height: 1.4;
                        }}
                        .slate-betting {{
                            display: grid;
                            grid-template-columns: 1fr 0.9fr 1fr;
                            text-align: center;
                            border-bottom: 1px solid #e6e6e6;
                            background: #fbfbfb;
                        }}
                        .bet-box {{
                            padding: 12px 8px;
                        }}
                        .bet-main {{
                            font-weight: 800;
                            font-size: 28px;
                            color: #164a9c;
                            line-height: 1.1;
                        }}
                        .bet-sub {{
                            font-size: 13px;
                            color: #666;
                        }}
                        .team-sections {{
                            display: grid;
                            grid-template-columns: 1fr 1fr;
                        }}
                        .team-col {{
                            border-right: 1px solid #ededed;
                        }}
                        .team-col:last-child {{
                            border-right: none;
                        }}
                        .pitcher-box {{
                            text-align: center;
                            padding: 14px 10px 10px 10px;
                            min-height: 78px;
                        }}
                        .pitcher-name {{
                            font-size: 17px;
                            font-weight: 700;
                            color: #444;
                        }}
                        .pitcher-meta {{
                            font-size: 14px;
                            color: #666;
                        }}
                        .lineup-status-confirmed {{
                            background: #1f8f4e;
                            color: white;
                            font-weight: 700;
                            font-size: 13px;
                            padding: 7px 12px;
                        }}
                        .lineup-status-not-confirmed {{
                            background: #e05353;
                            color: white;
                            font-weight: 700;
                            font-size: 13px;
                            padding: 7px 12px;
                        }}
                        .lineup-list {{
                            background: #faeded;
                            padding: 10px 14px 14px 14px;
                            min-height: 310px;
                        }}
                        .lineup-list.confirmed-bg {{
                            background: #eef7ef;
                        }}
                        .line-row {{
                            display: grid;
                            grid-template-columns: 20px 1fr auto auto;
                            gap: 8px;
                            align-items: baseline;
                            margin-bottom: 6px;
                            font-size: 15px;
                        }}
                        .line-spot {{
                            color: #666;
                        }}
                        .line-player {{
                            font-weight: 600;
                            color: #444;
                        }}
                        .line-pos {{
                            color: #777;
                            font-size: 13px;
                        }}
                        .line-sal {{
                            color: #17853a;
                            font-weight: 700;
                            font-size: 13px;
                        }}
                        .small-muted {{
                            color: #777;
                            font-size: 13px;
                        }}
                    </style>
                    </head>
                    <body>
                    <div class="slate-card">
                        <div class="slate-header">
                            <div class="slate-time">{game.get('game_time', '')} ET | {game.get('park', '')}</div>
                            <div class="slate-matchup">
                                <div class="away-team">{away_team}</div>
                                <div class="at-sign">@</div>
                                <div class="home-team">{home_team}</div>
                            </div>
                        </div>

                        {weather_html}

                        <div class="slate-betting">
                            <div class="bet-box">
                                <div class="bet-main">{away_proj}</div>
                                <div class="bet-sub">{away_ml} ML</div>
                            </div>
                            <div class="bet-box">
                                <div class="bet-main">{ou_txt}</div>
                                <div class="bet-sub">O/U</div>
                            </div>
                            <div class="bet-box">
                                <div class="bet-main">{home_proj}</div>
                                <div class="bet-sub">{home_ml} ML</div>
                            </div>
                        </div>

                        <div class="team-sections">
                            <div class="team-col">
                                <div class="pitcher-box">
                                    <div class="pitcher-name">{away_pitcher['Pitcher']}</div>
                                    <div class="pitcher-meta">Probable SP &nbsp;&nbsp; {fmt_salary(away_pitcher['Sal'])}</div>
                                </div>
                                <div class="lineup-status-{away_status_class}">{away_status_text}</div>
                                <div class="lineup-list {away_bg_class}">
                                    {away_rows_html}
                                </div>
                            </div>

                            <div class="team-col">
                                <div class="pitcher-box">
                                    <div class="pitcher-name">{home_pitcher['Pitcher']}</div>
                                    <div class="pitcher-meta">Probable SP &nbsp;&nbsp; {fmt_salary(home_pitcher['Sal'])}</div>
                                </div>
                                <div class="lineup-status-{home_status_class}">{home_status_text}</div>
                                <div class="lineup-list {home_bg_class}">
                                    {home_rows_html}
                                </div>
                            </div>
                        </div>
                    </div>
                    </body>
                    </html>
                    """

                    with cols[col_idx]:
                        components.html(card_html, height=760, scrolling=False)


    if tab == "FLUB Analysis":
        import streamlit as st
        import pandas as pd
        import numpy as np
        import altair as alt

        # =========================================================
        # PAGE CONFIG / STYLING
        # =========================================================
        st.markdown("""
        <style>
        div[data-baseweb="radio"] > div {
            gap: 0.35rem;
            flex-wrap: wrap;
        }

        div[data-baseweb="radio"] label {
            background: #f3f4f6;
            border: 1px solid #d1d5db;
            border-radius: 10px;
            padding: 8px 14px;
            margin-right: 4px;
            transition: all 0.15s ease-in-out;
        }

        div[data-baseweb="radio"] label:hover {
            border-color: #9ca3af;
            background: #e5e7eb;
        }

        div[data-baseweb="radio"] label[data-checked="true"] {
            background: #111827;
            border-color: #111827;
        }

        div[data-baseweb="radio"] label[data-checked="true"] p {
            color: white !important;
            font-weight: 600;
        }

        .flub-section {
            padding-top: 0.4rem;
            padding-bottom: 0.25rem;
        }

        .flub-note {
            font-size: 0.95rem;
            color: #6b7280;
        }
        </style>
        """, unsafe_allow_html=True)

        st.header("League Snapshot")
        st.caption("FLUB standings, roto trends, category boards, strength of schedule, and matchup luck.")

        # =========================================================
        # EXPECTED INPUT
        # ---------------------------------------------------------
        # You said you'll handle data loading.
        # This block assumes a dataframe exists called:
        # flub_df
        # =========================================================
        
        flub_df = load_flub_data()
        df = flub_df.copy()

        # =========================================================
        # CLEANUP
        # =========================================================
        if "Unnamed: 0" in df.columns:
            df = df.drop(columns=["Unnamed: 0"])

        numeric_cols = [
            "Week", "Team Wins", "Team Losses", "Team Ties",
            "Opp Wins", "Opp Losses", "Opp Ties",
            "AB", "AVG", "B_BB", "ER", "ERA", "H", "HBP", "HR", "K", "K/9",
            "OBP", "OUTS", "P_BB", "P_H", "QS", "R", "RBI", "SB", "SF", "SV", "W", "WHIP"
        ]
        for c in numeric_cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")

        df["Week"] = pd.to_numeric(df["Week"], errors="coerce")
        df = df[df["Week"].notna()].copy()
        df["Week"] = df["Week"].astype(int)

        df["Team"] = df["Team"].astype(str).str.strip()
        df["Opp"] = df["Opp"].astype(str).str.strip()

        hitting_cats = ["R", "HR", "RBI", "SB", "AVG", "OBP"]
        pitching_cats = ["W", "QS", "SV", "ERA", "WHIP", "K/9"]
        all_cats = hitting_cats + pitching_cats
        lower_is_better = ["ERA", "WHIP"]

        team_list = sorted(df["Team"].dropna().unique().tolist())
        week_list = sorted(df["Week"].dropna().unique().tolist())

        # =========================================================
        # HELPERS
        # =========================================================
        def safe_div(n, d):
            n = np.asarray(n, dtype=float)
            d = np.asarray(d, dtype=float)
            out = np.full_like(n, np.nan, dtype=float)
            mask = (d != 0) & ~np.isnan(d)
            out[mask] = n[mask] / d[mask]
            return out

        def add_derived_rates(g):
            g = g.copy()

            if all(col in g.columns for col in ["H", "AB"]):
                g["AVG_calc"] = safe_div(g["H"], g["AB"])
            else:
                g["AVG_calc"] = np.nan

            if all(col in g.columns for col in ["H", "B_BB", "HBP", "AB", "SF"]):
                g["OBP_calc"] = safe_div(
                    g["H"] + g["B_BB"] + g["HBP"],
                    g["AB"] + g["B_BB"] + g["HBP"] + g["SF"]
                )
            else:
                g["OBP_calc"] = np.nan

            if all(col in g.columns for col in ["ER", "OUTS"]):
                ip = g["OUTS"] / 3
                g["ERA_calc"] = safe_div(g["ER"] * 9, ip)
            else:
                g["ERA_calc"] = np.nan

            if all(col in g.columns for col in ["P_H", "P_BB", "OUTS"]):
                ip = g["OUTS"] / 3
                g["WHIP_calc"] = safe_div(g["P_H"] + g["P_BB"], ip)
            else:
                g["WHIP_calc"] = np.nan

            if all(col in g.columns for col in ["K", "OUTS"]):
                ip = g["OUTS"] / 3
                g["K9_calc"] = safe_div(g["K"] * 9, ip)
            else:
                g["K9_calc"] = np.nan

            g["AVG_final"] = np.where(pd.notna(g["AVG_calc"]), g["AVG_calc"], g["AVG"] if "AVG" in g.columns else np.nan)
            g["OBP_final"] = np.where(pd.notna(g["OBP_calc"]), g["OBP_calc"], g["OBP"] if "OBP" in g.columns else np.nan)
            g["ERA_final"] = np.where(pd.notna(g["ERA_calc"]), g["ERA_calc"], g["ERA"] if "ERA" in g.columns else np.nan)
            g["WHIP_final"] = np.where(pd.notna(g["WHIP_calc"]), g["WHIP_calc"], g["WHIP"] if "WHIP" in g.columns else np.nan)
            g["K9_final"] = np.where(pd.notna(g["K9_calc"]), g["K9_calc"], g["K/9"] if "K/9" in g.columns else np.nan)

            return g

        def aggregate_window(source_df, weeks):
            g = source_df[source_df["Week"].isin(weeks)].copy()

            agg_cols = [
                "AB", "B_BB", "ER", "H", "HBP", "HR", "K", "OUTS", "P_BB", "P_H",
                "QS", "R", "RBI", "SB", "SF", "SV", "W",
                "Team Wins", "Team Losses", "Team Ties"
            ]
            agg_dict = {c: "sum" for c in agg_cols if c in g.columns}

            team_agg = g.groupby("Team", as_index=False).agg(agg_dict)
            team_agg = add_derived_rates(team_agg)

            team_agg["AVG"] = team_agg["AVG_final"]
            team_agg["OBP"] = team_agg["OBP_final"]
            team_agg["ERA"] = team_agg["ERA_final"]
            team_agg["WHIP"] = team_agg["WHIP_final"]
            team_agg["K/9"] = team_agg["K9_final"]

            return team_agg

        def roto_rank_table(team_agg):
            out = team_agg[["Team"]].copy()
            n_teams = team_agg["Team"].nunique()

            for cat in all_cats:
                ascending = cat in lower_is_better
                out[f"{cat}_Rank"] = team_agg[cat].rank(method="average", ascending=ascending)
                out[f"{cat}_Pts"] = (n_teams + 1) - out[f"{cat}_Rank"]

            out["Roto Points"] = out[[f"{c}_Pts" for c in all_cats]].sum(axis=1)
            out["Overall Rank"] = out["Roto Points"].rank(method="min", ascending=False)

            for cat in all_cats:
                out[cat] = team_agg[cat].values

            for c in ["Team Wins", "Team Losses", "Team Ties"]:
                if c in team_agg.columns:
                    out[c] = team_agg[c].values

            return out.sort_values(["Overall Rank", "Team"]).reset_index(drop=True)

        def category_weekly_rank_df(source_df):
            wk = source_df.copy()
            wk = add_derived_rates(wk)

            wk["AVG"] = wk["AVG_final"]
            wk["OBP"] = wk["OBP_final"]
            wk["ERA"] = wk["ERA_final"]
            wk["WHIP"] = wk["WHIP_final"]
            wk["K/9"] = wk["K9_final"]

            weekly_frames = []
            for week_num, g in wk.groupby("Week"):
                g = g.copy()
                n_teams = g["Team"].nunique()
                temp = g[["Week", "Team"] + all_cats].copy()

                for cat in all_cats:
                    ascending = cat in lower_is_better
                    temp[f"{cat}_Rank"] = temp[cat].rank(method="average", ascending=ascending)
                    temp[f"{cat}_Pts"] = (n_teams + 1) - temp[f"{cat}_Rank"]

                temp["Weekly Roto Points"] = temp[[f"{c}_Pts" for c in all_cats]].sum(axis=1)
                temp["Weekly Roto Rank"] = temp["Weekly Roto Points"].rank(method="min", ascending=False)
                weekly_frames.append(temp)

            return pd.concat(weekly_frames, ignore_index=True)

        def category_summary_for_window(source_df, weeks):
            agg = aggregate_window(source_df, weeks)
            out = agg[["Team"] + all_cats].copy()

            for cat in all_cats:
                ascending = cat in lower_is_better
                out[f"{cat}_Rank"] = out[cat].rank(method="min", ascending=ascending)

            return out

        def build_matchup_results(source_df):
            wk = source_df.copy()
            wk = add_derived_rates(wk)

            wk["AVG"] = wk["AVG_final"]
            wk["OBP"] = wk["OBP_final"]
            wk["ERA"] = wk["ERA_final"]
            wk["WHIP"] = wk["WHIP_final"]
            wk["K/9"] = wk["K9_final"]

            results = wk[["Week", "Team", "Opp", "Team Wins", "Team Losses", "Team Ties"] + all_cats].copy()

            opp_actual = wk[["Week", "Team"] + all_cats].copy()
            opp_actual = opp_actual.rename(columns={"Team": "Opp", **{c: f"Opp_Actual_{c}" for c in all_cats}})
            results = results.merge(opp_actual, on=["Week", "Opp"], how="left")

            results["Matchup Score"] = results["Team Wins"] + (results["Team Ties"] * 0.5)

            opp_week_strength = []
            for week_num, g in wk.groupby("Week"):
                n_teams = g["Team"].nunique()
                tmp = g[["Team"] + all_cats].copy()

                for cat in all_cats:
                    ascending = cat in lower_is_better
                    tmp[f"{cat}_Pts"] = (n_teams + 1) - tmp[cat].rank(method="average", ascending=ascending)

                tmp["Opp Weekly Roto Pts"] = tmp[[f"{c}_Pts" for c in all_cats]].sum(axis=1)
                tmp["Week"] = week_num
                opp_week_strength.append(tmp[["Week", "Team", "Opp Weekly Roto Pts"]])

            opp_week_strength = pd.concat(opp_week_strength, ignore_index=True).rename(columns={"Team": "Opp"})
            results = results.merge(opp_week_strength, on=["Week", "Opp"], how="left")

            baseline_records = []
            for _, row in wk.iterrows():
                opp_team = row["Opp"]
                opp_week = row["Week"]

                opp_other_weeks = wk[(wk["Team"] == opp_team) & (wk["Week"] != opp_week)]
                if opp_other_weeks.empty:
                    continue

                opp_agg = aggregate_window(opp_other_weeks, opp_other_weeks["Week"].unique().tolist())
                if opp_agg.empty:
                    continue

                rec = {"Week": opp_week, "Team": row["Team"], "Opp": opp_team}
                for cat in all_cats:
                    rec[f"Opp_Baseline_{cat}"] = opp_agg.iloc[0][cat]
                baseline_records.append(rec)

            opp_baselines = pd.DataFrame(baseline_records)
            if not opp_baselines.empty:
                results = results.merge(opp_baselines, on=["Week", "Team", "Opp"], how="left")

            baseline_strength_rows = []
            season_agg = aggregate_window(wk, sorted(wk["Week"].unique().tolist()))
            season_context = season_agg[["Team"] + all_cats].copy()

            if not opp_baselines.empty:
                for _, row in opp_baselines.iterrows():
                    pts = 0.0
                    for cat in all_cats:
                        val = row[f"Opp_Baseline_{cat}"]
                        comp_series = season_context[cat].dropna()

                        if pd.isna(val):
                            continue

                        if cat in lower_is_better:
                            pts += 1 + (comp_series > val).sum() + 0.5 * (comp_series == val).sum() - 0.5
                        else:
                            pts += 1 + (comp_series < val).sum() + 0.5 * (comp_series == val).sum() - 0.5

                    baseline_strength_rows.append({
                        "Week": row["Week"],
                        "Opp": row["Opp"],
                        "Opp Baseline Roto Pts": pts
                    })

            opp_baseline_pts = pd.DataFrame(baseline_strength_rows)
            if not opp_baseline_pts.empty:
                results = results.merge(opp_baseline_pts, on=["Week", "Opp"], how="left")
                results["Opponent Hotness"] = results["Opp Weekly Roto Pts"] - results["Opp Baseline Roto Pts"]
            else:
                results["Opp Baseline Roto Pts"] = np.nan
                results["Opponent Hotness"] = np.nan

            for cat in all_cats:
                a = f"Opp_Actual_{cat}"
                b = f"Opp_Baseline_{cat}"
                if a in results.columns and b in results.columns:
                    if cat in lower_is_better:
                        results[f"{cat}_OppHot"] = results[b] - results[a]
                    else:
                        results[f"{cat}_OppHot"] = results[a] - results[b]

            return results

        # =========================================================
        # CORE DATASETS
        # =========================================================
        weekly_rank_df = category_weekly_rank_df(df)

        season_weeks = week_list
        last_3_weeks = week_list[-3:] if len(week_list) >= 3 else week_list
        last_5_weeks = week_list[-5:] if len(week_list) >= 5 else week_list

        season_agg = aggregate_window(df, season_weeks)
        last3_agg = aggregate_window(df, last_3_weeks)
        last5_agg = aggregate_window(df, last_5_weeks)

        season_roto = roto_rank_table(season_agg)
        last3_roto = roto_rank_table(last3_agg)
        last5_roto = roto_rank_table(last5_agg)

        roto_trend = season_roto[["Team", "Overall Rank", "Roto Points"]].rename(columns={
            "Overall Rank": "Season Rank",
            "Roto Points": "Season Roto Pts"
        })

        roto_trend = roto_trend.merge(
            last3_roto[["Team", "Overall Rank", "Roto Points"]].rename(columns={
                "Overall Rank": "Last 3 Rank",
                "Roto Points": "Last 3 Roto Pts"
            }),
            on="Team",
            how="left"
        )

        roto_trend = roto_trend.merge(
            last5_roto[["Team", "Overall Rank", "Roto Points"]].rename(columns={
                "Overall Rank": "Last 5 Rank",
                "Roto Points": "Last 5 Roto Pts"
            }),
            on="Team",
            how="left"
        )

        roto_trend["3W Trend"] = roto_trend["Season Rank"] - roto_trend["Last 3 Rank"]
        roto_trend["5W Trend"] = roto_trend["Season Rank"] - roto_trend["Last 5 Rank"]

        def trend_label(x):
            if x >= 2:
                return "Rising"
            elif x <= -2:
                return "Falling"
            return "Steady"

        roto_trend["3W Arrow"] = roto_trend["3W Trend"].apply(trend_label)
        roto_trend["5W Arrow"] = roto_trend["5W Trend"].apply(trend_label)

        matchup_results = build_matchup_results(df)

        schedule_summary = matchup_results.groupby("Team", as_index=False).agg({
            "Matchup Score": "mean",
            "Opp Weekly Roto Pts": "mean",
            "Opp Baseline Roto Pts": "mean",
            "Opponent Hotness": "mean",
            "Week": "count"
        }).rename(columns={
            "Matchup Score": "Avg Matchup Score",
            "Opp Weekly Roto Pts": "Avg Opp Weekly Strength",
            "Opp Baseline Roto Pts": "Avg Opp Baseline Strength",
            "Opponent Hotness": "Opponent Hotness Faced",
            "Week": "Weeks Played"
        })

        schedule_summary["Schedule Difficulty Index"] = (
            schedule_summary["Avg Opp Weekly Strength"] - schedule_summary["Avg Opp Weekly Strength"].mean()
        )
        schedule_summary["Schedule Luck Index"] = schedule_summary["Opponent Hotness Faced"]

        cat_sched_cols = [f"{c}_OppHot" for c in all_cats if f"{c}_OppHot" in matchup_results.columns]
        if len(cat_sched_cols) > 0:
            category_schedule = matchup_results.groupby("Team", as_index=False)[cat_sched_cols].mean()
            category_schedule.columns = ["Team"] + [c.replace("_OppHot", "") for c in category_schedule.columns if c != "Team"]
        else:
            category_schedule = pd.DataFrame({"Team": team_list})

        # =========================================================
        # TOP CONTROLS
        # =========================================================
        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.metric("Teams", len(team_list))
        with k2:
            st.metric("Weeks Logged", len(week_list))
        with k3:
            st.metric("Current Week", max(week_list))
        with k4:
            st.metric("Latest 5W Window", f"{last_5_weeks[0]}-{last_5_weeks[-1]}")

        st.markdown("")

        c1, c2, c3 = st.columns([1.2, 1.2, 1.6])

        with c1:
            selected_window = st.selectbox(
                "Category Table Window",
                ["Season", "Last 3 Weeks", "Last 5 Weeks", "Single Week"],
                index=0
            )

        with c2:
            selected_week = st.selectbox(
                "Single Week",
                week_list,
                index=len(week_list) - 1
            )

        with c3:
            selected_team = st.selectbox(
                "Team Spotlight",
                ["All Teams"] + team_list,
                index=0
            )

        # =========================================================
        # NAV MENU
        # =========================================================
        view = st.radio(
            "View",
            [
                "Roto Standings",
                "Trend Report",
                "Category Boards",
                "Schedule Strength",
                "Team Deep Dive",
                "Weekly Matchups"
            ],
            horizontal=True,
            label_visibility="collapsed"
        )

        st.markdown('<div class="flub-section"></div>', unsafe_allow_html=True)

        # =========================================================
        # ROTO STANDINGS
        # =========================================================
        if view == "Roto Standings":
            st.subheader("Season-to-Date Roto Standings")

            display_cols = [
                "Overall Rank", "Team", "Roto Points",
                "R", "HR", "RBI", "SB", "AVG", "OBP",
                "W", "QS", "SV", "ERA", "WHIP", "K/9"
            ]
            extra_match_cols = [c for c in ["Team Wins", "Team Losses", "Team Ties"] if c in season_roto.columns]

            show_df = season_roto[display_cols + extra_match_cols].copy()

            st.dataframe(
                show_df,
                use_container_width=True,
                hide_index=True
            )

            st.subheader("Trend Overlay")
            trend_display = roto_trend.sort_values("Season Rank").copy()
            trend_display = trend_display[[
                "Team", "Season Rank", "Season Roto Pts",
                "Last 3 Rank", "Last 3 Roto Pts", "3W Trend", "3W Arrow",
                "Last 5 Rank", "Last 5 Roto Pts", "5W Trend", "5W Arrow"
            ]]

            st.dataframe(trend_display, use_container_width=True, hide_index=True)

        # =========================================================
        # TREND REPORT
        # =========================================================
        elif view == "Trend Report":
            st.subheader("Weekly Roto Trend")

            trend_plot_df = weekly_rank_df.copy()
            if selected_team != "All Teams":
                trend_plot_df = trend_plot_df[trend_plot_df["Team"] == selected_team]

            trend_plot_df["Week"] = trend_plot_df["Week"].astype(str)

            chart = alt.Chart(trend_plot_df).mark_line(point=True).encode(
                x=alt.X("Week:O", title="Week"),
                y=alt.Y("Weekly Roto Rank:Q", title="Weekly Roto Rank", scale=alt.Scale(reverse=True)),
                color=alt.Color("Team:N"),
                tooltip=[
                    alt.Tooltip("Team:N"),
                    alt.Tooltip("Week:O"),
                    alt.Tooltip("Weekly Roto Points:Q", format=".1f"),
                    alt.Tooltip("Weekly Roto Rank:Q", format=".1f")
                ]
            ).properties(height=420)

            st.altair_chart(chart, use_container_width=True)

            st.subheader("Weekly Roto Points")

            chart2 = alt.Chart(trend_plot_df).mark_line(point=True).encode(
                x=alt.X("Week:O", title="Week"),
                y=alt.Y("Weekly Roto Points:Q", title="Weekly Roto Points"),
                color=alt.Color("Team:N"),
                tooltip=[
                    alt.Tooltip("Team:N"),
                    alt.Tooltip("Week:O"),
                    alt.Tooltip("Weekly Roto Points:Q", format=".1f"),
                    alt.Tooltip("Weekly Roto Rank:Q", format=".1f")
                ]
            ).properties(height=420)

            st.altair_chart(chart2, use_container_width=True)

            rolling_records = []
            weeks_sorted = week_list

            for i, wk in enumerate(weeks_sorted):
                w3 = weeks_sorted[max(0, i - 2):i + 1]
                agg3 = aggregate_window(df, w3)
                roto3 = roto_rank_table(agg3)[["Team", "Overall Rank", "Roto Points"]].rename(columns={
                    "Overall Rank": "Rolling 3W Rank",
                    "Roto Points": "Rolling 3W Pts"
                })
                roto3["End Week"] = wk

                w5 = weeks_sorted[max(0, i - 4):i + 1]
                agg5 = aggregate_window(df, w5)
                roto5 = roto_rank_table(agg5)[["Team", "Overall Rank", "Roto Points"]].rename(columns={
                    "Overall Rank": "Rolling 5W Rank",
                    "Roto Points": "Rolling 5W Pts"
                })
                roto5["End Week"] = wk

                merged = roto3.merge(roto5, on=["Team", "End Week"], how="outer")
                rolling_records.append(merged)

            rolling_df = pd.concat(rolling_records, ignore_index=True)

            if selected_team != "All Teams":
                rolling_df = rolling_df[rolling_df["Team"] == selected_team].copy()

            rolling_df["End Week"] = rolling_df["End Week"].astype(str)
            rolling_df["Rolling 3W Rank"] = pd.to_numeric(rolling_df["Rolling 3W Rank"], errors="coerce")
            rolling_df["Rolling 5W Rank"] = pd.to_numeric(rolling_df["Rolling 5W Rank"], errors="coerce")

            rolling_long = rolling_df.melt(
                id_vars=["Team", "End Week"],
                value_vars=["Rolling 3W Rank", "Rolling 5W Rank"],
                var_name="Metric",
                value_name="Value"
            )

            rolling_long = rolling_long.dropna(subset=["Value"]).copy()

            st.subheader("Rolling Window Rank History")

            roll_chart = alt.Chart(rolling_long).mark_line(point=True).encode(
                x=alt.X("End Week:O", title="Ending Week"),
                y=alt.Y("Value:Q", title="Rank", scale=alt.Scale(reverse=True)),
                color=alt.Color("Metric:N", title="Window"),
                detail="Team:N",
                tooltip=[
                    alt.Tooltip("Team:N"),
                    alt.Tooltip("End Week:O"),
                    alt.Tooltip("Metric:N"),
                    alt.Tooltip("Value:Q", format=".1f")
                ]
            ).properties(height=420)

            st.altair_chart(roll_chart, use_container_width=True)

        # =========================================================
        # CATEGORY BOARDS
        # =========================================================
        elif view == "Category Boards":
            st.subheader("Sortable Category Leaderboards")

            if selected_window == "Season":
                cat_tbl = category_summary_for_window(df, season_weeks)
                window_label = "Season"
            elif selected_window == "Last 3 Weeks":
                cat_tbl = category_summary_for_window(df, last_3_weeks)
                window_label = f"Last 3 Weeks ({last_3_weeks[0]}-{last_3_weeks[-1]})"
            elif selected_window == "Last 5 Weeks":
                cat_tbl = category_summary_for_window(df, last_5_weeks)
                window_label = f"Last 5 Weeks ({last_5_weeks[0]}-{last_5_weeks[-1]})"
            else:
                cat_tbl = category_summary_for_window(df, [selected_week])
                window_label = f"Week {selected_week}"

            st.caption(window_label)

            cat_choice = st.selectbox("Focus Category", all_cats, index=0)
            ascending_sort = cat_choice in lower_is_better

            ordered_cols = ["Team", cat_choice, f"{cat_choice}_Rank"] + [c for c in all_cats if c != cat_choice]
            cat_tbl_show = cat_tbl.sort_values(cat_choice, ascending=ascending_sort)[ordered_cols].copy()

            st.dataframe(cat_tbl_show, use_container_width=True, hide_index=True)

            st.subheader("Category Rank Snapshot")
            heat_tbl = cat_tbl[["Team"] + [f"{c}_Rank" for c in all_cats]].copy()
            heat_tbl = heat_tbl.rename(columns={f"{c}_Rank": c for c in all_cats})
            st.dataframe(heat_tbl, use_container_width=True, hide_index=True)

        # =========================================================
        # SCHEDULE STRENGTH
        # =========================================================
        elif view == "Schedule Strength":
            st.subheader("Schedule Strength & Luck")

            st.markdown("""
            **How this works**
            - **Avg Opp Weekly Strength** = how strong opponents actually were in the week they faced you  
            - **Avg Opp Baseline Strength** = how strong those same opponents normally profile  
            - **Schedule Luck Index** = whether teams tended to catch opponents on especially hot weeks  
            """)

            sched_show = schedule_summary.copy().sort_values("Schedule Luck Index", ascending=False)

            st.dataframe(
                sched_show[[
                    "Team", "Weeks Played", "Avg Matchup Score",
                    "Avg Opp Weekly Strength", "Avg Opp Baseline Strength",
                    "Schedule Difficulty Index", "Schedule Luck Index"
                ]],
                use_container_width=True,
                hide_index=True
            )

            c1, c2 = st.columns(2)

            with c1:
                st.markdown("**Most Unlucky Teams**")
                unlucky = sched_show.sort_values("Schedule Luck Index", ascending=False).head(5)
                st.dataframe(
                    unlucky[["Team", "Schedule Luck Index", "Avg Opp Weekly Strength"]],
                    hide_index=True,
                    use_container_width=True
                )

            with c2:
                st.markdown("**Friendliest Schedule Luck**")
                lucky = sched_show.sort_values("Schedule Luck Index", ascending=True).head(5)
                st.dataframe(
                    lucky[["Team", "Schedule Luck Index", "Avg Opp Weekly Strength"]],
                    hide_index=True,
                    use_container_width=True
                )

            if not category_schedule.empty and len(category_schedule.columns) > 1:
                st.subheader("By-Category Schedule Pressure")
                st.caption("Positive values mean opponents tended to be hotter than normal in that category when facing that team.")
                st.dataframe(category_schedule, use_container_width=True, hide_index=True)

            scatter = alt.Chart(sched_show).mark_circle(size=140).encode(
                x=alt.X("Avg Opp Weekly Strength:Q", title="Avg Opp Weekly Strength"),
                y=alt.Y("Avg Matchup Score:Q", title="Avg Matchup Score"),
                tooltip=[
                    alt.Tooltip("Team:N"),
                    alt.Tooltip("Avg Matchup Score:Q", format=".2f"),
                    alt.Tooltip("Avg Opp Weekly Strength:Q", format=".2f"),
                    alt.Tooltip("Avg Opp Baseline Strength:Q", format=".2f"),
                    alt.Tooltip("Schedule Luck Index:Q", format=".2f")
                ],
                color=alt.Color("Team:N", legend=None)
            ).properties(height=420)

            st.subheader("Schedule Luck Scatter")
            st.altair_chart(scatter, use_container_width=True)

        # =========================================================
        # TEAM DEEP DIVE
        # =========================================================
        elif view == "Team Deep Dive":
            st.subheader("Team Deep Dive")

            deep_team_default = selected_team if selected_team != "All Teams" else team_list[0]
            deep_team = st.selectbox(
                "Choose Team",
                team_list,
                index=team_list.index(deep_team_default)
            )

            team_week = weekly_rank_df[weekly_rank_df["Team"] == deep_team].copy()
            team_season = season_roto[season_roto["Team"] == deep_team].copy()
            team_last3 = last3_roto[last3_roto["Team"] == deep_team].copy()
            team_last5 = last5_roto[last5_roto["Team"] == deep_team].copy()

            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Season Roto Rank", int(team_season["Overall Rank"].iloc[0]))
            with c2:
                st.metric("Last 3 Rank", int(team_last3["Overall Rank"].iloc[0]))
            with c3:
                st.metric("Last 5 Rank", int(team_last5["Overall Rank"].iloc[0]))

            profile_rows = []
            for cat in all_cats:
                profile_rows.append({
                    "Category": cat,
                    "Season Value": team_season[cat].iloc[0],
                    "Season Rank": team_season[f"{cat}_Rank"].iloc[0],
                    "Last 3 Value": team_last3[cat].iloc[0],
                    "Last 3 Rank": team_last3[f"{cat}_Rank"].iloc[0],
                    "Last 5 Value": team_last5[cat].iloc[0],
                    "Last 5 Rank": team_last5[f"{cat}_Rank"].iloc[0],
                })

            profile_df = pd.DataFrame(profile_rows)

            st.markdown("**Category Profile**")
            st.dataframe(profile_df, use_container_width=True, hide_index=True)

            wk_cat = team_week[["Week", "Team"] + [f"{c}_Rank" for c in all_cats]].copy()
            wk_cat = wk_cat.rename(columns={f"{c}_Rank": c for c in all_cats})

            long_wk_cat = wk_cat.melt(
                id_vars=["Week", "Team"],
                var_name="Category",
                value_name="Rank"
            )

            long_wk_cat["Week"] = long_wk_cat["Week"].astype(str)

            cat_rank_chart = alt.Chart(long_wk_cat).mark_line(point=True).encode(
                x=alt.X("Week:O"),
                y=alt.Y("Rank:Q", scale=alt.Scale(reverse=True)),
                color=alt.Color("Category:N"),
                tooltip=[
                    alt.Tooltip("Week:O"),
                    alt.Tooltip("Category:N"),
                    alt.Tooltip("Rank:Q", format=".1f")
                ]
            ).properties(height=450)

            st.markdown("**Weekly Category Rank Trend**")
            st.altair_chart(cat_rank_chart, use_container_width=True)

            team_sched = matchup_results[matchup_results["Team"] == deep_team].copy()
            if not team_sched.empty:
                c1, c2 = st.columns(2)

                with c1:
                    st.markdown("**Toughest Hot-Opponent Weeks**")
                    hottest_opp = team_sched.sort_values("Opponent Hotness", ascending=False).head(5)
                    st.dataframe(
                        hottest_opp[["Week", "Opp", "Matchup Score", "Opp Weekly Roto Pts", "Opponent Hotness"]],
                        use_container_width=True,
                        hide_index=True
                    )

                with c2:
                    st.markdown("**Friendliest Opponent Weeks**")
                    easiest_opp = team_sched.sort_values("Opponent Hotness", ascending=True).head(5)
                    st.dataframe(
                        easiest_opp[["Week", "Opp", "Matchup Score", "Opp Weekly Roto Pts", "Opponent Hotness"]],
                        use_container_width=True,
                        hide_index=True
                    )

        # =========================================================
        # WEEKLY MATCHUPS
        # =========================================================
        elif view == "Weekly Matchups":
            st.subheader("Weekly Matchup Board")

            matchup_week = st.selectbox(
                "Matchup Week",
                week_list,
                index=len(week_list) - 1,
                key="flub_matchup_week"
            )

            week_df = df[df["Week"] == matchup_week].copy()
            week_df = add_derived_rates(week_df)

            week_df["AVG"] = week_df["AVG_final"]
            week_df["OBP"] = week_df["OBP_final"]
            week_df["ERA"] = week_df["ERA_final"]
            week_df["WHIP"] = week_df["WHIP_final"]
            week_df["K/9"] = week_df["K9_final"]

            matchup_seen = set()

            for _, row in week_df.iterrows():
                team = row["Team"]
                opp = row["Opp"]
                key = tuple(sorted([team, opp]))

                if key in matchup_seen:
                    continue
                matchup_seen.add(key)

                opp_row = week_df[(week_df["Team"] == opp) & (week_df["Opp"] == team)]
                if opp_row.empty:
                    continue

                opp_row = opp_row.iloc[0]

                cat_results = []
                team_cat_wins = 0
                opp_cat_wins = 0
                ties = 0

                for cat in all_cats:
                    t_val = row[cat]
                    o_val = opp_row[cat]

                    if pd.isna(t_val) or pd.isna(o_val):
                        winner = "—"
                    elif cat in lower_is_better:
                        if t_val < o_val:
                            winner = team
                            team_cat_wins += 1
                        elif t_val > o_val:
                            winner = opp
                            opp_cat_wins += 1
                        else:
                            winner = "Tie"
                            ties += 1
                    else:
                        if t_val > o_val:
                            winner = team
                            team_cat_wins += 1
                        elif t_val < o_val:
                            winner = opp
                            opp_cat_wins += 1
                        else:
                            winner = "Tie"
                            ties += 1

                    cat_results.append({
                        "Category": cat,
                        team: t_val,
                        opp: o_val,
                        "Winner": winner
                    })

                card_df = pd.DataFrame(cat_results)

                st.markdown(f"### Week {matchup_week}: {team} vs {opp}")
                st.write(f"**Final score:** {team_cat_wins}-{opp_cat_wins}-{ties}")
                st.dataframe(card_df, use_container_width=True, hide_index=True)
                st.markdown("---")
## end of code