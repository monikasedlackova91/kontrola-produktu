import streamlit as st

st.set_page_config(
    page_title="Rozcestník",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.title("Vyber část aplikace")
st.write("Klikni na to, co právě potřebuješ.")

st.markdown("###")

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("🍳 Kuchyň")
    st.write("Kontrola produktů a práce kuchyně.")
    if st.button("Otevřít kuchyň", use_container_width=True):
        st.switch_page("pages/0_Kuchyn.py")

with col2:
    st.subheader("📦 Bedny")
    st.write("Evidence beden k vyzvednutí.")
    if st.button("Otevřít bedny", use_container_width=True):
        st.switch_page("pages/1_Bedny_kuchyne.py")

with col3:
    st.subheader("🚚 Řidič")
    st.write("Jednoduché vyzvednutí beden.")
    if st.button("Otevřít řidiče", use_container_width=True):
        st.switch_page("pages/2_Ridic_bedny.py")
