# chal.py
# Simulador de Combos Rentables - Café y Pizzas El Chal

import streamlit as st
import pandas as pd
import numpy as np
from typing import Dict, List

st.set_page_config(layout="wide", page_title="Simulador de Combos – El Chal", page_icon="🍕")

# =========================
# Helpers robustos
# =========================
def pick_col(df: pd.DataFrame, candidates: List[str], required: bool = True, default=None):
    """Devuelve la 1ra columna que exista entre 'candidates' (case-sensitive)."""
    for c in candidates:
        if c in df.columns:
            return c
    if required:
        raise KeyError(f"No encontré ninguna de estas columnas: {candidates}")
    return default

def to_num(s):
    return pd.to_numeric(s, errors="coerce")

def norm_text(s):
    return str(s).strip().casefold()

@st.cache_data(ttl=1800)
def load_df(file) -> pd.DataFrame:
    df = pd.read_csv(file)
    return df

def ensure_cost(df: pd.DataFrame, price_col: str, cost_col: str, default_foodcost: float) -> pd.DataFrame:
    """Si no hay costo, lo estima con un % de food cost sobre precio."""
    if cost_col not in df.columns:
        df[cost_col] = to_num(df[price_col]) * default_foodcost
    return df

def label_row(row, name_col, size_col):
    name = str(row[name_col])
    size = str(row[size_col]) if size_col else ""
    return f"{name} [{size}]" if size and size.lower() != "nan" else name

def pesos(x): 
    try:
        return f"${x:,.2f}"
    except Exception:
        return x

# =========================
# UI – Carga de datos
# =========================
st.title("🍕 Simulador de Combos Rentables – Café y Pizzas *El Chal*")
st.caption("Arma combos, ajusta precio, simula costos y comisiones, y mide margen / contribución.")

left, right = st.columns([2,1])
with left:
    uploaded = st.file_uploader("Sube tu CSV de menú / precios", type=["csv"])
    default_cost_pct = st.slider("Si tu CSV no trae **Costo (MXN)**, ¿qué % de costo estimado usamos?",
                                 min_value=0.10, max_value=0.60, value=0.35, step=0.01)
with right:
    st.info("Columnas flexibles: Precio (MXN)/Precio, Costo (MXN)/Costo, Restaurante/Marca/Origen, Nombre del Producto, Tamaño/Presentación, Categoría/Subcategoría.")

if not uploaded:
    st.stop()

df_raw = load_df(uploaded)

# =========================
# Normalización de columnas
# =========================
try:
    price_col = pick_col(df_raw, ["Precio (MXN)", "Precio", "precio"])
except KeyError:
    st.error("Tu CSV debe incluir una columna de Precio. Nombres válidos: Precio (MXN) / Precio.")
    st.stop()

name_col = pick_col(df_raw, ["Nombre del Producto", "Producto", "Nombre"], required=True)
brand_col = pick_col(df_raw, ["Restaurante", "Marca", "Origen", "Proveedor"], required=False, default=None)
size_col = pick_col(df_raw, ["Tamaño", "Presentación", "Tamano", "Size"], required=False, default=None)
cat_col  = pick_col(df_raw, ["Categoría", "Categoria"], required=False, default=None)
subcat_col = pick_col(df_raw, ["Subcategoría", "Subcategoria"], required=False, default=None)
cost_col = pick_col(df_raw, ["Costo (MXN)", "Costo", "costo"], required=False, default="__COSTO_TMP__")

df = df_raw.copy()
df[price_col] = to_num(df[price_col])
df = ensure_cost(df, price_col, cost_col, default_cost_pct)

# Tag de restaurante
if brand_col:
    # Normalizar bandera de El Chal
    is_el_chal = df[brand_col].astype(str).str.contains("chal", case=False, na=False)
else:
    # Si no hay columna de restaurante, asumimos que TODO es de El Chal
    is_el_chal = pd.Series(True, index=df.index)

df["__display__"] = df.apply(lambda r: label_row(r, name_col, size_col), axis=1)

elchal_df = df.loc[is_el_chal].reset_index(drop=True)
comp_df   = df.loc[~is_el_chal].reset_index(drop=True)

if elchal_df.empty:
    st.warning("No detecté productos de *El Chal* (por columna Restaurante/Marca). Tomaré todo el archivo como productos de El Chal.")
    elchal_df = df.copy()
    comp_df = df.iloc[0:0].copy()

# =========================
# Panel – Filtros y constructor de combo
# =========================
st.subheader("🧩 Construcción del Combo")

f1, f2, f3 = st.columns(3)
with f1:
    cat_sel = st.selectbox("Filtra por **Categoría** (opcional):",
                           ["(todas)"] + (sorted(elchal_df[cat_col].dropna().unique()) if cat_col else []))
with f2:
    subcat_sel = st.selectbox("Filtra por **Subcategoría** (opcional):",
                              ["(todas)"] + (sorted(elchal_df[subcat_col].dropna().unique()) if subcat_col else []))
with f3:
    st.write(" ")

mask = pd.Series(True, index=elchal_df.index)
if cat_col and cat_sel != "(todas)":
    mask &= elchal_df[cat_col].astype(str).str.strip() == str(cat_sel).strip()
if subcat_col and subcat_sel != "(todas)":
    mask &= elchal_df[subcat_col].astype(str).str.strip() == str(subcat_sel).strip()

menu_df = elchal_df.loc[mask].copy()
if menu_df.empty:
    st.info("No hay productos con esos filtros. Quita filtros o sube otro CSV.")
    st.stop()

# Selección múltiple
options = menu_df["__display__"].tolist()
sel = st.multiselect("Elige los **productos** que integrarán el combo:", options)

if not sel:
    st.info("Selecciona al menos un producto para crear el combo.")
    st.stop()

# Cantidades por ítem
st.markdown("#### Cantidades por ítem del combo")
qty_cols = st.columns([1,4,1,1,1])
qty_cols[0].markdown("**Cant.**")
qty_cols[1].markdown("**Producto**")
qty_cols[2].markdown("**Precio**")
qty_cols[3].markdown("**Costo**")
qty_cols[4].markdown("**Subtotal**")

combo_rows = []
for item in sel:
    row = menu_df.loc[menu_df["__display__"] == item].iloc[0]
    p = float(row[price_col])
    c = float(row[cost_col])
    q = qty_cols[0].number_input(f"q_{item}", min_value=1, value=1, step=1, label_visibility="collapsed", key=f"qty_{item}")
    qty_cols[1].write(item)
    qty_cols[2].write(pesos(p))
    qty_cols[3].write(pesos(c))
    qty_cols[4].write(pesos(q*p))
    combo_rows.append({"Producto": item, "Precio": p, "Costo": c, "Cantidad": q})

combo_df = pd.DataFrame(combo_rows)
combo_df["Subtotal Precio"] = combo_df["Precio"] * combo_df["Cantidad"]
combo_df["Subtotal Costo"]  = combo_df["Costo"]  * combo_df["Cantidad"]

st.dataframe(combo_df[["Producto","Cantidad","Precio","Costo","Subtotal Precio","Subtotal Costo"]]
             .assign(Precio=lambda d: d["Precio"].map(pesos))
             .assign(Costo=lambda d: d["Costo"].map(pesos))
             .assign(**{"Subtotal Precio": lambda d: d["Subtotal Precio"].map(pesos),
                        "Subtotal Costo":  lambda d: d["Subtotal Costo"].map(pesos)}),
             use_container_width=True)

sum_price = float(combo_df["Subtotal Precio"].sum())
sum_cost  = float(combo_df["Subtotal Costo"].sum())

# =========================
# Simulación de precio del combo
# =========================
st.subheader("💵 Precio del Combo y Rentabilidad")

left, right = st.columns([2,2])

with left:
    st.markdown("**Estrategia de precio**")
    mode = st.radio(
        "¿Cómo fijamos el precio?",
        ["Descuento vs. precios lista", "Margen objetivo sobre costo"],
        horizontal=True
    )
    if mode == "Descuento vs. precios lista":
        desc = st.slider("Descuento sobre la suma de precios de lista (%)", 0, 60, 20, 1)
        combo_price = sum_price * (1 - desc/100.0)
    else:
        target_margin = st.slider("Margen objetivo (sobre precio)", 10, 80, 55, 1)
        # precio = costo / (1 - margen)
        combo_price = sum_cost / max(1e-6, (1 - target_margin/100.0))

with right:
    st.markdown("**Costos adicionales (opcional)**")
    app_commission = st.slider("Comisión de app de entrega (%)", 0, 35, 0, 1)
    packaging = st.number_input("Empaque por combo (MXN)", min_value=0.0, value=0.0, step=1.0)
    other_var = st.number_input("Otros costos variables por combo (MXN)", min_value=0.0, value=0.0, step=1.0)

# Comisión y costos variables
commission_cost = combo_price * (app_commission/100.0)
total_cost_combo = sum_cost + packaging + other_var + commission_cost
margin_abs = combo_price - total_cost_combo
margin_pct = (margin_abs / combo_price * 100) if combo_price > 0 else 0
discount_vs_list = (1 - combo_price / sum_price) * 100 if sum_price > 0 else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Precio de lista (suma)", pesos(sum_price))
k2.metric("Precio del **combo**", pesos(combo_price), f"{-discount_vs_list:.1f}% vs lista")
k3.metric("Costo total combo", pesos(total_cost_combo))
k4.metric("Margen del combo", f"{margin_pct:.1f}%", pesos(margin_abs))

# Sensibilidades rápidas
st.markdown("#### Sensibilidades")
s1, s2 = st.columns(2)
with s1:
    st.write("**Precio ±10%**")
    for delta in [-10, -5, 0, 5, 10]:
        p = combo_price * (1 + delta/100.0)
        m = (p - (sum_cost + packaging + other_var + p*(app_commission/100.0))) / p * 100 if p>0 else 0
        st.write(f"{delta:+d}% → {pesos(p)} | margen {m:,.1f}%")
with s2:
    st.write("**Comisión app de 0% a 30% (paso 5%)**")
    for com in range(0, 31, 5):
        m = (combo_price - (sum_cost + packaging + other_var + combo_price*(com/100.0))) / combo_price * 100 if combo_price>0 else 0
        st.write(f"{com}% → margen {m:,.1f}%")

# =========================
# Comparativo simple con competencia (opcional)
# =========================
with st.expander("📊 Referencia rápida vs competencia (opcional)"):
    if comp_df.empty:
        st.info("No tengo datos de competencia en el CSV.")
    else:
        # competencia comparable: misma subcategoría si existe, si no toda la categoría
        mask_comp = pd.Series(True, index=comp_df.index)
        if cat_col and cat_sel != "(todas)":
            mask_comp &= comp_df[cat_col].astype(str).str.strip() == str(cat_sel).strip()
        if subcat_col and subcat_sel != "(todas)":
            mask_comp &= comp_df[subcat_col].astype(str).str.strip() == str(subcat_sel).strip()
        ref_df = comp_df.loc[mask_comp, [brand_col, name_col, price_col]].copy() if brand_col else comp_df.loc[mask_comp, [name_col, price_col]].copy()
        ref_df.rename(columns={brand_col: "Competidor", name_col: "Producto", price_col: "Precio (MXN)"}, inplace=True)
        if ref_df.empty:
            st.info("No hay referencias bajo estos filtros.")
        else:
            st.dataframe(ref_df.sort_values("Precio (MXN)").assign(**{"Precio (MXN)": lambda d: d["Precio (MXN)"].map(pesos)}),
                         use_container_width=True)

# =========================
# Exportar combo
# =========================
st.markdown("---")
combo_name = st.text_input("Nombre del combo", value="Combo El Chal")
prep_time = st.number_input("Tiempo objetivo de preparación (min)", min_value=0, value=10, step=1)
export_cols = ["Producto","Cantidad","Precio","Costo","Subtotal Precio","Subtotal Costo"]
export_payload = {
    "combo": combo_name,
    "items": combo_df[export_cols].to_dict(orient="records"),
    "suma_precios_lista": round(sum_price, 2),
    "suma_costos": round(sum_cost, 2),
    "precio_combo": round(combo_price, 2),
    "costo_app": round(commission_cost, 2),
    "costo_empaque": round(packaging, 2),
    "otros_costos": round(other_var, 2),
    "costo_total_combo": round(total_cost_combo, 2),
    "margen_abs": round(margin_abs, 2),
    "margen_pct": round(margin_pct, 2),
    "descuento_vs_lista_pct": round(discount_vs_list, 2),
    "prep_time_min": int(prep_time)
}
st.download_button(
    "📥 Descargar combo (.json)",
    data=pd.Series(export_payload).to_json(orient="values", force_ascii=False),
    file_name=f"combo_{combo_name.replace(' ','_')}.json",
    mime="application/json"
)

st.success("Listo. ¡Juega con descuentos, margen objetivo y costos para afinar combos rentables!")

