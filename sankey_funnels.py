"""
Insurance Bills – Sankey & Funnel Visualizations
  03_sankey_aggregate.png  – single Sankey: Introduced → Committee → Crossed Over → Final
  04_funnel_multiples.png  – small-multiples funnel for 6 main categories
"""

import sqlite3, json, os, re, textwrap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
import matplotlib.patheffects as pe
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch
from matplotlib.path import Path
import matplotlib.patches as patches

DB_PATH = "/sessions/nifty-laughing-shannon/mnt/bill_collection/data/insurance_bills.db"
XLSX_PATH = "/sessions/nifty-laughing-shannon/mnt/uploads/Untitled spreadsheet.xlsx"
OUT_DIR  = "/sessions/nifty-laughing-shannon/mnt/bill_collection"

# ── load data ────────────────────────────────────────────────────────────────
def load_data():
    df = pd.read_excel(XLSX_PATH, sheet_name="Sheet1")
    return df

# Normalize categories to the 6 main ones (take first token before comma)
TOP_CATS = [
    "Consumer Protections & Market Conduct",
    "State Insurance & Residual markets",
    "Fossil Fuel Accountability",
    "Fortification Programs",
    "Non-Admitted Market",
    "Climate Resilience & Risk Mitigation",
    "State Insurance Office Regulatory Powers",
    "Data & Study",
]

CAT_COLORS = {
    "Consumer Protections & Market Conduct":    "#4361ee",
    "State Insurance & Residual markets":       "#3a0ca3",
    "Fossil Fuel Accountability":               "#f72585",
    "Fortification Programs":                   "#7209b7",
    "Non-Admitted Market":                      "#4cc9f0",
    "Climate Resilience & Risk Mitigation":     "#06d6a0",
    "State Insurance Office Regulatory Powers": "#ffd166",
    "Data & Study":                             "#ef8c2c",
    "Other":                                    "#aaaaaa",
}

STATUS_COLORS = {
    "Signed/Enacted/Adopted": "#2a9d8f",
    "Passed":                 "#57cc99",
    "Crossed Over":           "#f4a261",
    "In Committee":           "#8ecae6",
    "Introduced":             "#b0c4de",
    "Dead":                   "#e63946",
    "Vetoed":                 "#c1121f",
}

def primary_cat(cat_str):
    if pd.isna(cat_str):
        return "Other"
    first = str(cat_str).split(",")[0].strip()
    return first if first in TOP_CATS else "Other"

# ════════════════════════════════════════════════════════════════════════════
# 3.  AGGREGATE SANKEY
# ════════════════════════════════════════════════════════════════════════════
# Stages: Introduced → [In Committee | Crossed Over] → [Signed | Dead | Vetoed | Still Active]
# We build a manual Sankey using cubic bezier ribbons.

def bezier_ribbon(ax, x0, y0_top, y0_bot, x1, y1_top, y1_bot, color, alpha=0.55):
    """Draw a filled bezier ribbon between two vertical bands."""
    cx = (x0 + x1) / 2
    verts = [
        (x0, y0_top),
        (cx, y0_top),
        (cx, y1_top),
        (x1, y1_top),
        (x1, y1_bot),
        (cx, y1_bot),
        (cx, y0_bot),
        (x0, y0_bot),
        (x0, y0_top),
    ]
    codes = [Path.MOVETO,
             Path.CURVE4, Path.CURVE4, Path.CURVE4,
             Path.LINETO,
             Path.CURVE4, Path.CURVE4, Path.CURVE4,
             Path.CLOSEPOLY]
    path = Path(verts, codes)
    patch = patches.PathPatch(path, facecolor=color, edgecolor="none", alpha=alpha, zorder=2)
    ax.add_patch(patch)

def make_sankey(df):
    df = df.copy()
    df["cat"] = df["Category"].apply(primary_cat)

    # Map statuses to pipeline stages
    def to_stage(s):
        s = str(s)
        if s in ("Signed/Enacted/Adopted", "Passed"):        return "Signed into Law"
        if s == "Dead":                                        return "Dead"
        if s == "Vetoed":                                      return "Vetoed"
        if s == "Crossed Over":                                return "Crossed Over"
        if s in ("In Committee", "Introduced"):               return "In Committee"
        return "In Committee"

    df["stage"] = df["Status"].apply(to_stage)

    # Node layout  x positions: 0=Introduced, 1=Committee/CrossedOver, 2=Final
    # Every bill starts at "Introduced"
    # Then goes to Committee OR Crossed Over (intermediate)
    # Then to final outcome

    # For simplicity: track flows
    # Flow A: All bills → In Committee     (those stuck there or die in committee)
    # Flow B: All bills → Crossed Over     (those that crossed)
    # From In Committee → Dead / Signed / Still In Committee
    # From Crossed Over → Dead / Signed / Still Crossed Over

    cats_ordered = [c for c in TOP_CATS if c in df["cat"].values] + (["Other"] if "Other" in df["cat"].values else [])

    # Count flows per category
    # Stage 1 → Stage 2 transitions
    flows = {}  # (cat, mid_stage, final_stage) -> count
    for _, row in df.iterrows():
        cat   = row["cat"]
        stage = row["stage"]
        if stage in ("In Committee",):
            mid, final = "In Committee", "Still Active"
        elif stage == "Crossed Over":
            mid, final = "Crossed Over", "Still Active"
        elif stage == "Signed into Law":
            # assume went through committee then crossed over (simplified)
            mid, final = "Crossed Over", "Signed into Law"
        elif stage == "Dead":
            mid, final = "In Committee", "Dead"
        elif stage == "Vetoed":
            mid, final = "Crossed Over", "Vetoed"
        else:
            mid, final = "In Committee", "Still Active"
        flows[(cat, mid, final)] = flows.get((cat, mid, final), 0) + 1

    # --- Figure layout ---
    fig, ax = plt.subplots(figsize=(18, 11), facecolor="#0f1117")
    ax.set_facecolor("#0f1117")
    ax.set_xlim(-0.5, 3.5)
    ax.set_ylim(-1, len(df) + 5)
    ax.axis("off")

    fig.suptitle("Insurance Bills Pipeline: From Introduction to Outcome",
                 fontsize=18, fontweight="bold", color="white", y=0.97)
    fig.text(0.5, 0.93, "304 bills across 38 states · 2025–2026 sessions · colored by issue category",
             ha="center", fontsize=10, color="#aaaaaa")

    # Column x positions
    X = [0.2, 1.2, 2.2, 3.0]

    # Build vertical stacks for each column
    # Col 0: all bills by category
    # Col 1: In Committee | Crossed Over  (by category within each)
    # Col 2: final outcomes

    GAP = 2  # gap between segments in same column

    def build_stack(counts_dict, x=None, total_height=None):
        """Returns dict of key -> (y_top, y_bot) for each segment."""
        total = sum(counts_dict.values())
        if total_height is None:
            total_height = total
        scale = total_height / total if total > 0 else 1
        result = {}
        y = 0
        for i, (k, v) in enumerate(counts_dict.items()):
            h = v * scale
            result[k] = (y, y + h)
            y += h + GAP
        return result

    total_h = len(df) + GAP * (len(cats_ordered) - 1)

    # Col 0: all bills by category
    cat_counts_0 = {c: (df["cat"] == c).sum() for c in cats_ordered if (df["cat"] == c).sum() > 0}
    col0 = build_stack(cat_counts_0, X[0])

    # Col 1: split into In-Committee and Crossed-Over, each by category
    committee_by_cat  = {}
    crossedover_by_cat = {}
    for cat in cats_ordered:
        sub = df[df["cat"] == cat]
        n_comm = sub[sub["stage"].isin(["In Committee", "Dead"])].shape[0]
        n_cross = sub[sub["stage"].isin(["Crossed Over", "Signed into Law", "Vetoed"])].shape[0]
        if n_comm > 0:  committee_by_cat[cat]   = n_comm
        if n_cross > 0: crossedover_by_cat[cat] = n_cross

    # Stack committee cats then a gap then crossedover cats
    committee_stack  = build_stack(committee_by_cat)
    # Offset crossed-over stack above committee
    comm_top = max(v[1] for v in committee_stack.values()) if committee_stack else 0
    crossedover_stack = {}
    y = comm_top + GAP * 4
    for cat, v in crossedover_by_cat.items():
        crossedover_stack[cat] = (y, y + v)
        y += v + GAP

    # Col 2: final outcomes by category within outcome group
    # Groups: Signed, Still Active (committee+crossed), Dead, Vetoed
    signed_by_cat   = {c: (df[(df["cat"]==c) & (df["stage"]=="Signed into Law")].shape[0])
                       for c in cats_ordered}
    signed_by_cat   = {k: v for k, v in signed_by_cat.items() if v > 0}
    dead_by_cat     = {c: (df[(df["cat"]==c) & (df["stage"]=="Dead")].shape[0])
                       for c in cats_ordered}
    dead_by_cat     = {k: v for k, v in dead_by_cat.items() if v > 0}
    active_by_cat   = {c: (df[(df["cat"]==c) & (df["stage"].isin(["In Committee","Crossed Over","Still Active"]))].shape[0])
                       for c in cats_ordered}
    active_by_cat   = {k: v for k, v in active_by_cat.items() if v > 0}

    # Build col2 stack: signed at top, active in middle, dead at bottom
    col2 = {}
    y = 0
    for label, group in [("Dead", dead_by_cat), ("Still Active", active_by_cat), ("Signed into Law", signed_by_cat)]:
        for cat, v in group.items():
            col2[(label, cat)] = (y, y + v)
            y += v + GAP
        y += GAP * 2

    # ── DRAW NODES ──────────────────────────────────────────────────────────
    BAR_W = 0.08

    def draw_bar(ax, x, y_bot, y_top, color, label=None, fontsize=8):
        ax.fill_betweenx([y_bot, y_top], x - BAR_W, x + BAR_W,
                         color=color, alpha=0.95, zorder=3)
        if label and (y_top - y_bot) > 3:
            ax.text(x, (y_bot + y_top) / 2, label,
                    ha="center", va="center", fontsize=fontsize,
                    color="white", fontweight="bold", zorder=4,
                    rotation=0 if (y_top - y_bot) > 8 else 90)

    # Col 0
    for cat, (yb, yt) in col0.items():
        draw_bar(ax, X[0], yb, yt, CAT_COLORS.get(cat, "#aaa"))

    # Col 1 — committee
    for cat, (yb, yt) in committee_stack.items():
        draw_bar(ax, X[1], yb, yt, CAT_COLORS.get(cat, "#aaa"))
    # Col 1 — crossed over
    for cat, (yb, yt) in crossedover_stack.items():
        draw_bar(ax, X[1], yb, yt, CAT_COLORS.get(cat, "#aaa"))

    # Col 2
    outcome_colors = {"Signed into Law": "#2a9d8f", "Still Active": "#f4a261", "Dead": "#e63946"}
    for (outcome, cat), (yb, yt) in col2.items():
        color = CAT_COLORS.get(cat, "#aaa")
        draw_bar(ax, X[2], yb, yt, color)

    # ── DRAW RIBBONS ────────────────────────────────────────────────────────
    # Col0 → Col1
    # Track running offsets within each destination segment
    dest_offset_comm  = {cat: committee_stack[cat][0]  for cat in committee_stack}
    dest_offset_cross = {cat: crossedover_stack[cat][0] for cat in crossedover_stack}
    src_offset = {cat: col0[cat][0] for cat in col0}

    for cat in cats_ordered:
        if cat not in col0: continue
        color = CAT_COLORS.get(cat, "#aaa")
        n_comm  = committee_by_cat.get(cat, 0)
        n_cross = crossedover_by_cat.get(cat, 0)
        src_y = src_offset[cat]

        if n_comm > 0 and cat in dest_offset_comm:
            bezier_ribbon(ax,
                X[0], src_y + n_comm, src_y,
                X[1], dest_offset_comm[cat] + n_comm, dest_offset_comm[cat],
                color)
            dest_offset_comm[cat]  += n_comm
            src_y += n_comm
        if n_cross > 0 and cat in dest_offset_cross:
            bezier_ribbon(ax,
                X[0], src_y + n_cross, src_y,
                X[1], dest_offset_cross[cat] + n_cross, dest_offset_cross[cat],
                color)
            dest_offset_cross[cat] += n_cross

    # Col1 → Col2
    dest_offset_col2 = {k: v[0] for k, v in col2.items()}
    src_comm_offset  = {cat: committee_stack[cat][0]  for cat in committee_stack}
    src_cross_offset = {cat: crossedover_stack[cat][0] for cat in crossedover_stack}

    for cat in cats_ordered:
        color = CAT_COLORS.get(cat, "#aaa")

        # From committee: go to Dead or Still Active
        n_dead   = dead_by_cat.get(cat, 0)
        n_active_comm = active_by_cat.get(cat, 0)

        # Apportion active between committee and crossed-over sources
        n_comm_active  = min(n_active_comm, committee_by_cat.get(cat, 0) - n_dead)
        n_comm_active  = max(n_comm_active, 0)

        if n_dead > 0 and cat in src_comm_offset:
            sy = src_comm_offset[cat]
            dk = ("Dead", cat)
            if dk in dest_offset_col2:
                bezier_ribbon(ax,
                    X[1], sy + n_dead, sy,
                    X[2], dest_offset_col2[dk] + n_dead, dest_offset_col2[dk],
                    color)
                dest_offset_col2[dk]   += n_dead
                src_comm_offset[cat]   += n_dead

        if n_comm_active > 0 and cat in src_comm_offset:
            sy = src_comm_offset[cat]
            ak = ("Still Active", cat)
            if ak in dest_offset_col2:
                bezier_ribbon(ax,
                    X[1], sy + n_comm_active, sy,
                    X[2], dest_offset_col2[ak] + n_comm_active, dest_offset_col2[ak],
                    color)
                dest_offset_col2[ak]  += n_comm_active
                src_comm_offset[cat]  += n_comm_active

        # From crossed-over: go to Signed or Still Active
        n_signed = (df[(df["cat"]==cat) & (df["stage"]=="Signed into Law")].shape[0])
        n_cross_active = crossedover_by_cat.get(cat, 0) - n_signed

        if n_signed > 0 and cat in src_cross_offset:
            sy = src_cross_offset[cat]
            sk = ("Signed into Law", cat)
            if sk in dest_offset_col2:
                bezier_ribbon(ax,
                    X[1], sy + n_signed, sy,
                    X[2], dest_offset_col2[sk] + n_signed, dest_offset_col2[sk],
                    color)
                dest_offset_col2[sk]   += n_signed
                src_cross_offset[cat]  += n_signed

        if n_cross_active > 0 and cat in src_cross_offset:
            sy = src_cross_offset[cat]
            ak = ("Still Active", cat)
            if ak in dest_offset_col2:
                bezier_ribbon(ax,
                    X[1], sy + n_cross_active, sy,
                    X[2], dest_offset_col2[ak] + n_cross_active, dest_offset_col2[ak],
                    color)
                dest_offset_col2[ak]  += n_cross_active
                src_cross_offset[cat] += n_cross_active

    # ── COLUMN LABELS ───────────────────────────────────────────────────────
    col_labels = ["All Bills\nIntroduced", "Stage 2\n(In Committee /\nCrossed Over)", "Final\nOutcome"]
    for x, lbl in zip([X[0], X[1], X[2]], col_labels):
        ax.text(x, -1, lbl, ha="center", va="top", fontsize=10,
                color="white", fontweight="bold")

    # Stage 2 sub-labels
    if committee_stack:
        mid_comm = np.mean([np.mean(v) for v in committee_stack.values()])
        ax.text(X[1] + 0.14, mid_comm, "In\nCommittee",
                ha="left", va="center", fontsize=8, color="#8ecae6", fontweight="bold")
    if crossedover_stack:
        mid_cross = np.mean([np.mean(v) for v in crossedover_stack.values()])
        ax.text(X[1] + 0.14, mid_cross, "Crossed\nOver",
                ha="left", va="center", fontsize=8, color="#f4a261", fontweight="bold")

    # Col 2 outcome labels
    for outcome in ["Dead", "Still Active", "Signed into Law"]:
        oc_items = [(k, v) for k, v in col2.items() if k[0] == outcome]
        if oc_items:
            all_y = [y for _, (yb, yt) in oc_items for y in (yb, yt)]
            mid_y = (min(all_y) + max(all_y)) / 2
            total_n = sum(committee_by_cat.get(cat,0) if outcome != "Signed into Law"
                          else (df[(df["cat"]==cat) & (df["stage"]=="Signed into Law")].shape[0])
                          for (_, cat) in oc_items)
            ax.text(X[2] + 0.14, mid_y,
                    f"{outcome}\n(n={int(sum((yt-yb) for _,(yb,yt) in oc_items))})",
                    ha="left", va="center", fontsize=8.5,
                    color=outcome_colors.get(outcome, "white"), fontweight="bold")

    # ── CATEGORY LEGEND ─────────────────────────────────────────────────────
    handles = [mpatches.Patch(color=CAT_COLORS[c], label=c) for c in cats_ordered if c in CAT_COLORS]
    leg = ax.legend(handles=handles, loc="upper right", fontsize=7.5,
                    framealpha=0.2, edgecolor="#444", labelcolor="white",
                    title="Issue Category", title_fontsize=8,
                    facecolor="#1a1a2e")
    plt.setp(leg.get_title(), color="white")

    plt.tight_layout(rect=[0, 0, 1, 0.93])
    out = os.path.join(OUT_DIR, "03_sankey_aggregate.png")
    plt.savefig(out, dpi=160, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"Saved: {out}")
    return out


# ════════════════════════════════════════════════════════════════════════════
# 4.  SMALL-MULTIPLES FUNNEL
# ════════════════════════════════════════════════════════════════════════════

FUNNEL_CATS = [
    "Consumer Protections & Market Conduct",
    "State Insurance & Residual markets",
    "Fossil Fuel Accountability",
    "Fortification Programs",
    "Non-Admitted Market",
    "Climate Resilience & Risk Mitigation",
]

FUNNEL_STAGES = [
    ("Introduced",              ["Introduced"]),
    ("In Committee",            ["In Committee", "Introduced"]),
    ("Crossed Over",            ["Crossed Over"]),
    ("Signed into Law",         ["Signed/Enacted/Adopted", "Passed"]),
    ("Dead / Vetoed",           ["Dead", "Vetoed"]),
]

SHORT_LABELS = {
    "Consumer Protections & Market Conduct":    "Consumer\nProtections",
    "State Insurance & Residual markets":       "Residual\nMarkets",
    "Fossil Fuel Accountability":               "Fossil Fuel\nAccountability",
    "Fortification Programs":                   "Fortification\nPrograms",
    "Non-Admitted Market":                      "Non-Admitted\nMarket",
    "Climate Resilience & Risk Mitigation":     "Climate\nResilience",
}

def make_funnels(df):
    df = df.copy()
    df["cat"] = df["Category"].apply(primary_cat)

    fig, axes = plt.subplots(2, 3, figsize=(18, 11), facecolor="#f8f9fa")
    fig.suptitle("Bill Pipeline by Issue Category", fontsize=18,
                 fontweight="bold", color="#1a1a2e", y=0.98)
    fig.text(0.5, 0.94,
             "Width = share of bills · green = enacted · red = dead",
             ha="center", fontsize=10, color="#666666")

    stage_colors = {
        "Introduced":       "#b0c4de",
        "In Committee":     "#8ecae6",
        "Crossed Over":     "#f4a261",
        "Signed into Law":  "#2a9d8f",
        "Dead / Vetoed":    "#e63946",
    }

    for ax, cat in zip(axes.flat, FUNNEL_CATS):
        sub = df[df["cat"] == cat]
        total = len(sub)
        color = CAT_COLORS.get(cat, "#999")

        # Count each stage
        stage_counts = {}
        for label, statuses in FUNNEL_STAGES:
            stage_counts[label] = sub[sub["Status"].isin(statuses)].shape[0]

        # Separate terminal stages from pipeline stages
        pipeline = ["In Committee", "Crossed Over"]
        terminal_good = "Signed into Law"
        terminal_bad  = "Dead / Vetoed"

        # Draw horizontal funnel bars
        ax.set_facecolor("#f8f9fa")
        ax.spines[["top","right","left","bottom"]].set_visible(False)
        ax.tick_params(left=False, bottom=False)
        ax.set_xticks([])

        stages_to_plot = ["In Committee", "Crossed Over", "Signed into Law", "Dead / Vetoed"]
        bar_height = 0.55
        y_positions = range(len(stages_to_plot) - 1, -1, -1)

        max_count = max(stage_counts[s] for s in stages_to_plot) or 1

        for yi, stage in zip(y_positions, stages_to_plot):
            count = stage_counts[stage]
            width = count / total if total > 0 else 0
            bar_color = stage_colors[stage]

            # Background bar (full width, light)
            ax.barh(yi, 1.0, height=bar_height, color="#e8e8e8",
                    left=0, zorder=1)
            # Actual bar
            ax.barh(yi, width, height=bar_height, color=bar_color,
                    left=0, zorder=2, alpha=0.9)

            # Count label
            pct = f"{count/total:.0%}" if total > 0 else "0%"
            ax.text(width + 0.02, yi, f"{count}  ({pct})",
                    va="center", fontsize=9, color="#333333", fontweight="bold")

            # Stage label on left
            ax.text(-0.02, yi, stage, ha="right", va="center",
                    fontsize=8.5, color="#444444")

        ax.set_xlim(-0.38, 1.35)
        ax.set_ylim(-0.6, len(stages_to_plot) - 0.4)
        ax.set_yticks([])

        # Title with total and enactment rate
        enacted = stage_counts["Signed into Law"]
        rate = enacted / total if total > 0 else 0
        ax.set_title(
            f"{SHORT_LABELS.get(cat, cat)}\n"
            f"n={total}  ·  {rate:.0%} enacted",
            fontsize=10.5, fontweight="bold", color=color, pad=8,
            loc="center"
        )

        # Thin colored left border
        ax.axvline(-0.36, color=color, linewidth=5, zorder=5,
                   solid_capstyle="butt")

    plt.tight_layout(rect=[0, 0, 1, 0.93])
    out = os.path.join(OUT_DIR, "04_funnel_multiples.png")
    plt.savefig(out, dpi=160, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"Saved: {out}")
    return out


# ── main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    df = load_data()
    print(f"Loaded {len(df)} bills.")
    make_sankey(df)
    make_funnels(df)
    print("\nDone.")
