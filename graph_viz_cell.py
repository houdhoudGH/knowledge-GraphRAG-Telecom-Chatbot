"""
Drop-in notebook cell — produces a cleaner replacement for the current
hairball graph image. Run this in a new cell in your `7_neo4j_RAG.ipynb`
(or a fresh notebook) AFTER your validated CSV has been loaded.

Saves to: docs/images/graph_clean.png
"""

import os
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from collections import Counter

# ---------------------------------------------------------------------------
# 1. Load triples (validated preferred, extraction as fallback)
# ---------------------------------------------------------------------------
for path in ["../data/processed/relations_llm_validated.csv",
             "../data/processed/relations_extraction.csv",
             "data/processed/relations_llm_validated.csv",
             "data/processed/relations_extraction.csv"]:
    if os.path.exists(path):
        df = pd.read_csv(path)
        print(f"Loaded {len(df):,} triples from {path}")
        break
else:
    raise FileNotFoundError("Could not find triples CSV")

df = df.dropna(subset=["subject", "object", "relation"])
df["relation"] = df["relation"].str.upper()

# ---------------------------------------------------------------------------
# 2. Keep only the most-connected subgraph
#    This is the KEY fix vs the current hairball — limit the node count
# ---------------------------------------------------------------------------
TOP_N_NODES = 35   # tune between 30 and 50

# Count how often each entity appears (as subject or object)
node_counts = Counter(df["subject"].tolist() + df["object"].tolist())
top_nodes = {name for name, _ in node_counts.most_common(TOP_N_NODES)}

# Keep only triples where BOTH endpoints are in the top-N set
df_sub = df[df["subject"].isin(top_nodes) & df["object"].isin(top_nodes)].copy()
print(f"Subgraph: {len(top_nodes)} nodes, {len(df_sub)} edges")

# ---------------------------------------------------------------------------
# 3. Build the directed graph and capture node types
# ---------------------------------------------------------------------------
G = nx.DiGraph()
node_type = {}
for _, row in df_sub.iterrows():
    G.add_edge(str(row["subject"]), str(row["object"]),
               label=row["relation"])
    node_type[str(row["subject"])] = row.get("subject_type", "OTHER")
    node_type[str(row["object"])] = row.get("object_type", "OTHER")

# ---------------------------------------------------------------------------
# 4. Color palette — one color per entity type, NOT all sky blue
# ---------------------------------------------------------------------------
PALETTE = {
    "PERSON":    "#264653",  # dark teal
    "ORG":       "#e76f51",  # warm coral
    "ISSUE":     "#c1121f",  # deep red
    "DEVICE":    "#2a9d8f",  # green-teal
    "SERVICE":   "#f4a261",  # amber
    "ACTION":    "#8d99ae",  # cool grey
    "ACCOUNT":   "#6a4c93",  # purple
    "DATE":      "#a8a29e",  # neutral
    "LOC":       "#bc6c25",  # rust
}
DEFAULT_COLOR = "#999999"

node_colors = [PALETTE.get(node_type.get(n, "OTHER"), DEFAULT_COLOR)
               for n in G.nodes()]

# Node size scales with degree, so hubs are visually obvious
deg = dict(G.degree())
node_sizes = [400 + 180 * deg[n] for n in G.nodes()]

# ---------------------------------------------------------------------------
# 5. Draw — bigger figure, sparser layout, no edge label clutter
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(16, 11), facecolor="white")
ax.set_facecolor("white")

# k controls node spacing; higher = sparser. 2.0 works well for ~35 nodes.
pos = nx.spring_layout(G, k=2.0, iterations=120, seed=42)

# Edges first — light, thin, semi-transparent
nx.draw_networkx_edges(
    G, pos,
    edge_color="#3a3a3a",
    alpha=0.35,
    width=0.9,
    arrows=True,
    arrowsize=10,
    arrowstyle="-|>",
    connectionstyle="arc3,rad=0.05",  # slight curve = less overlap
)

# Nodes
nx.draw_networkx_nodes(
    G, pos,
    node_color=node_colors,
    node_size=node_sizes,
    edgecolors="white",
    linewidths=1.5,
    alpha=0.95,
)

# Labels — only on bigger nodes (clean up the small ones if too cluttered)
nx.draw_networkx_labels(
    G, pos,
    font_size=9,
    font_family="serif",
    font_color="#1a1a1a",
)

# Legend
legend_handles = [
    plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=color,
               markersize=11, label=label)
    for label, color in PALETTE.items()
    if label in set(node_type.values())
]
ax.legend(handles=legend_handles, loc="lower left", frameon=False,
          fontsize=9, ncol=1)

# Title
ax.set_title(
    "Telecom Knowledge Graph — top-connected entities",
    fontsize=14, family="serif", pad=20, loc="left"
)

ax.axis("off")
plt.tight_layout()

# ---------------------------------------------------------------------------
# 6. Save
# ---------------------------------------------------------------------------
out_dir = "docs/images"
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "graph_clean.png")
plt.savefig(out_path, dpi=200, bbox_inches="tight", facecolor="white")
plt.show()
print(f"Saved: {out_path}")
