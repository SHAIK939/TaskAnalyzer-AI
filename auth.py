import bcrypt
import streamlit as st
from database import create_user, get_user_by_email


def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password, stored):
    if not stored:
        return False
    # Supports old SHA-256 accounts only if the legacy column is explicitly used.
    try:
        return bcrypt.checkpw(password.encode(), stored.encode())
    except (ValueError, AttributeError):
        return False


def login_page():
    st.markdown("""
    <div style="text-align:center;padding:2.5rem 0 1.5rem">
      <h1 style="margin-bottom:.3rem">✨ TaskAnalyzer</h1>
      <p style="color:#9ca3af">Your personal AI workspace</p>
    </div>
    """, unsafe_allow_html=True)

    left, center, right = st.columns([1, 1.4, 1])
    with center:
        login_tab, signup_tab = st.tabs(["🔐 Login", "✨ Create account"])

        with login_tab:
            with st.form("login_form", clear_on_submit=False):
                email = st.text_input("Email", placeholder="Enter your email")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                submitted = st.form_submit_button("Login", use_container_width=True)
            if submitted:
                user = get_user_by_email(email)
                stored = user["password_hash"] if user and "password_hash" in user.keys() else None
                # Legacy fallback for existing SHA-256 users.
                if not stored and user and "password" in user.keys():
                    import hashlib
                    if hashlib.sha256(password.encode()).hexdigest() == user["password"]:
                        st.session_state.update({
                            "logged_in": True, "user_id": user["id"],
                            "username": user["username"], "email": user["email"]
                        })
                        st.rerun()
                elif user and verify_password(password, stored):
                    st.session_state.update({
                        "logged_in": True, "user_id": user["id"],
                        "username": user["username"], "email": user["email"]
                    })
                    st.rerun()
                else:
                    st.error("Invalid email or password.")

        with signup_tab:
            with st.form("signup_form", clear_on_submit=True):
                username = st.text_input("Username", placeholder="Choose a username")
                email = st.text_input("Email address", placeholder="Enter your email")
                password = st.text_input("Create password", type="password", placeholder="At least 8 characters")
                confirm = st.text_input("Confirm password", type="password")
                submitted = st.form_submit_button("Create account", use_container_width=True)
            if submitted:
                if not all([username.strip(), email.strip(), password, confirm]):
                    st.error("Please fill in all fields.")
                elif "@" not in email or "." not in email.rsplit("@", 1)[-1]:
                    st.error("Please enter a valid email address.")
                elif len(password) < 8:
                    st.error("Password must contain at least 8 characters.")
                elif password != confirm:
                    st.error("Passwords do not match.")
                else:
                    ok, msg = create_user(username, email, hash_password(password))
                    st.success(msg) if ok else st.error(msg)


def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()
