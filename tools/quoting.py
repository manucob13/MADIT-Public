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
            "#":          line_no,
            "SKU":        sku,
            "Description": description,
            "Qty":        qty,
            "Unit Cost":  unit_price,
            "Total Cost": total,
        })

    return meta, pd.DataFrame(items)


def parse_techdata(file) -> tuple[dict, pd.DataFrame]:
    return {}, pd.DataFrame()


def apply_margin(items: pd.DataFrame, margin_pct: float) -> pd.DataFrame:
    m = margin_pct / 100.0
    df = items.copy()
    df["Unit Price"] = df["Unit Cost"] / (1 - m)
    df["Total"]      = df["Unit Price"] * df["Qty"]
    return df


def show():
    st.title("📋 Quoting")

    distributor = st.radio(
        "Distributor",
        ["NEXTGEN", "TECHDATA"],
        horizontal=True,
    )

    st.divider()

    uploaded = st.file_uploader(
        f"Upload **{distributor}** quote (.xlsx)",
        type=["xlsx"],
        key=f"upload_{distributor}",
    )

    if uploaded is None:
        st.info("Upload an Excel file to get started.")
        return

    if distributor == "NEXTGEN":
        with st.spinner("Processing NEXTGEN quote..."):
            meta, items = parse_nextgen(uploaded)
    else:
        st.warning("TECHDATA parser coming soon. Please upload a NEXTGEN quote.")
        return

    if items.empty:
        st.error("No line items found. Is this a valid NEXTGEN quote?")
        return

    # ── Quote info ─────────────────────────────────────────────────────────────
    st.markdown("### 📄 Quote Information")
    col1, col2, col3 = st.columns(3)
    col1.metric("Quote #",   meta.get("quote_number", "—"))
    col2.metric("Expiry",    meta.get("expiry",        "—"))
    col3.metric("Currency",  meta.get("currency",      "AUD"))

    with st.expander("More details"):
        st.write(f"**Description:** {meta.get('description', '—')}")
        st.write(f"**End User:** {meta.get('end_user', '—')}")
        st.write(f"**Reseller:** {meta.get('reseller', '—')}")

    st.divider()

    # ── Cost table ─────────────────────────────────────────────────────────────
    st.markdown("### 🛒 Distributor Cost")
    st.dataframe(
        items.style.format({
            "Unit Cost":  "$ {:,.2f}",
            "Total Cost": "$ {:,.2f}",
        }),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    # ── Margin ─────────────────────────────────────────────────────────────────
    st.markdown("### 💰 Sell Price with Margin")
    margin_pct = st.number_input(
        "Margin (%)",
        min_value=0.0,
        max_value=99.0,
        value=10.0,
        step=0.5,
        format="%.1f",
        help="Formula: Sell Price = Cost / (1 - Margin)",
    )

    df_margin = apply_margin(items, margin_pct)

    # Table: no GST per line, just unit price and total
    display_cols = ["#", "SKU", "Description", "Qty", "Unit Price", "Total"]
    st.dataframe(
        df_margin[display_cols].style.format({
            "Unit Price": "$ {:,.2f}",
            "Total":      "$ {:,.2f}",
        }),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    # ── Summary ────────────────────────────────────────────────────────────────
    st.markdown("### 📊 Summary")

    cost_total  = items["Total Cost"].sum()
    sell_total  = df_margin["Total"].sum()
    gst_total   = sell_total * 0.10
    grand_total = sell_total + gst_total
    difference  = sell_total - cost_total

    summary = pd.DataFrame([
        {"Item": "Total cost (distributor)",              "Amount AUD": f"$ {cost_total:,.2f}"},
        {"Item": f"Total sell price ({margin_pct:.1f}% margin)", "Amount AUD": f"$ {sell_total:,.2f}"},
        {"Item": "Difference",                            "Amount AUD": f"$ {difference:,.2f}"},
        {"Item": "GST (10%)",                             "Amount AUD": f"$ {gst_total:,.2f}"},
        {"Item": "Grand Total (inc. GST)",                "Amount AUD": f"$ {grand_total:,.2f}"},
    ])

    st.dataframe(summary, use_container_width=True, hide_index=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cost",        f"AUD {cost_total:,.2f}")
    c2.metric("Sell Price",  f"AUD {sell_total:,.2f}")
    c3.metric("Difference",  f"AUD {difference:,.2f}")
    c4.metric("Grand Total", f"AUD {grand_total:,.2f}")
