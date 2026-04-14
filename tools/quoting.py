import streamlit as st
import pandas as pd
import openpyxl


def parse_nextgen(file) -> tuple[dict, pd.DataFrame]:
    """Parse a NEXTGEN quote xlsx and return (meta, items_df)."""
    df_raw = pd.read_excel(file, header=None, sheet_name=0)

    # --- Meta from row index 1 ---
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

    # --- Line items: rows where col[0] is a number ---
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
    """Parse a TECHDATA quote xlsx — pendiente de implementar."""
    # Se implementará cuando se reciba un ejemplo de quote TECHDATA
    return {}, pd.DataFrame()


def show():
    st.title("📋 Quoting")

    # ── Distributor selector ──────────────────────────────────────────────────
    distributor = st.radio(
        "Distribuidor",
        ["NEXTGEN", "TECHDATA"],
        horizontal=True,
    )

    st.divider()

    # ── File upload ───────────────────────────────────────────────────────────
    uploaded = st.file_uploader(
        f"Sube el quote de **{distributor}** (.xlsx)",
        type=["xlsx"],
        key=f"upload_{distributor}",
    )

    if uploaded is None:
        st.info("Sube un fichero Excel para comenzar.")
        return

    # ── Parse ─────────────────────────────────────────────────────────────────
    if distributor == "NEXTGEN":
        with st.spinner("Procesando quote NEXTGEN..."):
            meta, items = parse_nextgen(uploaded)
    else:
        st.warning("Parser de TECHDATA en construcción. Sube un quote NEXTGEN por ahora.")
        return

    if items.empty:
        st.error("No se encontraron line items en el fichero. ¿Es un quote NEXTGEN válido?")
        return

    # ── Quote metadata ────────────────────────────────────────────────────────
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

    # ── Items table ───────────────────────────────────────────────────────────
    st.markdown("### 🛒 Line Items")

    styled = items.style.format({
        "Precio Unit.": "$ {:,.2f}",
        "Total":        "$ {:,.2f}",
    })
    st.dataframe(styled, use_container_width=True, hide_index=True)

    # ── Totals ────────────────────────────────────────────────────────────────
    subtotal = items["Total"].sum()
    gst      = subtotal * 0.10
    total    = subtotal + gst

    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.metric("Subtotal",  f"AUD {subtotal:,.2f}")
    c2.metric("GST (10%)", f"AUD {gst:,.2f}")
    c3.metric("Total AUD", f"AUD {total:,.2f}")
