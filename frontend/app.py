import streamlit as st
import requests

BACKEND_URL = "http://localhost:8000"

st.set_page_config(page_title="Email Productivity Agent", layout="wide")

st.title("📧 Prompt-Driven Email Productivity Agent")

# ---------- SIDEBAR: PROMPT BRAIN ---------- #
st.sidebar.header("🧠 Prompt Brain")

if "prompts_loaded" not in st.session_state:
    st.session_state.prompts_loaded = False
    st.session_state.prompts = {}

def load_prompts():
    resp = requests.get(f"{BACKEND_URL}/prompts")
    if resp.status_code == 200:
        st.session_state.prompts = resp.json()
        st.session_state.prompts_loaded = True
    else:
        st.sidebar.error("Failed to load prompts from backend.")

if not st.session_state.prompts_loaded:
    load_prompts()

with st.sidebar.form("prompt_form"):
    cat_prompt = st.text_area(
        "Categorization Prompt",
        value=st.session_state.prompts.get("categorization_prompt", ""),
        height=120
    )
    act_prompt = st.text_area(
        "Action Item Prompt",
        value=st.session_state.prompts.get("action_item_prompt", ""),
        height=120
    )
    auto_prompt = st.text_area(
        "Auto-Reply Draft Prompt",
        value=st.session_state.prompts.get("auto_reply_prompt", ""),
        height=150
    )
    submitted = st.form_submit_button("Save Prompts")
    if submitted:
        payload = {
            "categorization_prompt": cat_prompt,
            "action_item_prompt": act_prompt,
            "auto_reply_prompt": auto_prompt
        }
        resp = requests.post(f"{BACKEND_URL}/prompts", json=payload)
        if resp.status_code == 200:
            st.sidebar.success("Prompts updated.")
            st.session_state.prompts = resp.json()
        else:
            st.sidebar.error("Failed to update prompts.")


# ---------- MAIN LAYOUT ---------- #

tab1, tab2, tab3 = st.tabs(["📥 Inbox & Processing", "💬 Email Agent", "✍️ Drafts"])


# ---------- TAB 1: Inbox & Processing ---------- #
with tab1:
    st.subheader("Inbox & Email Processing")

    col1, col2 = st.columns([1, 3])

    with col1:
        if st.button("Load & Process Mock Inbox"):
            resp = requests.post(f"{BACKEND_URL}/inbox/load")
            if resp.status_code == 200:
                st.success(f"Inbox processed. Emails processed: {resp.json()['processed_count']}")
            else:
                st.error(f"Failed to process inbox: {resp.text}")

        st.caption("This will load emails.json, categorize, and extract actions.")

    with col2:
        resp = requests.get(f"{BACKEND_URL}/emails")
        if resp.status_code == 200:
            emails = resp.json()
            if emails:
                st.write("**Emails:**")
                st.dataframe(emails, use_container_width="stretch")
            else:
                st.info("No emails loaded yet. Click 'Load & Process  Inbox'.")
        else:
            st.error("Failed to fetch emails.")


# ---------- TAB 2: Email Agent (Chat-style) ---------- #
with tab2:
    st.subheader("Email Agent – Ask Questions")

    # Load emails for dropdown
    resp = requests.get(f"{BACKEND_URL}/emails")
    email_options = []
    if resp.status_code == 200:
        email_options = resp.json()

    email_id_map = {f"{e['id']} | {e['subject'][:40]}": e["id"] for e in email_options} if email_options else {}
    selected_email_label = st.selectbox(
        "Select an email (optional)",
        options=["None"] + list(email_id_map.keys())
    )

    user_query = st.text_area(
        "Ask something (e.g., 'Summarize this email', 'What tasks do I need to do?', 'Show me all urgent emails')",
        height=120
    )

    if st.button("Ask Agent"):
        if not user_query.strip():
            st.warning("Please type a question.")
        else:
            payload = {
                "email_id": None if selected_email_label == "None" else email_id_map[selected_email_label],
                "user_query": user_query
            }
            resp = requests.post(f"{BACKEND_URL}/agent/query", json=payload)
            if resp.status_code == 200:
                response_text = resp.json().get("response", "")
                st.markdown("**Agent Response:**")
                st.code(response_text)
            else:
                st.error(f"Request failed: {resp.text}")


# ---------- TAB 3: Draft Generation ---------- #
with tab3:
    st.subheader("Generate & View Drafts")

    resp = requests.get(f"{BACKEND_URL}/emails")
    email_options = []
    if resp.status_code == 200:
        email_options = resp.json()

    email_id_map = {f"{e['id']} | {e['subject'][:40]}": e["id"] for e in email_options} if email_options else {}
    selected_email_label = st.selectbox(
        "Reply to an existing email (optional)",
        options=["None"] + list(email_id_map.keys()),
        key="draft_email_select"
    )

    tone = st.selectbox("Tone", ["formal", "friendly", "brief"])
    extra = st.text_area("Additional instructions (optional)", height=80)

    if st.button("Generate Draft"):
        payload = {
            "email_id": None if selected_email_label == "None" else email_id_map[selected_email_label],
            "tone": tone,
            "additional_instructions": extra or None
        }
        resp = requests.post(f"{BACKEND_URL}/drafts", json=payload)
        if resp.status_code == 200:
            draft = resp.json()
            st.success(f"Draft created (ID: {draft['id']})")
            st.markdown("**Subject:**")
            st.write(draft["subject"])
            st.markdown("**Body:**")
            st.code(draft["body"])
            if draft.get("suggested_follow_ups"):
                st.markdown("**Suggested follow-ups:**")
                for item in draft["suggested_follow_ups"]:
                    st.write(f"- {item}")
        else:
            st.error(f"Failed to create draft: {resp.text}")

    st.markdown("---")
    st.markdown("### Saved Drafts")

    resp = requests.get(f"{BACKEND_URL}/drafts")
    if resp.status_code == 200:
        drafts = resp.json()
        if drafts:
            for d in drafts:
                with st.expander(f"Draft #{d['id']} (email_id={d['email_id']})"):
                    st.markdown(f"**Subject:** {d['subject']}")
                    st.markdown("**Body:**")
                    st.code(d["body"])
                    if d.get("suggested_follow_ups"):
                        st.markdown("**Suggested follow-ups:**")
                        for item in d["suggested_follow_ups"]:
                            st.write(f"- {item}")
        else:
            st.info("No drafts yet.")
    else:
        st.error("Failed to load drafts.")



BACKEND_URL="https://emailagentzproductive.onrender.com/"
