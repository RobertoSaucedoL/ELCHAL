# chal.py
# Simulador de Combos Rentables – Café y Pizzas El Chal
# - Menú integrado (no pide CSV). Panel opcional para actualizarlo.
# - IA (Gemini) para generar combos creativos y rentables (alta diversidad).
# - Editor manual, métricas, sensibilidades y exportación.

import streamlit as st
import pandas as pd
import numpy as np
import json, re, random, uuid
from typing import List, Dict, Any

# --------- UI responsive / mobile tweaks ----------
st.set_page_config(layout="wide", page_title="Simulador de Combos – El Chal", page_icon="🍕")
st.markdown("""
<style>
/* Mobile friendly paddings + full width buttons */
@media (max-width: 640px){
  .block-container {padding-top: .6rem; padding-left: .6rem; padding-right: .6rem;}
  button[kind="primary"], .stButton>button, .stDownloadButton>button {width: 100%;}
}
.dataframe tbody tr th {display:none;}  /* oculta índice de tablas */
</style>
""", unsafe_allow_html=True)

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
    if not text:
        return None
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try: return json.loads(m.group(0))
        except Exception: pass
    m = re.search(r"\[[\s\S]*\]", text)
    if m:
        try: return json.loads(m.group(0))
        except Exception: pass
    return None

def call_gemini(prompt: str) -> Any:
    if not GEMINI_AVAILABLE:
        return "IA no disponible."
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        cfg = {"temperature": 1.3, "top_p": 0.95, "max_output_tokens": 4096}
        resp = model.generate_content(prompt, generation_config=cfg)
        txt = getattr(resp, "text", "") or ""
        data = extract_json_block(txt)
        return data if data is not None else txt
    except Exception as e:
        return {"error": f"{e}"}

# =========================
# Helpers
# =========================
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

# =========================
# Menú integrado (puedes editarlo aquí)
# =========================
DEFAULT_MENU: List[Dict[str, Any]] = [
    # --- DESAYUNOS ---
    {"ID":"D001","Tipo":"COMIDA","Categoría":"Desayunos","Producto":"Paquete Desayuno (Platillo + café + jugo/fruta)","Precio Actual (MXN)":130,"Nuevo Precio Sugerido (MXN)":165,"PRECIO EN APPS":189,"PRECIO PARA APPS CON FORMULA":169,"PRECIO MINIMO":149},
    {"ID":"D002","Tipo":"COMIDA","Categoría":"Desayunos","Producto":"Huevos al gusto (a la carta)","Precio Actual (MXN)":85,"Nuevo Precio Sugerido (MXN)":115,"PRECIO EN APPS":149,"PRECIO PARA APPS CON FORMULA":149,"PRECIO MINIMO":89},
    {"ID":"D003","Tipo":"COMIDA","Categoría":"Desayunos","Producto":"Omelette (a la carta)","Precio Actual (MXN)":90,"Nuevo Precio Sugerido (MXN)":119,"PRECIO EN APPS":149,"PRECIO PARA APPS CON FORMULA":149,"PRECIO MINIMO":89},
    {"ID":"D004","Tipo":"COMIDA","Categoría":"Desayunos","Producto":"Molletes clásicos (a la carta)","Precio Actual (MXN)":85,"Nuevo Precio Sugerido (MXN)":109,"PRECIO EN APPS":135,"PRECIO PARA APPS CON FORMULA":135,"PRECIO MINIMO":89},
    {"ID":"D005","Tipo":"COMIDA","Categoría":"Desayunos","Producto":"Chilaquiles con pollo o huevo (a la carta)","Precio Actual (MXN)":95,"Nuevo Precio Sugerido (MXN)":125,"PRECIO EN APPS":149,"PRECIO PARA APPS CON FORMULA":149,"PRECIO MINIMO":95},
    {"ID":"D012","Tipo":"COMIDA","Categoría":"Desayunos","Producto":"Wafles con maple o mermelada (a la carta)","Precio Actual (MXN)":75,"Nuevo Precio Sugerido (MXN)":89,"PRECIO EN APPS":115,"PRECIO PARA APPS CON FORMULA":115,"PRECIO MINIMO":89},

    # --- PIZZAS PERSONALES ---
    {"ID":"P001","Tipo":"COMIDA","Categoría":"Pizzas Personales","Producto":"Queso","Precio Actual (MXN)":130,"Nuevo Precio Sugerido (MXN)":159,"PRECIO EN APPS":199,"PRECIO PARA APPS CON FORMULA":199,"PRECIO MINIMO":139},
    {"ID":"P003","Tipo":"COMIDA","Categoría":"Pizzas Personales","Producto":"Pepperoni","Precio Actual (MXN)":150,"Nuevo Precio Sugerido (MXN)":175,"PRECIO EN APPS":229,"PRECIO PARA APPS CON FORMULA":229,"PRECIO MINIMO":149},
    {"ID":"P005","Tipo":"COMIDA","Categoría":"Pizzas Personales","Producto":"Hawaiana","Precio Actual (MXN)":150,"Nuevo Precio Sugerido (MXN)":189,"PRECIO EN APPS":245,"PRECIO PARA APPS CON FORMULA":245,"PRECIO MINIMO":169},
    {"ID":"P007","Tipo":"COMIDA","Categoría":"Pizzas Personales","Producto":"Margarita","Precio Actual (MXN)":150,"Nuevo Precio Sugerido (MXN)":199,"PRECIO EN APPS":269,"PRECIO PARA APPS CON FORMULA":269,"PRECIO MINIMO":159},
    {"ID":"P009","Tipo":"COMIDA","Categoría":"Pizzas Personales","Producto":"Veggie Lover","Precio Actual (MXN)":150,"Nuevo Precio Sugerido (MXN)":199,"PRECIO EN APPS":269,"PRECIO PARA APPS CON FORMULA":269,"PRECIO MINIMO":159},
    {"ID":"P011","Tipo":"COMIDA","Categoría":"Pizzas Personales","Producto":"Mexicana","Precio Actual (MXN)":160,"Nuevo Precio Sugerido (MXN)":199,"PRECIO EN APPS":269,"PRECIO PARA APPS CON FORMULA":269,"PRECIO MINIMO":159},
    {"ID":"P013","Tipo":"COMIDA","Categoría":"Pizzas Personales","Producto":"Búfalo Chicken","Precio Actual (MXN)":160,"Nuevo Precio Sugerido (MXN)":199,"PRECIO EN APPS":229,"PRECIO PARA APPS CON FORMULA":229,"PRECIO MINIMO":159},
    {"ID":"P015","Tipo":"COMIDA","Categoría":"Pizzas Personales","Producto":"BBQ Chicken","Precio Actual (MXN)":160,"Nuevo Precio Sugerido (MXN)":199,"PRECIO EN APPS":269,"PRECIO PARA APPS CON FORMULA":269,"PRECIO MINIMO":159},
    {"ID":"P017","Tipo":"COMIDA","Categoría":"Pizzas Personales","Producto":"Dulce Nutella","Precio Actual (MXN)":160,"Nuevo Precio Sugerido (MXN)":185,"PRECIO EN APPS":229,"PRECIO PARA APPS CON FORMULA":229,"PRECIO MINIMO":159},
    {"ID":"P019","Tipo":"COMIDA","Categoría":"Pizzas Personales","Producto":"Ricota","Precio Actual (MXN)":180,"Nuevo Precio Sugerido (MXN)":229,"PRECIO EN APPS":289,"PRECIO PARA APPS CON FORMULA":289,"PRECIO MINIMO":199},
    {"ID":"P021","Tipo":"COMIDA","Categoría":"Pizzas Personales","Producto":"BLT","Precio Actual (MXN)":180,"Nuevo Precio Sugerido (MXN)":229,"PRECIO EN APPS":289,"PRECIO PARA APPS CON FORMULA":289,"PRECIO MINIMO":199},
    {"ID":"P023","Tipo":"COMIDA","Categoría":"Pizzas Personales","Producto":"Chicken Ranch","Precio Actual (MXN)":180,"Nuevo Precio Sugerido (MXN)":229,"PRECIO EN APPS":289,"PRECIO PARA APPS CON FORMULA":289,"PRECIO MINIMO":199},
    {"ID":"P025","Tipo":"COMIDA","Categoría":"Pizzas Personales","Producto":"Pesto","Precio Actual (MXN)":180,"Nuevo Precio Sugerido (MXN)":229,"PRECIO EN APPS":289,"PRECIO PARA APPS CON FORMULA":289,"PRECIO MINIMO":199},
    {"ID":"P027","Tipo":"COMIDA","Categoría":"Pizzas Personales","Producto":"Steak & Cheese","Precio Actual (MXN)":180,"Nuevo Precio Sugerido (MXN)":229,"PRECIO EN APPS":289,"PRECIO PARA APPS CON FORMULA":289,"PRECIO MINIMO":199},
    {"ID":"P029","Tipo":"COMIDA","Categoría":"Pizzas Personales","Producto":"Southwest Steak","Precio Actual (MXN)":180,"Nuevo Precio Sugerido (MXN)":229,"PRECIO EN APPS":289,"PRECIO PARA APPS CON FORMULA":289,"PRECIO MINIMO":199},
    {"ID":"P031","Tipo":"COMIDA","Categoría":"Pizzas Personales","Producto":"Santa Fe Chicken","Precio Actual (MXN)":180,"Nuevo Precio Sugerido (MXN)":229,"PRECIO EN APPS":289,"PRECIO PARA APPS CON FORMULA":289,"PRECIO MINIMO":199},
    {"ID":"P033","Tipo":"COMIDA","Categoría":"Pizzas Personales","Producto":"Meat Lover","Precio Actual (MXN)":190,"Nuevo Precio Sugerido (MXN)":239,"PRECIO EN APPS":315,"PRECIO PARA APPS CON FORMULA":315,"PRECIO MINIMO":199},
    {"ID":"P035","Tipo":"COMIDA","Categoría":"Pizzas Personales","Producto":"Mediterranea","Precio Actual (MXN)":190,"Nuevo Precio Sugerido (MXN)":239,"PRECIO EN APPS":315,"PRECIO PARA APPS CON FORMULA":315,"PRECIO MINIMO":199},
    {"ID":"P037","Tipo":"COMIDA","Categoría":"Pizzas Personales","Producto":"Works","Precio Actual (MXN)":190,"Nuevo Precio Sugerido (MXN)":239,"PRECIO EN APPS":315,"PRECIO PARA APPS CON FORMULA":315,"PRECIO MINIMO":199},

    # --- PIZZAS FAMILIARES ---
    {"ID":"P002","Tipo":"COMIDA","Categoría":"Pizzas Familiares","Producto":"Queso Familiar","Precio Actual (MXN)":230,"Nuevo Precio Sugerido (MXN)":265,"PRECIO EN APPS":329,"PRECIO PARA APPS CON FORMULA":329,"PRECIO MINIMO":239},
    {"ID":"P004","Tipo":"COMIDA","Categoría":"Pizzas Familiares","Producto":"Pepperoni Familiar","Precio Actual (MXN)":270,"Nuevo Precio Sugerido (MXN)":319,"PRECIO EN APPS":389,"PRECIO PARA APPS CON FORMULA":389,"PRECIO MINIMO":289},
    {"ID":"P006","Tipo":"COMIDA","Categoría":"Pizzas Familiares","Producto":"Hawaiana Familiar","Precio Actual (MXN)":270,"Nuevo Precio Sugerido (MXN)":319,"PRECIO EN APPS":389,"PRECIO PARA APPS CON FORMULA":389,"PRECIO MINIMO":289},
    {"ID":"P008","Tipo":"COMIDA","Categoría":"Pizzas Familiares","Producto":"Margarita Familiar","Precio Actual (MXN)":270,"Nuevo Precio Sugerido (MXN)":319,"PRECIO EN APPS":389,"PRECIO PARA APPS CON FORMULA":389,"PRECIO MINIMO":279},
    {"ID":"P010","Tipo":"COMIDA","Categoría":"Pizzas Familiares","Producto":"Veggie Lover Familiar","Precio Actual (MXN)":270,"Nuevo Precio Sugerido (MXN)":319,"PRECIO EN APPS":389,"PRECIO PARA APPS CON FORMULA":389,"PRECIO MINIMO":279},
    {"ID":"P012","Tipo":"COMIDA","Categoría":"Pizzas Familiares","Producto":"Mexicana Familiar","Precio Actual (MXN)":280,"Nuevo Precio Sugerido (MXN)":329,"PRECIO EN APPS":395,"PRECIO PARA APPS CON FORMULA":395,"PRECIO MINIMO":299},
    {"ID":"P014","Tipo":"COMIDA","Categoría":"Pizzas Familiares","Producto":"Búfalo Chicken Familiar","Precio Actual (MXN)":280,"Nuevo Precio Sugerido (MXN)":329,"PRECIO EN APPS":399,"PRECIO PARA APPS CON FORMULA":399,"PRECIO MINIMO":309},
    {"ID":"P016","Tipo":"COMIDA","Categoría":"Pizzas Familiares","Producto":"BBQ Chicken Familiar","Precio Actual (MXN)":280,"Nuevo Precio Sugerido (MXN)":329,"PRECIO EN APPS":399,"PRECIO PARA APPS CON FORMULA":399,"PRECIO MINIMO":309},
    {"ID":"P018","Tipo":"COMIDA","Categoría":"Pizzas Familiares","Producto":"Dulce Nutella Familiar","Precio Actual (MXN)":280,"Nuevo Precio Sugerido (MXN)":329,"PRECIO EN APPS":395,"PRECIO PARA APPS CON FORMULA":395,"PRECIO MINIMO":289},
    {"ID":"P020","Tipo":"COMIDA","Categoría":"Pizzas Familiares","Producto":"Ricota Familiar","Precio Actual (MXN)":330,"Nuevo Precio Sugerido (MXN)":379,"PRECIO EN APPS":475,"PRECIO PARA APPS CON FORMULA":475,"PRECIO MINIMO":359},
    {"ID":"P022","Tipo":"COMIDA","Categoría":"Pizzas Familiares","Producto":"BLT Familiar","Precio Actual (MXN)":330,"Nuevo Precio Sugerido (MXN)":379,"PRECIO EN APPS":475,"PRECIO PARA APPS CON FORMULA":475,"PRECIO MINIMO":359},
    {"ID":"P024","Tipo":"COMIDA","Categoría":"Pizzas Familiares","Producto":"Chicken Ranch Familiar","Precio Actual (MXN)":330,"Nuevo Precio Sugerido (MXN)":379,"PRECIO EN APPS":475,"PRECIO PARA APPS CON FORMULA":475,"PRECIO MINIMO":349},
    {"ID":"P026","Tipo":"COMIDA","Categoría":"Pizzas Familiares","Producto":"Pesto Familiar","Precio Actual (MXN)":330,"Nuevo Precio Sugerido (MXN)":379,"PRECIO EN APPS":475,"PRECIO PARA APPS CON FORMULA":475,"PRECIO MINIMO":359},
    {"ID":"P028","Tipo":"COMIDA","Categoría":"Pizzas Familiares","Producto":"Steak & Cheese Familiar","Precio Actual (MXN)":330,"Nuevo Precio Sugerido (MXN)":389,"PRECIO EN APPS":499,"PRECIO PARA APPS CON FORMULA":499,"PRECIO MINIMO":389},
    {"ID":"P030","Tipo":"COMIDA","Categoría":"Pizzas Familiares","Producto":"Southwest Steak Familiar","Precio Actual (MXN)":330,"Nuevo Precio Sugerido (MXN)":389,"PRECIO EN APPS":499,"PRECIO PARA APPS CON FORMULA":499,"PRECIO MINIMO":389},
    {"ID":"P032","Tipo":"COMIDA","Categoría":"Pizzas Familiares","Producto":"Santa Fe Chicken Familiar","Precio Actual (MXN)":330,"Nuevo Precio Sugerido (MXN)":379,"PRECIO EN APPS":475,"PRECIO PARA APPS CON FORMULA":475,"PRECIO MINIMO":349},
    {"ID":"P034","Tipo":"COMIDA","Categoría":"Pizzas Familiares","Producto":"Meat Lover Familiar","Precio Actual (MXN)":350,"Nuevo Precio Sugerido (MXN)":419,"PRECIO EN APPS":545,"PRECIO PARA APPS CON FORMULA":545,"PRECIO MINIMO":419},
    {"ID":"P036","Tipo":"COMIDA","Categoría":"Pizzas Familiares","Producto":"Mediterranea Familiar","Precio Actual (MXN)":350,"Nuevo Precio Sugerido (MXN)":395,"PRECIO EN APPS":515,"PRECIO PARA APPS CON FORMULA":515,"PRECIO MINIMO":399},
    {"ID":"P038","Tipo":"COMIDA","Categoría":"Pizzas Familiares","Producto":"Works Familiar","Precio Actual (MXN)":350,"Nuevo Precio Sugerido (MXN)":409,"PRECIO EN APPS":529,"PRECIO PARA APPS CON FORMULA":529,"PRECIO MINIMO":409},

    # --- HAMBURGUESAS y HOT DOGS ---
    {"ID":"H001","Tipo":"COMIDA","Categoría":"Hamburguesas","Producto":"Clásica","Precio Actual (MXN)":70,"Nuevo Precio Sugerido (MXN)":109,"PRECIO EN APPS":139,"PRECIO PARA APPS CON FORMULA":139,"PRECIO MINIMO":109},
    {"ID":"H002","Tipo":"COMIDA","Categoría":"Hamburguesas","Producto":"Hawaiana","Precio Actual (MXN)":80,"Nuevo Precio Sugerido (MXN)":119,"PRECIO EN APPS":155,"PRECIO PARA APPS CON FORMULA":155,"PRECIO MINIMO":119},
    {"ID":"H003","Tipo":"COMIDA","Categoría":"Hamburguesas","Producto":"Milanesa de pollo","Precio Actual (MXN)":80,"Nuevo Precio Sugerido (MXN)":109,"PRECIO EN APPS":139,"PRECIO PARA APPS CON FORMULA":139,"PRECIO MINIMO":109},
    {"ID":"H004","Tipo":"COMIDA","Categoría":"Hamburguesas","Producto":"Champiñones y queso de cabra","Precio Actual (MXN)":96,"Nuevo Precio Sugerido (MXN)":129,"PRECIO EN APPS":165,"PRECIO PARA APPS CON FORMULA":165,"PRECIO MINIMO":129},
    {"ID":"H005","Tipo":"COMIDA","Categoría":"Hamburguesas","Producto":"Arrachera","Precio Actual (MXN)":85,"Nuevo Precio Sugerido (MXN)":139,"PRECIO EN APPS":179,"PRECIO PARA APPS CON FORMULA":179,"PRECIO MINIMO":139},
    {"ID":"H006","Tipo":"COMIDA","Categoría":"Hamburguesas","Producto":"Regia (doble carne)","Precio Actual (MXN)":102,"Nuevo Precio Sugerido (MXN)":149,"PRECIO EN APPS":199,"PRECIO PARA APPS CON FORMULA":199,"PRECIO MINIMO":149},
    {"ID":"HD01","Tipo":"COMIDA","Categoría":"Hot Dogs","Producto":"Clásico","Precio Actual (MXN)":45,"Nuevo Precio Sugerido (MXN)":65,"PRECIO EN APPS":65,"PRECIO PARA APPS CON FORMULA":65,"PRECIO MINIMO":49},
    {"ID":"HD02","Tipo":"COMIDA","Categoría":"Hot Dogs","Producto":"Con Tocino","Precio Actual (MXN)":55,"Nuevo Precio Sugerido (MXN)":65,"PRECIO EN APPS":89,"PRECIO PARA APPS CON FORMULA":89,"PRECIO MINIMO":65},

    # --- SÁNDWICHES y OTROS ---
    {"ID":"S001","Tipo":"COMIDA","Categoría":"Sándwiches","Producto":"Sándwich Pavo (Baguel/Cuerno)","Precio Actual (MXN)":89,"Nuevo Precio Sugerido (MXN)":109,"PRECIO EN APPS":139,"PRECIO PARA APPS CON FORMULA":139,"PRECIO MINIMO":109},
    {"ID":"S002","Tipo":"COMIDA","Categoría":"Sándwiches","Producto":"Sándwich Pavo (Baguette/Chapata)","Precio Actual (MXN)":107,"Nuevo Precio Sugerido (MXN)":129,"PRECIO EN APPS":169,"PRECIO PARA APPS CON FORMULA":169,"PRECIO MINIMO":129},
    {"ID":"S005","Tipo":"COMIDA","Categoría":"Sándwiches","Producto":"Sándwich Milanesa (Baguel/Cuerno)","Precio Actual (MXN)":89,"Nuevo Precio Sugerido (MXN)":109,"PRECIO EN APPS":139,"PRECIO PARA APPS CON FORMULA":139,"PRECIO MINIMO":109},
    {"ID":"S006","Tipo":"COMIDA","Categoría":"Sándwiches","Producto":"Sándwich Milanesa (Baguette/Chapata)","Precio Actual (MXN)":107,"Nuevo Precio Sugerido (MXN)":129,"PRECIO EN APPS":165,"PRECIO PARA APPS CON FORMULA":165,"PRECIO MINIMO":129},
    {"ID":"S009","Tipo":"COMIDA","Categoría":"Sándwiches","Producto":"Sándwich 3 quesos (a la carta)","Precio Actual (MXN)":100,"Nuevo Precio Sugerido (MXN)":119,"PRECIO EN APPS":155,"PRECIO PARA APPS CON FORMULA":155,"PRECIO MINIMO":119},
    {"ID":"S013","Tipo":"COMIDA","Categoría":"Sándwiches","Producto":"Sándwich Carnes frías (a la carta)","Precio Actual (MXN)":122,"Nuevo Precio Sugerido (MXN)":149,"PRECIO EN APPS":195,"PRECIO PARA APPS CON FORMULA":195,"PRECIO MINIMO":149},
    {"ID":"M002","Tipo":"COMIDA","Categoría":"Otros Salados","Producto":"Molletes Especiales (con carne)","Precio Actual (MXN)":107,"Nuevo Precio Sugerido (MXN)":129,"PRECIO EN APPS":165,"PRECIO PARA APPS CON FORMULA":165,"PRECIO MINIMO":129},
    {"ID":"M003","Tipo":"COMIDA","Categoría":"Otros Salados","Producto":"Burritos (Pavo o Milanesa)","Precio Actual (MXN)":85,"Nuevo Precio Sugerido (MXN)":105,"PRECIO EN APPS":135,"PRECIO PARA APPS CON FORMULA":135,"PRECIO MINIMO":105},
    {"ID":"M004","Tipo":"COMIDA","Categoría":"Otros Salados","Producto":"Ensalada con proteína","Precio Actual (MXN)":109,"Nuevo Precio Sugerido (MXN)":125,"PRECIO EN APPS":165,"PRECIO PARA APPS CON FORMULA":165,"PRECIO MINIMO":125},
    {"ID":"M005","Tipo":"COMIDA","Categoría":"Otros Salados","Producto":"Pechuga asada/empanizada con guarnición","Precio Actual (MXN)":85,"Nuevo Precio Sugerido (MXN)":119,"PRECIO EN APPS":155,"PRECIO PARA APPS CON FORMULA":155,"PRECIO MINIMO":119},

    # --- PASTAS y CREPAS ---
    {"ID":"PA01","Tipo":"COMIDA","Categoría":"Pastas","Producto":"Pasta (cualquier especialidad)","Precio Actual (MXN)":145,"Nuevo Precio Sugerido (MXN)":175,"PRECIO EN APPS":225,"PRECIO PARA APPS CON FORMULA":225,"PRECIO MINIMO":169},
    {"ID":"C001","Tipo":"COMIDA","Categoría":"Crepas Saladas","Producto":"Crepa Pavo con Manchego (y similares)","Precio Actual (MXN)":96,"Nuevo Precio Sugerido (MXN)":119,"PRECIO EN APPS":155,"PRECIO PARA APPS CON FORMULA":155,"PRECIO MINIMO":119},
    {"ID":"C003","Tipo":"COMIDA","Categoría":"Crepas Saladas","Producto":"Crepa Salami / Hawaiana / 3 Quesos","Precio Actual (MXN)":114,"Nuevo Precio Sugerido (MXN)":129,"PRECIO EN APPS":169,"PRECIO PARA APPS CON FORMULA":169,"PRECIO MINIMO":129},
    {"ID":"C005","Tipo":"COMIDA","Categoría":"Crepas Saladas","Producto":"Crepa Pechuga de Pavo con Serrano","Precio Actual (MXN)":129,"Nuevo Precio Sugerido (MXN)":149,"PRECIO EN APPS":195,"PRECIO PARA APPS CON FORMULA":195,"PRECIO MINIMO":149},
    {"ID":"C002","Tipo":"POSTRE","Categoría":"Crepas Dulces","Producto":"Crepa Nutella / Cajeta / Philadelphia","Precio Actual (MXN)":85,"Nuevo Precio Sugerido (MXN)":95,"PRECIO EN APPS":125,"PRECIO PARA APPS CON FORMULA":125,"PRECIO MINIMO":95},
    {"ID":"C004","Tipo":"POSTRE","Categoría":"Crepas Dulces","Producto":"Crepa Nutella con fruta / Cajeta con nuez","Precio Actual (MXN)":96,"Nuevo Precio Sugerido (MXN)":109,"PRECIO EN APPS":145,"PRECIO PARA APPS CON FORMULA":145,"PRECIO MINIMO":109},

    # --- SNACKS ---
    {"ID":"SN01","Tipo":"COMIDA","Categoría":"Snacks","Producto":"Orden de papas gajo o a la francesa","Precio Actual (MXN)":45,"Nuevo Precio Sugerido (MXN)":59,"PRECIO EN APPS":75,"PRECIO PARA APPS CON FORMULA":75,"PRECIO MINIMO":59},
    {"ID":"SN02","Tipo":"COMIDA","Categoría":"Snacks","Producto":"Dedos de Queso (8 pzas)","Precio Actual (MXN)":150,"Nuevo Precio Sugerido (MXN)":175,"PRECIO EN APPS":215,"PRECIO PARA APPS CON FORMULA":215,"PRECIO MINIMO":149},
    {"ID":"SN03","Tipo":"COMIDA","Categoría":"Snacks","Producto":"Boneless Wings (8 pzas)","Precio Actual (MXN)":150,"Nuevo Precio Sugerido (MXN)":175,"PRECIO EN APPS":205,"PRECIO PARA APPS CON FORMULA":205,"PRECIO MINIMO":159},
    {"ID":"SN04","Tipo":"COMIDA","Categoría":"Snacks","Producto":"Costillitas BBQ (300 gr)","Precio Actual (MXN)":150,"Nuevo Precio Sugerido (MXN)":189,"PRECIO EN APPS":245,"PRECIO PARA APPS CON FORMULA":245,"PRECIO MINIMO":189},
    {"ID":"SN05","Tipo":"COMIDA","Categoría":"Snacks","Producto":"Papa al horno (con toppings)","Precio Actual (MXN)":80,"Nuevo Precio Sugerido (MXN)":99,"PRECIO EN APPS":129,"PRECIO PARA APPS CON FORMULA":129,"PRECIO MINIMO":99},
    {"ID":"SN06","Tipo":"COMIDA","Categoría":"Snacks","Producto":"Nudos (6 pzas)","Precio Actual (MXN)":45,"Nuevo Precio Sugerido (MXN)":55,"PRECIO EN APPS":65,"PRECIO PARA APPS CON FORMULA":65,"PRECIO MINIMO":55},

    # --- BEBIDAS ---
    {"ID":"B001","Tipo":"BEBIDA","Categoría":"Bebidas Calientes","Producto":"Café Americano","Precio Actual (MXN)":33,"Nuevo Precio Sugerido (MXN)":45,"PRECIO EN APPS":49,"PRECIO PARA APPS CON FORMULA":49,"PRECIO MINIMO":39},
    {"ID":"B002","Tipo":"BEBIDA","Categoría":"Bebidas Calientes","Producto":"Espresso 1oz","Precio Actual (MXN)":33,"Nuevo Precio Sugerido (MXN)":39,"PRECIO EN APPS":49,"PRECIO PARA APPS CON FORMULA":49,"PRECIO MINIMO":39},
    {"ID":"B004","Tipo":"BEBIDA","Categoría":"Bebidas Calientes","Producto":"Capuchino","Precio Actual (MXN)":49,"Nuevo Precio Sugerido (MXN)":65,"PRECIO EN APPS":75,"PRECIO PARA APPS CON FORMULA":75,"PRECIO MINIMO":55},
    {"ID":"B008","Tipo":"BEBIDA","Categoría":"Bebidas Calientes","Producto":"Latte / Moka / Chai / Matcha","Precio Actual (MXN)":63,"Nuevo Precio Sugerido (MXN)":79,"PRECIO EN APPS":89,"PRECIO PARA APPS CON FORMULA":89,"PRECIO MINIMO":65},
    {"ID":"B010","Tipo":"BEBIDA","Categoría":"Bebidas Calientes","Producto":"Tisana","Precio Actual (MXN)":49,"Nuevo Precio Sugerido (MXN)":75,"PRECIO EN APPS":85,"PRECIO PARA APPS CON FORMULA":85,"PRECIO MINIMO":55},
    {"ID":"B005","Tipo":"BEBIDA","Categoría":"Bebidas Frías","Producto":"Frapé / Smoothie / Malteada","Precio Actual (MXN)":75,"Nuevo Precio Sugerido (MXN)":85,"PRECIO EN APPS":109,"PRECIO PARA APPS CON FORMULA":109,"PRECIO MINIMO":85},
    {"ID":"B009","Tipo":"BEBIDA","Categoría":"Bebidas Frías","Producto":"Soda Italiana / Limonada","Precio Actual (MXN)":57,"Nuevo Precio Sugerido (MXN)":65,"PRECIO EN APPS":89,"PRECIO PARA APPS CON FORMULA":89,"PRECIO MINIMO":65},
    {"ID":"B006","Tipo":"BEBIDA","Categoría":"Bebidas Frías","Producto":"Agua de Sabor","Precio Actual (MXN)":35,"Nuevo Precio Sugerido (MXN)":39,"PRECIO EN APPS":49,"PRECIO PARA APPS CON FORMULA":49,"PRECIO MINIMO":39},
    {"ID":"B007","Tipo":"BEBIDA","Categoría":"Bebidas Frías","Producto":"Coca Cola / Agua Mineral","Precio Actual (MXN)":35,"Nuevo Precio Sugerido (MXN)":45,"PRECIO EN APPS":49,"PRECIO PARA APPS CON FORMULA":49,"PRECIO MINIMO":45},

    # --- EXTRAS ---
    {"ID":"E001","Tipo":"COMIDA","Categoría":"Extras","Producto":"Cambio a Capuchino (en paquete)","Precio Actual (MXN)":16,"Nuevo Precio Sugerido (MXN)":25,"PRECIO EN APPS":35,"PRECIO PARA APPS CON FORMULA":35,"PRECIO MINIMO":25},
    {"ID":"E002","Tipo":"COMIDA","Categoría":"Extras","Producto":"Ingrediente Extra (Desayuno/Molletes/Crepas)","Precio Actual (MXN)":20,"Nuevo Precio Sugerido (MXN)":15,"PRECIO EN APPS":35,"PRECIO PARA APPS CON FORMULA":35,"PRECIO MINIMO":10},
    {"ID":"E003","Tipo":"COMIDA","Categoría":"Extras","Producto":"Orilla Rellena de Queso (Personal)","Precio Actual (MXN)":50,"Nuevo Precio Sugerido (MXN)":55,"PRECIO EN APPS":69,"PRECIO PARA APPS CON FORMULA":69,"PRECIO MINIMO":55},
    {"ID":"E004","Tipo":"COMIDA","Categoría":"Extras","Producto":"Orilla Rellena de Queso (Familiar)","Precio Actual (MXN)":70,"Nuevo Precio Sugerido (MXN)":85,"PRECIO EN APPS":99,"PRECIO PARA APPS CON FORMULA":99,"PRECIO MINIMO":85},
    {"ID":"E005","Tipo":"COMIDA","Categoría":"Extras","Producto":"Ingrediente Extra Pizza (Personal)","Precio Actual (MXN)":40,"Nuevo Precio Sugerido (MXN)":25,"PRECIO EN APPS":45,"PRECIO PARA APPS CON FORMULA":45,"PRECIO MINIMO":20},
    {"ID":"E006","Tipo":"COMIDA","Categoría":"Extras","Producto":"Ingrediente Gourmet Pizza (Personal)","Precio Actual (MXN)":50,"Nuevo Precio Sugerido (MXN)":59,"PRECIO EN APPS":79,"PRECIO PARA APPS CON FORMULA":79,"PRECIO MINIMO":59},
    {"ID":"E012","Tipo":"COMIDA","Categoría":"Extras","Producto":"Empaque para Llevar (Domo/Vaso)","Precio Actual (MXN)":5,"Nuevo Precio Sugerido (MXN)":9,"PRECIO EN APPS":np.nan,"PRECIO PARA APPS CON FORMULA":np.nan,"PRECIO MINIMO":9},
]

# Carga DataFrame base
df = pd.DataFrame(DEFAULT_MENU)

# ========= Panel opcional para actualizar menú por CSV (no se muestra por defecto) =========
with st.expander("📥 (Opcional) Actualizar menú desde CSV"):
    up = st.file_uploader("Sube tu CSV con el mismo formato de columnas", type=["csv"])
    if up:
        try:
            df_csv = pd.read_csv(up)
            # normaliza dinero
            for c in ["Precio Actual (MXN)","Nuevo Precio Sugerido (MXN)","PRECIO EN APPS","PRECIO PARA APPS CON FORMULA","PRECIO MINIMO"]:
                if c in df_csv.columns: df_csv[c] = parse_money(df_csv[c])
            # valida columnas mínimas
            for req in ["ID","Categoría","Producto","Precio Actual (MXN)"]:
                if req not in df_csv.columns:
                    st.error(f"Falta la columna requerida: {req}")
                    st.stop()
            df = df_csv.copy()
            st.success("Menú actualizado desde CSV.")
        except Exception as e:
            st.error(f"No pude leer tu CSV: {e}")

# Normalización
for c in ["Precio Actual (MXN)","Nuevo Precio Sugerido (MXN)","PRECIO EN APPS","PRECIO PARA APPS CON FORMULA","PRECIO MINIMO"]:
    if c in df.columns:
        df[c] = parse_money(df[c])

id_col   = pick_col(df, ["ID"])
cat_col  = pick_col(df, ["Categoría","Categoria"])
prod_col = pick_col(df, ["Producto"])
p_actual = pick_col(df, ["Precio Actual (MXN)","Precio Actual"])
p_sug    = pick_col(df, ["Nuevo Precio Sugerido (MXN)","Nuevo Precio Sugerido"], required=False, default=None)
p_apps   = pick_col(df, ["PRECIO EN APPS","Precio en Apps"], required=False, default=None)
p_apps_f = pick_col(df, ["PRECIO PARA APPS CON FORMULA","Precio para Apps con formula"], required=False, default=None)
p_min    = pick_col(df, ["PRECIO MINIMO","Precio Minimo","Precio mínimo"], required=False, default=None)

# =========================
# Food cost por categoría
# =========================
st.title("🍕 Simulador de Combos Rentables – *El Chal*")
st.caption("Genera combos con IA o constrúyelos a mano. Ajusta comisiones/costos y exporta.")

st.markdown("### ⚙️ Parámetros de costo (food cost por categoría)")
defaults = {
    "Desayunos": 0.35, "Pizzas Personales": 0.32, "Pizzas Familiares": 0.35,
    "Hamburguesas": 0.38, "Hot Dogs": 0.32, "Sándwiches": 0.33, "Otros Salados": 0.33,
    "Pastas": 0.34, "Crepas Saladas": 0.32, "Crepas Dulces": 0.30,
    "Snacks": 0.30, "Bebidas Calientes": 0.25, "Bebidas Frías": 0.28, "Extras": 0.15
}
unique_cats = sorted(df[cat_col].dropna().unique())
cat_cost_pct: Dict[str, float] = {}
with st.expander("Ajusta % por categoría (predeterminados sugeridos)", expanded=False):
    for cat in unique_cats:
        cat_cost_pct[cat] = st.slider(cat, 0.10, 0.60, float(defaults.get(cat, 0.33)), 0.01, key=f"fc_{cat}")

# =========================
# Base de precios + costos generales
# =========================
st.markdown("### 💵 Base de precios + costos adicionales")
base_col_name = st.radio(
    "Usar como precio base por producto",
    ["Precio Actual", "Nuevo Precio Sugerido", "Precio en Apps", "Precio Apps (Fórmula)", "Precio Mínimo"],
    horizontal=True
)
base_map = {"Precio Actual":p_actual,"Nuevo Precio Sugerido":p_sug,"Precio en Apps":p_apps,"Precio Apps (Fórmula)":p_apps_f,"Precio Mínimo":p_min}
base_col = base_map[base_col_name]
if base_col is None: st.error(f"No existe la columna para **{base_col_name}** en el menú."); st.stop()

c1,c2,c3 = st.columns(3)
with c1: app_commission = st.slider("Comisión de app (%)", 0, 35, 0, 1)
with c2: packaging = st.number_input("Empaque por combo (MXN)", 0.0, step=1.0, value=0.0)
with c3: other_var = st.number_input("Otros costos variables (MXN)", 0.0, step=1.0, value=0.0)

# Catálogo compacto (ID -> info) para IA y editor
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
# Funciones de evaluación/heurística
# =========================
def price_floor_for_items(items):
    s = 0.0
    for it in items:
        pid = str(it["id"]); qty = float(it.get("qty",1))
        pm = catalog.get(pid, {}).get("precio_min")
        if pm: s += pm*qty
    return s

def eval_combo(items, precio_combo) -> Dict[str, float]:
    sum_base,sum_cost=0.0,0.0
    for it in items:
        pid = str(it["id"]); qty = float(it.get("qty",1))
        info = catalog.get(pid); 
        if not info or info.get("precio_base") is None: continue
        base = float(info["precio_base"])
        sum_base += base*qty
        sum_cost += costo_estimado_row(base, info["categoria"], cat_cost_pct)*qty
    commission_cost = precio_combo*(app_commission/100.0)
    total_cost_combo = sum_cost + packaging + other_var + commission_cost
    margen_abs = precio_combo - total_cost_combo
    margen_pct = (margen_abs/precio_combo*100) if precio_combo>0 else 0
    desc_vs_base = (1 - precio_combo/sum_base)*100 if sum_base>0 else 0
    return {"sum_base":sum_base,"sum_cost":sum_cost,"commission_cost":commission_cost,
            "total_cost_combo":total_cost_combo,"margen_abs":margen_abs,
            "margen_pct":margen_pct,"desc_vs_base":desc_vs_base}

def heuristic_combos(num=3, min_items=2, max_items=3, ensure_min=True):
    rng = random.Random()
    combos = []
    ids = list(catalog.keys())
    princ = [i for i in ids if re.search(r"pizza|hamb|hot dog|pasta", catalog[i]["categoria"], re.I)]
    bebidas = [i for i in ids if re.search(r"bebidas?|coca|agua", catalog[i]["categoria"], re.I)]
    extras  = [i for i in ids if re.search(r"extra|snack|papas|nudos", catalog[i]["categoria"], re.I)]

    for _ in range(num):
        n_it = rng.randint(min_items, max_items)
        items = []
        if princ: items.append({"id": rng.choice(princ), "qty": 1}); n_it -= 1
        pools = [bebidas, extras, ids]
        while n_it>0:
            pool = rng.choice(pools)
            if pool: items.append({"id": rng.choice(pool), "qty": 1}); n_it -= 1
            else: break
        ev = eval_combo(items, 1.0)
        if ev["sum_cost"]<=0 or ev["sum_base"]<=0: continue
        # margen 50-60% vs descuento 15-30%
        p_margin = ev["sum_cost"]/ (1 - rng.uniform(0.50,0.60))
        p_disc   = ev["sum_base"]*(1 - rng.uniform(0.15,0.30))
        price = max(p_margin, p_disc)
        if ensure_min: price = max(price, price_floor_for_items(items))
        ev2 = eval_combo(items, price)
        combos.append({
            "name": f"Combo Heurístico {uuid.uuid4().hex[:4]}",
            "items": items,
            "precio_combo": round(price,2),
            "metrics": ev2,
            "copy": "Principal + bebida a súper precio.",
            "why": "Valor alto percibido, margen sano y descuento competitivo."
        })
    return combos

# =========================
# 🤖 Generación de combos (IA)
# =========================
st.markdown("## 🤖 Generación de combos (IA)")
left_ai, right_ai = st.columns([2,1])
with left_ai:
    n_combos = st.slider("¿Cuántos combos proponer?", 1, 5, 3, 1)
    objetivos = st.multiselect("Objetivo de la tanda", 
                               ["Alta rentabilidad","Atracción (precio bajo)","Ticket medio","Familias","Oficina/pareja"],
                               default=["Alta rentabilidad","Ticket medio"])
with right_ai:
    min_items = st.number_input("Mínimo ítems por combo", 2, 6, 2, 1)
    max_items = st.number_input("Máximo ítems por combo", 2, 8, 3, 1)
    ensure_min_price = st.checkbox("Forzar ≥ suma de precios mínimos", value=True)

st.caption("La IA usa **temperatura alta** y un token aleatorio para que cada tanda sea diferente.")

if st.button("🎲 Generar combos (IA)", type="primary", use_container_width=True):
    sample_catalog = list(catalog.values())[:140]
    token_random = uuid.uuid4().hex
    prompt = f"""
Eres experto en pricing QSR en México. Crea **{n_combos} combos** creativos, competitivos y rentables para "El Chal".
Usa diversidad alta (token: {token_random}).
Catálogo: {json.dumps(sample_catalog, ensure_ascii=False)}
Parámetros actuales: comision_app_pct={app_commission}, empaque={packaging}, otros_costos={other_var}, base_precios="{base_col_name}"
Reglas:
- Ítems por combo: entre {min_items} y {max_items}, con al menos 1 principal (categorías que contengan pizza/hamburguesa/hot dog/pasta).
- Precio sugerido ≥ suma de precios mínimos si hay.
- Margen final objetivo (sobre precio) 45–65% después de costos/comisión.
- Descuento vs suma de precios base: 10–35%.
- Nombra el combo (≤40 chars), agrega "copy" (<140 chars) y "why" (1–2 frases).
Devuelve SOLO JSON:
{{"combos":[{{"name":"...","items":[{{"id":"P001","qty":1}},{{"id":"B001","qty":2}}],"precio_combo":249.0,"copy":"...","why":"..."}}]}}
"""
    out = call_gemini(prompt) if GEMINI_AVAILABLE else {"combos": heuristic_combos(n_combos, min_items, max_items, ensure_min_price)}
    if isinstance(out, dict) and "combos" in out:
        st.session_state["ai_combos"] = out["combos"]
    elif isinstance(out, list):
        st.session_state["ai_combos"] = out
    else:
        st.error("La IA no devolvió un JSON válido."); st.write(out)

# Mostrar resultados IA
if "ai_combos" in st.session_state and st.session_state["ai_combos"]:
    st.subheader("Propuestas")
    for i, combo in enumerate(st.session_state["ai_combos"], start=1):
        name = combo.get("name", f"Combo {i}")
        items = combo.get("items", [])
        price = float(combo.get("precio_combo", 0))
        if ensure_min_price: price = max(price, price_floor_for_items(items))
        metrics = eval_combo(items, price)

        colA, colB = st.columns([2,1])
        with colA:
            st.markdown(f"### {i}. {name}")
            rows=[]
            for it in items:
                pid=str(it.get("id")); qty=float(it.get("qty",1)); info=catalog.get(pid,{})
                rows.append({"ID":pid,"Categoría":info.get("categoria","—"),"Producto":info.get("producto","—"),
                             "Cant.":qty,"Precio base":info.get("precio_base",np.nan),"Precio mínimo":info.get("precio_min",np.nan)})
            tbl = pd.DataFrame(rows)
            st.dataframe(tbl.assign(**{"Precio base":lambda d:d["Precio base"].map(pesos),
                                       "Precio mínimo":lambda d:d["Precio mínimo"].map(pesos)}),
                         use_container_width=True)
        with colB:
            k1,k2 = st.columns(2)
            k1.metric("Precio combo", pesos(price))
            k2.metric("Margen", f"{metrics['margen_pct']:.1f}%", pesos(metrics['margen_abs']))
            k3,k4 = st.columns(2)
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

# =========================
# Editor del combo aplicado / Manual
# =========================
st.markdown("---")
st.header("🛠️ Editor del combo")

if "work_combo_items" not in st.session_state:
    st.info("Aún no has aplicado un combo de IA. Puedes generar arriba o construir uno manualmente.")
    with st.expander("Construcción manual rápida"):
        f1,f2 = st.columns(2)
        with f1:
            cat_sel = st.selectbox("Filtra por categoría", ["(todas)"] + unique_cats)
        with f2:
            search = st.text_input("Busca por texto (Producto contiene)")
        mask = pd.Series(True, index=df.index)
        if cat_sel != "(todas)": mask &= df[cat_col] == cat_sel
        if search: mask &= df[prod_col].astype(str).str.contains(search, case=False, na=False)
        options = df.loc[mask, id_col].astype(str).tolist()
        add_ids = st.multiselect("Agrega productos por ID", options)
        rows=[]
        for pid in add_ids:
            info=catalog[pid]; base=info["precio_base"] or 0.0
            cost=costo_estimado_row(base, info["categoria"], cat_cost_pct)
            q= st.number_input(f"Cantidad {pid}",1,10,1,1,key=f"qty_{pid}")
            rows.append({"ID":pid,"Categoría":info["categoria"],"Producto":info["producto"],
                         "Cantidad":q,"Precio base":base,"Costo estimado":cost,
                         "Precio mínimo":info.get("precio_min",0.0),
                         "Subtotal Precio":q*base,"Subtotal Costo":q*cost})
        if rows:
            st.session_state["work_combo_items"]=pd.DataFrame(rows)
            st.session_state["work_combo_price"]=float(sum(r["Subtotal Precio"] for r in rows))
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
    modo_precio = st.radio("Definir precio", ["Descuento vs base","Margen objetivo"], horizontal=True)
    if modo_precio=="Descuento vs base":
        desc = st.slider("Descuento (%)", 0, 60, 20, 1)
        combo_price = sum_price*(1 - desc/100)
    else:
        target_margin = st.slider("Margen objetivo (%)", 10, 80, 55, 1)
        combo_price = sum_cost / max(1e-6, 1 - target_margin/100)
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
        "comision_app_pct": app_commission, "empaque_mxn": packaging, "otros_costos_mxn": other_var,
        "modo_precio": modo_precio,
        "descuento_pct": (desc if modo_precio=="Descuento vs base" else None),
        "margen_objetivo_pct": (target_margin if modo_precio=="Margen objetivo" else None),
        "enforce_min": enforce_min
    },
    "precio_combo": round(combo_price, 2),
    "costo_total_combo": round(total_cost_combo, 2),
    "margen_abs": round(margin_abs, 2),
    "margen_pct": round(margin_pct, 2)
}
st.download_button("📥 Descargar combo (.json)", data=json.dumps(payload, ensure_ascii=False, indent=2),
                   file_name=f"combo_{export_name.replace(' ','_')}.json", mime="application/json")

st.success("Listo. Ya no requiere CSV; es mobile-friendly y la IA te dará propuestas distintas en cada tanda.")

