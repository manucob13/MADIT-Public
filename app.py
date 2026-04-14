import streamlit as st

st.set_page_config(
    page_title="MADIT | Herramientas",
    page_icon="🔷",
    layout="wide",
)

# ─── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://api.fontshare.com/v2/css?f[]=satoshi@400,500,700&display=swap');

  html, body, [class*="css"] { font-family: 'Satoshi', 'Inter', sans-serif; }

  section[data-testid="stSidebar"] {
      background-color: #0f1923;
      border-right: 1px solid #1e2d3d;
  }
  section[data-testid="stSidebar"] * { color: #c9d4df !important; }

  .madit-logo {
      display: flex; align-items: center; gap: 10px;
      padding: 8px 0 16px 0;
  }
  .madit-logo-text {
      font-size: 1.45rem; font-weight: 700;
      letter-spacing: 0.04em; color: #ffffff !important;
  }

  .user-badge {
      display: flex; align-items: center; gap: 8px;
      background: #1a2a3a; border: 1px solid #1e3a52;
      border-radius: 8px; padding: 8px 12px; margin-bottom: 4px;
  }
  .user-badge span { font-size: 0.875rem; font-weight: 500; color: #a8bfd4 !important; }
  .user-dot { width: 8px; height: 8px; background: #22c55e; border-radius: 50%; flex-shrink: 0; }

  div[data-testid="stRadio"] > label { display: none; }

  .block-container { padding-top: 2rem; padding-left: 2.5rem; padding-right: 2.5rem; }
  h1 { font-family: 'Satoshi', 'Inter', sans-serif !important; font-weight: 700; }

  .welcome-card {
      background: linear-gradient(135deg, #0f2a45 0%, #0a1f35 100%);
      border: 1px solid #1e3a52; border-radius: 12px;
      padding: 28px 32px; margin-bottom: 24px;
  }
  .welcome-card h2 { color: #ffffff; font-size: 1.4rem; font-weight: 600; margin-bottom: 4px; }
  .welcome-card p { color: #7fa3c4; font-size: 0.9rem; margin: 0; }

  .login-logo { text-align: center; margin-bottom: 28px; padding-top: 16px; }
  .login-logo-text { font-size: 1.8rem; font-weight: 700; letter-spacing: 0.05em; color: #1a6fe8; margin-top: 8px; }
  .login-subtitle { font-size: 0.85rem; color: #5a7a99; margin-top: 4px; }

  section[data-testid="stSidebar"] div.stButton button {
      background: transparent; border: 1px solid #1e3a52;
      border-radius: 8px; color: #7fa3c4 !important;
      font-size: 0.85rem; transition: all 0.15s;
  }
  section[data-testid="stSidebar"] div.stButton button:hover {
      background: #1a2a3a; border-color: #2a4a62; color: #c9d4df !important;
  }
</style>
""", unsafe_allow_html=True)

# ─── Inline SVG logo ──────────────────────────────────────────────────────────
LOGO_SVG = """<svg style="margin-top:12px; display:inline-block;" width="56" height="56" viewBox="-4 -4 40 40" fill="none" xmlns="http://www.w3.org/2000/svg" aria-label="MADIT">
  <rect width="32" height="32" rx="7" fill="#1a6fe8"/>
  <path d="M5 23L10 11H14L16.5 18L19 11H23L28 23H24.2L22.4 18L20 23H13L10.6 18L8.8 23H5Z" fill="white"/>
</svg>"""

LOGO_SIDEBAR = """<div class="madit-logo">
  <svg width="34" height="34" viewBox="-2 -2 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect width="32" height="32" rx="7" fill="#1a6fe8"/>
    <path d="M5 23L10 11H14L16.5 18L19 11H23L28 23H24.2L22.4 18L20 23H13L10.6 18L8.8 23H5Z" fill="white"/>
  </svg>
  <span class="madit-logo-text">MADIT</span>
</div>"""

# ─── Session state ─────────────────────────────────────────────────────────────
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

# ─── LOGIN ─────────────────────────────────────────────────────────────────────
if not st.session_state["authenticated"]:
    _, col_c, _ = st.columns([1, 1.2, 1])
    with col_c:
        st.markdown(
            f'<div class="login-logo">{LOGO_SVG}'
            '<div class="login-logo-text">MADIT</div>'
            '<div class="login-subtitle">Portal de Herramientas Internas</div>'
            '</div>',
            unsafe_allow_html=True
        )
        with st.form("login_form"):
            username = st.text_input("Usuario", placeholder="tu usuario")
            password = st.text_input("Contraseña", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("Entrar", use_container_width=True)

            if submitted:
                usuarios = st.secrets["credentials"]
                if username in usuarios and usuarios[username] == password:
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = username
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos.")

# ─── APP ───────────────────────────────────────────────────────────────────────
else:
    with st.sidebar:
        st.markdown(LOGO_SIDEBAR, unsafe_allow_html=True)
        st.divider()

        st.markdown(
            f'<div class="user-badge">'
            f'<div class="user-dot"></div>'
            f'<span>{st.session_state["username"]}</span>'
            f'</div>',
            unsafe_allow_html=True
        )
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

    # ─── Pages ────────────────────────────────────────────────────────────────
    if pagina == "🏠 Inicio":
        col1, col2 = st.columns([0.05, 0.95])
        with col1:
            st.markdown(LOGO_SVG, unsafe_allow_html=True)
        with col2:
            st.title("MADIT")

        st.markdown(
            f'<div class="welcome-card">'
            f'<h2>Bienvenido, {st.session_state["username"]} 👋</h2>'
            f'<p>Selecciona una herramienta en el menú lateral para comenzar.</p>'
            f'</div>',
            unsafe_allow_html=True
        )

        st.subheader("Herramientas disponibles")
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.info("**📋 Quoting**\nGeneración de presupuestos")
        with col_b:
            st.warning("**🔧 Más herramientas**\nPróximamente...")
        with col_c:
            st.warning("**📊 Reportes**\nPróximamente...")

    elif pagina == "📋 Quoting":
        from tools.quoting import show
        show()
