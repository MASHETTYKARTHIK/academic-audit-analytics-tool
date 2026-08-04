import streamlit as st

from db import authenticate_user, create_user, hash_password, initialize_db, username_exists

initialize_db()

st.set_page_config(page_title="Academic Audit Analytics Tool", layout="wide")

if "user" not in st.session_state:
    st.session_state.user = None

st.title("Academic Audit Analytics Tool")
st.caption("Registrar-friendly audit entry with role-based analytics and editable records")

st.markdown(
    """
    <style>
    .stApp { background: #f8fafc; }
    .block-container { padding-top: 1.5rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

if st.session_state.user is None:
    tabs = st.tabs(["Login", "Register"])

    with tabs[0]:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")

        if submitted:
            user = authenticate_user(username, password)
            if user:
                st.session_state.user = user
                st.session_state.role = user["role"]
                st.rerun()
            else:
                st.error("Invalid username or password")

    with tabs[1]:
        with st.form("register_form"):
            reg_username = st.text_input("Username")
            reg_password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            reg_role = st.selectbox("Role", ["registrar", "admin"])
            register_submitted = st.form_submit_button("Register")

        if register_submitted:
            if not reg_username.strip():
                st.error("Username cannot be empty")
            elif username_exists(reg_username):
                st.error("Username already taken")
            elif reg_password != confirm_password:
                st.error("Passwords do not match")
            elif len(reg_password) < 6:
                st.error("Password must be at least 6 characters")
            else:
                create_user(reg_username.strip(), hash_password(reg_password), reg_role)
                st.success("Account created. Please go to the Login tab to sign in.")
else:
    st.success(f"Signed in as {st.session_state.user['username']} ({st.session_state.user['role']})")
    if st.button("Logout", key="home_logout_1"):
        st.session_state.user = None
        st.session_state.role = None
        st.rerun()

if st.session_state.user is not None:
    if st.session_state.user["role"] == "registrar":
        st.switch_page("pages/1_Registrar.py")
    elif st.session_state.user["role"] == "admin":
        st.switch_page("pages/2_Admin.py")
