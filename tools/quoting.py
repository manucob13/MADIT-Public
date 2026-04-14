import streamlit as st
import pandas as pd
import zipfile
import xml.etree.ElementTree as ET
import io


def read_xlsx_native(file) -> pd.DataFrame:
    content = file.read()
    z = zipfile.ZipFile(io.BytesIO(content))

    shared_strings = []
    if "xl/sharedStrings.xml" in z.namelist():
        tree = ET.parse(z.open("xl/sharedStrings.xml"))
        root = tree.getroot()
        ns = root.tag.split("}")[0] + "}" if "}" in root.tag else ""
        for si in root.findall(f"{ns}si"):
            texts = si.findall(f".//{ns}t")
            shared_strings.append("".join(t.text or "" for t in texts))

    sheet_file = next(
        name for name in z.namelist()
        if name.startswith("xl/worksheets/") and name.endswith(".xml")
    )
    tree = ET.parse(z.open(sheet_file))
    root = tree.getroot()
    ns = root.tag.split("}")[0] + "}" if "}" in root.tag else ""

    rows = []
    for row in root.findall(f".//{ns}row"):
        row_data = {}
        for cell in row.findall(f"{ns}c"):
            col_ref = "".join(filter(str.isalpha, cell.get("r", "")))
            col_idx = 0
            for ch in col_ref:
                col_idx = col_idx * 26 + (ord(ch) - ord("A") + 1)
            col_idx -= 1
            v = cell.find(f"{ns}v")
            t = cell.get("t", "")
            if v is not None and v.text is not None:
                if t == "s":
                    row_data[col_idx] = shared_strings[int(v.text)]
                else:
                    row_data[col_idx] = v.text
            else:
                row_data[col_idx] = ""
        rows.append(row_data)

    if not rows:
        return pd.DataFrame()

    max_col = max(max(r.keys()) for r in rows if r)
    data = [[r.get(c, "") for c in range(max_col + 1)] for r in rows]
    return pd.DataFrame(data)


def parse_nextgen(file) -> tuple[dict, pd.DataFrame]:
    df_raw = read_xlsx_native(file)

    meta = {}
    try:
        row1 = df_raw.iloc[1]
        meta["quote_number"] = str(row1[1]).strip()
        meta["description"]  = str(row1[4]).strip()
        meta["expiry"]       = str(row1[7]).split(" ")[0].strip()
        meta["end_user"]     = str(row1[26]).strip() if len(row1) > 26 else ""
        meta["reseller"]     = str(row1[31]).strip() if len(row1) > 31 else ""
        meta["currency"]     = str(row1[43]).strip() if len(row1) > 43 else "AUD"
    except Exception:
        pass

    items = []
    for _, row in df_raw.iterrows():
        try:
            line_no = int(float(str(row[0])))
        except (ValueError, TypeError):
            continue
        sku         = str(row[1]).strip()
        description = str(row[2]).replace("_x000a_", " ").strip()
        try:
            qty        = int(float(str(row[5])))
            unit_price = float(str(row[6]))
            total      = float(str(row[7]))
        except (ValueError, TypeError):
            continue
        items.append({
            "#":            line_no,
            "SKU":          sku,
            "Descripción":  description,
            "Qty":          qty,
            "Precio Unit.": unit_price,
            "Total":        total,
        })

    return meta, pd.DataFrame(items)


def parse_techdata(file) -> tuple[dict, pd.DataFrame]:
    return {}, pd.DataFrame()


def apply_margin(items: pd.DataFrame, margin_pct: float) -> pd.DataFrame:
    m = margin_pct / 100.0
    df = items.copy()
    df["PVP Unit."]   = df["Precio Unit."] / (1 - m)
    df["PVP Total"]   = df["PVP Unit."] * df["Qty"]
    df["GST (10%)"]   = df["PVP Total"] * 0.10
    df["Total c/GST"] = df["PVP Total"] + df["GST (10%)"]
    return df


def show():
    st.title("📋 Quoting")

    distributor = st.radio(
        "Distribuidor",
        ["NEXTGEN", "TECHDATA"],
        horizontal=True,
    )

    st.divider()

    uploaded = st.file_uploader(
        f"Sube el quote de **{distributor}** (.xlsx)",
        type=["xlsx"],
        key=f"upload_{distributor}",
    )

    if uploaded is None:
        st.info("Sube un fichero Excel para comenzar.")
        return

    if distributor == "NEXTGEN":
        with st.spinner("Procesando quote NEXTGEN..."):
            meta, items = parse_nextgen(uploaded)
    else:
        st.warning("Parser de TECHDATA en construcción.")
        return

    if items.empty:
        st.error("No se encontraron line items. ¿Es un quote NEXTGEN válido?")
        return

    # ── Metadata ──────────────────────────────────────────────────────────────
    st.markdown("### 📄 Información del Quote")
    col1, col2, col3 = st.columns(3)
    col1.metric("Quote #",  meta.get("quote_number", "—"))
    col2.metric("Expiry",   meta.get("expiry",        "—"))
    col3.metric("Currency", meta.get("currency",      "AUD"))

    with st.expander("Más detalles"):
        st.write(f"**Descripción:** {meta.get('description', '—')}")
        st.write(f"**End User:** {meta.get('end_user', '—')}")
        st.write(f"**Reseller:** {meta.get('reseller', '—')}")

    st.divider()

    # ── Coste original ────────────────────────────────────────────────────────
    st.markdown("### 🛒 Coste Original (Distribuidor)")
    st.dataframe(
        items.style.format({
            "Precio Unit.": "$ {:,.2f}",
            "Total":        "$ {:,.2f}",
        }),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    # ── Margen ────────────────────────────────────────────────────────────────
    st.markdown("### 💰 Precio de Venta con Margen")
    margin_pct = st.number_input(
        "Margen (%)",
        min_value=0.0,
        max_value=99.0,
        value=10.0,
        step=0.5,
        format="%.1f",
        help="Fórmula: PVP = Coste / (1 - Margen)",
    )

    df_margin = apply_margin(items, margin_pct)

    # Solo: #, SKU, Descripción, Qty, PVP Unit., PVP Total, GST (10%), Total c/GST
    display_cols = ["#", "SKU", "Descripción", "Qty", "PVP Unit.", "PVP Total", "GST (10%)", "Total c/GST"]
    st.dataframe(
        df_margin[display_cols].style.format({
            "PVP Unit.":   "$ {:,.2f}",
            "PVP Total":   "$ {:,.2f}",
            "GST (10%)":   "$ {:,.2f}",
            "Total c/GST": "$ {:,.2f}",
        }),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    # ── Resumen ───────────────────────────────────────────────────────────────
    st.markdown("### 📊 Resumen")

    coste_total = items["Total"].sum()
    pvp_total   = df_margin["PVP Total"].sum()
    gst_total   = df_margin["GST (10%)"].sum()
    total_gst   = df_margin["Total c/GST"].sum()
    diferencia  = pvp_total - coste_total

    resumen = pd.DataFrame([
        {"Concepto": "Coste total original",                    "Importe AUD": f"$ {coste_total:,.2f}"},
        {"Concepto": f"Precio total (margen {margin_pct:.1f}%)", "Importe AUD": f"$ {pvp_total:,.2f}"},
        {"Concepto": "Diferencia",                              "Importe AUD": f"$ {diferencia:,.2f}"},
        {"Concepto": "GST (10%)",                               "Importe AUD": f"$ {gst_total:,.2f}"},
        {"Concepto": "Total con GST",                           "Importe AUD": f"$ {total_gst:,.2f}"},
    ])

    st.dataframe(resumen, use_container_width=True, hide_index=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Coste",       f"AUD {coste_total:,.2f}")
    c2.metric("Precio",      f"AUD {pvp_total:,.2f}")
    c3.metric("Diferencia",  f"AUD {diferencia:,.2f}")
    c4.metric("Total c/GST", f"AUD {total_gst:,.2f}")
