import streamlit as st
import pandas as pd
import subprocess
import os
import psutil
import time
from datetime import datetime
import altair as alt
import plotly.express as px
import uuid
import base64
import json
from streamlit_autorefresh import st_autorefresh

from supports import (
    sendEmail,
    loadRecentMachineData,
    loadLatestMachineData,
    loadInventory,
    loadUserDb,
    validateLogin,
    loadMaintenanceTasks,
    confirmMaintenanceTask,
    generatePendingReport,
    generateCompletedReport
)

# Page configuration
st.set_page_config(
    page_title="MachineSync Home",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🏭"
)

st_autorefresh(interval=10000, limit=None, key="auto-refresh")

# Custom CSS for styling
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Poppins', sans-serif !important;
    }

    /* === Sidebar Panel Styling === */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #e8d3c0, #262730);
        padding: 2rem 1rem 1rem 1rem;
        color: #3b2f2f;
    }

    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #3b2f2f !important;
        font-size: 28px;
        font-weight: 700;
        margin-bottom: 1rem;
    }

    /* === Sidebar Radio Button Styling === */
    [data-testid="stSidebar"] .stRadio > label {
        font-size: 18px !important;
        font-weight: 600 !important;
        color: #3b2f2f !important;
        padding: 0.6rem 1rem;
        display: block;
        border-radius: 8px;
        transition: all 0.3s ease;
    }

    [data-testid="stSidebar"] .stRadio > label:hover {
        background-color: rgba(80, 40, 20, 0.08);
        box-shadow: 0 0 10px rgba(80, 40, 20, 0.2);
        cursor: pointer;
    }

    [data-testid="stSidebar"] .stRadio > div[role='radiogroup'] > label[data-selected="true"] {
        background-color: rgba(80, 40, 20, 0.15);
        font-weight: 700;
    }

    /* === Sidebar Text Font Enforcer === */
    [data-testid="stSidebar"] * {
        font-family: 'Poppins', sans-serif !important;
        font-weight: 600;
    }

    /* === Logout Button Styling === */
    [data-testid="stSidebar"] button[kind="secondary"] {
        background-color: #ffffff15;
        color: #3b2f2f;
        border: 1px solid #00000030;
        border-radius: 6px;
        margin-top: 1rem;
        font-size: 16px;
        font-weight: 600;
        font-family: 'Poppins', sans-serif !important;
    }

    [data-testid="stSidebar"] button[kind="secondary"]:hover {
        background-color: #ffffff25;
        box-shadow: 0 0 8px rgba(0, 0, 0, 0.2);
    }

    /* === Page and Card Styling === */
    .stApp {
        background-color: #fdfbf7;
    }

    .main .block-container {
        padding: 2rem;
        max-width: 1400px;
    }

    .card {
        background: white;
        border-radius: 10px;
        padding: 1.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }

    /* === Table Styling === */
    .styled-table {
        width: 100%;
        border-collapse: collapse;
        font-family: 'Poppins', sans-serif;
    }
    .styled-table th, .styled-table td {
        border: 1px solid #dddddd;
        text-align: center;
        padding: 8px;
        font-weight: bold;
    }
    .styled-table th {
        background-color: #f2f2f2;
        color: #333;
    }
    .styled-table td.error {
        background-color: #ffcccc;
        color: red;
    }

    /* === Footer Styling === */
    .footer {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: #3b2f2f;
        color: white;
        text-align: center;
        padding: 0.5rem;
        font-size: 0.9rem;
        z-index: 999;
        font-family: 'Poppins', sans-serif !important;
    }

    /* === Status Color Tags === */
    .status-running { color: #28a745; }
    .status-idle { color: #ffc107; }
    .status-error { color: #dc3545; }
    </style>

    <div class="footer">
        MachineSync Home | ☃️ Built by Team Maintenance ☃️ | May 2025          
    </style>
""", unsafe_allow_html=True)

# Machine Operation check
def is_machine_running(script_name="machine_operation.py"):
    for proc in psutil.process_iter(["pid", "cmdline"]):
        try:
            cmdline = proc.info.get("cmdline", [])
            if isinstance(cmdline, list) and script_name in cmdline and proc.info["pid"] != os.getpid():
                return True
        except Exception:
            continue
    return False

if not os.path.exists("machines.csv") or not is_machine_running():
    try:
        subprocess.Popen(["python", "machine_operation.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)
    except Exception as e:
        st.error(f"Failed to read machine data: {e}")

# Authentication of login
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

if not st.session_state.logged_in:
    st.title("🔐 User Login")
    with st.container():
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            with st.form("login_form"):
                username = st.text_input("Username", placeholder="Enter username")
                password = st.text_input("Password", type="password", placeholder="Enter password")
                submit = st.form_submit_button("Login", type="primary")
                if submit:
                    if validateLogin(username, password):
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")
    st.stop()

# Set the Sidebar
with st.sidebar:
    st.title("🏭 Equipment Status")
    st.markdown(f"**Welcome, `{st.session_state.username}`** 🔅")
    tab = st.radio("Navigation", [
        "🏠 Home",
        "🗄️ Inventory",
        "🛠️ Maintenance",
        "👥 Users",
        "📩 Reports"
    ], label_visibility="collapsed")
    
    if st.button("🚪🗝️ Logout", type="secondary"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()

# Status icon mapping
def status_icon(status):
    return status.strip().capitalize()

# Home Tab
if tab == "🏠 Home":
    st.title("🏭 Operation & Maintenance Tracking System")
    
    df = loadLatestMachineData()
    df_full = loadRecentMachineData(minutes=10) 

    if df is not None:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        running = (df['status'] == 'running').sum()
        idle = (df['status'] == 'idle').sum()
        error= (df['status'] == 'error').sum()
        total = len(df)
        percent_running = (running / total * 100) if total else 0

        # Display Date and current time
        now = datetime.now()
        today_date = now.strftime("%A, %B %d, %Y")
        current_time = now.strftime("%I:%M %p")

        st.markdown(f"""
            <div style='font-size:28px; color:#444; padding-bottom:0.5rem;'>
                🗓 <b>{today_date}</b> | ⏱ <b>{current_time}</b>
            </div>
        """, unsafe_allow_html=True)

        # Machine Status Icons
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"<div style='font-size:24px;'> ✳️ <b>Running</b><br><span style='font-size:20px'>{running}/{total}</span></div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div style='font-size:24px;'> ⚠️ <b>Idle</b><br><span style='font-size:20px'>{idle}</span></div>", unsafe_allow_html=True)
        with col3:
            st.markdown(f"<div style='font-size:24px;'> 🛑 <b>Error</b><br><span style='font-size:20px'>{error}</span></div>", unsafe_allow_html=True)
        with col4:
            st.markdown(f"<div style='font-size:24px;'>〽️ <b> % Operating </b><br><span style='font-size:20px'>{percent_running:.1f}%</span></div>", unsafe_allow_html=True)

        # Error Notification Mail
        errors = df[df["status"] == "error"]
        if not errors.empty:
            err_ids = ', '.join(errors["machine_id"].astype(str))
            st.error(f"📌 Machines in ERROR state: {err_ids}")
            sendEmail(
                recipient="kinsyoung@gmail.com",
                subject="🚨 Machine Error Reporting",
                message=f"Please attend to Machines  {err_ids} which have entered ERROR state:"
            )

        # Machine Operation Status
        st.markdown("#### 📜 Machine Operation Status")

        #Parameters to view 
        df_view = df[["machine_id", "timestamp", "status", "temperature", "vibration", "rpm", "cumulative_hours", "daily_hours"]].copy()
        df_view["status"] = df_view["status"].apply(status_icon)
        #df_html = df_view.to_html(index=False, classes="styled-table")

        # Convert temp/vibration/status highlights 
        def apply_html_highlights(row):
            row = row.copy()
            if row["status"].lower() == "error":
                row["status"] = f'<td class="error">{row["status"]}</td>'
            else:
                row["status"] = f"<td>{row['status']}</td>"

            temp_style = ' class="error"' if row["temperature"] > 250 else ''
            vib_style = ' class="error"' if row["vibration"] > 0.9 else ''

            row["temperature"] = f'<td{temp_style}>{row["temperature"]:.2f}</td>'
            row["vibration"] = f'<td{vib_style}>{row["vibration"]:.2f}</td>'

            for col in ["machine_id", "timestamp", "rpm", "cumulative_hours", "daily_hours"]:
                row[col] = f"<td>{row[col]}</td>"

            return row

        # Build Table row-by-row
        rows_html = ""
        for _, row in df_view.iterrows():
            row_html = apply_html_highlights(row)
            row_str = "<tr>" + "".join(row_html.values) + "</tr>"
            rows_html += row_str

        headers = "".join([f"<th>{col}</th>" for col in df_view.columns])
        table_html = f"""
        <table class="styled-table">
            <thead><tr>{headers}</tr></thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
        """

        # Display in Streamlit
        st.markdown(table_html, unsafe_allow_html=True)

        # Highlight when temperature is above 250
        def highlight_temperature(val):
            if val > 250:
                return "background-color: #ffcccc; color: red; font-weight: bold;"
            return ""

        # Highlight when vibration is above 0.9
        def highlight_vibration(val):
            if val > 0.9:
                return "background-color: #ffcccc; color: red; font-weight: bold;"
            return ""

        # Highlight when machine is in Error state
        def highlight_status(val):
            if "error" in str(val).lower():
                return "background-color: #ffcccc; color: red; font-weight: bold;"
            return ""

        styled_table = (
            df_view.style
            .hide(axis='index')
            .set_properties(**{"font-weight": "bold"})
            .map(highlight_status, subset=["status"])
            .map(highlight_temperature, subset=["temperature"])
            .map(highlight_vibration, subset=["vibration"])
        )

        st.markdown("#### 📊 Machine Status Overview")
        col1, col2 = st.columns([2,1])

        # Plot the Pie chart using status_display
        with col1:
                df = df.copy()
                df['status_display'] = df['status'].str.capitalize()
                status_counts = df.groupby('status_display').size().reset_index(name='count')
                fig = px.pie(
                    status_counts,
                    values='count',
                    names='status_display',
                    title='Status Distribution',
                    color='status_display',
                    color_discrete_map={'Running': '#28a745', 'Idle': '#ffc107', 'Error': '#dc3545'}
                )
                fig.update_layout(margin=dict(t=50, b=0, l=0, r=0))
                fig.update_traces(textfont=dict(size=18, family="Arial Black"))
                #fig.update_layout(legend=dict(font=dict(size=16, family="Arial Black")))
                st.plotly_chart(fig, use_container_width=True)

        # Temperature Trend Chart
        with col2:
            if df_full is not None and not df_full.empty:
                temp_chart = alt.Chart(df_full).mark_line().encode(
                    x='timestamp:T',
                    y='temperature:Q',
                    color='machine_id:N',
                    tooltip=['machine_id', 'temperature', 'timestamp']
                ).properties(
                    title='Temperature Trends',
                    height=400
                )
                st.altair_chart(temp_chart, use_container_width=True)
            else:
                st.warning("⏳ Not enough recent data to display temperature trends.")


# Inventory Tab
elif tab == "🗄️ Inventory":
    st.title("📒 Machine Inventory")
    # Map machines_inventory.csv to the related machine model in technical_specs.json file and give tabulated details
    df_inventory = pd.read_csv("machines_inventory.csv")

    try:
        with open("technical_specs.json", "r") as f:
            technical_specs_by_model = json.load(f)
    except FileNotFoundError:
        st.error("Error: technical_specs.json not found.")
        technical_specs_by_model = {}
    except json.JSONDecodeError:
        st.error("Error: Invalid JSON format in technical_specs.json.")
        technical_specs_by_model = {}

    model_icon_map = {
        "CTX beta 1250 TC": "⚙️",
        "LTC-50i SERIES": "🦠",
        "LTC-20i SERIES": "🦾",
        "iT SERIES": "🏗️",
        "NTX 3000": "☸️",
        "VSC 500": "☸"
    }

    machines = df_inventory.to_dict(orient="records")
    cols = st.columns(2)

    for i, machine in enumerate(machines):
        col = cols[i % 2]
        model = machine["Model"].strip()
        icon = model_icon_map.get(model, "📦")
        specs_raw = technical_specs_by_model.get(model)

        with col:
            with st.container():
                st.markdown(f"""
                    <div class="inventory-col">
                        <h3>{icon} {machine['MACHINE NUMBER']} — <span style='color:#1a3c6e'>{model}</span></h3>
                        <p>📅 Installation Date: {machine['INSTALLATION DATE']} | 🔢 Serial No: {machine['SERIAL  NUMBER']} | 🏭 Manufacturer: {machine['MANUFACTURER']}</p>
                """, unsafe_allow_html=True)

                if specs_raw:
                    with st.expander("📘 Technical Specifications"):
                        specs_list = []
                        for spec_block in specs_raw:
                            valid_keys = [k for k in spec_block.keys() if k not in ['mm', 'in', 'mm (in)']]
                            if len(valid_keys) >= 2:
                                label = spec_block[valid_keys[0]]
                                value = spec_block[valid_keys[1]]
                                unit = spec_block.get("mm") or spec_block.get("in") or spec_block.get("mm (in)") or ""
                                specs_list.append({
                                    "Specification": label,
                                    "Value": value,
                                    "Unit": unit
                                })

                        specs_df = pd.DataFrame(specs_list).astype(str)
                        st.dataframe(specs_df, use_container_width=True)
                else:
                    st.info("ℹ️ No technical specs available for this machine.")

                st.markdown("</div>", unsafe_allow_html=True)

# Maintenance Tab
elif tab == "🛠️ Maintenance":
    st.title("🧰 Maintenance Tasks Due")

    Maintenance = loadMaintenanceTasks()

    for machine_id, df_due in Maintenance.items():
        if not df_due.empty:
            st.markdown(f"### 🛠️ Machine `{machine_id}`")
            for _, row in df_due.iterrows():
                article = row["Article Number"]
                name = row["Name"]
                mfr = row.get("Manufacturer", "Unknown")
                hours_left = round(row.get("Hours Left", 0), 2)

                checkbox_key = f"checkbox-{machine_id}-{article}"
                with st.container():
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"""
                            <div style="background-color: #f5f9ff; padding: 0.2rem 0.6rem; border-radius: 20px; border-left: 4px solid #1a3c6e; margin-bottom: 2px;">
                                <h5 style="margin-bottom: 0.2rem; font-size: 15px;">🔩 {name}</h5>
                                <p style="margin-bottom: 0.2rem; font-size: 15px;"><b>🧾 Article:</b> {article} | <b>🏭 Manufacturer:</b> {mfr}</p>
                                <p style="color: #dc3545; font-size: 15px;"><b>⏳ Hours Left:</b> {hours_left}</p>
                        """, unsafe_allow_html=True)

                        if st.checkbox("💾 Save Maintenance Task ", key=checkbox_key):
                            confirmMaintenanceTask(machine_id, article)
                            st.success(f"✅ Maintenance/Replacement Task Completed and Saved for **{name}**")
                    with col2:
                        st.empty()


# Users Tab
elif tab == "👥 Users":
    st.title("👤 User Management")
    
    users = loadUserDb()
    is_admin = users.get(st.session_state.username, {}).get("role", "").strip().lower() == "admin"
    
    if is_admin:
        st.subheader("🔒 User List")
        df = pd.DataFrame.from_dict(users, orient="index").drop(index=st.session_state.username, errors='ignore')
        st.dataframe(df, use_container_width=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("##### ✖ Remove User")
            user_to_remove = st.selectbox(
                "Select user to remove",
                [u for u in users if u != st.session_state.username],
                key="remove_user"
            )
            if st.button("Remove User", key="remove_button"):
                if user_to_remove in users:
                    del users[user_to_remove]
                    pd.DataFrame(users).T.to_csv("users.csv")
                    st.success(f"User '{user_to_remove}' removed.")
                    st.rerun()
        
        with col2:
            st.markdown("##### ✚ Add User")
            with st.form("add_user_form"):
                new_user = st.text_input("Username", placeholder="Enter username")
                new_pass = st.text_input("Password", type="password", placeholder="Enter password")
                new_role = st.selectbox("Role", ["user", "admin"], key="new_role")
                if st.form_submit_button("Add User"):
                    if new_user not in users:
                        users[new_user] = {"password": new_pass, "role": new_role}
                        pd.DataFrame(users).T.to_csv("users.csv")
                        st.success("User added successfully.")
                        st.rerun()
    else:
        st.warning("Only admins can manage users.")

# Maintenance Report Tab
elif tab == "📩 Reports":
    st.title("📝 Maintenance Reports")
    
    with st.container():
        st.markdown("### Download Reports")
        
        col1, col2 = st.columns(2)      
        with col1:
            if st.button("⏳ Download Pending Tasks"):
                pending_path = generatePendingReport()
                if pending_path:
                    with open(pending_path, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode()
                        href = f'<a href="data:file/csv;base64,{b64}" download="pending_maintenance.csv">📥 Download Pending</a>'
                        st.markdown(href, unsafe_allow_html=True)
                else:
                    st.warning("No pending tasks found.")

        with col2:
            if st.button("✓ Download Completed Tasks"):
                completed_path = generateCompletedReport()
                if completed_path:
                    with open(completed_path, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode()
                        href = f'<a href="data:file/csv;base64,{b64}" download="completed_maintenance.csv">📥 Download Completed</a>'
                        st.markdown(href, unsafe_allow_html=True)
                else:
                    st.info("No completed records found.")





