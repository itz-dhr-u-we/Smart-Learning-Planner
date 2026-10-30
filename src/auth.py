import streamlit as st
import hashlib
from datetime import date, timedelta
from src.database import SessionLocal, user
import os

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    return hash_password(password) == hashed


def render_auth_page():
    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #F1ECFA, #F3F7FF, #FFF5F0);
    }

    [data-testid="stHeader"] {
        background: transparent;
    }

    .block-container {
        max-width: 650px;
        padding-top: 5rem;
    }

    h1 {
        color: #493D67 !important;
        text-align: center;
        font-size: 2.3rem !important;
        font-weight: 750 !important;
    }

    h2, h3 {
        color: #574A75 !important;
        text-align: center;
    }

    [data-testid="stForm"] {
        background: rgba(255,255,255,0.9);
        border: 1px solid #E5DDF0;
        border-radius: 20px;
        padding: 25px;
    }

    .stTextInput input {
        border-radius: 10px;
        border-color: #DDD5EC;
        background: white;
    }

    [data-testid="stSelectbox"] > div > div {
        border-radius: 10px;
        background: white;
    }

    .stButton > button {
        background: #8E7AB8;
        color: white;
        border: none;
        border-radius: 10px;
        font-weight: 600;
        width: 100%;
        padding: 10px;
    }

    .stButton > button:hover {
        background: #75619F;
        color: white;
        border: none;
    }

    [data-testid="stAlert"] {
        border-radius: 12px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.title("Smart Learning Planner")
    st.subheader("Your personal space to plan, learn and grow.")

    choice = st.selectbox("Choose Action", ["Login", "Sign Up"])

    db = SessionLocal()

    try:
        if choice == "Sign Up":
            st.subheader("Create Your Account")

            new_username = st.text_input("Username")
            new_pass = st.text_input("Password", type="password")
            institute = st.text_input("Institute Name")

            if st.button("Create Account"):
                if new_username.strip() and new_pass:
                    existing_user = db.query(user).filter(
                        user.username == new_username.strip()
                    ).first()

                    if existing_user:
                        st.error("Username already exists. Choose another.")
                    else:
                        hashed_pw = hash_password(new_pass)

                        new_user_obj = user(
                            username=new_username.strip(),
                            password_hash=hashed_pw,
                            institute=institute.strip()
                        )

                        db.add(new_user_obj)
                        db.commit()

                        st.success("Account created! Please log in.")
                else:
                    st.warning("Please provide both username and password.")

        else:
            st.subheader("Welcome Back")

            username = st.text_input("Username")
            password = st.text_input("Password", type="password")

            if st.button("Login"):
                existing_user = db.query(user).filter(
                    user.username == username.strip()
                ).first()

                if existing_user and verify_password(
                    password, existing_user.password_hash
                ):
                    st.session_state.logged_in = True
                    st.session_state.user_id = existing_user.id
                    st.session_state.username = existing_user.username

                    st.success("Logged in successfully!")
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

    finally:
        db.close()
