"""
Telecom GraphRAG — scripted demo.

Replays the 9 question/answer pairs from `7_neo4j_RAG.ipynb`. Answers
have been polished for clarity while preserving the original substance,
including the deliberate "I don't know" responses that demonstrate
faithful uncertainty.

Run:
    pip install streamlit
    streamlit run app.py
"""

import time
import streamlit as st

st.set_page_config(
    page_title="Telecom GraphRAG",
    page_icon="🕸️",
    layout="wide",
)

# ----------------------------------------------------------------------------
# Q&A bank — polished from 7_neo4j_RAG.ipynb
# ----------------------------------------------------------------------------
QA_BANK = {
    # ----- Q1
    "How are tickets typically reported?": {
        "answer": "Tickets are typically reported via email — confirmed across multiple evidence sentences in the graph.",
        "triples": [
            (
                "TICKET",
                "REPORTED_VIA",
                "email",
                "The customer reported the issue via email and received a ticket confirmation within minutes.",
            ),
            (
                "TICKET",
                "REPORTED_VIA",
                "email",
                "An email was sent to support to open a new ticket for the billing dispute.",
            ),
            (
                "TICKET",
                "REPORTED_VIA",
                "email",
                "You should receive an email with instructions on how to contact our technical support team.",
            ),
        ],
    },
    # ----- Q2
    "Who handles escalated tickets for Union Mobile?": {
        "answer": (
            "Escalated tickets for Union Mobile are handled by **Jettie** and **Paulo**. "
            "The graph also surfaces a third escalation target whose agent name is not "
            "captured in the evidence."
        ),
        "triples": [
            (
                "TICKET",
                "ESCALATED_TO",
                "Jettie",
                "The ticket was escalated to Jettie from the Union Mobile support team for further investigation.",
            ),
            (
                "TICKET",
                "ESCALATED_TO",
                "Paulo",
                "Paulo from Union Mobile took over the escalated ticket and resolved the connectivity issue.",
            ),
            (
                "TICKET",
                "ESCALATED_TO",
                "Union Mobile",
                "All unresolved tier-1 tickets are escalated to the Union Mobile specialist team.",
            ),
        ],
    },
    # ----- Q3
    "With what device are issues most frequently reported?": {
        "answer": (
            "**Samsung Galaxy S21** is the device most frequently associated with reported "
            "issues, appearing in 3 distinct cases — followed by iPhone 13, router, and SIM card."
        ),
        "aggregation": [
            ("Samsung Galaxy S21", 3),
            ("iPhone 13", 2),
            ("router", 2),
            ("SIM card", 1),
        ],
    },
    # ----- Q4: analytical reasoning
    "Why are Samsung Galaxy devices reported frequently are they more prone to issues or bad phones?": {
        "answer": (
            "Samsung Galaxy S21 appears in 3 issue reports — tied with VPN as the most-frequent "
            "entity in the dataset. Frequency alone, however, is not evidence of defect: without "
            "normalizing by user base or session count, a widely-used device will naturally appear "
            "in more reports.\n\n"
            "The graph contains issue-to-device links but no usage prior, so a defect hypothesis "
            "cannot be evaluated from this evidence alone. Additional telemetry would be required "
            "to determine causation."
        ),
        "aggregation": [
            ("VPN", 3),
            ("Samsung Galaxy S21", 3),
            ("iPhone 13", 2),
            ("router", 2),
            ("SIM card", 1),
        ],
    },
    # ----- Q5
    "Which team is responsible when tickets are escalated?": {
        "answer": "Escalated tickets are routed to the **Union Mobile** specialist team.",
        "triples": [
            (
                "TICKET",
                "ESCALATED_TO",
                "Union Mobile",
                "All unresolved tier-1 tickets are escalated to the Union Mobile specialist team.",
            ),
            (
                "Jettie",
                "MEMBER_OF",
                "Union Mobile",
                "Jettie is a senior agent in the Union Mobile escalation team.",
            ),
            (
                "Paulo",
                "MEMBER_OF",
                "Union Mobile",
                "Paulo joined the Union Mobile escalation team in March.",
            ),
        ],
    },
    # ----- Q6: faithful uncertainty — the closer
    "What is the billing amount for account 29917?": {
        "answer": (
            "I don't know. The graph contains billing amounts of **500** and **30** "
            "(`ACCOUNT -[HAS_BILLING_AMOUNT]→ 500`, `ACCOUNT -[HAS_BILLING_AMOUNT]→ 30`), "
            "but no triple links either amount to account number 29917 specifically. "
            "I cannot answer this question from the available evidence."
        ),
        "triples": [
            (
                "ACCOUNT",
                "HAS_BILLING_AMOUNT",
                "500",
                "The total monthly billing amount on the account was 500 dollars including roaming.",
            ),
            (
                "ACCOUNT",
                "HAS_BILLING_AMOUNT",
                "30",
                "A 30 dollar late fee was added to the account this billing cycle.",
            ),
        ],
        "faithful_uncertainty": True,
    },
    # ----- Q7: faithful uncertainty
    "How much billing is associated with recent tickets?": {
        "answer": (
            "I don't know. The retrieved evidence references only a single ticket and "
            "does not indicate whether other tickets exist or how billing is associated "
            "with them. The graph cannot answer this question without additional ticket "
            "and billing relations."
        ),
        "triples": [
            (
                "TICKET",
                "RELATED_TO_ACCOUNT",
                "AB-12345",
                "Ticket #4521 is linked to account AB-12345 with an open billing inquiry.",
            ),
        ],
        "faithful_uncertainty": True,
    },
    # ----- Q8: long-form analytical
    "Explain how tickets are typically escalated and handled, based on the graph.": {
        "answer": (
            "The graph shows a consistent escalation pattern centered on **Union Mobile**:\n\n"
            "**1. Trigger.** Unresolved tier-1 tickets are escalated to the Union Mobile "
            "specialist team (`TICKET -[ESCALATED_TO]→ Union Mobile`).\n\n"
            "**2. Assignment.** Once routed, tickets are picked up by named representatives — "
            "the evidence specifically identifies Jettie, Paulo, and Cordia.\n\n"
            "**3. Resolution.** Representatives engage directly with the customer, as "
            "captured in agent-introduction evidence sentences.\n\n"
            "The graph does not capture downstream steps such as routing logic, time-to-"
            "resolution, or re-escalation. A complete escalation workflow would require "
            "additional event-level relations beyond what the current schema models."
        ),
        "triples": [
            (
                "TICKET",
                "ESCALATED_TO",
                "Union Mobile",
                "All unresolved tier-1 tickets are escalated to the Union Mobile specialist team.",
            ),
            (
                "TICKET",
                "ESCALATED_TO",
                "Jettie",
                "The ticket was escalated to Jettie from the Union Mobile support team for further investigation.",
            ),
            (
                "TICKET",
                "ESCALATED_TO",
                "Paulo",
                "Paulo from Union Mobile took over the escalated ticket and resolved the connectivity issue.",
            ),
            (
                "Cordia",
                "MEMBER_OF",
                "Union Mobile",
                "Cordia handled the escalated case after the first-tier agent could not resolve it.",
            ),
        ],
    },
    # ----- Q9: pattern detection
    "What patterns can you find in issue reports and the devices used?": {
        "answer": (
            "Three patterns emerge from the retrieved evidence:\n\n"
            "**1. Device concentration.** All matching customer-issue triples involve the "
            "Samsung Galaxy S21, indicating a strong concentration around a single device model.\n\n"
            "**2. Recurring use case.** The reported issues center on streaming services — "
            "Netflix appears repeatedly across distinct evidence sentences.\n\n"
            "**3. Geography is not a factor.** The same issue is reported from a consistent "
            "location (Berlin, Germany), suggesting the problem is device- or service-bound "
            "rather than network-region-bound."
        ),
        "triples": [
            (
                "CUSTOMER",
                "HAS_DEVICE",
                "Samsung Galaxy S21",
                "Customer confirmed the streaming issue happens consistently on the Samsung Galaxy S21.",
            ),
            (
                "ISSUE",
                "AFFECTS_DEVICE",
                "Samsung Galaxy S21",
                "Streaming on Netflix repeatedly fails on the Samsung Galaxy S21.",
            ),
            (
                "ISSUE",
                "LOCATED_AT",
                "Berlin",
                "The streaming issue was reported by a customer located in Berlin Germany.",
            ),
            (
                "ISSUE",
                "LOCATED_AT",
                "Berlin",
                "The same Netflix loading problem occurred again while the customer was in Berlin.",
            ),
        ],
    },
}


# ----------------------------------------------------------------------------
# UI helpers
# ----------------------------------------------------------------------------
def render_triples(triples):
    """Render a list of (subject, relation, object, evidence) tuples."""
    for s, r, o, ev in triples:
        st.markdown(f"`{s}` —[**{r}**]→ `{o}`")
        st.caption(f"_{ev}_")


def render_aggregation(rows):
    """Render aggregation-style retrieval (e.g. device frequency)."""
    for name, count in rows:
        st.markdown(f"`{name}` — count **{count}**")


def render_answer(entry):
    """Render an assistant answer with the right kind of evidence panel."""
    st.markdown(entry["answer"])
    if entry.get("faithful_uncertainty"):
        st.info(
            "★ **Faithful uncertainty by design.** The model is constrained to "
            "answer only from retrieved graph evidence — when that evidence is "
            "insufficient, it says so explicitly instead of hallucinating.",
            icon="ℹ️",
        )
    if "aggregation" in entry:
        n = len(entry["aggregation"])
        with st.expander(f"Source triples — {n} retrieved", expanded=True):
            render_aggregation(entry["aggregation"])
    elif "triples" in entry and entry["triples"]:
        n = len(entry["triples"])
        with st.expander(f"Source triples — {n} retrieved", expanded=True):
            render_triples(entry["triples"])


# ----------------------------------------------------------------------------
# Header
# ----------------------------------------------------------------------------
st.markdown(
    """
    <div style="padding: 8px 0 4px 0;">
      <h1 style="margin-bottom: 4px;">🕸️ Telecom GraphRAG</h1>
      <p style="color: #6c6c6c; margin-top: 0;">
        Knowledge-graph chatbot for telecom customer support.
        Every answer is grounded in extracted triples — no hallucination.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------------
# Sidebar
# ----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### Project pipeline")
    st.markdown(
        """
        1. **Ingest** — 300K+ telecom conversations (Talkmap · Comcast · Bitext)
        2. **Clean** — 9-step custom text-cleaning pipeline
        3. **NER** — spaCy `en_core_web_lg` + EntityRuler + regex
        4. **Relations** — dependency-parse rules → typed triples
        5. **Validate** — Llama 3.1 reviews every triple (conf ≥ 0.90)
        6. **Graph** — Neo4j Aura with weighted edges
        7. **GraphRAG** — Cypher retrieval + grounded LLM answer
        """
    )

    st.markdown("---")
    st.markdown("### Graph statistics")
    st.metric("Source conversations", "300K+")
    st.metric("Extracted triples", "98,041")
    st.metric("LLM-validated", "1,135")
    st.metric("Relation types", "9")

    st.markdown("---")
    st.markdown("### About this demo")
    st.caption(
        "This demo replays validated question/answer pairs from "
        "`7_neo4j_RAG.ipynb`. The Neo4j Aura instance used during "
        "development is no longer active; the full pipeline is "
        "reproducible from the notebooks in this repo."
    )

# ----------------------------------------------------------------------------
# Suggested questions
# ----------------------------------------------------------------------------
st.markdown("#### Try a question")
cols = st.columns(4)
demo_top = [
    "How are tickets typically reported?",
    "Who handles escalated tickets for Union Mobile?",
    "With what device are issues most frequently reported?",
    "What is the billing amount for account 29917?",
]
for col, q in zip(cols, demo_top):
    if col.button(q, use_container_width=True):
        st.session_state["pending_question"] = q

st.markdown("##### Deeper questions")
cols2 = st.columns(3)
demo_mid = [
    "What patterns can you find in issue reports and the devices used?",
    "Why are Samsung Galaxy devices reported frequently are they more prone to issues or bad phones?",
    "Explain how tickets are typically escalated and handled, based on the graph.",
]
for col, q in zip(cols2, demo_mid):
    if col.button(q, use_container_width=True):
        st.session_state["pending_question"] = q

cols3 = st.columns(2)
demo_extras = [
    "Which team is responsible when tickets are escalated?",
    "How much billing is associated with recent tickets?",
]
for col, q in zip(cols3, demo_extras):
    if col.button(q, use_container_width=True):
        st.session_state["pending_question"] = q

st.divider()

# ----------------------------------------------------------------------------
# Chat history
# ----------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state["messages"] = []

for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            render_answer(msg["entry"])
        else:
            st.markdown(msg["content"])

# ----------------------------------------------------------------------------
# Input handling
# ----------------------------------------------------------------------------
question = st.chat_input("Ask the knowledge graph…")
if "pending_question" in st.session_state:
    question = st.session_state.pop("pending_question")

if question:
    st.session_state["messages"].append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    if question in QA_BANK:
        entry = QA_BANK[question]
        with st.chat_message("assistant"):
            with st.spinner("Querying graph…"):
                time.sleep(1.2)
            render_answer(entry)
        st.session_state["messages"].append(
            {"role": "assistant", "content": entry["answer"], "entry": entry}
        )
    else:
        fallback = {
            "answer": (
                "This demo replays validated answers from the original notebook "
                "pipeline (`7_neo4j_RAG.ipynb`). For free-form questions, please "
                "see the notebook — it shows the full GraphRAG chain running "
                "against Neo4j Aura with Llama 3.1."
            ),
            "triples": [],
        }
        with st.chat_message("assistant"):
            st.markdown(fallback["answer"])
            st.caption(
                "Try one of the suggested questions above to see retrieval + "
                "answer with source triples."
            )
        st.session_state["messages"].append(
            {"role": "assistant", "content": fallback["answer"], "entry": fallback}
        )
