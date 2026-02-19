import streamlit as st
from supabase import create_client, Client
import time
import pandas as pd
from streamlit_folium import st_folium
import folium
import uuid # Para generar nombres de archivo únicos
import requests

# Importar módulos personalizados
from modules import properties

# --- 1. CONFIGURACIÓN Y ESTILOS ---
st.set_page_config(
    page_title="Distrito 0 | Plataforma",
    page_icon="assets/Pin Do Logo.jpg",
    layout="wide"
)

# Estilos CSS personalizados (Branding Distrito 0)
st.markdown("""
    <style>
    /* 1. Fondo general */
    [data-testid="stAppViewContainer"] { background-color: #f8f9fa; }
    
    /* 2. Login Container */
    .login-container {
        background-color: #ffffff;
        padding: 40px;
        border-radius: 20px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.08);
        text-align: center;
        border-top: 6px solid #b02cd4;
        margin-top: 50px;
    }
    
    /* 3. Textos oscuros en login */
    .login-container h1, .login-container h3, .login-container p, .login-container div {
        color: #333333 !important;
    }

    /* 4. Botones */
    .stButton>button {
        background: linear-gradient(90deg, #b02cd4 0%, #ff00ff 100%);
        color: white !important;
        border: none;
        border-radius: 25px;
        padding: 12px 30px;
        font-weight: 600;
        transition: all 0.3s ease;
        width: 100%;
    }
    .stButton>button:hover {
        transform: scale(1.02);
        box-shadow: 0 5px 15px rgba(176, 44, 212, 0.4);
    }

    /* 5. Inputs */
    .stTextInput>div>div>input {
        border-radius: 12px;
        border: 1px solid #e0e0e0;
        padding: 12px;
        background-color: #ffffff;
        color: #333333;
    }
    
    /* 6. Badge Rol */
    .role-badge {
        display: inline-block;
        padding: 5px 12px;
        background: linear-gradient(90deg, #fce4ec 0%, #f3e5f5 100%);
        color: #880e4f;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: bold;
        border: 1px solid #f8bbd0;
        margin-top: 5px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. CONEXIÓN A SUPABASE ---
def init_connection():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except:
        st.error("⚠️ Falta configurar .streamlit/secrets.toml")
        return None

supabase = init_connection()

# --- 3. GESTIÓN DE ESTADO ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'user_role' not in st.session_state: st.session_state['user_role'] = None
if 'user_info' not in st.session_state: st.session_state['user_info'] = {}
if 'access_token' not in st.session_state: st.session_state['access_token'] = None
if 'refresh_token' not in st.session_state: st.session_state['refresh_token'] = None
if 'current_view' not in st.session_state: st.session_state['current_view'] = 'dashboard'

if st.session_state['access_token']:
    try:
        supabase.auth.set_session(st.session_state['access_token'], st.session_state['refresh_token'])
    except Exception as e:
        st.session_state['logged_in'] = False
        st.session_state['access_token'] = None

# --- 4. LÓGICA ---
def login_user(email, password):
    try:
        auth_response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        user_id = auth_response.user.id
        st.session_state['access_token'] = auth_response.session.access_token
        st.session_state['refresh_token'] = auth_response.session.refresh_token

        response = supabase.table('user_profiles').select("*").eq('id', user_id).execute()
        if len(response.data) > 0:
            profile = response.data[0]
            st.session_state['logged_in'] = True
            st.session_state['user_role'] = profile['role']
            st.session_state['user_info'] = profile
            st.toast(f"¡Bienvenido {profile['full_name']}!", icon="👋")
            time.sleep(1)
            st.rerun()
        else:
            st.error("Usuario sin perfil asignado.")
    except Exception as e:
        st.error("Credenciales incorrectas.")
        print(f"DEBUG: {e}")

def create_new_user(email, password, full_name, role, assigned_districts):
    try:
        # Usar un cliente temporal para no cerrar la sesión del admin actual al crear otro usuario
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        temp_client = create_client(url, key)
        
        # Crear usuario en Auth
        auth_response = temp_client.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "full_name": full_name
                }
            }
        })
        
        if auth_response.user:
            user_id = auth_response.user.id
            
            # Usar el cliente temporal (usuario nuevo) si hay sesión, para cumplir con RLS estándar (usuario crea su propio perfil)
            # Si no hay sesión (requiere confirmación email), usamos el cliente admin (supabase)
            client_to_use = temp_client if auth_response.session else supabase
            
            user_data = {
                'id': user_id,
                'email': email,
                'full_name': full_name,
                'role': role,
                'assigned_districts': assigned_districts
            }
            
            client_to_use.table('user_profiles').insert(user_data).execute()
            return True, "Usuario creado exitosamente"
        else:
            return False, "No se pudo crear el usuario (Error de Autenticación)"
            
    except Exception as e:
        return False, f"Error al crear usuario: {str(e)}"

def update_user(user_id, email, full_name, role, assigned_districts):
    try:
        data = {
            'email': email,
            'full_name': full_name,
            'role': role,
            'assigned_districts': assigned_districts
        }
        supabase.table('user_profiles').update(data).eq('id', user_id).execute()
        return True, "Usuario actualizado exitosamente"
    except Exception as e:
        return False, f"Error al actualizar usuario: {str(e)}"

def create_distrito(nombre, direccion, comuna, region, lat, lon, isocronas, foto, poly_5, poly_10, poly_15, poly_20):
    try:
        user_id = st.session_state['user_info']['id']
        foto_url = None
        urls_poligonos = {"5": None, "10": None, "15": None, "20": None}

        if foto:
            ext = foto.name.split('.')[-1]
            fname = f"{user_id}/{uuid.uuid4()}.{ext}"
            supabase.storage.from_("distrito_fotos").upload(file=foto.getvalue(), path=fname, file_options={"content-type": foto.type})
            foto_url = supabase.storage.from_("distrito_fotos").get_public_url(fname)
            
        poligonos_inputs = {"5": poly_5, "10": poly_10, "15": poly_15, "20": poly_20}
        for k, archivo in poligonos_inputs.items():
            if archivo:
                ext = archivo.name.split('.')[-1]
                fname = f"{user_id}/{uuid.uuid4()}_{k}min.{ext}"
                supabase.storage.from_("distrito_fotos").upload(file=archivo.getvalue(), path=fname, file_options={"content-type": "application/json"})
                urls_poligonos[k] = supabase.storage.from_("distrito_fotos").get_public_url(fname)

        params = {
            "p_nombre": nombre, "p_direccion": direccion, "p_comuna": comuna, "p_region": region,
            "p_lat": lat, "p_lon": lon, "p_isocronas": isocronas, "p_foto_url": foto_url,
            "p_poligono_url_5": urls_poligonos["5"], "p_poligono_url_10": urls_poligonos["10"],
            "p_poligono_url_15": urls_poligonos["15"], "p_poligono_url_20": urls_poligonos["20"]
        }
        supabase.rpc("create_distrito_func", params).execute()
        return True
    except Exception as e:
        st.error(f"Error al crear: {e}")
        return False

def update_distrito(distrito_id, nombre, direccion, comuna, region, lat, lon, isocronas, 
                    foto, poly_5, poly_10, poly_15, poly_20, current_foto_url, current_poly_urls):
    try:
        user_id = st.session_state['user_info']['id']
        final_foto_url = current_foto_url
        if foto:
            ext = foto.name.split('.')[-1]
            fname = f"{user_id}/{uuid.uuid4()}.{ext}"
            supabase.storage.from_("distrito_fotos").upload(file=foto.getvalue(), path=fname, file_options={"content-type": foto.type})
            final_foto_url = supabase.storage.from_("distrito_fotos").get_public_url(fname)

        final_poly_urls = current_poly_urls.copy()
        poligonos_inputs = {"5": poly_5, "10": poly_10, "15": poly_15, "20": poly_20}
        for k, archivo in poligonos_inputs.items():
            if archivo:
                ext = archivo.name.split('.')[-1]
                fname = f"{user_id}/{uuid.uuid4()}_{k}min.{ext}"
                supabase.storage.from_("distrito_fotos").upload(file=archivo.getvalue(), path=fname, file_options={"content-type": "application/json"})
                final_poly_urls[k] = supabase.storage.from_("distrito_fotos").get_public_url(fname)

        params = {
            "p_id": distrito_id, "p_nombre": nombre, "p_direccion": direccion, "p_comuna": comuna,
            "p_region": region, "p_lat": lat, "p_lon": lon, "p_isocronas": isocronas,
            "p_foto_url": final_foto_url, "p_poligono_url_5": final_poly_urls["5"],
            "p_poligono_url_10": final_poly_urls["10"], "p_poligono_url_15": final_poly_urls["15"],
            "p_poligono_url_20": final_poly_urls["20"]
        }
        supabase.rpc("update_distrito_func", params).execute()
        return True
    except Exception as e:
        st.error(f"Error al actualizar: {e}")
        return False

def delete_distrito(distrito_id):
    try:
        supabase.rpc("delete_distrito_func", {"p_id": distrito_id}).execute()
        return True
    except Exception as e:
        st.error(f"Error al eliminar: {e}")
        return False

def logout_user():
    supabase.auth.sign_out()
    st.session_state['logged_in'] = False
    st.session_state['user_role'] = None
    st.session_state['user_info'] = {}
    st.session_state['access_token'] = None
    st.session_state['refresh_token'] = None
    st.session_state['current_view'] = 'dashboard'
    st.rerun()

# --- 5. VISTAS ---

def view_login():
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        try:
            st.image("assets/Logo Distrito 0.jpg", width=140)
        except:
            st.title("DISTRITO 0")
        st.markdown("<h3>Acceso a Plataforma</h3>", unsafe_allow_html=True)
        st.markdown("<p style='color: #666;'>Ingresa tus credenciales</p>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            email = st.text_input("Correo", placeholder="usuario@distrito0.cl")
            password = st.text_input("Contraseña", type="password")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("INGRESAR"):
                login_user(email, password)
        st.markdown('</div>', unsafe_allow_html=True)

def view_admin_users():
    if st.session_state.get('user_role') != 'super_admin':
        st.error("Acceso no autorizado.")
        return

    with st.sidebar:
        try: st.image("assets/Pin Do Logo.jpg", width=70)
        except: st.write("📍")
        if st.button("← Volver al Dashboard"):
            st.session_state['current_view'] = 'dashboard'
            st.rerun()
        st.divider()
        if st.button("Cerrar Sesión"): logout_user()

    st.title("Administración de Usuarios")
    
    # Obtener lista de distritos para el multiselect
    distritos_resp = supabase.table('distritos').select("id, nombre").execute()
    distritos_map = {d['nombre']: d['id'] for d in distritos_resp.data}
    id_to_name = {v: k for k, v in distritos_map.items()}
    
    tab_create, tab_edit = st.tabs(["➕ Crear Usuario", "✏️ Editar Usuarios"])
    
    with tab_create:
        st.markdown("Crea nuevos usuarios y asígnales distritos específicos.")
        with st.form("create_user_form"):
            c1, c2 = st.columns(2)
            new_email = c1.text_input("Correo Electrónico")
            new_pass = c2.text_input("Contraseña", type="password")
            new_name = st.text_input("Nombre Completo")
            
            c3, c4 = st.columns(2)
            new_role = c3.selectbox("Rol", ["franchisee_admin", "franchisee_editor", "franchisee_viewer", "super_admin"])
            selected_districts = c4.multiselect("Asignar Distritos", list(distritos_map.keys()))
            
            if st.form_submit_button("Crear Usuario"):
                if not new_email or not new_pass or not new_name:
                    st.error("Todos los campos son obligatorios.")
                else:
                    district_ids = [distritos_map[name] for name in selected_districts]
                    success, msg = create_new_user(new_email, new_pass, new_name, new_role, district_ids)
                    if success: st.success(msg)
                    else: st.error(msg)

    with tab_edit:
        st.markdown("Edita la información y permisos de usuarios existentes.")
        # Obtener usuarios
        users_resp = supabase.table('user_profiles').select("*").order('created_at', desc=True).execute()
        users = users_resp.data
        
        if not users:
            st.info("No hay usuarios registrados.")
        else:
            user_options = {f"{u['full_name']} ({u['email']})": u['id'] for u in users}
            sel_user_label = st.selectbox("Seleccionar Usuario", [""] + list(user_options.keys()))
            
            if sel_user_label:
                uid = user_options[sel_user_label]
                u_data = next((u for u in users if u['id'] == uid), None)
                
                if u_data:
                    with st.form("edit_user_form"):
                        ec1, ec2 = st.columns(2)
                        # Nota: Editar el email aquí solo actualiza el perfil, no el login de Supabase Auth (requiere service role)
                        e_email = ec1.text_input("Correo (Perfil)", value=u_data.get('email', ''))
                        e_name = ec2.text_input("Nombre Completo", value=u_data.get('full_name', ''))
                        
                        ec3, ec4 = st.columns(2)
                        roles = ["franchisee_admin", "franchisee_editor", "franchisee_viewer", "super_admin"]
                        curr_role = u_data.get('role')
                        e_role = ec3.selectbox("Rol", roles, index=roles.index(curr_role) if curr_role in roles else 0)
                        
                        # Pre-seleccionar distritos actuales
                        curr_dist_ids = u_data.get('assigned_districts') or []
                        default_dists = [id_to_name[did] for did in curr_dist_ids if did in id_to_name]
                        e_dists = ec4.multiselect("Distritos Asignados", list(distritos_map.keys()), default=default_dists)
                        
                        if st.form_submit_button("Actualizar Datos"):
                            new_d_ids = [distritos_map[name] for name in e_dists]
                            ok, msg = update_user(uid, e_email, e_name, e_role, new_d_ids)
                            if ok: 
                                st.success(msg)
                                time.sleep(1)
                                st.rerun()
                            else: st.error(msg)

def view_dashboard():
    with st.sidebar:
        try: st.image("assets/Pin Do Logo.jpg", width=70)
        except: st.write("📍")
        user = st.session_state['user_info']
        st.write(f"**{user.get('full_name', 'Usuario')}**")
        st.caption(user.get('email'))
        
        role_map = {'super_admin': '👑 Super Admin', 'franchisee_admin': '🏢 Admin', 
                    'franchisee_editor': '✏️ Editor', 'franchisee_viewer': '👀 Visita'}
        label = role_map.get(st.session_state['user_role'], 'Usuario')
        st.markdown(f"<div class='role-badge'>{label}</div>", unsafe_allow_html=True)
        
        # Botón para Super Admin
        if st.session_state['user_role'] == 'super_admin':
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("👥 Administrar Usuarios"):
                st.session_state['current_view'] = 'admin_users'
                st.rerun()
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🏠 Propiedades"):
            st.session_state['current_view'] = 'properties'
            st.rerun()

        st.divider()
        if st.button("Cerrar Sesión"): logout_user()

    st.title("Bienvenido a Distrito 0")
    st.divider()
    role = st.session_state['user_role']
    # Obtener todos los distritos
    response = supabase.table('distritos').select("*").execute()
    all_distritos = response.data
    
    # Filtrar distritos según el rol y asignación
    if role == 'super_admin':
        distritos_data = all_distritos
    else:
        assigned_ids = st.session_state['user_info'].get('assigned_districts', [])
        if assigned_ids:
            distritos_data = [d for d in all_distritos if d['id'] in assigned_ids]
        else:
            distritos_data = []

    # Obtener propiedades asociadas a los distritos visibles para mostrarlas en el mapa
    props_data = []
    if distritos_data:
        visible_ids = [d['id'] for d in distritos_data]
        try:
            # Consultar propiedades con datos básicos y satélites para el popup
            q_props = """
                id, lat, lon, direccion, distrito_id,
                propiedades_backoffice(tipo_propiedad),
                propiedades_portal(precio_publicacion)
            """
            response_props = supabase.table('propiedades').select(q_props).in_('distrito_id', visible_ids).execute()
            props_data = response_props.data
        except Exception as e:
            print(f"Error cargando propiedades en mapa: {e}")

    # Definir pestañas disponibles según permisos
    tabs = ["🗺️ Visualizar"]
    if role == 'super_admin': tabs.append("➕ Crear")
    if role in ['super_admin', 'franchisee_admin', 'franchisee_editor']: tabs.append("✏️ Editar")
    current_tabs = st.tabs(tabs)

    # --- VISUALIZAR (MAPA) ---
    with current_tabs[0]:
            st.header("Mapa de Distritos")
            if not distritos_data:
                st.info("No hay distritos.")
                m = folium.Map(location=[-33.4372, -70.6342], zoom_start=11)
                st_folium(m, width='100%', height=500)
            else:
                df = pd.DataFrame(distritos_data)
                try: 
                    clat, clon = df['lat'].mean(), df['lon'].mean()
                except: 
                    clat, clon = -33.4372, -70.6342
                
                m = folium.Map(location=[clat, clon], zoom_start=12, tiles=None)
                folium.TileLayer(tiles='OpenStreetMap', name='Calles').add_to(m)
                folium.TileLayer(tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', attr='Google', name='Híbrido').add_to(m)

                for _, row in df.iterrows():
                    # Marcador Principal (El pin morado)
                    html = f"<b>{row['nombre']}</b><br><small>{row['direccion']}</small>"
                    if row.get('foto_url'): html += f"<br><img src='{row['foto_url']}' style='width:100%'>"
                    folium.Marker([row['lat'], row['lon']], popup=html, tooltip=row['nombre'], 
                                  icon=folium.Icon(color='purple', icon='info-sign')).add_to(m)

                    # Polígonos (Filtrando el punto central)
                    colors = {'5': '#4CAF50', '10': '#FFC107', '15': '#FF9800', '20': '#F44336'}
                    iso_cfg = row.get('isocronas_config') or []
                    
                    for mins in ['20', '15', '10', '5']:
                        url = row.get(f"poligono_url_{mins}")
                        if url and (f"{mins} min" in iso_cfg):
                            try:
                                r = requests.get(url)
                                if r.status_code == 200:
                                    geo_data = r.json()
                                    
                                    # --- FILTRO MÁGICO: ELIMINAR PUNTOS CENTRALES ---
                                    # Si el GeoJSON tiene 'features', filtramos para dejar solo Polígonos
                                    if 'features' in geo_data:
                                        filtered_feats = [f for f in geo_data['features'] if f['geometry']['type'] != 'Point']
                                        geo_data['features'] = filtered_feats
                                    # ------------------------------------------------

                                    folium.GeoJson(
                                        geo_data,
                                        name=f"{row['nombre']} ({mins}m)",
                                        style_function=lambda x, c=colors[mins]: {'fillColor': c, 'color': c, 'weight': 1, 'fillOpacity': 0.3}
                                    ).add_to(m)
                            except: pass
                
                # --- NUEVO: Marcadores de Propiedades ---
                for p in props_data:
                    if p.get('lat') and p.get('lon'):
                        # Preparar datos para el popup
                        tipo = "Propiedad"
                        precio_str = ""
                        
                        # Extraer tipo de propiedad (Backoffice)
                        if p.get('propiedades_backoffice'):
                            bo = p['propiedades_backoffice']
                            # Manejo robusto por si Supabase devuelve lista o dict
                            if isinstance(bo, list) and bo: bo = bo[0]
                            if isinstance(bo, dict): tipo = bo.get('tipo_propiedad') or "Propiedad"
                            
                        # Extraer precio (Portal)
                        if p.get('propiedades_portal'):
                            portal = p['propiedades_portal']
                            if isinstance(portal, list) and portal: portal = portal[0]
                            if isinstance(portal, dict):
                                val = portal.get('precio_publicacion')
                                if val: precio_str = f"<br>UF {val:,.0f}"
                        
                        html_prop = f"<b>{tipo}</b><br>{p.get('direccion', 'Sin dirección')}{precio_str}"
                        
                        folium.Marker(
                            [p['lat'], p['lon']],
                            popup=html_prop,
                            tooltip=tipo,
                            icon=folium.Icon(color='blue', icon='home')
                        ).add_to(m)
                
                folium.LayerControl().add_to(m)
                st_folium(m, width='100%', height=600, returned_objects=[])
                st.dataframe(df[['nombre', 'comuna', 'region']], use_container_width=True, hide_index=True)

    # --- CREAR (Solo Super Admin) ---
    if role == 'super_admin':
        with current_tabs[1]:
            st.header("Crear Distrito")
            with st.form("crear"):
                nombre = st.text_input("Nombre")
                direccion = st.text_input("Dirección")
                c1, c2 = st.columns(2)
                comuna = c1.text_input("Comuna")
                region = c2.text_input("Región")
                lat = c1.number_input("Latitud", format="%.6f")
                lon = c2.number_input("Longitud", format="%.6f")
                
                opts = ["5 min", "10 min", "15 min", "20 min", "25 min", "30 min"]
                isos = st.multiselect("Isocronas Visibles", opts, default=["5 min", "10 min", "15 min"])
                foto = st.file_uploader("Foto", type=['jpg','png','jpeg'])
                
                st.markdown("##### Archivos GeoJSON")
                cc1, cc2 = st.columns(2)
                p5 = cc1.file_uploader("5 min", key="p5")
                p10 = cc2.file_uploader("10 min", key="p10")
                p15 = cc1.file_uploader("15 min", key="p15")
                p20 = cc2.file_uploader("20 min", key="p20")

                if st.form_submit_button("Crear"):
                    if create_distrito(nombre, direccion, comuna, region, lat, lon, isos, foto, p5, p10, p15, p20):
                        st.success("Creado!"); time.sleep(1); st.rerun()

    # --- EDITAR (Super Admin y Editores) ---
    if role in ['super_admin', 'franchisee_admin', 'franchisee_editor']:
        edit_tab_index = 2 if role == 'super_admin' else 1
        with current_tabs[edit_tab_index]:
            st.header("Editar")
            if not distritos_data: st.info("Nada para editar")
            else:
                d_map = {d['nombre']: d for d in distritos_data}
                sel = st.selectbox("Elegir Distrito", list(d_map.keys()))
                d = d_map[sel]
                with st.form("editar"):
                        enom = st.text_input("Nombre", d['nombre'])
                        edir = st.text_input("Dirección", d['direccion'])
                        k1, k2 = st.columns(2)
                        ecom = k1.text_input("Comuna", d['comuna'])
                        elat = k1.number_input("Lat", d['lat'], format="%.6f")
                        ereg = k2.text_input("Región", d['region'])
                        elon = k2.number_input("Lon", d['lon'], format="%.6f")
                        eiso = st.multiselect("Isocronas", opts, default=d['isocronas_config'] or [])
                        
                        st.write("📸 Foto Actual"); 
                        if d['foto_url']: st.image(d['foto_url'], width=150)
                        efoto = st.file_uploader("Nueva Foto")

                        st.write("🗺️ Polígonos")
                        kk1, kk2 = st.columns(2)
                        ep5 = kk1.file_uploader(f"5 min {'✅' if d.get('poligono_url_5') else ''}", key="ep5")
                        ep10 = kk2.file_uploader(f"10 min {'✅' if d.get('poligono_url_10') else ''}", key="ep10")
                        ep15 = kk1.file_uploader(f"15 min {'✅' if d.get('poligono_url_15') else ''}", key="ep15")
                        ep20 = kk2.file_uploader(f"20 min {'✅' if d.get('poligono_url_20') else ''}", key="ep20")

                        if st.form_submit_button("Guardar"):
                            curr_p = {k: d.get(f'poligono_url_{k}') for k in ["5","10","15","20"]}
                            if update_distrito(d['id'], enom, edir, ecom, ereg, elat, elon, eiso, efoto, ep5, ep10, ep15, ep20, d['foto_url'], curr_p):
                                st.success("Actualizado!"); time.sleep(1); st.rerun()
                    
                if st.button("Eliminar Distrito", type="primary"):
                    if delete_distrito(d['id']): st.success("Eliminado"); time.sleep(1); st.rerun()

if st.session_state['logged_in']: 
    if st.session_state.get('current_view') == 'admin_users':
        view_admin_users()
    elif st.session_state.get('current_view') == 'properties':
        properties.render_properties_view(supabase)
    else:
        view_dashboard()
else: view_login()