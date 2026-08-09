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
    st.title("Smart Learning Planner")
    st.subheader("Your AI buddy to help you study is here!")

    choice = st.selectbox("Choose Action", ["Login", "Sign Up"])

    db = SessionLocal()
    if choice == "Sign Up":
        st.subheader("Create a New Account")
        new_username = st.text_input("Username")
        new_pass = st.text_input("Password", type="password")
        institute = st.text_input("Institute Name")

        if st.button("Register"):
            if new_username and new_pass:
                existing_user = db.query(user).filter(user.username == new_username).first()
                if existing_user:
                    st.error("Username already exists. Please choose another.")
                else:
                    hashed_pw = hash_password(new_pass)
                    new_user_obj = user(username=new_username, password_hash=hashed_pw, institute=institute)
                    db.add(new_user_obj)
                    db.commit()
                    st.success("Account created successfully! Please switch to the Login tab.")
            else:
                st.warning("Please provide both username and password.")
    else:
        st.subheader("Login to Your Account")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            _user = db.query(user).filter(user.username == username).first()
            if _user and verify_password(password, _user.password_hash):
                st.session_state.logged_in = True
                st.session_state.user_id = _user.id
                st.session_state.username = _user.username
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Invalid username or password")
    
    db.close()