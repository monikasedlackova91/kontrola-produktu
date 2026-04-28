import streamlit as st


def check_password():
    if st.session_state.get("logged_in"):
        return True

    st.title("🔒 Přihlášení")
    st.write("Zadej heslo pro vstup do aplikace.")

    password = st.text_input("Heslo", type="password")

    if st.button("Přihlásit"):
        if password == st.secrets["APP_PASSWORD"]:
            st.session_state["logged_in"] = True
            st.rerun()
        else:
            st.error("Špatné heslo.")

    st.stop()
