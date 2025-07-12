import streamlit as st
import pandas as pd

# Configuración de la página
st.set_page_config(layout="wide", page_title="Simulador de Precios El Chal")

# --- Carga de Datos ---
@st.cache_data
def load_data(filepath):
    """Carga los datos de precios desde un archivo CSV."""
    try:
        df = pd.read_csv(filepath)
        # Asegurarse de que la columna de precios es numérica
        df['Precio (MXN)'] = pd.to_numeric(df['Precio (MXN)'], errors='coerce')
        return df
    except FileNotFoundError:
        st.error(f"Error: No se encontró el archivo '{filepath}'. Asegúrese de que el archivo CSV está en la misma carpeta que el script.")
        return None

# --- Funciones de la Aplicación ---
def display_price_comparison(df, el_chal_product, new_price):
    """Muestra la comparación de precios para un producto dado."""
    # Filtrar por la subcategoría del producto de El Chal para encontrar comparables
    subcategory = el_chal_product.iloc
    size = el_chal_product.iloc
    
    # Priorizar la comparación por tamaño y subcategoría
    competitors = df == subcategory) & 
                     (df!= 'Café y Pizzas El Chal') &
                     (df.str.contains('Grande|Familiar|14', case=False, na=False) if 'Familiar' in size else df.str.contains('Personal|Chica', case=False, na=False))]

    if competitors.empty:
        st.warning(f"No se encontraron competidores directos para la subcategoría '{subcategory}' y tamaño similar. Mostrando competidores de la misma categoría.")
        category = el_chal_product['Categoría'].iloc
        competitors = df[(df['Categoría'] == category) & (df!= 'Café y Pizzas El Chal')]

    st.subheader(f"Comparativa de Mercado para: {subcategory}")

    # Crear una lista para los datos de la tabla de comparación
    comparison_data =
    for _, row in competitors.iterrows():
        if pd.notna(row['Precio (MXN)']):
            difference = new_price - row['Precio (MXN)']
            comparison_data.append({
                'Competidor': row,
                'Producto Competidor': row['Nombre del Producto'],
                'Precio Competidor (MXN)': f"${row['Precio (MXN)']:.2f}",
                'Diferencia con Precio Simulado': f"${difference:.2f}",
                'Análisis': 'Más caro' if difference > 0 else 'Más barato' if difference < 0 else 'Igual'
            })
    
    if comparison_data:
        comparison_df = pd.DataFrame(comparison_data)
        st.dataframe(comparison_df, use_container_width=True)
    else:
        st.info("No hay datos de precios de competidores para esta categoría.")

# --- Interfaz de Usuario ---
st.title("📈 Simulador de Precios y Análisis Competitivo")
st.markdown("Herramienta para analizar y simular la estrategia de precios de **Café y Pizzas El Chal**.")

data = load_data('pizzeria_data.csv')

if data is not None:
    # Separar los datos de El Chal del resto
    el_chal_df = data == 'Café y Pizzas El Chal'].copy()
    competitors_df = data!= 'Café y Pizzas El Chal'].copy()

    st.sidebar.header("Panel de Simulación")

    # Crear una lista de productos de El Chal para el selector
    el_chal_df['display_name'] = el_chal_df['Nombre del Producto'] + " (" + el_chal_df + ")"
    product_list = el_chal_df['display_name'].unique()
    
    selected_product_display_name = st.sidebar.selectbox(
        "Seleccione un producto de 'El Chal' para analizar:",
        product_list
    )

    if selected_product_display_name:
        # Obtener la información completa del producto seleccionado
        selected_product_info = el_chal_df[el_chal_df['display_name'] == selected_product_display_name]
        current_price = selected_product_info['Precio (MXN)'].iloc

        st.sidebar.metric(label="Precio Actual", value=f"${current_price:.2f}")

        # Slider para simular un nuevo precio
        new_simulated_price = st.sidebar.number_input(
            "Ingrese el Nuevo Precio Simulado (MXN):",
            min_value=0.0,
            value=current_price,
            step=5.0,
            format="%.2f"
        )
        
        st.header(f"Análisis para: {selected_product_display_name}")
        st.info(f"Simulando un nuevo precio de **${new_simulated_price:.2f}** (Precio actual: ${current_price:.2f})")

        # Mostrar la comparación de precios
        display_price_comparison(competitors_df, selected_product_info, new_simulated_price)

    st.markdown("---")
    st.header("Base de Datos de la Competencia")
    st.dataframe(data, use_container_width=True)

else:
    st.warning("La aplicación no puede funcionar sin el archivo de datos. Por favor, siga las instrucciones del informe.")
