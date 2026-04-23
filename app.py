import streamlit as st

st.set_page_config(
    page_title="Rozcestník",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.title("Vyber část aplikace")
st.write("Klikni na to, co právě potřebuješ.")

st.markdown("###")

with st.container(border=True):
    st.subheader("🍳 Kuchyň")
    st.write("Kontrola produktů, chybějící suroviny a práce kuchyně.")
    if st.button("Otevřít kuchyň", use_container_width=True):
        st.switch_page("pages/0_Kuchyn.py")

with st.container(border=True):
    st.subheader("📦 Bedny")
    st.write("Evidence beden k vyzvednutí a práce kuchyně s bednami.")
    if st.button("Otevřít bedny", use_container_width=True):
        st.switch_page("pages/1_Bedny_kuchyne.py")

with st.container(border=True):
    st.subheader("🚚 Řidič")
    st.write("Jednoduché vyzvednutí a práce řidiče.")
    if st.button("Otevřít řidiče", use_container_width=True):
        st.switch_page("pages/2_Ridic_bedny.py")

with st.container(border=True):
    st.subheader("📖 Recepty")
    st.write("Dopisování a úprava receptů k produktům.")
    if st.button("Otevřít recepty", use_container_width=True):
        st.switch_page("pages/3_Recepty.py")

with st.container(border=True):
    st.subheader("🧾 Produkty")
    st.write("Přehled a správa produktů.")
    if st.button("Otevřít produkty", use_container_width=True):
        st.switch_page("pages/4_Produkty.py")
