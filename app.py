import streamlit as st

st.set_page_config(
    page_title="MADIT | Herramientas",
    page_icon="🔷",
    layout="wide",
)

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔷 MADIT")
    st.subheader("Portal de Herramientas Internas")
    st.divider()

    with st.form("login_form"):
        username = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        submitted = st.form_submit_button("Entrar")

        if submitted:
            usuarios = st.secrets["credentials"]
            if username in usuarios and usuarios[username] == password:
                st.session_state["authenticated"] = True
                st.session_state["username"] = username
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")

else:
    with st.sidebar:
        st.markdown("""
        <svg width="150" height="50" viewBox="0 0 150 50" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect width="40" height="40" x="0" y="5" rx="8" fill="#1a6fe8"/>
          <path d="M8 38L14 18H19L23 29L27 18H32L38 38H33.5L31 29.5L28 38H18L15 29.5L12.5 38H8Z" fill="white"/>
          <text x="48" y="33" font-family="Inter, sans-serif" font-size="22" font-weight="700" fill="#1a6fe8">MADIT</text>
        </svg>
        """, unsafe_allow_html=True)
        st.divider()
        st.markdown(f"👤 **{st.session_state['username']}**")
        st.divider()

        pagina = st.radio(
            "Menú",
            ["🏠 Inicio", "📋 Quoting"],
            label_visibility="hidden"
        )

        st.divider()
        if st.button("🚪 Cerrar sesión", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    if pagina == "🏠 Inicio":
        st.title("🔷 MADIT")
        st.write(f"Bienvenido, **{st.session_state['username']}**")
        st.info("Selecciona una herramienta en el menú lateral.")

    elif pagina == "📋 Quoting":
        st.title("📋 Quoting")
        st.info("Herramienta en construcción...")
