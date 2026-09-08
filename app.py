import streamlit as st

st.set_page_config(page_title="TaskAnalyzer AI", page_icon="✨", layout="wide", initial_sidebar_state="expanded")

from database import (
    initialize_database, create_conversation, get_conversations,
    get_messages, save_message, update_conversation_title, delete_conversation,
    conversation_belongs_to,
)
from auth import login_page, logout
from ai_engine import generate_response, analyze_file

initialize_database()

for key, value in {
    "logged_in": False, "user_id": None, "username": None,
    "email": None, "conversation_id": None
}.items():
    st.session_state.setdefault(key, value)

st.markdown("""
<style>
.stApp { background:#0e1117; }
[data-testid="stSidebar"] { background:#171923; border-right:1px solid #2b303b; }
.block-container { max-width:1250px; padding-top:1.5rem; padding-bottom:1rem; }
.brand { font-size:1.7rem; font-weight:800; margin-bottom:.1rem; }
.sub { color:#9ca3af; font-size:.88rem; margin-bottom:1.2rem; }
.empty { max-width:760px; margin:8vh auto 2rem; text-align:center; padding:2rem; }
.empty h1 { font-size:2.8rem; margin-bottom:.4rem; }
.empty p { color:#9ca3af; font-size:1.05rem; }
div[data-testid="stChatMessage"] { border-radius:14px; }
</style>
""", unsafe_allow_html=True)

if not st.session_state.logged_in:
    login_page()
    st.stop()

user_id = st.session_state.user_id
if not user_id:
    st.error("Session expired. Please log in again.")
    if st.button("Return to login"):
        logout()
    st.stop()


def new_chat():
    st.session_state.conversation_id = create_conversation(user_id)
    st.rerun()


def title_from(text):
    text = " ".join(text.split())
    return text[:50].rstrip() + ("..." if len(text) > 50 else "")


with st.sidebar:
    st.markdown('<div class="brand">✨ TaskAnalyzer</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub">Your personal AI workspace</div>', unsafe_allow_html=True)
    st.markdown(f"👋 **Hello, {st.session_state.username or 'User'}**")
    st.divider()

    if st.button("＋ New Chat", type="primary", use_container_width=True):
        new_chat()

    search = st.text_input("Search chats", placeholder="Search conversations...", label_visibility="collapsed")
    st.caption("CHAT HISTORY")

    conversations = get_conversations(user_id, search)
    for conv in conversations:
        c1, c2 = st.columns([5, 1])
        active = conv["id"] == st.session_state.conversation_id
        with c1:
            label = ("● " if active else "💬 ") + (conv["title"] or "New conversation")
            if st.button(label, key=f"open_{conv['id']}", use_container_width=True):
                st.session_state.conversation_id = conv["id"]
                st.rerun()
        with c2:
            if st.button("×", key=f"del_{conv['id']}", help="Delete chat"):
                delete_conversation(conv["id"], user_id)
                if st.session_state.conversation_id == conv["id"]:
                    st.session_state.conversation_id = None
                st.rerun()

    st.divider()
    st.caption("ACCOUNT")
    st.write(f"👤 **{st.session_state.username or 'User'}**")
    st.caption(st.session_state.email or "")
    if st.button("🚪 Logout", use_container_width=True):
        logout()


# Ensure a valid active conversation.
if (
    st.session_state.conversation_id is None
    or not conversation_belongs_to(st.session_state.conversation_id, user_id)
):
    st.session_state.conversation_id = create_conversation(user_id)

conversation_id = st.session_state.conversation_id
messages = get_messages(conversation_id, user_id)

if not messages:
    st.markdown("""
    <div class="empty">
      <h1>✨ TaskAnalyzer AI</h1>
      <p>Ask anything, analyze screenshots and PDFs, plan projects, study smarter, and get work done.</p>
    </div>
    """, unsafe_allow_html=True)
    cols = st.columns(4)
    prompts = [
        "Explain a difficult topic",
        "Create a study plan",
        "Analyze my project requirements",
        "Brainstorm project ideas",
    ]
    for col, prompt in zip(cols, prompts):
        with col:
            if st.button(prompt, use_container_width=True):
                st.session_state["suggested_prompt"] = prompt
                st.rerun()

for message in messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

uploaded_file = st.file_uploader(
    "Attach an image, screenshot, PDF or text file",
    type=["png", "jpg", "jpeg", "webp", "pdf", "txt"],
    help="The attachment is analyzed together with your next message."
)
if uploaded_file and uploaded_file.type and uploaded_file.type.startswith("image/"):
    st.image(uploaded_file, caption=uploaded_file.name, width=500)
elif uploaded_file:
    st.caption(f"📎 Ready to analyze: {uploaded_file.name}")

suggested = st.session_state.pop("suggested_prompt", None)
prompt = st.chat_input("Message TaskAnalyzer...")
if suggested and not prompt:
    prompt = suggested

if prompt and prompt.strip():
    prompt = prompt.strip()
    first_message = len(messages) == 0

    with st.chat_message("user"):
        st.markdown(prompt)
        if uploaded_file:
            st.caption(f"📎 {uploaded_file.name}")

    save_message(conversation_id, "user", prompt)

    if first_message:
        update_conversation_title(conversation_id, user_id, title_from(prompt))

    history_rows = get_messages(conversation_id, user_id)
    history = [{"role": row["role"], "content": row["content"]} for row in history_rows[:-1]]

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            if uploaded_file:
                ok, response = analyze_file(prompt, uploaded_file, history)
            else:
                ok, response = generate_response(prompt, history)

        if ok:
            st.markdown(response)
            save_message(conversation_id, "assistant", response)
        else:
            st.error(response)

    st.rerun()
