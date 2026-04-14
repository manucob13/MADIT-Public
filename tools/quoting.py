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
            "#":           line_no,
            "SKU":         sku,
            "Description": description,
            "Qty":         qty,
            "Unit Cost":   unit_price,
            "Total Cost":  total,
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


def fmt(val) -> str:
    try:
        return f"$ {float(val):,.2f}"
    except (ValueError, TypeError):
        return str(val) if val != "" else ""


def render_html_table(df: pd.DataFrame, money_cols: list, total_col: str) -> str:
    """Render a clean HTML table with small font, bold total row."""
    styles = """
    <style>
      .madit-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.78rem;
        font-family: 'Inter', 'Segoe UI', sans-serif;
      }
      .madit-table thead tr {
        background-color: #1a2a3a;
        color: #ffffff;
      }
      .madit-table thead th {
        padding: 8px 12px;
        text-align: left;
        font-weight: 600;
        letter-spacing: 0.03em;
        white-space: nowrap;
      }
      .madit-table tbody tr {
        border-bottom: 1px solid #e8e8e8;
      }
      .madit-table tbody tr:nth-child(even) {
        background-color: #f7f9fb;
      }
      .madit-table tbody tr:hover {
        background-color: #eef3f8;
      }
      .madit-table tbody td {
        padding: 6px 12px;
        color: #2c3e50;
        vertical-align: top;
      }
      .madit-table .money {
        text-align: right;
        font-variant-numeric: tabular-nums;
        white-space: nowrap;
      }
      .madit-table .total-row td {
        font-weight: 700;
        background-color: #e8f0f7 !important;
        border-top: 2px solid #1a2a3a;
        color: #0f1923;
      }
    </style>
    """

    header = "<thead><tr>" + "".join(f"<th>{col}</th>" for col in df.columns) + "</tr></thead>"

    rows_html = ""
    for _, row in df.iterrows():
        is_total = str(row.get("Description", row.get("", ""))).strip().upper() == "TOTAL"
        row_class = ' class="total-row"' if is_total else ""
        cells = ""
        for col in df.columns:
            val = row[col]
            if col in money_cols:
                display = fmt(val)
                cells += f'<td class="money">{display}</td>'
            else:
                cells += f"<td>{val}</td>"
        rows_html += f"<tr{row_class}>{cells}</tr>"

    tbody = f"<tbody>{rows_html}</tbody>"
    table = f'<table class="madit-table">{header}{tbody}</table>'
    return styles + table


def add_totals_cost(df: pd.DataFrame) -> pd.DataFrame:
    totals = {
        "#": "", "SKU": "", "Description": "TOTAL",
        "Qty": "", "Unit Cost": "", "Total Cost": df["Total Cost"].sum(),
    }
    return pd.concat([df, pd.DataFrame([totals])], ignore_index=True)


def add_totals_sell(df: pd.DataFrame) -> pd.DataFrame:
    totals = {
        "#": "", "SKU": "", "Description": "TOTAL",
        "Qty": "", "Unit Price": "", "Total": df["Total"].sum(),
    }
    return pd.concat([df, pd.DataFrame([totals])], ignore_index=True)


def render_summary_table(summary: pd.DataFrame) -> str:
    styles = """
    <style>
      .summary-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.82rem;
        font-family: 'Inter', 'Segoe UI', sans-serif;
      }
      .summary-table thead tr {
        background-color: #1a2a3a;
        color: #ffffff;
      }
      .summary-table thead th {
        padding: 9px 16px;
        text-align: left;
        font-weight: 600;
        letter-spacing: 0.03em;
      }
      .summary-table tbody tr {
        border-bottom: 1px solid #e0e0e0;
      }
      .summary-table tbody tr:last-child {
        font-weight: 700;
        background-color: #e8f0f7;
        border-top: 2px solid #1a2a3a;
      }
      .summary-table tbody td {
        padding: 8px 16px;
        color: #2c3e50;
        font-variant-numeric: tabular-nums;
      }
      .summary-table tbody td:not(:first-child) {
        text-align: right;
        white-space: nowrap;
      }
    </style>
    """
    header = "<thead><tr>" + "".join(f"<th>{col}</th>" for col in summary.columns) + "</tr></thead>"
    rows_html = ""
    for _, row in summary.iterrows():
        cells = "".join(f"<td>{row[col]}</td>" for col in summary.columns)
        rows_html += f"<tr>{cells}</tr>"
    table = f'<table class="summary-table">{header}<tbody>{rows_html}</tbody></table>'
    return styles + table


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
    col1.metric("Quote #",  meta.get("quote_number", "—"))
    col2.metric("Expiry",   meta.get("expiry",        "—"))
    col3.metric("Currency", meta.get("currency",      "AUD"))

    with st.expander("More details"):
        st.write(f"**Description:** {meta.get('description', '—')}")
        st.write(f"**End User:** {meta.get('end_user', '—')}")
        st.write(f"**Reseller:** {meta.get('reseller', '—')}")

    st.divider()

    # ── Distributor cost table ─────────────────────────────────────────────────
    st.markdown("### 🛒 Distributor Cost")
    st.markdown(
        render_html_table(add_totals_cost(items), ["Unit Cost", "Total Cost"], "Total Cost"),
        unsafe_allow_html=True,
    )

    st.divider()

    # ── Sell price table ───────────────────────────────────────────────────────
    st.markdown("### 💰 Sell Price with Margin")

    if "margin_pct" not in st.session_state:
        st.session_state["margin_pct"] = 10.0

    margin_pct = st.session_state["margin_pct"]
    df_margin  = apply_margin(items, margin_pct)
    sell_cols  = ["#", "SKU", "Description", "Qty", "Unit Price", "Total"]
    st.markdown(
        render_html_table(add_totals_sell(df_margin[sell_cols].copy()), ["Unit Price", "Total"], "Total"),
        unsafe_allow_html=True,
    )

    st.divider()

    # ── Summary ────────────────────────────────────────────────────────────────
    st.markdown("### 📊 Summary")

    _, col_input, _ = st.columns([1, 1, 1])
    with col_input:
        st.number_input(
            "Margin (%)",
            min_value=0.0,
            max_value=99.0,
            step=0.5,
            format="%.1f",
            help="Formula: Sell Price = Cost / (1 - Margin)",
            key="margin_pct",
        )

    margin_pct = st.session_state["margin_pct"]
    df_margin  = apply_margin(items, margin_pct)

    cost_total   = items["Total Cost"].sum()
    cost_gst     = cost_total * 0.10
    cost_inc_gst = cost_total + cost_gst
    sell_total   = df_margin["Total"].sum()
    sell_gst     = sell_total * 0.10
    sell_inc_gst = sell_total + sell_gst

    summary = pd.DataFrame([
        {"": "Subtotal (ex. GST)", "Cost": fmt(cost_total),   "Sell Price": fmt(sell_total),   "Difference": fmt(sell_total   - cost_total)},
        {"": "GST (10%)",          "Cost": fmt(cost_gst),     "Sell Price": fmt(sell_gst),     "Difference": fmt(sell_gst     - cost_gst)},
        {"": "Total (inc. GST)",   "Cost": fmt(cost_inc_gst), "Sell Price": fmt(sell_inc_gst), "Difference": fmt(sell_inc_gst - cost_inc_gst)},
    ])

    _, col_mid, _ = st.columns([1, 2, 1])
    with col_mid:
        st.markdown(render_summary_table(summary), unsafe_allow_html=True)
