# chal.py
# Simulador de Combos Rentables para "Café y Pizzas El Chal"
# - Carga tu menú (CSV) con columnas: ID, Tipo, Categoría, Producto,
#   Precio Actual (MXN), Nuevo Precio Sugerido (MXN), PRECIO EN APPS,
#   PRECIO PARA APPS CON FORMULA, PRECIO MINIMO (las últimas 3 opcionales).
# - IA (Gemini) para generar combos creativos y rentables (variabilidad alta).
# - Edición y exportación de combos.

import streamlit as st
import pandas as pd
import numpy as np
import json, re, random, uuid
from typing import List, Dict, Any

st.set_page_config(layout="wide", page_title="Simulador de Combos – El Chal", page_icon="🍕")

# =========================
# IA: Gemini (opcional)
# =========================
try:
    import google.generativeai as genai
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    GEMINI_AVAILABLE = True
except Exception:
    GEMINI_AVAILABLE = False
    st.warning("⚠️ **Gemini no configurado**: agrega GEMINI_API_KEY en `st.secrets` para habilitar IA.")

def extract_json_block(text: str):
    """Intenta extraer el primer bloque JSON válido del texto."""
    if not text:
        return None
    # 1) bloque { ... }
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    # 2) bloque [ ... ]
    m = re.search(r"\[[\s\S]*\]", text)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return None

def call_gemini(prompt: str) -> Any:
    """Llama a Gemini (temperatura alta para diversidad). Devuelve JSON si hay, o texto."""
    if not GEMINI_AVAILABLE:
        return "IA no disponible."
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        # Config con aleatoriedad y tokens suficientes
        gen_cfg = {
            "temperature": 1.25,
            "top_p": 0.95,
            "max_output_tokens": 4096,
        }
        resp = model.generate_content(prompt, generation_config=gen_cfg)
        txt = getattr(resp, "text", "") or ""
        data = extract_json_block(txt)
        return data if data is not None else txt
    except Exception as e:
        return {"error": f"{e}"}

# =========================
# Helpers
# =========================
def parse_money(series: pd.Series) -> pd.Series:
    """Convierte '$1,234.50', '1,234', '-' a float."""
    return pd.to_numeric(
        series.astype(str).str.replace(r"[^\d\.\-]", "", regex=True).replace({"": np.nan, "nan": np.nan, "-": np.nan}),
        errors="coerce"
    )

def pick_col(df: pd.DataFrame, names: List[str], required=True, default=None) -> str:
    for n in names:
        if n in df.columns:
            return n
    if required:
        raise KeyError(f"No encontré ninguna de estas columnas: {names}")
    return default

def pesos(x: float) -> str:
    try:
        return f"${x:,.2f}"
    except Exception:
        return str(x)

@st.cache_data(ttl=1800)
def load_menu(file) -> pd.DataFrame:
    return pd.read_csv(file)

def costo_estimado_row(price: float, cat: str, cat_cost_pct: Dict[str, float]) -> float:
    return float(price) * float(cat_cost_pct.get(cat, 0.33))

# =========================
# UI: carga de menú
# =========================
st.title("🍕 Simulador de Combos Rentables – *El Chal*")
st.caption("Genera combos con IA o constrúyelos a mano. Ajusta comisiones/costos y exporta.")

up_left, up_right = st.columns([2,1])
with up_left:
    uploaded = st.file_uploader("Sube tu CSV del menú", type=["csv"])
with up_right:
    st.info("Requeridas: **ID, Categoría, Producto, Precio Actual (MXN)**.\n"
            "Opcionales: *Nuevo Precio Sugerido (MXN), PRECIO EN APPS, PRECIO PARA APPS CON FORMULA, PRECIO MINIMO*.")

if not uploaded:
    st.stop()

df_raw = load_menu(uploaded)

# =========================
# Normalización de columnas
# =========================
try:
    id_col   = pick_col(df_raw, ["ID"])
    tipo_col = pick_col(df_raw, ["Tipo"], required=False, default=None)
    cat_col  = pick_col(df_raw, ["Categoría", "Categoria"])
    prod_col = pick_col(df_raw, ["Producto"])
    p_actual = pick_col(df_raw, ["Precio Actual (MXN)", "Precio Actual"])
    p_sug    = pick_col(df_raw, ["Nuevo Precio Sugerido (MXN)", "Nuevo Precio Sugerido"], required=False, default=None)
    p_apps   = pick_col(df_raw, ["PRECIO EN APPS", "Precio en Apps"], required=False, default=None)
    p_apps_f = pick_col(df_raw, ["PRECIO PARA APPS CON FORMULA", "Precio para Apps con formula"], required=False, default=None)
    p_min    = pick_col(df_raw, ["PRECIO MINIMO", "Precio Minimo", "Precio mínimo"], required=False, default=None)
except KeyError as e:
    st.error(str(e))
    st.stop()

df = df_raw.copy()
for c in [p_actual, p_sug, p_apps, p_apps_f, p_min]:
    if c:
        df[c] = parse_money(df[c])

# Borrar filas sin producto o sin precio actual numérico
df = df[df[prod_col].notna()].copy()
df = df[df[p_actual].notna()].copy()

# =========================
# Food cost por categoría
# =========================
st.markdown("### ⚙️ Parámetros de Costo (Food Cost por categoría)")
defaults = {
    "Desayunos": 0.35,
    "Pizzas Personales": 0.32,
    "Pizzas Familiares": 0.35,
    "Hamburguesas": 0.38,
    "Hot Dogs": 0.32,
    "Sándwiches": 0.33,
    "Otros Salados": 0.33,
    "Pastas": 0.34,
    "Crepas Saladas": 0.32,
    "Crepas Dulces": 0.30,
    "Snacks": 0.30,
    "Bebidas Calientes": 0.25,
    "Bebidas Frías": 0.28,
    "Extras": 0.15
}
unique_cats = sorted(df[cat_col].dropna().unique())
cat_cost_pct: Dict[str, float] = {}
with st.expander("Ajusta los % por categoría (predeterminados sugeridos)", expanded=False):
    for cat in unique_cats:
        base = defaults.get(cat, 0.33)
        cat_cost_pct[cat] = st.slider(f"{cat}", 0.10, 0.60, float(base), 0.01, key=f"fc_{cat}")

# =========================
# Base de precios + costos generales
# =========================
st.markdown("### 💵 Base de precios + Costos adicionales")
base_col_name = st.radio(
    "Elige la base de precios por producto",
    ["Precio Actual", "Nuevo Precio Sugerido", "Precio en Apps", "Precio Apps (Fórmula)", "Precio Mínimo"],
    horizontal=True
)

base_map = {
    "Precio Actual": p_actual,
    "Nuevo Precio Sugerido": p_sug,
    "Precio en Apps": p_apps,
    "Precio Apps (Fórmula)": p_apps_f,
    "Precio Mínimo": p_min
}
base_col = base_map[base_col_name]
if base_col is None:
    st.error(f"No existe la columna para **{base_col_name}** en tu CSV.")
    st.stop()

c1, c2, c3 = st.columns(3)
with c1:
    app_commission = st.slider("Comisión de app (%)", 0, 35, 0, 1)
with c2:
    packaging = st.number_input("Empaque por combo (MXN)", min_value=0.0, value=0.0, step=1.0)
with c3:
    other_var = st.number_input("Otros costos variables (MXN)", min_value=0.0, value=0.0, step=1.0)

# Catálogo compacto para IA (dict ID -> datos)
catalog = {}
for _, r in df.iterrows():
    pid = str(r[id_col])
    catalog[pid] = {
        "id": pid,
        "categoria": str(r[cat_col]),
        "producto": str(r[prod_col]),
        "precio_base": float(r[base_col]) if pd.notna(r[base_col]) else None,
        "precio_min": float(r[p_min]) if (p_min and pd.notna(r[p_min])) else None
    }

# =========================
# 🔮 Generación de combos con IA
# =========================
st.markdown("## 🤖 Generación de combos (IA)")
left_ai, right_ai = st.columns([2,1])
with left_ai:
    n_combos = st.slider("¿Cuántos combos proponer?", 1, 5, 3, 1)
    objetivos = st.multiselect("Objetivo de la tanda (influye a la IA)", 
                               ["Alta rentabilidad", "Atracción (precio bajo)", "Ticket medio", "Familias", "Oficina/pareja"],
                               default=["Alta rentabilidad","Ticket medio"])
with right_ai:
    min_items = st.number_input("Mínimo de ítems por combo", 2, 6, 2, 1)
    max_items = st.number_input("Máximo de ítems por combo", 2, 8, 3, 1)
    ensure_min_price = st.checkbox("Forzar ≥ suma de precios mínimos", value=True)

ai_note = st.caption("La IA usa alta temperatura y un token aleatorio para que cada tanda sea **diferente**.")

def price_floor_for_items(items):
    s = 0.0
    for it in items:
        pid = str(it["id"])
        qty = float(it.get("qty", 1))
        pm = catalog.get(pid, {}).get("precio_min")
        if pm:
            s += pm * qty
    return s

def eval_combo(items, precio_combo) -> Dict[str, float]:
    """Calcula totales, costo estimado y margen con los parámetros actuales."""
    sum_base = 0.0
    sum_cost = 0.0
    for it in items:
        pid = str(it["id"])
        qty = float(it.get("qty", 1))
        info = catalog.get(pid)
        if not info or info.get("precio_base") is None:
            continue
        base = float(info["precio_base"])
        sum_base += base * qty
        cost = costo_estimado_row(base, info["categoria"], cat_cost_pct)
        sum_cost += cost * qty
    commission_cost = precio_combo * (app_commission/100.0)
    total_cost_combo = sum_cost + packaging + other_var + commission_cost
    margen_abs = precio_combo - total_cost_combo
    margen_pct = (margen_abs / precio_combo * 100) if precio_combo > 0 else 0
    desc_vs_base = (1 - precio_combo / sum_base) * 100 if sum_base > 0 else 0
    return {
        "sum_base": sum_base, "sum_cost": sum_cost, "commission_cost": commission_cost,
        "total_cost_combo": total_cost_combo, "margen_abs": margen_abs, "margen_pct": margen_pct,
        "desc_vs_base": desc_vs_base
    }

def heuristic_combos(num=3):
    """Fallback si IA no disponible: genera combos sencillos con heurística."""
    rng = random.Random()
    combos = []
    cat_principales = [c for c in unique_cats if re.search(r"pizza|hamb|pastas?|hot dog", c, re.I)]
    ids = list(catalog.keys())
    for _ in range(num):
        items = []
        # principal
        princ_cats = cat_principales or unique_cats
        pick_cat = rng.choice(princ_cats)
        principal_ids = [i for i in ids if catalog[i]["categoria"] == pick_cat]
        if principal_ids:
            items.append({"id": rng.choice(principal_ids), "qty": 1})
        # bebida
        bebidas = [i for i in ids if re.search(r"bebidas?|coca|agua", catalog[i]["categoria"], re.I)]
        if bebidas:
            items.append({"id": rng.choice(bebidas), "qty": 1})
        # extra (opcional)
        extras = [i for i in ids if re.search(r"extra|snack|papas|nudos", catalog[i]["categoria"], re.I)]
        if extras and rng.random() < 0.6:
            items.append({"id": rng.choice(extras), "qty": 1})
        # precio objetivo por margen 55% y descuento 15–30% vs base
        ev = eval_combo(items, 1.0)  # solo para sumar bases y costos
        if ev["sum_cost"] <= 0 or ev["sum_base"] <= 0:
            continue
        p_margin = ev["sum_cost"] / (1 - 0.55)  # margen objetivo 55%
        p_disc = ev["sum_base"] * (1 - rng.uniform(0.15, 0.30))
        price = max(p_margin, p_disc)
        if ensure_min_price:
            floor_ = price_floor_for_items(items)
            price = max(price, floor_)
        ev = eval_combo(items, price)
        combos.append({
            "name": f"Combo Heurístico {uuid.uuid4().hex[:4]}",
            "items": items,
            "precio_combo": round(price, 2),
            "metrics": ev,
            "copy": "Sabor top + bebida a precio irresistible.",
            "why": "Cobertura de principal + bebida con margen sano y descuento competitivo."
        })
    return combos

if st.button("🎲 Generar combos (IA)"):
    # Contexto para IA: tope 120 ítems para mantener prompt razonable
    sample_catalog = list(catalog.values())[:120]
    token_random = uuid.uuid4().hex  # fuerza diversidad
    prompt = f"""
Eres experto en pricing y creación de combos para QSR en México.
Objetivo: propón **{n_combos} combos** creativos, competitivos y rentables para "El Chal".
Genera SIEMPRE combos distintos entre tandas (diversidad alta). Token aleatorio: {token_random}

Datos:
- catálogo (hasta 120 ítems): {json.dumps(sample_catalog, ensure_ascii=False)}
- comisión_app_pct: {app_commission}
- empaque_mxn: {packaging}
- otros_costos_mxn: {other_var}
- base_precios: "{base_col_name}"
- reglas:
  * Ítems por combo: entre {min_items} y {max_items}.
  * Debe haber al menos 1 **principal** (categorías que contienen: pizza, hamburguesa, hot dog, pasta).
  * **Precio sugerido** ≥ suma de **precios mínimos** si hay (aplícalo).
  * Margen objetivo final (sobre precio) después de costos y comisión: entre **45% y 65%**.
  * Descuento atractivo vs suma de precios base: **10% a 35%**.
  * Evita duplicidades absurdas (2 bebidas iguales salvo versión "familiar").
  * Nombra el combo de forma **atractiva** y breve (≤ 40 caracteres).
  * Incluye un **copy** de marketing (< 140 caracteres).
  * Justifica en 1-2 frases por qué es creativo y competitivo.

Devuelve SOLO JSON con esta forma (sin texto adicional):
{{
  "combos": [
    {{
      "name": "Combo Ejemplo",
      "items": [{{"id": "P001", "qty": 1}}, {{"id": "B001", "qty": 2}}],
      "precio_combo": 249.0,
      "copy": "Pizza + 2 bebidas a súper precio",
      "why": "Cobertura familiar y alto valor percibido"
    }}
  ]
}}
"""
    out = call_gemini(prompt) if GEMINI_AVAILABLE else {"combos": heuristic_combos(n_combos)}
    if isinstance(out, dict) and "combos" in out:
        st.session_state["ai_combos"] = out["combos"]
    elif isinstance(out, list):
        st.session_state["ai_combos"] = out
    else:
        st.error("La IA no devolvió un JSON válido.")
        st.write(out)

# Mostrar combos generados
if "ai_combos" in st.session_state and st.session_state["ai_combos"]:
    st.subheader("Resultados de la IA")
    for i, combo in enumerate(st.session_state["ai_combos"], start=1):
        name = combo.get("name", f"Combo {i}")
        items = combo.get("items", [])
        price = float(combo.get("precio_combo", 0))
        # Ajuste por piso de mínimos
        if ensure_min_price:
            floor_ = price_floor_for_items(items)
            if price < floor_:
                price = floor_
        metrics = eval_combo(items, price)
        colA, colB = st.columns([2,1])
        with colA:
            st.markdown(f"### {i}. {name}")
            rows = []
            for it in items:
                pid = str(it.get("id"))
                qty = float(it.get("qty", 1))
                info = catalog.get(pid, {})
                rows.append({
                    "ID": pid,
                    "Categoría": info.get("categoria", "—"),
                    "Producto": info.get("producto", "—"),
                    "Cant.": qty,
                    "Precio base": info.get("precio_base", np.nan),
                    "Precio mínimo": info.get("precio_min", np.nan),
                })
            tbl = pd.DataFrame(rows)
            st.dataframe(
                tbl.assign(**{
                    "Precio base":   lambda d: d["Precio base"].map(pesos),
                    "Precio mínimo": lambda d: d["Precio mínimo"].map(pesos),
                }),
                use_container_width=True
            )
        with colB:
            k1, k2 = st.columns(2)
            k1.metric("Precio combo", pesos(price))
            k2.metric("Margen", f"{metrics['margen_pct']:.1f}%", pesos(metrics['margen_abs']))
            k3, k4 = st.columns(2)
            k3.metric("Desc. vs base", f"{metrics['desc_vs_base']:.1f}%")
            k4.metric("Costo total", pesos(metrics["total_cost_combo"]))
            st.caption(f"Comisión app: {pesos(metrics['commission_cost'])}")
            if combo.get("copy"):
                st.success(combo["copy"])
            if combo.get("why"):
                st.caption(combo["why"])
            # Botón aplicar combo
            if st.button(f"✅ Usar este combo ({i})", key=f"apply_{i}"):
                # Construye combo_df de trabajo
                work_rows = []
                for it in items:
                    pid = str(it.get("id"))
                    qty = float(it.get("qty", 1))
                    info = catalog.get(pid, {})
                    base = info.get("precio_base", 0.0) or 0.0
                    cost = costo_estimado_row(base, info.get("categoria",""), cat_cost_pct)
                    work_rows.append({
                        "ID": pid,
                        "Categoría": info.get("categoria",""),
                        "Producto": info.get("producto",""),
                        "Cantidad": qty,
                        "Precio base": base,
                        "Costo estimado": cost,
                        "Precio mínimo": info.get("precio_min", 0.0),
                        "Subtotal Precio": qty*base,
                        "Subtotal Costo": qty*cost
                    })
                st.session_state["work_combo_name"] = name
                st.session_state["work_combo_price"] = price
                st.session_state["work_combo_items"] = pd.DataFrame(work_rows)
                st.success("Combo aplicado abajo para edición.")

# =========================
# ✍️ Editor del combo aplicado / Manual
# =========================
st.markdown("---")
st.header("🛠️ Editor del combo (manual / aplicado)")
# Si no hay combo aplicado, empieza vacío con selector
if "work_combo_items" not in st.session_state:
    st.info("Aún no has aplicado un combo de IA. Puedes **generar** uno arriba o construirlo manualmente.")
    # Construcción manual rápida
    with st.expander("Construcción manual rápida"):
        # Filtros
        f1, f2 = st.columns(2)
        with f1:
            cat_sel = st.selectbox("Filtra por categoría", ["(todas)"] + unique_cats)
        with f2:
            search = st.text_input("Busca por texto (Producto contiene)")
        mask = pd.Series(True, index=df.index)
        if cat_sel != "(todas)":
            mask &= df[cat_col] == cat_sel
        if search:
            mask &= df[prod_col].astype(str).str.contains(search, case=False, na=False)
        options = df.loc[mask, id_col].astype(str).tolist()
        add_ids = st.multiselect("Agrega productos por ID", options)
        rows = []
        for pid in add_ids:
            info = catalog[pid]
            base = info["precio_base"] or 0.0
            cost = costo_estimado_row(base, info["categoria"], cat_cost_pct)
            q = st.number_input(f"Cantidad {pid}", 1, 10, 1, 1, key=f"qty_{pid}")
            rows.append({
                "ID": pid, "Categoría": info["categoria"], "Producto": info["producto"],
                "Cantidad": q, "Precio base": base, "Costo estimado": cost,
                "Precio mínimo": info.get("precio_min", 0.0),
                "Subtotal Precio": q*base, "Subtotal Costo": q*cost
            })
        if rows:
            st.session_state["work_combo_items"] = pd.DataFrame(rows)
            st.session_state["work_combo_price"] = float(sum(r["Subtotal Precio"] for r in rows))
            st.session_state["work_combo_name"] = "Combo manual"
        else:
            st.stop()

# Mostrar/editar combo de trabajo
work_df = st.session_state["work_combo_items"]
st.text_input("Nombre del combo", value=st.session_state.get("work_combo_name","Combo"), key="work_combo_name")
st.dataframe(
    work_df.assign(**{
        "Precio base":      lambda d: d["Precio base"].map(pesos),
        "Costo estimado":   lambda d: d["Costo estimado"].map(pesos),
        "Subtotal Precio":  lambda d: d["Subtotal Precio"].map(pesos),
        "Subtotal Costo":   lambda d: d["Subtotal Costo"].map(pesos),
        "Precio mínimo":    lambda d: d["Precio mínimo"].map(pesos),
    }),
    use_container_width=True
)

sum_price = float(work_df["Subtotal Precio"].sum())
sum_cost  = float(work_df["Subtotal Costo"].sum())
sum_min   = float((work_df["Precio mínimo"] * work_df["Cantidad"]).sum()) if "Precio mínimo" in work_df.columns else 0.0

# Definir precio del combo
colp1, colp2 = st.columns(2)
with colp1:
    modo_precio = st.radio("Definir precio del combo", ["Descuento vs base", "Margen objetivo"], horizontal=True)
    if modo_precio == "Descuento vs base":
        desc = st.slider("Descuento (%)", 0, 60, 20, 1)
        combo_price = sum_price * (1 - desc/100.0)
    else:
        target_margin = st.slider("Margen objetivo (%)", 10, 80, 55, 1)
        combo_price = sum_cost / max(1e-6, 1 - target_margin/100.0)
with colp2:
    enforce_min = st.checkbox("Forzar ≥ suma de precios mínimos", value=True)
    if enforce_min and combo_price < sum_min:
        st.warning(f"Ajuste por mínimos: {pesos(sum_min)}")
        combo_price = sum_min

commission_cost = combo_price * (app_commission/100.0)
total_cost_combo = sum_cost + packaging + other_var + commission_cost
margin_abs = combo_price - total_cost_combo
margin_pct = (margin_abs / combo_price * 100) if combo_price > 0 else 0
discount_vs_base = (1 - combo_price / sum_price) * 100 if sum_price > 0 else 0

m1, m2, m3, m4 = st.columns(4)
m1.metric("Suma base", pesos(sum_price))
m2.metric("Precio combo", pesos(combo_price), f"{-discount_vs_base:.1f}% vs base")
m3.metric("Costo total", pesos(total_cost_combo))
m4.metric("Margen", f"{margin_pct:.1f}%", pesos(margin_abs))

# Exportar
st.markdown("---")
export_name = st.session_state.get("work_combo_name","Combo")
payload = {
    "combo": export_name,
    "base_precios": base_col_name,
    "items": work_df.to_dict(orient="records"),
    "suma_precios_base": round(sum_price, 2),
    "suma_costos_estimados": round(sum_cost, 2),
    "suma_precios_minimos": round(sum_min, 2),
    "parametros": {
        "comision_app_pct": app_commission,
        "empaque_mxn": packaging,
        "otros_costos_mxn": other_var,
        "modo_precio": modo_precio,
        "descuento_pct": desc if modo_precio == "Descuento vs base" else None,
        "margen_objetivo_pct": target_margin if modo_precio == "Margen objetivo" else None,
        "enforce_min": enforce_min
    },
    "precio_combo": round(combo_price, 2),
    "costo_total_combo": round(total_cost_combo, 2),
    "margen_abs": round(margin_abs, 2),
    "margen_pct": round(margin_pct, 2)
}
st.download_button(
    "📥 Descargar combo (.json)",
    data=json.dumps(payload, ensure_ascii=False, indent=2),
    file_name=f"combo_{export_name.replace(' ','_')}.json",
    mime="application/json"
)

st.success("Listo. La IA te dará propuestas distintas en cada tanda; puedes aplicarlas, ajustarlas y exportarlas.")
