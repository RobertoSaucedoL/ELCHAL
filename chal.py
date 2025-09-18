# chal.py
# Simulador de Combos Rentables – Café y Pizzas El Chal
# IA (Gemini) afilada + heurística con reglas realistas y sensibilidad "nudos con nutella"
# Precio base por defecto: Precio Apps (Fórmula)

import json, re, uuid, random
from typing import List, Dict, Any

import streamlit as st
import pandas as pd
import numpy as np
import google.generativeai as genai  # <— import requerido por tu snippet

# -------- UI responsive --------
st.set_page_config(layout="wide", page_title="Simulador de Combos – El Chal", page_icon="🍕")
st.markdown("""
<style>
@media (max-width: 640px){
  .block-container {padding-top:.6rem;padding-left:.6rem;padding-right:.6rem;}
  .stButton>button, .stDownloadButton>button {width:100%;}
}
.dataframe tbody tr th {display:none;}
</style>
""", unsafe_allow_html=True)

# -------- Configuración de Gemini AI (TAL CUAL tu snippet) --------
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    GEMINI_AVAILABLE = True
except (FileNotFoundError, KeyError):
    GEMINI_AVAILABLE = False
    st.warning(
        "⚠️ **Advertencia**: La clave de API de Gemini no está configurada en `st.secrets`. "
        "Las funcionalidades de IA no estarán disponibles."
    )

def extract_json_block(text: str):
    if not text: return None
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try: return json.loads(m.group(0))
        except Exception: pass
    m = re.search(r"\[[\s\S]*\]", text)
    if m:
        try: return json.loads(m.group(0))
        except Exception: pass
    return None

def call_gemini(prompt: str):
    if not GEMINI_AVAILABLE:
        return {"error": "IA no disponible"}
    model = genai.GenerativeModel("gemini-1.5-flash")
    cfg = {"temperature": 1.25, "top_p": 0.95, "max_output_tokens": 4096}
    resp = model.generate_content(prompt, generation_config=cfg)
    txt = getattr(resp, "text", "") or ""
    data = extract_json_block(txt)
    return data if data is not None else {"raw": txt}

# -------- Helpers --------
def parse_money(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str).str.replace(r"[^\d\.\-]", "", regex=True)
              .replace({"": np.nan, "nan": np.nan, "-": np.nan}),
        errors="coerce"
    )

def pick_col(df: pd.DataFrame, names: List[str], required=True, default=None) -> str:
    for n in names:
        if n in df.columns: return n
    if required: raise KeyError(f"No encontré ninguna de estas columnas: {names}")
    return default

def pesos(x: float) -> str:
    try: return f"${x:,.2f}"
    except Exception: return str(x)

def costo_estimado_row(price: float, cat: str, cat_cost_pct: Dict[str, float]) -> float:
    return float(price) * float(cat_cost_pct.get(cat, 0.33))

# -------- Menú integrado (extracto suficiente para probar; puedes ampliar) --------
DEFAULT_MENU: List[Dict[str, Any]] = [
    {"ID":"D001","Tipo":"COMIDA","Categoría":"Desayunos","Producto":"Paquete Desayuno (Platillo + café + jugo/fruta)","Precio Actual (MXN)":130,"Nuevo Precio Sugerido (MXN)":165,"PRECIO EN APPS":189,"PRECIO PARA APPS CON FORMULA":169,"PRECIO MINIMO":149},
    {"ID":"D002","Tipo":"COMIDA","Categoría":"Desayunos","Producto":"Huevos al gusto (a la carta)","Precio Actual (MXN)":85,"Nuevo Precio Sugerido (MXN)":115,"PRECIO EN APPS":149,"PRECIO PARA APPS CON FORMULA":149,"PRECIO MINIMO":89},

    {"ID":"P003","Tipo":"COMIDA","Categoría":"Pizzas Personales","Producto":"Pepperoni","Precio Actual (MXN)":150,"Nuevo Precio Sugerido (MXN)":175,"PRECIO EN APPS":229,"PRECIO PARA APPS CON FORMULA":229,"PRECIO MINIMO":149},
    {"ID":"P007","Tipo":"COMIDA","Categoría":"Pizzas Personales","Producto":"Margarita","Precio Actual (MXN)":150,"Nuevo Precio Sugerido (MXN)":199,"PRECIO EN APPS":269,"PRECIO PARA APPS CON FORMULA":269,"PRECIO MINIMO":159},
    {"ID":"P033","Tipo":"COMIDA","Categoría":"Pizzas Personales","Producto":"Meat Lover","Precio Actual (MXN)":190,"Nuevo Precio Sugerido (MXN)":239,"PRECIO EN APPS":315,"PRECIO PARA APPS CON FORMULA":315,"PRECIO MINIMO":199},

    {"ID":"P004","Tipo":"COMIDA","Categoría":"Pizzas Familiares","Producto":"Pepperoni Familiar","Precio Actual (MXN)":270,"Nuevo Precio Sugerido (MXN)":319,"PRECIO EN APPS":389,"PRECIO PARA APPS CON FORMULA":389,"PRECIO MINIMO":289},
    {"ID":"P034","Tipo":"COMIDA","Categoría":"Pizzas Familiares","Producto":"Meat Lover Familiar","Precio Actual (MXN)":350,"Nuevo Precio Sugerido (MXN)":419,"PRECIO EN APPS":545,"PRECIO PARA APPS CON FORMULA":545,"PRECIO MINIMO":419},

    {"ID":"H001","Tipo":"COMIDA","Categoría":"Hamburguesas","Producto":"Clásica","Precio Actual (MXN)":70,"Nuevo Precio Sugerido (MXN)":109,"PRECIO EN APPS":139,"PRECIO PARA APPS CON FORMULA":139,"PRECIO MINIMO":109},
    {"ID":"HD02","Tipo":"COMIDA","Categoría":"Hot Dogs","Producto":"Con Tocino","Precio Actual (MXN)":55,"Nuevo Precio Sugerido (MXN)":65,"PRECIO EN APPS":89,"PRECIO PARA APPS CON FORMULA":89,"PRECIO MINIMO":65},

    {"ID":"S009","Tipo":"COMIDA","Categoría":"Sándwiches","Producto":"Sándwich 3 quesos (a la carta)","Precio Actual (MXN)":100,"Nuevo Precio Sugerido (MXN)":119,"PRECIO EN APPS":155,"PRECIO PARA APPS CON FORMULA":155,"PRECIO MINIMO":119},

    {"ID":"PA01","Tipo":"COMIDA","Categoría":"Pastas","Producto":"Pasta (cualquier especialidad)","Precio Actual (MXN)":145,"Nuevo Precio Sugerido (MXN)":175,"PRECIO EN APPS":225,"PRECIO PARA APPS CON FORMULA":225,"PRECIO MINIMO":169},

    {"ID":"C002","Tipo":"POSTRE","Categoría":"Crepas Dulces","Producto":"Crepa Nutella / Cajeta / Philadelphia","Precio Actual (MXN)":85,"Nuevo Precio Sugerido (MXN)":95,"PRECIO EN APPS":125,"PRECIO PARA APPS CON FORMULA":125,"PRECIO MINIMO":95},
    {"ID":"C004","Tipo":"POSTRE","Categoría":"Crepas Dulces","Producto":"Crepa Nutella con fruta / Cajeta con nuez","Precio Actual (MXN)":96,"Nuevo Precio Sugerido (MXN)":109,"PRECIO EN APPS":145,"PRECIO PARA APPS CON FORMULA":145,"PRECIO MINIMO":109},

    {"ID":"SN01","Tipo":"COMIDA","Categoría":"Snacks","Producto":"Orden de papas gajo o a la francesa","Precio Actual (MXN)":45,"Nuevo Precio Sugerido (MXN)":59,"PRECIO EN APPS":75,"PRECIO PARA APPS CON FORMULA":75,"PRECIO MINIMO":59},
    {"ID":"SN06","Tipo":"COMIDA","Categoría":"Snacks","Producto":"Nudos (6 pzas)","Precio Actual (MXN)":45,"Nuevo Precio Sugerido (MXN)":55,"PRECIO EN APPS":65,"PRECIO PARA APPS CON FORMULA":65,"PRECIO MINIMO":55},

    {"ID":"B005","Tipo":"BEBIDA","Categoría":"Bebidas Frías","Producto":"Frapé / Smoothie / Malteada","Precio Actual (MXN)":75,"Nuevo Precio Sugerido (MXN)":85,"PRECIO EN APPS":109,"PRECIO PARA APPS CON FORMULA":109,"PRECIO MINIMO":85},
    {"ID":"B009","Tipo":"BEBIDA","Categoría":"Bebidas Frías","Producto":"Soda Italiana / Limonada","Precio Actual (MXN)":57,"Nuevo Precio Sugerido (MXN)":65,"PRECIO EN APPS":89,"PRECIO PARA APPS CON FORMULA":89,"PRECIO MINIMO":65},
    {"ID":"B007","Tipo":"BEBIDA","Categoría":"Bebidas Frías","Producto":"Coca Cola / Agua Mineral","Precio Actual (MXN)":35,"Nuevo Precio Sugerido (MXN)":45,"PRECIO EN APPS":49,"PRECIO PARA APPS CON FORMULA":49,"PRECIO MINIMO":45},

    {"ID":"B004","Tipo":"BEBIDA","Categoría":"Bebidas Calientes","Producto":"Capuchino","Precio Actual (MXN)":49,"Nuevo Precio Sugerido (MXN)":65,"PRECIO EN APPS":75,"PRECIO PARA APPS CON FORMULA":75,"PRECIO MINIMO":55},
    {"ID":"B001","Tipo":"BEBIDA","Categoría":"Bebidas Calientes","Producto":"Café Americano","Precio Actual (MXN)":33,"Nuevo Precio Sugerido (MXN)":45,"PRECIO EN APPS":49,"PRECIO PARA APPS CON FORMULA":49,"PRECIO MINIMO":39},
]

df = pd.DataFrame(DEFAULT_MENU)
for c in ["Precio Actual (MXN)","Nuevo Precio Sugerido (MXN)","PRECIO EN APPS","PRECIO PARA APPS CON FORMULA","PRECIO MINIMO"]:
    if c in df.columns: df[c] = parse_money(df[c])

# -------- Column mapping --------
id_col   = pick_col(df, ["ID"])
cat_col  = pick_col(df, ["Categoría","Categoria"])
prod_col = pick_col(df, ["Producto"])
p_actual = pick_col(df, ["Precio Actual (MXN)","Precio Actual"])
p_sug    = pick_col(df, ["Nuevo Precio Sugerido (MXN)","Nuevo Precio Sugerido"], required=False, default=None)
p_apps   = pick_col(df, ["PRECIO EN APPS","Precio en Apps"], required=False, default=None)
p_apps_f = pick_col(df, [
    "PRECIO PARA APPS CON FORMULA","Precio para Apps con formula",
    "Precio APPS (Formulas)","Precio APPS (Fórmulas)","Precio Apps (Fórmula)"
], required=False, default=None)
p_min    = pick_col(df, ["PRECIO MINIMO","Precio Minimo","Precio mínimo"], required=False, default=None)

st.title("🍕 Simulador de Combos – *El Chal*")
st.caption("IA creativa y reglas realistas. Precio base por defecto: **Precio Apps (Fórmula)**.")

# -------- Food cost por categoría --------
defaults_fc = {
    "Desayunos":0.35,"Pizzas Personales":0.32,"Pizzas Familiares":0.35,"Hamburguesas":0.38,"Hot Dogs":0.32,
    "Sándwiches":0.33,"Otros Salados":0.33,"Pastas":0.34,"Crepas Saladas":0.32,"Crepas Dulces":0.30,
    "Snacks":0.30,"Bebidas Calientes":0.25,"Bebidas Frías":0.28,"Extras":0.15
}
unique_cats = sorted(df[cat_col].dropna().unique())
cat_cost_pct: Dict[str, float] = {}
with st.expander("⚙️ Ajusta food cost por categoría", expanded=False):
    for c in unique_cats:
        cat_cost_pct[c] = st.slider(c, 0.10, 0.60, float(defaults_fc.get(c,0.33)), 0.01, key=f"fc_{c}")

# -------- Base de precios preferida (por defecto Apps Fórmula) --------
st.markdown("### 💵 Base de precios + costos adicionales")
options_base = ["Precio Apps (Fórmula)","Precio en Apps","Nuevo Precio Sugerido","Precio Actual","Precio Mínimo"]
base_map = {"Precio Apps (Fórmula)": p_apps_f,"Precio en Apps": p_apps,"Nuevo Precio Sugerido": p_sug,"Precio Actual": p_actual,"Precio Mínimo": p_min}
default_choice = "Precio Apps (Fórmula)" if p_apps_f is not None else ("Precio en Apps" if p_apps is not None else "Precio Actual")
idx = options_base.index(default_choice)
base_col_name = st.radio("Usar como precio base por producto", options_base, index=idx, horizontal=True)
base_col = base_map[base_col_name]
if base_col is None:
    st.error(f"No existe la columna para **{base_col_name}** en tu menú."); st.stop()

c1,c2,c3 = st.columns(3)
with c1: app_commission = st.slider("Comisión de app (%)", 0, 35, 0, 1)
with c2: packaging = st.number_input("Empaque por combo (MXN)", 0.0, step=1.0, value=0.0)
with c3: other_var = st.number_input("Otros costos variables (MXN)", 0.0, step=1.0, value=0.0)

# -------- Catálogo --------
catalog: Dict[str, Dict[str, Any]] = {}
for _, r in df.iterrows():
    pid = str(r[id_col])
    catalog[pid] = {
        "id": pid,
        "categoria": str(r[cat_col]),
        "producto": str(r[prod_col]),
        "precio_base": float(r[base_col]) if pd.notna(r[base_col]) else None,
        "precio_min": float(r[p_min]) if (p_min and pd.notna(r[p_min])) else None
    }

# -------- Reglas de pairing --------
def is_principal(cat: str) -> bool:
    return bool(re.search(r"pizza|hamburguesa|hot dog|pastas?", cat, re.I))
def is_breakfast(cat: str) -> bool:
    return bool(re.search(r"desayuno", cat, re.I))
def is_cold_drink(cat: str) -> bool:
    return "Bebidas Frías" in cat or bool(re.search(r"frías|soda|coca|agua", cat, re.I))
def is_hot_drink(cat: str) -> bool:
    return "Bebidas Calientes" in cat

def price_floor_for_items(items):
    s = 0.0
    for it in items:
        pid = str(it["id"]); qty = float(it.get("qty",1))
        pm = catalog.get(pid, {}).get("precio_min")
        if pm: s += pm*qty
    return s

def eval_combo(items, precio_combo) -> Dict[str, float]:
    sum_base=sum_cost=0.0
    for it in items:
        pid=str(it["id"]); qty=float(it.get("qty",1))
        info=catalog.get(pid); 
        if not info or info.get("precio_base") is None: continue
        base=float(info["precio_base"]); sum_base += base*qty
        sum_cost += costo_estimado_row(base, info["categoria"], cat_cost_pct)*qty
    commission_cost = precio_combo*(app_commission/100.0)
    total_cost_combo = sum_cost + packaging + other_var + commission_cost
    margen_abs = precio_combo - total_cost_combo
    margen_pct = (margen_abs/precio_combo*100) if precio_combo>0 else 0
    desc_vs_base = (1 - precio_combo/sum_base)*100 if sum_base>0 else 0
    return {"sum_base":sum_base,"sum_cost":sum_cost,"commission_cost":commission_cost,
            "total_cost_combo":total_cost_combo,"margen_abs":margen_abs,"margen_pct":margen_pct,
            "desc_vs_base":desc_vs_base}

# -------- Heurística realista (fallback) --------
def heuristic_combos(num=3, min_items=2, max_items=3, ensure_min=True):
    rng=random.Random()
    ids=list(catalog.keys())
    principals=[i for i in ids if is_principal(catalog[i]["categoria"]) or is_breakfast(catalog[i]["categoria"])]
    cold=[i for i in ids if is_cold_drink(catalog[i]["categoria"])]
    hot =[i for i in ids if is_hot_drink(catalog[i]["categoria"])]
    snacks=[i for i in ids if re.search(r"snacks?", catalog[i]["categoria"], re.I)]
    desserts=[i for i in ids if re.search(r"Crepas Dulces|POSTRE", catalog[i]["categoria"], re.I)]

    combos=[]
    for _ in range(num):
        items=[]
        n_it=rng.randint(min_items, max_items)

        # principal
        if principals:
            p_id=rng.choice(principals); items.append({"id":p_id,"qty":1}); n_it-=1
            p_cat=catalog[p_id]["categoria"]
        else:
            p_id=rng.choice(ids); items.append({"id":p_id,"qty":1}); n_it-=1
            p_cat=catalog[p_id]["categoria"]

        # bebida acorde
        if is_principal(p_cat) and cold:
            items.append({"id": rng.choice(cold), "qty": 1}); n_it-=1
        elif is_breakfast(p_cat) and hot:
            items.append({"id": rng.choice(hot), "qty": 1}); n_it-=1

        # antojos (favorecer nudos + nutella)
        if n_it>0:
            if rng.random()<0.6 and "SN06" in catalog and ( "C002" in catalog or "C004" in catalog ):
                items.append({"id":"SN06","qty":1}); n_it-=1
                if n_it>0: items.append({"id": "C002" if "C002" in catalog else "C004", "qty":1}); n_it-=1
            while n_it>0:
                pool = snacks + desserts + cold
                if not pool: break
                items.append({"id": rng.choice(pool), "qty": 1}); n_it-=1

        # precio con margen/desc realistas
        ev=eval_combo(items, 1.0)
        if ev["sum_cost"]<=0 or ev["sum_base"]<=0: continue
        p_margin = ev["sum_cost"]/ (1 - rng.uniform(0.50,0.60))
        p_disc   = ev["sum_base"]*(1 - rng.uniform(0.15,0.30))
        price = max(p_margin, p_disc)
        if ensure_min: price = max(price, price_floor_for_items(items))
        ev2=eval_combo(items, price)
        combos.append({
            "name": f"Combo Heurístico {uuid.uuid4().hex[:4]}",
            "items": items,
            "precio_combo": round(price,2),
            "metrics": ev2,
            "copy":"Principal + bebida fría y antojo con gran valor.",
            "why":"Evita bebidas calientes con pizza/hamb/hotdog/pasta y suma snack/postre popular."
        })
    return combos

# -------- Generación con IA --------
st.markdown("## 🤖 Generación de combos (IA)")
cA,cB = st.columns([2,1])
with cA:
    n_combos = st.slider("¿Cuántos combos proponer?", 1, 5, 3, 1)
    objetivos = st.multiselect("Objetivo de la tanda",
        ["Alta rentabilidad","Atracción (precio bajo)","Ticket medio","Familias","Oficina/pareja"],
        default=["Alta rentabilidad","Ticket medio"])
with cB:
    min_items = st.number_input("Mínimo ítems", 2, 6, 2, 1)
    max_items = st.number_input("Máximo ítems", 2, 8, 3, 1)
    ensure_min_price = st.checkbox("Forzar ≥ suma de precios mínimos", value=True)

st.caption("Reglas: pizza/hamb/hot dog/pasta → bebidas **frías**; desayunos → **calientes**; considera **nudos + nutella**.")

if st.button("🎲 Generar combos (IA)", type="primary", use_container_width=True):
    sample_catalog = list(catalog.values())[:160]
    token = uuid.uuid4().hex
    prompt = f"""
Eres experto en pricing QSR en México. Genera **{n_combos} combos** creativos y rentables para "El Chal".
REGLAS:
- Si el principal es pizza/hamburguesa/hot dog/pasta: **NO** bebidas calientes; usa **Bebidas Frías** (Coca/Agua/Soda).
- Si el principal es **Desayunos**: sí usa **Bebidas Calientes** (Americano/Capuchino).
- Favorece combos con snack/postre. Considera explícitamente **"Nudos (SN06) + Crepa Nutella (C002 o C004)"**.
- Ítems por combo: entre {min_items} y {max_items}, al menos 1 principal.
- Precio ≥ suma de mínimos si existe.
- Margen objetivo 45–65% tras food cost + comisión {app_commission}% + empaque {packaging} + otros {other_var}.
- Descuento vs base: 10–35%.
Devuelve SOLO JSON:
{{"combos":[{{"name":"...","items":[{{"id":"P003","qty":1}},{{"id":"B007","qty":1}},{{"id":"SN06","qty":1}}],"precio_combo":289.0,"copy":"...","why":"..."}}]}}
Catálogo: {json.dumps(sample_catalog, ensure_ascii=False)}
Token diversidad: {token}
"""
    out = call_gemini(prompt) if GEMINI_AVAILABLE else {"combos": heuristic_combos(n_combos, min_items, max_items, ensure_min_price)}
    if isinstance(out, dict) and "combos" in out:
        st.session_state["ai_combos"] = out["combos"]
    else:
        st.error("La IA no devolvió JSON válido."); st.write(out)

# -------- Mostrar resultados IA --------
if st.session_state.get("ai_combos"):
    st.subheader("Propuestas")
    for i, combo in enumerate(st.session_state["ai_combos"], start=1):
        name = combo.get("name", f"Combo {i}")
        items = combo.get("items", [])
        price = float(combo.get("precio_combo", 0.0))
        if ensure_min_price: price = max(price, price_floor_for_items(items))
        metrics = eval_combo(items, price)

        colA,colB = st.columns([2,1])
        with colA:
            st.markdown(f"### {i}. {name}")
            rows=[]
            for it in items:
                pid=str(it.get("id")); qty=float(it.get("qty",1)); info=catalog.get(pid,{})
                rows.append({"ID":pid,"Categoría":info.get("categoria","—"),"Producto":info.get("producto","—"),
                             "Cant.":qty,"Precio base":info.get("precio_base",np.nan),"Precio mínimo":info.get("precio_min",np.nan)})
            tbl=pd.DataFrame(rows)
            st.dataframe(tbl.assign(**{
                "Precio base":lambda d:d["Precio base"].map(pesos),
                "Precio mínimo":lambda d:d["Precio mínimo"].map(pesos),
            }), use_container_width=True)
        with colB:
            k1,k2=st.columns(2)
            k1.metric("Precio combo", pesos(price))
            k2.metric("Margen", f"{metrics['margen_pct']:.1f}%", pesos(metrics['margen_abs']))
            k3,k4=st.columns(2)
            k3.metric("Desc. vs base", f"{metrics['desc_vs_base']:.1f}%")
            k4.metric("Costo total", pesos(metrics["total_cost_combo"]))
            st.caption(f"Comisión app: {pesos(metrics['commission_cost'])}")
            if combo.get("copy"): st.success(combo["copy"])
            if combo.get("why"): st.caption(combo["why"])
            if st.button(f"✅ Usar este combo ({i})", key=f"apply_{i}", use_container_width=True):
                work_rows=[]
                for it in items:
                    pid=str(it.get("id")); qty=float(it.get("qty",1)); info=catalog.get(pid,{})
                    base=info.get("precio_base",0.0) or 0.0
                    cost=costo_estimado_row(base, info.get("categoria",""), cat_cost_pct)
                    work_rows.append({"ID":pid,"Categoría":info.get("categoria",""),"Producto":info.get("producto",""),
                                      "Cantidad":qty,"Precio base":base,"Costo estimado":cost,
                                      "Precio mínimo":info.get("precio_min",0.0),
                                      "Subtotal Precio":qty*base,"Subtotal Costo":qty*cost})
                st.session_state["work_combo_name"]=name
                st.session_state["work_combo_price"]=price
                st.session_state["work_combo_items"]=pd.DataFrame(work_rows)
                st.success("Combo aplicado abajo para edición.")

# -------- Editor / Manual --------
st.markdown("---")
st.header("🛠️ Editor del combo")
if "work_combo_items" not in st.session_state:
    st.info("Aplica un combo de IA o construye uno manualmente.")
    with st.expander("Construcción manual rápida"):
        f1,f2 = st.columns(2)
        with f1: cat_sel = st.selectbox("Filtra por categoría", ["(todas)"] + unique_cats)
        with f2: search = st.text_input("Busca por texto (Producto contiene)")
        mask = pd.Series(True, index=df.index)
        if cat_sel != "(todas)": mask &= df[cat_col] == cat_sel
        if search: mask &= df[prod_col].astype(str).str.contains(search, case=False, na=False)
        options = df.loc[mask, id_col].astype(str).tolist()
        add_ids = st.multiselect("Agrega productos por ID", options)
        rows=[]
        for pid in add_ids:
            info=catalog[pid]; base=info["precio_base"] or 0.0
            cost=costo_estimado_row(base, info["categoria"], cat_cost_pct)
            q=st.number_input(f"Cantidad {pid}", 1, 10, 1, 1, key=f"qty_{pid}")
            rows.append({"ID":pid,"Categoría":info["categoria"],"Producto":info["producto"],
                         "Cantidad":q,"Precio base":base,"Costo estimado":cost,
                         "Precio mínimo":info.get("precio_min",0.0),
                         "Subtotal Precio":q*base,"Subtotal Costo":q*cost})
        if rows:
            st.session_state["work_combo_items"]=pd.DataFrame(rows)
            st.session_state["work_combo_name"]="Combo manual"
        else:
            st.stop()

work_df = st.session_state["work_combo_items"]
st.text_input("Nombre del combo", value=st.session_state.get("work_combo_name","Combo"), key="work_combo_name")

st.dataframe(
    work_df.assign(**{
        "Precio base":lambda d:d["Precio base"].map(pesos),
        "Costo estimado":lambda d:d["Costo estimado"].map(pesos),
        "Subtotal Precio":lambda d:d["Subtotal Precio"].map(pesos),
        "Subtotal Costo":lambda d:d["Subtotal Costo"].map(pesos),
        "Precio mínimo":lambda d:d["Precio mínimo"].map(pesos),
    }),
    use_container_width=True
)

sum_price=float(work_df["Subtotal Precio"].sum())
sum_cost=float(work_df["Subtotal Costo"].sum())
sum_min=float((work_df["Precio mínimo"]*work_df["Cantidad"]).sum()) if "Precio mínimo" in work_df.columns else 0.0

colp1,colp2 = st.columns(2)
with colp1:
    modo = st.radio("Definir precio", ["Descuento vs base","Margen objetivo"], horizontal=True)
    if modo=="Descuento vs base":
        desc = st.slider("Descuento (%)", 0, 60, 20, 1)
        combo_price = sum_price*(1 - desc/100)
    else:
        target = st.slider("Margen objetivo (%)", 10, 80, 55, 1)
        combo_price = sum_cost / max(1e-6, 1 - target/100)
with colp2:
    enforce_min = st.checkbox("Forzar ≥ suma de mínimos", value=True)
    if enforce_min and combo_price < sum_min:
        st.warning(f"Ajuste por mínimos: {pesos(sum_min)}")
        combo_price = sum_min

commission_cost = combo_price*(app_commission/100.0)
total_cost_combo = sum_cost + packaging + other_var + commission_cost
margin_abs = combo_price - total_cost_combo
margin_pct = (margin_abs/combo_price*100) if combo_price>0 else 0
discount_vs_base = (1 - combo_price/sum_price)*100 if sum_price>0 else 0

m1,m2,m3,m4 = st.columns(4)
m1.metric("Suma base", pesos(sum_price))
m2.metric("Precio combo", pesos(combo_price), f"{-discount_vs_base:.1f}% vs base")
m3.metric("Costo total", pesos(total_cost_combo))
m4.metric("Margen", f"{margin_pct:.1f}%", pesos(margin_abs))

# -------- Export --------
st.markdown("---")
export_name = st.session_state.get("work_combo_name","Combo")
payload = {
    "combo": export_name,
    "base_precios": base_col_name,
    "items": work_df.to_dict(orient="records"),
    "suma_precios_base": round(sum_price,2),
    "suma_costos_estimados": round(sum_cost,2),
    "suma_precios_minimos": round(sum_min,2),
    "parametros": {
        "comision_app_pct": app_commission,
        "empaque_mxn": packaging,
        "otros_costos_mxn": other_var,
        "modo_precio": modo,
        "descuento_pct": (desc if modo=="Descuento vs base" else None),
        "margen_objetivo_pct": (target if modo=="Margen objetivo" else None),
        "enforce_min": enforce_min
    },
    "precio_combo": round(combo_price,2),
    "costo_total_combo": round(total_cost_combo,2),
    "margen_abs": round(margin_abs,2),
    "margen_pct": round(margen_pct,2)
}
st.download_button("📥 Descargar combo (.json)",
    data=json.dumps(payload, ensure_ascii=False, indent=2),
    file_name=f"combo_{export_name.replace(' ','_')}.json",
    mime="application/json"
)


