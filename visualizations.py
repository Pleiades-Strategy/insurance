"""
Insurance Bills Visualizations
Generates two charts:
  1. Choropleth map — bills by state, colored by enactment rate
  2. Stacked bar — "state of play" by issue area and bill status
"""

import sqlite3
import json
import os
import collections
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
import matplotlib.cm as cm
import numpy as np
import pandas as pd

DB_PATH = "/sessions/nifty-laughing-shannon/mnt/bill_collection/data/insurance_bills.db"
OUT_DIR = "/sessions/nifty-laughing-shannon/mnt/bill_collection"

# ── colour palette ──────────────────────────────────────────────────────────
STATUS_COLORS = {
    "Signed/Enacted/Adopted": "#2a9d8f",
    "Crossed Over":           "#57cc99",
    "Passed":                 "#80ed99",
    "In Committee":           "#f4a261",
    "Introduced":             "#f9c74f",
    "Dead":                   "#e76f51",
    "Vetoed":                 "#c1121f",
}

# ── load data ────────────────────────────────────────────────────────────────
def load_data():
    conn = sqlite3.connect(DB_PATH)
    bills = pd.read_sql("SELECT bill_id, state, status, keyword_tags FROM bills", conn)
    conn.close()
    return bills


# ════════════════════════════════════════════════════════════════════════════
# 1.  CHOROPLETH MAP
# ════════════════════════════════════════════════════════════════════════════

# State abbreviation → (center_x, center_y) in a simple tile-grid layout
# This is a standard "statebins" layout so we don't need a shapefile
STATE_GRID = {
    "AK": (0, 0), "HI": (1, 0),
    "WA": (1, 9), "OR": (1, 8), "CA": (1, 7),
    "MT": (2, 9), "ID": (2, 8), "NV": (2, 7), "AZ": (2, 6),
    "WY": (3, 9), "UT": (3, 8), "CO": (3, 7), "NM": (3, 6),
    "ND": (4, 9), "SD": (4, 8), "NE": (4, 7), "KS": (4, 6), "OK": (4, 5), "TX": (4, 4),
    "MN": (5, 9), "IA": (5, 8), "MO": (5, 7), "AR": (5, 6), "LA": (5, 5),
    "WI": (6, 9), "IL": (6, 8), "TN": (6, 6), "MS": (6, 5),
    "MI": (7, 9), "IN": (7, 8), "KY": (7, 7), "AL": (7, 6),
    "OH": (8, 8), "WV": (8, 7), "GA": (8, 6), "FL": (8, 5),
    "PA": (9, 8), "VA": (9, 7), "NC": (9, 6), "SC": (9, 5),
    "NY": (10, 9), "MD": (10, 7), "DE": (10, 6),
    "VT": (11, 10), "NJ": (11, 8), "DC": (11, 7),
    "NH": (12, 10), "MA": (12, 9), "CT": (12, 8), "RI": (12, 7),
    "ME": (13, 10),
}

def make_choropleth(bills):
    # Per-state totals
    state_counts = bills.groupby("state").size().rename("total")
    signed = bills[bills["status"] == "Signed/Enacted/Adopted"].groupby("state").size().rename("signed")
    df = pd.concat([state_counts, signed], axis=1).fillna(0)
    df["enact_rate"] = df["signed"] / df["total"]
    MIN_BILLS = 3  # grey out states with fewer bills on enactment map

    fig, axes = plt.subplots(1, 2, figsize=(20, 9), facecolor="#f8f9fa")
    fig.suptitle("U.S. Insurance Bill Landscape by State", fontsize=20, fontweight="bold",
                 y=0.97, color="#1a1a2e")

    cmap_vol  = matplotlib.colormaps["YlOrRd"]
    cmap_rate = matplotlib.colormaps["RdYlGn"]

    max_total  = df["total"].max()
    max_signed = df["signed"].max()

    for ax_idx, (ax, metric, cmap, label) in enumerate(zip(
        axes,
        ["total", "signed"],
        [cmap_vol, cmap_rate],
        ["Total Bills Introduced", f"Bills Signed into Law\n(grey = fewer than {MIN_BILLS} bills introduced)"]
    )):
        ax.set_facecolor("#e8edf2")
        ax.set_title(label, fontsize=13, fontweight="bold", pad=14, color="#1a1a2e")
        ax.set_xlim(-0.7, 14.5)
        ax.set_ylim(-0.7, 11.5)
        ax.set_aspect("equal")
        ax.axis("off")

        all_states = list(STATE_GRID.keys())
        for st in all_states:
            col_x, row_y = STATE_GRID[st]
            has_data = st in df.index
            # For enactment map, grey out low-volume states
            insufficient = has_data and metric == "signed" and df.loc[st, "total"] < MIN_BILLS

            if has_data and not insufficient:
                val = df.loc[st, metric]
                norm_val = val / (max_total if metric == "total" else max_signed)
                color = cmap(norm_val)
                edge = "#ffffff"
                lw = 1.0
            else:
                color = "#d0d0d0"
                edge = "#aaaaaa"
                lw = 0.5

            rect = mpatches.FancyBboxPatch(
                (col_x - 0.45, row_y - 0.45), 0.9, 0.9,
                boxstyle="round,pad=0.06",
                facecolor=color, edgecolor=edge, linewidth=lw,
                zorder=2
            )
            ax.add_patch(rect)

            # Determine text contrast colour
            if has_data and not insufficient:
                norm_val = df.loc[st, metric] / (max_total if metric == "total" else max_signed)
                text_color = "white" if norm_val > 0.55 else "#333333"
            else:
                text_color = "#888888"

            ax.text(col_x, row_y + 0.1, st, ha="center", va="center",
                    fontsize=7.5, fontweight="bold", color=text_color, zorder=3)

            # Value label — show "X (Y%)" on enactment map
            if has_data and not insufficient:
                if metric == "total":
                    val_disp = str(int(df.loc[st, metric]))
                else:
                    n_signed = int(df.loc[st, "signed"])
                    rate     = df.loc[st, "enact_rate"]
                    val_disp = f"{n_signed} ({rate:.0%})"
                ax.text(col_x, row_y - 0.2, val_disp, ha="center", va="center",
                        fontsize=5.5, color=text_color, zorder=3)

        # Colorbar
        vmax = max_total if metric == "total" else max_signed
        sm = cm.ScalarMappable(cmap=cmap, norm=mcolors.Normalize(vmin=0, vmax=vmax))
        sm.set_array([])
        cbar = fig.colorbar(sm, ax=ax, orientation="horizontal",
                            fraction=0.04, pad=0.02, aspect=40)
        cbar.ax.tick_params(labelsize=9)
        if metric == "signed":
            cbar.set_label("Number of bills signed into law", fontsize=8, labelpad=4)

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    out = os.path.join(OUT_DIR, "01_choropleth_map.png")
    plt.savefig(out, dpi=160, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"Saved: {out}")
    return out


# ════════════════════════════════════════════════════════════════════════════
# 2.  STACKED BAR — STATE OF PLAY BY ISSUE AREA
# ════════════════════════════════════════════════════════════════════════════

# Human-readable labels for keyword tags
TAG_LABELS = {
    "consumer_protections_and_market_conduct": "Consumer Protections\n& Market Conduct",
    "state_insurance_residual_markets":         "Residual /\nLast-Resort Markets",
    "fortification_programs":                   "Home Fortification\nPrograms",
    "state_insurance_office_regulatory_powers": "State Insurance\nOffice Powers",
    "non_admitted_market":                       "Non-Admitted\n(Surplus Lines) Market",
    "climate_resilience_and_risk_mitigation":    "Climate Resilience\n& Risk Mitigation",
    "data_and_study":                            "Data &\nStudy",
    "fossil_fuel_accountability":                "Fossil Fuel\nAccountability",
    "rate_regulation":                           "Rate\nRegulation",
    "building_codes_land_use":                   "Building Codes\n& Land Use",
    "catastrophe_modeling":                      "Catastrophe\nModeling",
    "reinsurance":                               "Reinsurance",
    "property_disclosure":                       "Property\nDisclosure",
    "litigation_and_tort_reform":                "Litigation &\nTort Reform",
    "climate_risk_disclosure":                   "Climate Risk\nDisclosure",
    "anti_esg":                                  "Anti-ESG",
}

STATUS_ORDER = [
    "Signed/Enacted/Adopted",
    "Passed",
    "Crossed Over",
    "In Committee",
    "Introduced",
    "Dead",
    "Vetoed",
]

def explode_tags(bills):
    """Return a flat DataFrame with one row per (bill_id, tag)."""
    rows = []
    for _, row in bills.iterrows():
        if not row["keyword_tags"]:
            continue
        try:
            tags = json.loads(row["keyword_tags"])
        except Exception:
            continue
        for tag in tags:
            rows.append({"bill_id": row["bill_id"], "tag": tag, "status": row["status"]})
    return pd.DataFrame(rows)

def make_stacked_bar(bills):
    flat = explode_tags(bills)

    # Count per (tag, status)
    pivot = (flat.groupby(["tag", "status"])
                 .size()
                 .unstack(fill_value=0))

    # Ensure all status columns exist
    for s in STATUS_ORDER:
        if s not in pivot.columns:
            pivot[s] = 0
    pivot = pivot[STATUS_ORDER]

    # Sort by total bills descending
    pivot["_total"] = pivot.sum(axis=1)
    pivot = pivot.sort_values("_total", ascending=True).drop(columns="_total")

    # Rename index to human labels
    pivot.index = [TAG_LABELS.get(t, t) for t in pivot.index]

    fig, ax = plt.subplots(figsize=(14, 10), facecolor="#f8f9fa")
    ax.set_facecolor("#f8f9fa")

    # Draw horizontal stacked bars
    left = np.zeros(len(pivot))
    bars_by_status = {}
    for status in STATUS_ORDER:
        vals = pivot[status].values
        bars = ax.barh(
            pivot.index, vals, left=left,
            color=STATUS_COLORS.get(status, "#aaaaaa"),
            edgecolor="white", linewidth=0.6,
            label=status, height=0.65
        )
        bars_by_status[status] = (bars, left.copy(), vals)
        left += vals

    # Add value labels inside bars (only if bar is wide enough)
    for status, (bars, lefts, vals) in bars_by_status.items():
        for bar, l, v in zip(bars, lefts, vals):
            if v >= 3:
                ax.text(
                    l + v / 2, bar.get_y() + bar.get_height() / 2,
                    str(int(v)), ha="center", va="center",
                    fontsize=8, fontweight="bold",
                    color="white" if status in ("Signed/Enacted/Adopted", "Dead", "Vetoed") else "#333333"
                )

    # Enactment rate annotation on right side
    totals = pivot.sum(axis=1)
    signed = pivot.get("Signed/Enacted/Adopted", pd.Series(0, index=pivot.index))
    passed = pivot.get("Passed", pd.Series(0, index=pivot.index))
    enacted = signed + passed

    for i, (idx, total) in enumerate(totals.items()):
        rate = enacted[idx] / total if total > 0 else 0
        ax.text(
            total + 0.4, i,
            f"{rate:.0%} enacted",
            va="center", fontsize=8, color="#555555"
        )

    ax.set_xlabel("Number of Bills", fontsize=12, labelpad=10)
    ax.set_title("State of Play: Insurance Bills by Issue Area",
                 fontsize=17, fontweight="bold", pad=18, color="#1a1a2e")
    ax.set_xlim(0, totals.max() * 1.18)
    ax.tick_params(axis="y", labelsize=9.5)
    ax.tick_params(axis="x", labelsize=9)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.xaxis.grid(True, linestyle="--", alpha=0.4, color="#cccccc")
    ax.set_axisbelow(True)

    # Legend
    handles = [mpatches.Patch(color=STATUS_COLORS[s], label=s) for s in STATUS_ORDER
               if s in pivot.columns and pivot[s].sum() > 0]
    ax.legend(handles=handles, loc="lower right", fontsize=9,
              framealpha=0.9, edgecolor="#cccccc",
              title="Bill Status", title_fontsize=9)

    # Subtitle
    fig.text(0.5, 0.97,
             "Bills may carry multiple tags · 281 total bills across 38 states · 2025–2026 sessions",
             ha="center", fontsize=9, color="#777777")

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    out = os.path.join(OUT_DIR, "02_state_of_play_bar.png")
    plt.savefig(out, dpi=160, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"Saved: {out}")
    return out


# ── main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import matplotlib.ticker

    bills = load_data()
    print(f"Loaded {len(bills)} bills.")

    make_choropleth(bills)
    make_stacked_bar(bills)

    print("\nDone.")
