"""
Responsible Insurance in the States — Legislative Tracker
Streamlit web interface for browsing, filtering, and analyzing insurance bills.

Run with:
    streamlit run app.py
"""

import json
import sqlite3
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))
from config import DB_PATH

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Insurance Bill Tracker",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Data loading (cached so it only runs once per session)
# ---------------------------------------------------------------------------

@st.cache_data
def load_bills():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("""
        SELECT
            b.bill_id,
            b.state,
            b.bill_number,
            b.title,
            b.summary,
            b.status,
            b.session,
            b.introduced_date,
            b.last_action_date,
            b.bill_url,
            b.document_link,
            b.keyword_tags,
            b.full_text,
            GROUP_CONCAT(DISTINCT bs.legislator_name || ' (' || COALESCE(bs.legislator_party, '?') || ')') AS sponsors
        FROM bills b
        LEFT JOIN bill_sponsors bs ON b.bill_id = bs.bill_id
        GROUP BY b.bill_id
        ORDER BY b.last_action_date DESC NULLS LAST
    """, conn)
    conn.close()

    def parse_tags(t):
        if not t:
            return []
        try:
            return json.loads(t)
        except Exception:
            return []

    df["tags"] = df["keyword_tags"].apply(parse_tags)
    df["tags_display"] = df["tags"].apply(
        lambda tags: ", ".join(t.replace("_", " ").title() for t in tags)
    )
    return df


@st.cache_data
def load_hearings():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("""
        SELECT
            h.id,
            h.bill_id,
            b.state,
            b.bill_number,
            b.title AS bill_title,
            h.title,
            h.start_dt,
            h.end_dt,
            h.status,
            h.location,
            h.description,
            h.event_link
        FROM hearings h
        LEFT JOIN bills b ON h.bill_id = b.bill_id
        ORDER BY h.start_dt DESC NULLS LAST
    """, conn)
    conn.close()
    return df


@st.cache_data
def load_sponsors():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("""
        SELECT
            bs.legislator_name,
            bs.legislator_party,
            bs.role,
            bs.district,
            bs.state_code,
            bs.in_office,
            bs.ballotpedia_url,
            bs.follow_the_money_url,
            COUNT(DISTINCT bs.bill_id) AS bill_count,
            GROUP_CONCAT(DISTINCT b.state) AS states_active
        FROM bill_sponsors bs
        LEFT JOIN bills b ON bs.bill_id = b.bill_id
        GROUP BY bs.legislator_name
        ORDER BY bill_count DESC
    """, conn)
    conn.close()
    return df


# ---------------------------------------------------------------------------
# Similarity engine (cached so index is only built once)
# ---------------------------------------------------------------------------

@st.cache_resource
def load_similarity_engine():
    try:
        from similarity.engine import SimilarityEngine
        engine = SimilarityEngine()
        engine.build_index()
        return engine
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CATEGORY_LABELS = {
    "state_insurance_residual_markets":           "State Insurance & Residual Markets",
    "fortification_programs":                     "Fortification Programs",
    "non_admitted_market":                        "Non-Admitted Market",
    "consumer_protections_and_market_conduct":    "Consumer Protections & Market Conduct",
    "catastrophe_modeling":                       "Catastrophe Modeling",
    "data_and_study":                             "Data & Study",
    "fossil_fuel_accountability":                 "Fossil Fuel Accountability",
    "state_insurance_office_regulatory_powers":   "State Insurance Office / Regulatory Powers",
    "property_disclosure":                        "Property Disclosure",
    "building_codes_land_use":                    "Building Codes / Land Use",
    "climate_resilience_and_risk_mitigation":     "Climate Resilience & Risk Mitigation",
    "reinsurance":                                "Reinsurance",
    "litigation_and_tort_reform":                 "Litigation & Tort Reform",
    "rate_regulation":                            "Rate Regulation",
    "climate_risk_disclosure":                    "Climate Risk Disclosure",
    "anti_esg":                                   "Anti-ESG",
}

STATUS_COLORS = {
    "Introduced":             "🔵",
    "In Committee":           "🟡",
    "Crossed Over":           "🟠",
    "Passed":                 "🟢",
    "Signed/Enacted/Adopted": "✅",
    "Dead":                   "🔴",
    "Vetoed":                 "❌",
}

def status_badge(status):
    icon = STATUS_COLORS.get(status, "⚪")
    return f"{icon} {status}"


# ---------------------------------------------------------------------------
# Session state helpers
# ---------------------------------------------------------------------------

def set_selected_bill(bill_id: str):
    st.session_state["selected_bill_id"] = bill_id
    st.session_state["page"] = "🔍 Bill Detail"


def get_selected_bill():
    return st.session_state.get("selected_bill_id")


# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------

def sidebar_filters(df):
    st.sidebar.title("🏛️ Insurance Bill Tracker")
    st.sidebar.markdown("---")

    all_states = sorted(df["state"].dropna().unique().tolist())
    selected_states = st.sidebar.multiselect("State", all_states)

    all_statuses = sorted(df["status"].dropna().unique().tolist())
    selected_statuses = st.sidebar.multiselect("Bill Status", all_statuses)

    all_tags = sorted(CATEGORY_LABELS.keys())
    tag_options = {CATEGORY_LABELS[t]: t for t in all_tags}
    selected_tag_labels = st.sidebar.multiselect("Category", list(tag_options.keys()))
    selected_tags = [tag_options[l] for l in selected_tag_labels]

    search = st.sidebar.text_input("Search bills", placeholder="e.g. FAIR Plan, rate filing...")

    st.sidebar.markdown("---")
    st.sidebar.caption(f"{len(df)} total bills across {df['state'].nunique()} states")

    return selected_states, selected_statuses, selected_tags, search


def apply_filters(df, states, statuses, tags, search):
    if states:
        df = df[df["state"].isin(states)]
    if statuses:
        df = df[df["status"].isin(statuses)]
    if tags:
        df = df[df["tags"].apply(lambda t: any(tag in t for tag in tags))]
    if search:
        s = search.lower()
        df = df[
            df["title"].str.lower().str.contains(s, na=False) |
            df["summary"].str.lower().str.contains(s, na=False) |
            df["bill_number"].str.lower().str.contains(s, na=False)
        ]
    return df


# ---------------------------------------------------------------------------
# Bill detail panel (shared between tracker click-through and detail view)
# ---------------------------------------------------------------------------

def render_bill_detail(bill, all_bills_df):
    """Render the full detail panel for a single bill row."""

    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader(f"{bill.state} {bill.bill_number}")
        st.markdown(f"**{bill.title}**")
    with col2:
        if pd.notna(bill.status):
            st.markdown(f"**Status:** {status_badge(bill.status)}")
        if pd.notna(bill.last_action_date):
            st.markdown(f"**Last Action:** {bill.last_action_date}")
        if pd.notna(bill.introduced_date):
            st.markdown(f"**Introduced:** {bill.introduced_date}")

    if bill.tags:
        tag_str = " · ".join(
            f"`{CATEGORY_LABELS.get(t, t.replace('_', ' ').title())}`"
            for t in bill.tags
        )
        st.markdown(f"**Categories:** {tag_str}")

    st.markdown("---")

    if pd.notna(bill.summary) and bill.summary:
        st.markdown("**Summary**")
        st.write(bill.summary)

    if pd.notna(bill.sponsors) and bill.sponsors:
        st.markdown("**Sponsors**")
        st.write(bill.sponsors)

    link_cols = st.columns(2)
    if pd.notna(bill.bill_url) and bill.bill_url:
        link_cols[0].markdown(f"[View on BillTrack50]({bill.bill_url})")
    if pd.notna(bill.document_link) and bill.document_link:
        link_cols[1].markdown(f"[View Document]({bill.document_link})")

    # Hearings
    hearings_df = load_hearings()
    bill_hearings = hearings_df[hearings_df["bill_id"] == bill.bill_id]
    if not bill_hearings.empty:
        st.markdown("---")
        st.markdown("**Hearings**")
        for _, h in bill_hearings.iterrows():
            date_str = str(h.get("start_dt", "") or "")[:10] or "TBD"
            parts = [f"📅 {date_str}"]
            if pd.notna(h.get("title")) and h["title"]:
                parts.append(h["title"])
            if pd.notna(h.get("location")) and h["location"]:
                parts.append(h["location"])
            line = " — ".join(parts)
            if pd.notna(h.get("event_link")) and h["event_link"]:
                line += f" · [Link]({h['event_link']})"
            st.markdown(line)

    # Similar bills
    st.markdown("---")
    st.markdown("**Similar Bills**")

    if pd.isna(bill.full_text) or not bill.full_text:
        st.caption("Full text not yet available — run LegiScan to enable similarity search.")
        return

    engine = load_similarity_engine()
    if engine is None:
        st.caption("Similarity engine unavailable.")
        return

    top_n = st.slider("Number of similar bills", 3, 20, 8, key=f"sim_{bill.bill_id}")
    similar = engine.find_similar(bill.bill_id, top_n=top_n)

    if not similar:
        st.caption("No similar bills found.")
        return

    sim_rows = []
    for s in similar:
        tags_str = ", ".join(CATEGORY_LABELS.get(t, t) for t in s.get("tags", []))
        sim_rows.append({
            "Score": s["score"],
            "State": s["state"],
            "Bill": s["bill_number"],
            "Title": s["title"][:70] + ("..." if len(s["title"]) > 70 else ""),
            "Categories": tags_str,
            "_bill_id": s["bill_id"],
        })

    sim_df = pd.DataFrame(sim_rows)

    # Allow clicking into a similar bill
    selected = st.dataframe(
        sim_df.drop(columns=["_bill_id"]),
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key=f"sim_table_{bill.bill_id}",
    )
    if selected and selected.selection.rows:
        clicked_id = sim_rows[selected.selection.rows[0]]["_bill_id"]
        set_selected_bill(clicked_id)
        st.rerun()


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

def view_tracker(df):
    st.header("Bill Tracker")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Bills", len(df))
    col2.metric("States", df["state"].nunique())
    active = df[df["status"].isin(["Introduced", "In Committee", "Crossed Over", "Passed"])]
    col3.metric("Active Bills", len(active))
    enacted = df[df["status"] == "Signed/Enacted/Adopted"]
    col4.metric("Enacted", len(enacted))

    st.markdown("---")
    st.caption("Click any row to open bill detail.")

    # Build display table — keep bill_id as hidden index for selection mapping
    display_df = df[["bill_id", "state", "bill_number", "title", "status", "last_action_date", "tags_display"]].copy()
    display_df["status_display"] = display_df["status"].apply(
        lambda s: status_badge(s) if pd.notna(s) else ""
    )
    display_df["title_short"] = display_df["title"].str[:80].fillna("")

    table_df = display_df[["state", "bill_number", "title_short", "status_display", "last_action_date", "tags_display"]].copy()
    table_df.columns = ["State", "Bill", "Title", "Status", "Last Action", "Categories"]

    selected = st.dataframe(
        table_df,
        use_container_width=True,
        hide_index=True,
        height=520,
        on_select="rerun",
        selection_mode="single-row",
        key="tracker_table",
    )

    if selected and selected.selection.rows:
        row_idx = selected.selection.rows[0]
        clicked_bill_id = display_df.iloc[row_idx]["bill_id"]
        set_selected_bill(clicked_bill_id)
        st.rerun()

    st.caption(f"Showing {len(df)} bills")


def view_bill_detail(df):
    st.header("Bill Detail")

    # --- Search box ---
    search_query = st.text_input(
        "Search for a bill",
        placeholder="Type a bill number, state, keyword, or sponsor name...",
        key="bill_detail_search",
    )

    # If we arrived here from a click, pre-populate with that bill
    preselected_id = get_selected_bill()

    if search_query:
        q = search_query.lower()
        matches = df[
            df["title"].str.lower().str.contains(q, na=False) |
            df["bill_number"].str.lower().str.contains(q, na=False) |
            df["state"].str.lower().str.contains(q, na=False) |
            df["summary"].str.lower().str.contains(q, na=False) |
            df["sponsors"].str.lower().str.contains(q, na=False)
        ]

        if matches.empty:
            st.info("No bills match your search.")
            return

        if len(matches) == 1:
            # Exactly one match — go straight to detail
            bill = matches.iloc[0]
        else:
            # Multiple matches — show a small picker
            st.caption(f"{len(matches)} bills match. Select one:")
            match_options = {
                f"{row.state} {row.bill_number} — {row.title[:70]}": row.bill_id
                for row in matches.head(30).itertuples()
            }
            chosen_label = st.radio("", list(match_options.keys()), label_visibility="collapsed")
            chosen_id = match_options[chosen_label]
            bill = df[df["bill_id"] == chosen_id].iloc[0]

    elif preselected_id:
        # Arrived via click from tracker or similar bills table
        match = df[df["bill_id"] == preselected_id]
        if match.empty:
            st.info("Selected bill not found. Try searching above.")
            return
        bill = match.iloc[0]

    else:
        st.info("Search for a bill above, or click any row in the Bill Tracker.")
        return

    st.markdown("---")
    render_bill_detail(bill, df)


def view_dashboard(df):
    st.header("Dashboard")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Bills by Status")
        status_counts = df["status"].value_counts().reset_index()
        status_counts.columns = ["Status", "Count"]
        st.bar_chart(status_counts.set_index("Status"))

    with col2:
        st.subheader("Bills by State")
        state_counts = df["state"].value_counts().head(15).reset_index()
        state_counts.columns = ["State", "Count"]
        st.bar_chart(state_counts.set_index("State"))

    st.markdown("---")

    st.subheader("Bills by Category")
    tag_counts = {}
    for tags in df["tags"]:
        for tag in tags:
            label = CATEGORY_LABELS.get(tag, tag)
            tag_counts[label] = tag_counts.get(label, 0) + 1

    if tag_counts:
        tag_df = pd.DataFrame(
            sorted(tag_counts.items(), key=lambda x: x[1], reverse=True),
            columns=["Category", "Bills"]
        )
        st.bar_chart(tag_df.set_index("Category"))

    st.markdown("---")

    st.subheader("Recently Active Bills")
    recent = df[df["last_action_date"].notna()].head(10)[
        ["state", "bill_number", "title", "status", "last_action_date"]
    ].copy()
    recent.columns = ["State", "Bill", "Title", "Status", "Last Action"]
    recent["Status"] = recent["Status"].apply(lambda s: status_badge(s) if pd.notna(s) else "")
    recent["Title"] = recent["Title"].str[:70]
    st.dataframe(recent, use_container_width=True, hide_index=True)


def view_legislators(df):
    st.header("Legislators")

    sponsors_df = load_sponsors()

    col1, col2 = st.columns(2)
    with col1:
        party_filter = st.multiselect("Party", ["D", "R", "I"])
    with col2:
        search = st.text_input("Search by name", placeholder="e.g. Chang")

    filtered = sponsors_df.copy()
    if party_filter:
        filtered = filtered[filtered["legislator_party"].isin(party_filter)]
    if search:
        filtered = filtered[
            filtered["legislator_name"].str.lower().str.contains(search.lower(), na=False)
        ]

    st.metric("Legislators shown", len(filtered))
    st.markdown("---")

    display = filtered[[
        "legislator_name", "legislator_party", "role",
        "district", "states_active", "bill_count"
    ]].copy()
    display.columns = ["Name", "Party", "Role", "District", "States", "Bills Sponsored"]
    st.dataframe(display, use_container_width=True, hide_index=True, height=600)


def view_hearings():
    st.header("Hearings")

    hearings_df = load_hearings()

    if hearings_df.empty:
        st.info("No hearings data available.")
        return

    st.metric("Total Hearings", len(hearings_df))
    st.markdown("---")

    display = hearings_df[[
        "state", "bill_number", "bill_title", "title",
        "start_dt", "status", "location"
    ]].copy()
    display.columns = ["State", "Bill", "Bill Title", "Hearing", "Date", "Status", "Location"]
    display["Date"] = display["Date"].str[:10]
    display["Bill Title"] = display["Bill Title"].str[:50]
    st.dataframe(display, use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # Initialise session state
    if "page" not in st.session_state:
        st.session_state["page"] = "📋 Bill Tracker"
    if "selected_bill_id" not in st.session_state:
        st.session_state["selected_bill_id"] = None

    df = load_bills()
    states, statuses, tags, search = sidebar_filters(df)
    filtered_df = apply_filters(df, states, statuses, tags, search)

    page = st.sidebar.radio(
        "View",
        ["📋 Bill Tracker", "🔍 Bill Detail", "📊 Dashboard", "👤 Legislators", "📅 Hearings"],
        index=["📋 Bill Tracker", "🔍 Bill Detail", "📊 Dashboard", "👤 Legislators", "📅 Hearings"].index(
            st.session_state["page"]
        ),
        key="nav_radio",
    )
    # Keep session state in sync if user manually clicks the nav
    st.session_state["page"] = page

    if page == "📋 Bill Tracker":
        view_tracker(filtered_df)
    elif page == "🔍 Bill Detail":
        view_bill_detail(df)   # always pass full df so click-through works even with filters active
    elif page == "📊 Dashboard":
        view_dashboard(filtered_df)
    elif page == "👤 Legislators":
        view_legislators(filtered_df)
    elif page == "📅 Hearings":
        view_hearings()


if __name__ == "__main__":
    main()
