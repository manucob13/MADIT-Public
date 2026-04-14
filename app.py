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
        st.image("https://via.placeholder.com/150x50?text=MADIT", width=150)
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
