import streamlit as st
import pandas as pd
import uuid
import json

def upload_file(supabase, file, bucket="propiedades_docs"):
    """Sube un archivo a Supabase Storage y retorna la URL pública."""
    if not file:
        return None
    try:
        # Estructura: user_id/uuid_filename.ext
        user_id = st.session_state['user_info']['id']
        ext = file.name.split('.')[-1]
        filename = f"{user_id}/{uuid.uuid4()}.{ext}"
        
        supabase.storage.from_(bucket).upload(
            file=file.getvalue(), 
            path=filename, 
            file_options={"content-type": file.type}
        )
        return supabase.storage.from_(bucket).get_public_url(filename)
    except Exception as e:
        st.error(f"Error subiendo archivo {file.name}: {e}")
        return None

def create_property(supabase, data):
    try:
        # 1. Insertar en la tabla BASE y obtener el ID
        base_data = {
            "distrito_id": data.get("distrito_id"),
            "direccion": data.get("direccion"),
            "comuna": data.get("comuna"),
            "lat": data.get("lat"),
            "lon": data.get("lon")
        }
        res = supabase.table('propiedades').insert(base_data).execute()
        if not res.data:
            return False
        
        prop_id = res.data[0]['id']

        # 2. Insertar en tablas satélites (si hay datos)
        
        # SII
        sii_data = {
            "propiedad_id": prop_id, "rol_sii": data.get("rol_sii"), "detalle_direccion": data.get("detalle_direccion"),
            "sup_sii": data.get("sup_sii"), "sup_terreno_sii": data.get("sup_terreno_sii"),
            "contribuciones": data.get("contribuciones"), "piso_sii": data.get("piso_sii"), "ano_construccion": data.get("ano_construccion")
        }
        supabase.table('propiedades_sii').insert(sii_data).execute()

        # CBR
        cbr_data = {
            "propiedad_id": prop_id, "inscripcion_fna": data.get("inscripcion_fna"), "fecha_ultima_compraventa": data.get("fecha_ultima_compraventa"),
            "moneda_transaccion": data.get("moneda_transaccion"), "precio_compra": data.get("precio_compra"),
            "tipo_compraventa": data.get("tipo_compraventa"), "propietarios": data.get("propietarios"), "adjunto_compraventa_url": data.get("adjunto_compraventa_url")
        }
        supabase.table('propiedades_cbr').insert(cbr_data).execute()

        # PORTAL
        portal_data = {
            "propiedad_id": prop_id, "link_portal_inmobiliario": data.get("link_portal_inmobiliario"), "copia_publicacion_pdf_url": data.get("copia_publicacion_pdf_url"),
            "descripcion_publicacion": data.get("descripcion_publicacion"), "corredor": data.get("corredor"), "precio_publicacion": data.get("precio_publicacion"),
            "fecha_publicacion": data.get("fecha_publicacion"), "superficie_util": data.get("superficie_util"), "superficie_total": data.get("superficie_total"),
            "tipologia": data.get("tipologia")
        }
        supabase.table('propiedades_portal').insert(portal_data).execute()

        # BACKOFFICE
        bo_data = {
            "propiedad_id": prop_id, "foto_fachada_url": data.get("foto_fachada_url"), "distancia_distrito": data.get("distancia_distrito"),
            "tiempo_caminando": data.get("tiempo_caminando"), "tipo_propiedad": data.get("tipo_propiedad"), "num_estacionamientos": data.get("num_estacionamientos"),
            "pisos": data.get("pisos"), "tiene_jardin": data.get("tiene_jardin"), "material_piso": data.get("material_piso"), "tiene_piscina": data.get("tiene_piscina")
        }
        supabase.table('propiedades_backoffice').insert(bo_data).execute()

        # CAPTACION
        cap_data = {
            "propiedad_id": prop_id, "descripcion_captacion": data.get("descripcion_captacion"), "precio_sugerido": data.get("precio_sugerido"),
            "precio_publicacion_captacion": data.get("precio_publicacion_captacion"), "sup_interior": data.get("sup_interior"),
            "sup_terraza": data.get("sup_terraza"), "sup_total_captacion": data.get("sup_total_captacion"), "sup_jardin": data.get("sup_jardin")
        }
        supabase.table('propiedades_captacion').insert(cap_data).execute()

        return True
    except Exception as e:
        st.error(f"Error al guardar propiedad: {e}")
        return False

def render_properties_view(supabase):
    st.title("Gestión de Propiedades")

    # Obtener distritos para el selector
    distritos_resp = supabase.table('distritos').select("id, nombre").execute()
    distritos_opts = {d['nombre']: d['id'] for d in distritos_resp.data}

    tab_list, tab_create = st.tabs(["📋 Listado de Propiedades", "🏠 Nueva Propiedad"])

    # --- TAB: NUEVA PROPIEDAD ---
    with tab_create:
        st.markdown("### Ficha de Propiedad")
        
        with st.form("form_nueva_propiedad"):
            # 0. VINCULACIÓN
            st.info("📍 Vinculación")
            distrito_sel = st.selectbox("Asignar a Distrito", options=list(distritos_opts.keys()))
            
            # 1. DATOS SII
            with st.expander("🏛️ Datos SII", expanded=True):
                c1, c2, c3 = st.columns(3)
                direccion = c1.text_input("Dirección")
                detalle_dir = c2.text_input("Detalle (Depto/Casa)")
                comuna = c3.text_input("Comuna")
                
                c4, c5, c6 = st.columns(3)
                rol_sii = c4.text_input("ROL SII")
                lat = c5.number_input("Latitud", format="%.6f", value=0.0)
                lon = c6.number_input("Longitud", format="%.6f", value=0.0)
                
                c7, c8, c9 = st.columns(3)
                sup_sii = c7.number_input("Sup. Construida SII (m2)")
                sup_terreno = c8.number_input("Sup. Terreno SII (m2)")
                contribuciones = c9.number_input("Contribuciones ($)", step=1000)
                
                c10, c11 = st.columns(2)
                piso_sii = c10.number_input("Piso (N°)", step=1)
                ano_const = c11.number_input("Año Construcción", step=1, value=2000)

            # 2. DATOS CBR
            with st.expander("📜 Datos Conservador (CBR)", expanded=False):
                cb1, cb2 = st.columns(2)
                inscripcion_fna = cb1.text_input("Inscripción FNA")
                tipo_compraventa = cb2.text_input("Tipo Compraventa")
                
                cb3, cb4, cb5 = st.columns(3)
                fecha_compra = cb3.date_input("Fecha Última Compraventa", value=None)
                moneda = cb4.selectbox("Moneda", ["Pesos", "UF"])
                precio_compra = cb5.number_input("Precio Compra")
                
                st.markdown("**Propietarios**")
                prop_nombre = st.text_input("Nombre Propietario(s)")
                prop_rut = st.text_input("RUT Propietario(s)")
                
                adjunto_cbr = st.file_uploader("Adjunto Compraventa (PDF)", type="pdf")

            # 3. PORTAL INMOBILIARIO
            with st.expander("🌐 Portal Inmobiliario (Histórico)", expanded=False):
                pi1, pi2 = st.columns(2)
                link_portal = pi1.text_input("Link Publicación")
                corredor = pi2.text_input("Corredor")
                
                pi3, pi4, pi5 = st.columns(3)
                precio_pub = pi3.number_input("Precio Publicación")
                fecha_pub = pi4.date_input("Fecha Publicación", value=None)
                tipologia = pi5.text_input("Tipología")
                
                pi6, pi7 = st.columns(2)
                sup_util = pi6.number_input("Sup. Útil")
                sup_total = pi7.number_input("Sup. Total")
                
                desc_pub = st.text_area("Descripción Publicación")
                pdf_pub = st.file_uploader("Copia Publicación (PDF)", type="pdf")

            # 4. BACKOFFICE
            with st.expander("🏢 Información Backoffice Distrito 0", expanded=False):
                bo1, bo2 = st.columns(2)
                tipo_prop = bo1.selectbox("Tipo Propiedad", ["Casa", "Departamento", "Terreno", "Oficina"])
                material_piso = bo2.text_input("Material Piso")
                
                bo3, bo4 = st.columns(2)
                distancia = bo3.number_input("Distancia a Distrito (m)")
                tiempo = bo4.number_input("Tiempo Caminando (min)")
                
                bo5, bo6, bo7, bo8 = st.columns(4)
                n_estac = bo5.number_input("Estacionamientos", step=1)
                n_pisos = bo6.number_input("Cantidad Pisos", step=1)
                jardin = bo7.checkbox("Tiene Jardín")
                piscina = bo8.checkbox("Tiene Piscina")
                
                foto_fachada = st.file_uploader("Foto Fachada", type=["jpg", "png", "jpeg"])

            # 5. CAPTACIONES
            with st.expander("🤝 Captación (Venta Propia)", expanded=False):
                cap1, cap2 = st.columns(2)
                precio_sug = cap1.number_input("Precio Sugerido")
                precio_cap = cap2.number_input("Precio Publicación Captación")
                
                cap3, cap4, cap5, cap6 = st.columns(4)
                s_int = cap3.number_input("Sup. Interior")
                s_terr = cap4.number_input("Sup. Terraza")
                s_tot_cap = cap5.number_input("Sup. Total Captación")
                s_jar = cap6.number_input("Sup. Jardín")
                
                desc_cap = st.text_area("Descripción Propiedad (Captación)")

            submitted = st.form_submit_button("💾 Guardar Propiedad")
            
            if submitted:
                # Subir archivos
                url_cbr = upload_file(supabase, adjunto_cbr)
                url_pdf_pub = upload_file(supabase, pdf_pub)
                url_fachada = upload_file(supabase, foto_fachada)
                
                # Construir objeto de datos
                prop_data = {
                    "distrito_id": distritos_opts[distrito_sel],
                    # SII
                    "direccion": direccion, "detalle_direccion": detalle_dir, "comuna": comuna,
                    "lat": lat, "lon": lon, "rol_sii": rol_sii, "sup_sii": sup_sii,
                    "sup_terreno_sii": sup_terreno, "contribuciones": contribuciones,
                    "piso_sii": piso_sii, "ano_construccion": ano_const,
                    # CBR
                    "inscripcion_fna": inscripcion_fna, "tipo_compraventa": tipo_compraventa,
                    "fecha_ultima_compraventa": fecha_compra.isoformat() if fecha_compra else None,
                    "moneda_transaccion": moneda, "precio_compra": precio_compra,
                    "propietarios": [{"nombre": prop_nombre, "rut": prop_rut}], # Simple JSON structure
                    "adjunto_compraventa_url": url_cbr,
                    # Portal
                    "link_portal_inmobiliario": link_portal, "corredor": corredor,
                    "precio_publicacion": precio_pub, 
                    "fecha_publicacion": fecha_pub.isoformat() if fecha_pub else None,
                    "tipologia": tipologia, "superficie_util": sup_util, "superficie_total": sup_total,
                    "descripcion_publicacion": desc_pub, "copia_publicacion_pdf_url": url_pdf_pub,
                    # Backoffice
                    "tipo_propiedad": tipo_prop, "material_piso": material_piso,
                    "distancia_distrito": distancia, "tiempo_caminando": tiempo,
                    "num_estacionamientos": n_estac, "pisos": n_pisos,
                    "tiene_jardin": jardin, "tiene_piscina": piscina,
                    "foto_fachada_url": url_fachada,
                    # Captacion
                    "precio_sugerido": precio_sug, "precio_publicacion_captacion": precio_cap,
                    "sup_interior": s_int, "sup_terraza": s_terr,
                    "sup_total_captacion": s_tot_cap, "sup_jardin": s_jar,
                    "descripcion_captacion": desc_cap
                }
                
                if create_property(supabase, prop_data):
                    st.success("Propiedad creada exitosamente")
                    st.rerun()

    # --- TAB: LISTADO ---
    with tab_list:
        st.subheader("Inventario de Propiedades")
        # Cargar propiedades
        # Hacemos un JOIN con las tablas satélites para mostrar info en la tabla
        # Nota: Supabase usa la sintaxis tabla_relacionada(*) para traer los datos anidados
        query = """
            *,
            distritos(nombre),
            propiedades_portal(precio_publicacion),
            propiedades_backoffice(tipo_propiedad)
        """
        props = supabase.table('propiedades').select(query).execute().data
        
        if not props:
            st.info("No hay propiedades registradas.")
        else:
            # Aplanar datos para la tabla (extraer nombre distrito)
            df_data = []
            for p in props:
                row = p.copy()
                
                # Aplanar Distrito
                if p.get('distritos'):
                    row['distrito'] = p['distritos']['nombre']
                else:
                    row['distrito'] = "Sin Asignar"
                
                # Aplanar Precio (Portal)
                if p.get('propiedades_portal'):
                    # Puede ser una lista o un objeto dependiendo de la relación (1:1 suele ser objeto o lista de 1)
                    portal = p['propiedades_portal']
                    # Si es lista, tomamos el primero, si es dict, directo
                    if isinstance(portal, list) and len(portal) > 0:
                        row['precio_publicacion'] = portal[0].get('precio_publicacion')
                    elif isinstance(portal, dict):
                        row['precio_publicacion'] = portal.get('precio_publicacion')
                
                # Aplanar Tipo (Backoffice)
                if p.get('propiedades_backoffice'):
                    bo = p['propiedades_backoffice']
                    if isinstance(bo, list) and len(bo) > 0:
                        row['tipo_propiedad'] = bo[0].get('tipo_propiedad')
                    elif isinstance(bo, dict):
                        row['tipo_propiedad'] = bo.get('tipo_propiedad')

                df_data.append(row)
            
            df = pd.DataFrame(df_data)
            # Seleccionar columnas clave para la vista previa
            cols_to_show = ['direccion', 'comuna', 'distrito', 'precio_publicacion', 'tipo_propiedad']
            st.dataframe(df[cols_to_show], use_container_width=True)
