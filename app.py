import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date, time
import firebase_admin
from firebase_admin import credentials, firestore
from typing import List, Dict, Any, Optional
import requests
from urllib.parse import urlparse
import json
import math
import pydeck as pdk
import unicodedata
from PIL import Image, ImageDraw, ImageFont
import io
import base64
from collections import Counter
import os

# Constants
FREE_LIMIT = 10  # Free sample records
CREDIT_PACK = 5000  # Records per $150 pack
SHOW_MAP = False

# Predefined user credentials
CREDENTIALS = {
    "admin@iqvia.com": {
        "password": "admin",
        "uid": "dummy_admin_uid",
        "name": "Admin User",
        "company": "IQVIA"
    }
}

# Page config
st.set_page_config(
    page_title="Prescription Data Dashboard",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Backblaze B2 credentials
B2_KEY_ID = "003d7a703a866650000000002"
B2_APP_KEY = "K003vbdISgXEt2B9ZZmJ4nkSV8Rrxxc"

# CSS styling
st.markdown("""
<style>
    :root {
        --panel: #ffffff;
        --muted: #6c757d;
        --text: #212529;
        --primary: #0d6efd;
        --primary-600: #0b5ed7;
        --accent: #198754;
        --border: #dee2e6;
        --bg: #f8f9fa;
        --background-color: #f8f9fa;
        --secondary-background-color: #ffffff;
        --text-color: #212529;
        --primary-color: #0d6efd;
    }
    html { font-size: 150%; }
    
    /* Fix for expander headers - ensure proper contrast */
    .streamlit-expanderHeader {
        color: var(--text) !important;
        background-color: #f0f2f6 !important;
        border: 1px solid var(--border) !important;
        border-radius: 4px !important;
        padding: 12px 16px !important;
        font-weight: 600 !important;
        margin-bottom: 8px !important;
    }
    
    .streamlit-expanderHeader:hover {
        background-color: #e6eaf0 !important;
    }
    
    [data-testid="stExpander"] summary { 
        color: var(--text) !important; 
        background-color: #f0f2f6 !important;
    }
    
    [data-testid="stExpander"] summary svg { 
        fill: var(--text) !important; 
    }
    
    [data-testid="stAppViewContainer"] { background: var(--bg); color: var(--text); }
    [data-testid="stHeader"] { background: var(--panel); color: var(--text); border-bottom: 1px solid var(--border); }
    section[data-testid="stSidebar"] { background: var(--panel) !important; color: var(--text) !important; border-right: 1px solid var(--border); }
    section[data-testid="stSidebar"] .stMarkdown, section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] label { color: var(--text) !important; }
    .stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4, .stMarkdown h5, .stMarkdown h6, p, label { color: var(--text) !important; }
    .stTextInput input, .stPassword input, .stDateInput input, .stNumberInput input { background: var(--panel) !important; color: var(--text) !important; border: 1px solid var(--border) !important; }
    .stTextInput label, .stPassword label, .stDateInput label, .stNumberInput label { color: var(--muted) !important; }
    input::placeholder { color: var(--muted) !important; }
    .stButton>button { background: var(--primary); color: #ffffff; border: 1px solid var(--primary-600); border-radius: 8px; padding: 0.5rem 1rem; font-weight: 600; }
    .stButton>button:hover { background: var(--primary-600); border-color: var(--primary-600); }
    div[role="tablist"] button[role="tab"] { color: var(--muted); border-bottom: 2px solid transparent; }
    div[role="tablist"] button[aria-selected="true"] { color: var(--text); border-bottom-color: var(--primary); }
    div[data-testid="metric-container"] { background: #ffffff; border: 1px solid var(--border); border-radius: 10px; padding: 12px; }
    div[data-testid="metric-container"] * { color: var(--text) !important; }
    .quota-progress { height: 8px; background: var(--primary); border-radius: 4px; margin-top: 8px; }
    .record-nav { display: flex; align-items: center; gap: 12px; margin: 8px 0 4px 0; }
    .pill { display: inline-block; padding: 4px 12px; border: 1px solid var(--border); border-radius: 999px; color: var(--text); font-size: 14px; margin-right: 6px; }
    
    .streamlit-expanderContent { color: var(--text) !important; }
    
    /* Ensure proper contrast for all text elements */
    .stAlert, .stException, .stSuccess, .stWarning, .stInfo, .stError {
        color: var(--text) !important;
    }
    
    /* Fix for dataframes */
    .dataframe { color: var(--text) !important; }
    .dataframe th { color: var(--text) !important; }
    .dataframe td { color: var(--text) !important; }
    
    /* Fix for selectbox and other dropdowns */
    .stSelectbox label, .stMultiselect label { color: var(--text) !important; }
    
    /* Fix for checkbox labels */
    .stCheckbox label { color: var(--text) !important; }
    
    /* Fix for radio button labels */
    .stRadio label { color: var(--text) !important; }
    
    /* Fix for slider labels */
    .stSlider label { color: var(--text) !important; }
    
    /* Fix for caption text */
    .stCaption { color: var(--muted) !important; }
    
    /* Fix for download button text color */
    .stDownloadButton button {
        color: #ffffff !important;
        background-color: var(--primary) !important;
    }
    
    /* Fix for metric numbers - ensure they're visible */
    div[data-testid="stMetricValue"] {
        color: var(--text) !important;
    }
    
    /* Fix for dropdown menus */
    .stSelectbox div[data-baseweb="select"] > div {
        color: var(--text) !important;
        background-color: var(--panel) !important;
    }
    
    /* Fix for form submit button */
    .stFormSubmitButton button {
        background-color: var(--primary) !important;
        color: #ffffff !important;
    }
    
    /* Fix for number input in pagination */
    .stNumberInput input {
        color: var(--text) !important;
    }
    
    /* Fix for dropdown options */
    .stSelectbox [role="listbox"] {
        background-color: var(--panel) !important;
        color: var(--text) !important;
    }
    
    .stSelectbox [role="option"] {
        color: var(--text) !important;
        background-color: var(--panel) !important;
    }
    
    .stSelectbox [role="option"]:hover {
        background-color: #e9ecef !important;
    }
    
    /* Fix for dividers */
    .stDivider {
        border-color: var(--border) !important;
    }
    
    /* Fix for expander dropdown arrows */
    .streamlit-expanderHeader svg {
        fill: var(--text) !important;
    }
    
    /* Fix for all dropdown text */
    [data-baseweb="select"] div {
        color: var(--text) !important;
    }
    
    /* Fix for dropdown placeholder text */
    [data-baseweb="select"] div[aria-activedescendant] {
        color: var(--text) !important;
    }
    
    /* Fix for date input width */
    .stDateInput input {
        min-width: 140px !important;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource(show_spinner=False)
def get_firestore_client():
    if not firebase_admin._apps:
        # Check if running locally by looking for a JSON credentials file
        json_path = "login-f29f0-firebase-adminsdk-eoqgr-23461e0aac.json"
        if os.path.exists(json_path):
            # Load credentials from JSON file for local environment
            cred = credentials.Certificate(json_path)
        else:
            # Use Streamlit secrets for deployed environment
            firebase_config = dict(st.secrets["firebase"])
            firebase_config["private_key"] = firebase_config["private_key"].replace("\\n", "\n")
            cred = credentials.Certificate(firebase_config)
        # Initialize Firebase app
        firebase_admin.initialize_app(cred)
    return firestore.client()

@st.cache_resource(show_spinner=False)
def get_b2_authorization() -> Dict[str, str]:
    auth_url = "https://api.backblazeb2.com/b2api/v2/b2_authorize_account"
    resp = requests.get(auth_url, auth=(B2_KEY_ID, B2_APP_KEY), timeout=20)
    resp.raise_for_status()
    data = resp.json()
    return {"authorizationToken": data["authorizationToken"], "downloadUrl": data["downloadUrl"]}

@st.cache_data(show_spinner=False, ttl=3600)
def get_governorate(lat: float, lon: float) -> str:
    addr = reverse_geocode(lat, lon)
    if addr:
        a = addr.get('address', {})
        gov = a.get('state') or a.get('province') or a.get('county') or 'Unknown'
        return gov
    return 'Unknown'

def fetch_b2_file_bytes(file_url: str) -> Optional[bytes]:
    if not file_url:
        return None
    try:
        auth = get_b2_authorization()
        token = auth["authorizationToken"]
        download_base = auth["downloadUrl"].rstrip('/')
        r = requests.get(file_url, headers={"Authorization": token}, timeout=30)
        if r.status_code == 200:
            return r.content
        parsed = urlparse(file_url)
        parts = parsed.path.split('/file/', 1)
        if len(parts) == 2:
            tail = parts[1].lstrip('/')
            rebuilt = f"{download_base}/file/{tail}"
            r2 = requests.get(rebuilt, headers={"Authorization": token}, timeout=30)
            if r2.status_code == 200:
                return r2.content
    except Exception:
        return None
    return None

def _to_english_ascii(text: Optional[str]) -> Optional[str]:
    if not isinstance(text, str):
        return text
    try:
        ascii_text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii').strip()
        return ascii_text if ascii_text else text
    except Exception:
        return text

def _to_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)) and value > 10_000_000_000:
        try:
            return datetime.fromtimestamp(value / 1000.0)
        except Exception:
            pass
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except Exception:
            pass
    return None

def _haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def _extract_confirmed_drug_names(source: Any) -> Optional[List[str]]:
    if not isinstance(source, dict):
        return None
    candidate_keys = ['confirmedDrugs', 'confirmed_drugs']
    name_keys = ['name', 'drugName', 'medicine', 'brand', 'generic', 'product', 'text', 'item']
    def normalize_entry(entry: Any) -> Optional[str]:
        if entry is None:
            return None
        if isinstance(entry, str):
            return entry.strip()
        if isinstance(entry, dict):
            for nk in name_keys:
                val = entry.get(nk)
                if isinstance(val, str) and val.strip():
                    return val.strip()
        return None
    for k in candidate_keys:
        val = source.get(k)
        if isinstance(val, list) and val:
            names: List[str] = []
            for item in val:
                nm = normalize_entry(item)
                if nm:
                    names.append(nm)
            if names:
                seen = set()
                unique: List[str] = []
                for n in names:
                    key = n.lower().strip()
                    if key not in seen:
                        seen.add(key)
                        unique.append(n)
                return unique
        elif isinstance(val, dict):
            nm = normalize_entry(val)
            if nm:
                return [nm]
    for outer_key in ['ocr', 'extraction', 'result', 'payload', 'data']:
        obj = source.get(outer_key)
        if isinstance(obj, dict):
            inner = _extract_confirmed_drug_names(obj)
            if inner:
                return inner
    return None

def draw_ocr_visualization(image_bytes: bytes, ocr_data: Dict[str, Any]) -> bytes:
    try:
        img = Image.open(io.BytesIO(image_bytes))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 28)
            small_font = ImageFont.truetype("arial.ttf", 24)
        except:
            font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        colors = {
            'word': '#FF6B6B',
            'block': '#4ECDC4',
            'paragraph': '#45B7D1',
            'line': '#96CEB4'
        }
        text_annotations = ocr_data.get('textAnnotations', [])
        if text_annotations:
            for i, annotation in enumerate(text_annotations[1:], 1):
                bounding_poly = annotation.get('boundingPoly', {})
                vertices = bounding_poly.get('vertices', [])
                description = annotation.get('description', '')
                if len(vertices) >= 4:
                    points = [(v.get('x', 0), v.get('y', 0)) for v in vertices]
                    draw.polygon(points, outline=colors['word'], width=2)
                    if description and len(points) > 0:
                        x, y = points[0]
                        draw.text((x, y-40), description, fill=colors['word'], font=small_font)
        full_text = ocr_data.get('fullTextAnnotation', {})
        pages = full_text.get('pages', [])
        for page in pages:
            blocks = page.get('blocks', [])
            for block in blocks:
                block_bbox = block.get('boundingBox', {})
                block_vertices = block_bbox.get('vertices', [])
                if len(block_vertices) >= 4:
                    block_points = [(v.get('x', 0), v.get('y', 0)) for v in block_vertices]
                    draw.polygon(block_points, outline=colors['block'], width=3)
                paragraphs = block.get('paragraphs', [])
                for paragraph in paragraphs:
                    para_bbox = paragraph.get('boundingBox', {})
                    para_vertices = para_bbox.get('vertices', [])
                    if len(para_vertices) >= 4:
                        para_points = [(v.get('x', 0), v.get('y', 0)) for v in para_vertices]
                        draw.polygon(para_points, outline=colors['paragraph'], width=2)
                    words = paragraph.get('words', [])
                    for word in words:
                        word_bbox = word.get('boundingBox', {})
                        word_vertices = word_bbox.get('vertices', [])
                        if len(word_vertices) >= 4:
                            word_points = [(v.get('x', 0), v.get('y', 0)) for v in word_vertices]
                            draw.polygon(word_points, outline=colors['line'], width=1)
        legend_y = 10
        legend_x = img.width - 200
        draw.rectangle([legend_x-10, legend_y-5, img.width-10, legend_y+100], fill='white', outline='black')
        draw.text((legend_x, legend_y), "OCR Annotations:", fill='black', font=font)
        draw.text((legend_x, legend_y+20), "■ Words", fill=colors['word'], font=small_font)
        draw.text((legend_x, legend_y+35), "■ Lines", fill=colors['line'], font=small_font)
        draw.text((legend_x, legend_y+50), "■ Paragraphs", fill=colors['paragraph'], font=small_font)
        draw.text((legend_x, legend_y+65), "■ Blocks", fill=colors['block'], font=small_font)
        output_buffer = io.BytesIO()
        img.save(output_buffer, format='PNG')
        return output_buffer.getvalue()
    except Exception as e:
        st.error(f"Error creating OCR visualization: {str(e)}")
        return image_bytes

def extract_text_from_ocr(ocr_data: Dict[str, Any]) -> Dict[str, Any]:
    result = {
        'full_text': '',
        'detected_languages': [],
        'text_blocks': [],
        'word_count': 0,
        'confidence_scores': []
    }
    try:
        full_text_annotation = ocr_data.get('fullTextAnnotation', {})
        result['full_text'] = full_text_annotation.get('text', '')
        pages = full_text_annotation.get('pages', [])
        if pages:
            page_properties = pages[0].get('property', {})
            detected_languages = page_properties.get('detectedLanguages', [])
            result['detected_languages'] = [
                {
                    'language': lang.get('languageCode', 'unknown'),
                    'confidence': lang.get('confidence', 0)
                }
                for lang in detected_languages
            ]
        text_annotations = ocr_data.get('textAnnotations', [])
        if text_annotations and len(text_annotations) > 1:
            for annotation in text_annotations[1:]:
                description = annotation.get('description', '')
                bounding_poly = annotation.get('boundingPoly', {})
                vertices = bounding_poly.get('vertices', [])
                if description.strip():
                    result['text_blocks'].append({
                        'text': description,
                        'bounding_box': vertices
                    })
                    result['word_count'] += len(description.split())
        if not result['text_blocks']:
            for page in pages:
                blocks = page.get('blocks', [])
                for block in blocks:
                    paragraphs = block.get('paragraphs', [])
                    for paragraph in paragraphs:
                        words = paragraph.get('words', [])
                        paragraph_text = ''
                        for word in words:
                            symbols = word.get('symbols', [])
                            word_text = ''.join([symbol.get('text', '') for symbol in symbols])
                            paragraph_text += word_text
                            if symbols:
                                last_symbol = symbols[-1]
                                detected_break = last_symbol.get('property', {}).get('detectedBreak', {})
                                break_type = detected_break.get('type', '')
                                if break_type in ['SPACE', 'EOL_SURE_SPACE']:
                                    paragraph_text += ' '
                                elif break_type in ['LINE_BREAK', 'EOL_SURE_SPACE']:
                                    paragraph_text += '\n'
                        if paragraph_text.strip():
                            result['text_blocks'].append({
                                'text': paragraph_text.strip(),
                                'bounding_box': paragraph.get('boundingBox', {}).get('vertices', [])
                            })
                            result['word_count'] += len(paragraph_text.split())
    except Exception as e:
        st.error(f"Error extracting text from OCR: {str(e)}")
    return result

@st.cache_data(show_spinner=False, ttl=3600)
def reverse_geocode(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    try:
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            "lat": lat,
            "lon": lon,
            "format": "jsonv2",
            "addressdetails": 1,
            "accept-language": "en",
        }
        headers = {
            "User-Agent": "health-data-dashboard/1.0 (contact: admin@company.com)"
        }
        r = requests.get(url, params=params, headers=headers, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

@st.cache_data(show_spinner=False, ttl=3600)
def find_nearest_pharmacy(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    headers = {
        "User-Agent": "health-data-dashboard/1.0 (contact: admin@company.com)",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }
    for radius in (10, 30, 500, 1000, 2000, 3000, 4000, 5000):
        try:
            query = f"""
            [out:json][timeout:25];
            (nwr["amenity"="pharmacy"](around:{radius},{lat},{lon}););
            out center tags qt 50;
            """
            r = requests.post(
                "https://overpass-api.de/api/interpreter",
                data=query,
                headers=headers,
                timeout=30,
            )
            if r.status_code != 200:
                continue
            data = r.json()
            elements = data.get("elements", [])
            best = None
            for el in elements:
                el_lat = el.get("lat") or (el.get("center") or {}).get("lat")
                el_lon = el.get("lon") or (el.get("center") or {}).get("lon")
                if el_lat is None or el_lon is None:
                    continue
                dist = _haversine_distance_m(lat, lon, float(el_lat), float(el_lon))
                if best is None or dist < best[0]:
                    tags = el.get("tags") or {}
                    raw_name = tags.get("name:en") or tags.get("alt_name:en") or tags.get("int_name") or tags.get("name") or "Pharmacy"
                    display_name = _to_english_ascii(raw_name)
                    best = (
                        dist,
                        {
                            "name": display_name or "Pharmacy",
                            "lat": float(el_lat),
                            "lon": float(el_lon),
                            "tags": tags,
                            "id": el.get("id"),
                        },
                    )
            if best is not None:
                best[1]["distance_m"] = round(best[0], 1)
                return best[1]
        except Exception:
            continue
    return None

@st.cache_data(show_spinner=True, ttl=60)
def fetch_prescriptions(start_date: Optional[date], end_date: Optional[date]) -> List[Dict[str, Any]]:
    db = get_firestore_client()
    col = db.collection('updated_data_sample')
    query = col
    apply_range = False
    if start_date is not None:
        apply_range = True
        start_dt = datetime.combine(start_date, time.min)
        query = query.where('timestamp', '>=', start_dt.timestamp() * 1000)
    if end_date is not None:
        apply_range = True
        end_dt = datetime.combine(end_date, time.max)
        query = query.where('timestamp', '<=', end_dt.timestamp() * 1000)
    try:
        if apply_range:
            query = query.order_by('timestamp', direction=firestore.Query.DESCENDING)
        else:
            query = query.order_by('timestamp', direction=firestore.Query.DESCENDING)
    except Exception:
        pass
    docs = list(query.limit(1000).stream())
    records: List[Dict[str, Any]] = []
    for d in docs:
        data = d.to_dict() or {}
        timestamp = _to_datetime(data.get('timestamp')) or _to_datetime(data.get('createdAt')) or _to_datetime(data.get('location', {}).get('capturedAt'))
        loc_map = data.get('location') or {}
        textual_location = data.get('textualLocation') or loc_map.get('textualLocation')
        latitude = loc_map.get('latitude')
        longitude = loc_map.get('longitude')
        record = {
            'Timestamp': timestamp.isoformat() if timestamp else None,
            'Date': timestamp.date().isoformat() if isinstance(timestamp, datetime) else None,
            'Location': textual_location or '',
            'Image URL': data.get('imageUrl') or '',
            'User Full Name': data.get('username') or '',
            'Pharmacy Name': data.get('pharmacy_name') or '',
            'Latitude': latitude,
            'Longitude': longitude,
            'Location JSON URL': data.get('locationJsonUrl') or '',
            'Confirmed Drugs': _extract_confirmed_drug_names(data) or [],
            'Raw': data,
        }
        records.append(record)
    return records
# Session State
if 'user' not in st.session_state:
    st.session_state.user = None
if 'records_viewed' not in st.session_state:
    st.session_state.records_viewed = 5
if 'is_free_sample' not in st.session_state:
    st.session_state.is_free_sample = True
if 'credits' not in st.session_state:
    st.session_state.credits = 0
if 'active_record' not in st.session_state:
    st.session_state.active_record = 1
if 'show_map' not in st.session_state:
    st.session_state.show_map = False
if 'compact_view' not in st.session_state:
    st.session_state.compact_view = False
if 'list_mode' not in st.session_state:
    st.session_state.list_mode = True
if 'show_ocr_visualization' not in st.session_state:
    st.session_state.show_ocr_visualization = True
if 'records_per_page' not in st.session_state:
    st.session_state.records_per_page = 30
if 'active_page' not in st.session_state:
    st.session_state.active_page = 1

# Login Function
def show_login():
    with st.container():
        st.subheader("🔐 Login")
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login", key="login_btn"):
            user_info = CREDENTIALS.get(email)
            if user_info and password == user_info['password']:
                st.session_state.user = {
                    'email': email,
                    'uid': user_info['uid'],
                    'name': user_info['name'],
                    'company': user_info['company']
                }
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Invalid credentials.")

# Signup Function
def show_signup():
    with st.container():
        st.subheader("📝 Create Account")
        company_name = st.text_input("Company Name")
        email = st.text_input("Work Email")
        full_name = st.text_input("Full Name")
        password = st.text_input("Password", type="password")
        if st.button("Register", key="signup_btn"):
            st.success("Account request submitted!")

# Main App Logic
if st.session_state.user is None:
    st.title("Healthcare Data Analytics Platform")
    st.write("Advanced prescription data analysis for pharmaceutical companies")
    show_login()
else:
    st.title(f"Prescription Data Dashboard")
    st.caption(f"{st.session_state.user['company']} • {datetime.now().strftime('%B %d, %Y')}")
    with st.sidebar:
        st.subheader(f"👤 {st.session_state.user['name']}")
        st.write(f"**Company:** {st.session_state.user['company']}")
        st.write(f"**Email:** {st.session_state.user['email']}")
        st.divider()
        remaining = FREE_LIMIT - st.session_state.records_viewed if st.session_state.is_free_sample else st.session_state.credits - st.session_state.records_viewed
        st.subheader("📊 Data Quota")
        st.write(f"Records viewed: **{st.session_state.records_viewed}** / {FREE_LIMIT if st.session_state.is_free_sample else st.session_state.credits}")
        progress = st.session_state.records_viewed / FREE_LIMIT if st.session_state.is_free_sample else (st.session_state.records_viewed / st.session_state.credits if st.session_state.credits > 0 else 1)
        st.markdown(f"<div class='quota-progress' style='width: {progress*100}%'></div>", unsafe_allow_html=True)
        st.divider()
        st.subheader("🔍 Filters")
        with st.form("filters_form"):
            start_date = st.date_input("Start Date", value=st.session_state.get('filter_start', None), key="filter_start")
            end_date = st.date_input("End Date", value=st.session_state.get('filter_end', None), key="filter_end")
            location_filter = st.text_input("Location contains", value=st.session_state.get('filter_location', ''), key="filter_location")
            user_filter = st.text_input("User/Pharmacy contains", value=st.session_state.get('filter_user', ''), key="filter_user", help="Search by user name or pharmacy name")
            submitted = st.form_submit_button("Apply Filters")
            if submitted:
                st.rerun()
        st.divider()
        st.subheader("🎛️ View")
        st.session_state.show_map = st.checkbox("Show Map", value=st.session_state.get('show_map', False), help="Toggle inline map rendering (slower)")
        st.session_state.compact_view = st.checkbox("Compact View", value=st.session_state.get('compact_view', False), help="Smaller images and tighter spacing")
        st.session_state.show_ocr_visualization = st.checkbox("Show OCR Annotations", value=st.session_state.get('show_ocr_visualization', False), help="Display OCR bounding boxes and text annotations on images")
        st.session_state.list_mode = st.checkbox("List Mode (scroll)", value=st.session_state.get('list_mode', True), help="Scroll through multiple records per page with pagination")
        if st.session_state.list_mode:
            options = [5, 10, 20, 30, 50]
            default_val = st.session_state.get('records_per_page', 30)
            if default_val not in options:
                default_val = 30
            st.session_state.records_per_page = st.selectbox("Records per page", options=options, index=options.index(default_val))
        if st.button("Reset Filters"):
            for k in ['filter_start', 'filter_end', 'filter_location', 'filter_user']:
                if k in st.session_state:
                    del st.session_state[k]
            st.session_state.active_record = 1
            st.rerun()
        if st.button("Logout", type="primary"):
            st.session_state.user = None
            st.rerun()
    if remaining <= 0:
        st.error("Your data quota has been exhausted. Please purchase additional credits.")
        with st.expander("💳 Purchase Credits", expanded=True):
            st.write("Our standard credit package provides access to 5,000 prescription records for $150.")
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("Purchase 5,000 Credits ($150)"):
                    st.info("Redirecting to payment gateway...")
            with col2:
                if st.button("Contact Sales"):
                    st.info("Please email sales@healthdata.com")
            if st.button("Check Payment Status"):
                st.success("Payment processed! 5,000 credits added.")
                st.session_state.is_free_sample = False
                st.session_state.credits += CREDIT_PACK
                st.session_state.records_viewed = 0
                st.rerun()
    else:
        effective_start = st.session_state.get('filter_start', None)
        effective_end = st.session_state.get('filter_end', None)
        records = fetch_prescriptions(effective_start, effective_end)
        df = pd.DataFrame(records)
        if not df.empty:
            if st.session_state.get('filter_location'):
                df = df[df['Location'].fillna('').str.contains(st.session_state['filter_location'], case=False, na=False)]
            if st.session_state.get('filter_user'):
                user_filter_term = st.session_state['filter_user']
                user_mask = (
                    df['User Full Name'].fillna('').str.contains(user_filter_term, case=False, na=False) |
                    df['Pharmacy Name'].fillna('').str.contains(user_filter_term, case=False, na=False)
                )
                df = df[user_mask]
                # Fetch unfiltered data for statistics
        # stats_records = fetch_prescriptions(None, None)
        # stats_df = pd.DataFrame(stats_records)
        st.subheader("📊 Overview")
        col1, col2, col3 = st.columns([1, 1, 1])
        col1.metric("Total Prescriptions", len(df))
        col2.metric("Locations", len(df['Location'].dropna().unique()) if not df.empty else 0)
        col3.metric("Users", len(df['User Full Name'].dropna().unique()) if not df.empty else 0)
        st.divider()
        # Drug Statistics Section
        st.subheader("📊 Drug Statistics")
        # Drug Statistics Section
        with st.expander("📊 Drug Statistics", expanded=not st.session_state.compact_view):
            # Use df for statistics to apply filters
            if not df.empty:
                # Add Governorate column
                df['Governorate'] = df.apply(
                    lambda row: get_governorate(row['Latitude'], row['Longitude']) 
                    if pd.notnull(row['Latitude']) and pd.notnull(row['Longitude']) 
                    else 'Unknown', axis=1
                )
                
                # Most common drugs overall
                st.write("**Most Common Drugs Overall:**")
                all_drugs = [drug.lower() for drugs in df['Confirmed Drugs'] for drug in (drugs if drugs else [])]
                drug_counts = Counter(all_drugs)
                if drug_counts:
                    top_drugs = drug_counts.most_common(10)
                    top_drugs_df = pd.DataFrame(top_drugs, columns=['Drug', 'Count'])
                    fig = px.bar(
                        top_drugs_df,
                        x='Drug',
                        y='Count',
                        title="Top 10 Most Common Drugs",
                        color_discrete_sequence=['#3498db'],
                        labels={'Drug': 'Drug Name', 'Count': 'Number of Prescriptions'},
                    )
                    fig.update_layout(
                        plot_bgcolor='#ffffff',
                        paper_bgcolor='#ffffff',
                        font=dict(color='#000000'),
                        xaxis=dict(gridcolor='#d1d5db', zerolinecolor='#d1d5db', tickangle=45, tickfont=dict(color='#000000'), title_font=dict(color='#000000')),
                        yaxis=dict(gridcolor='#d1d5db', zerolinecolor='#d1d5db', tickfont=dict(color='#000000'), title_font=dict(color='#000000'), tickvals=list(range(0, int(top_drugs_df['Count'].max()) + 1, 1))),
                        title_font=dict(color='#000000'),
                        showlegend=False,
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.write("No drugs found.")
                
                # Most common drugs in each governorate
                st.write("**Most Common Drugs by Governorate:**")
                exploded_df = df.explode('Confirmed Drugs')
                exploded_df['Confirmed Drugs'] = exploded_df['Confirmed Drugs'].str.lower()
                gov_drug_counts = exploded_df.groupby('Governorate')['Confirmed Drugs'].value_counts().reset_index(name='Count')
                top_per_gov = gov_drug_counts[gov_drug_counts['Governorate'] != 'Unknown'].groupby('Governorate').head(5)
                
                if not top_per_gov.empty:
                    all_governorates = sorted(top_per_gov['Governorate'].unique())
                    # Initialize session state for governorate selections if not already set
                    if 'selected_governorates' not in st.session_state:
                        st.session_state.selected_governorates = all_governorates
                    
                    # Checkbox panel for governorates
                    st.write("**Select Governorates:**")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Select All"):
                            st.session_state.selected_governorates = all_governorates
                            st.rerun()
                    with col2:
                        if st.button("Deselect All"):
                            st.session_state.selected_governorates = []
                            st.rerun()
                    
                    # Display governorates in three columns
                    selected_governorates = []
                    num_cols = 3
                    cols = st.columns(num_cols)
                    for i, gov in enumerate(all_governorates):
                        col_idx = i % num_cols
                        with cols[col_idx]:
                            is_selected = st.checkbox(
                                gov,
                                value=gov in st.session_state.selected_governorates,
                                key=f"gov_{gov}"
                            )
                            if is_selected:
                                selected_governorates.append(gov)
                    # Update session state
                    st.session_state.selected_governorates = selected_governorates
                    
                    if selected_governorates:
                        for gov in selected_governorates:
                            st.write(f"#### {gov}")
                            gov_data = top_per_gov[top_per_gov['Governorate'] == gov][['Confirmed Drugs', 'Count']]
                            fig = px.bar(
                                gov_data,
                                x='Confirmed Drugs',
                                y='Count',
                                title=f"Top 5 Drugs in {gov}",
                                color_discrete_sequence=['#2ecc71'],
                                labels={'Confirmed Drugs': 'Drug Name', 'Count': 'Number of Prescriptions'},
                            )
                            fig.update_layout(
                                plot_bgcolor='#ffffff',
                                paper_bgcolor='#ffffff',
                                font=dict(color='#000000'),
                                xaxis=dict(gridcolor='#d1d5db', zerolinecolor='#d1d5db', tickangle=45, tickfont=dict(color='#000000'), title_font=dict(color='#000000')),
                                yaxis=dict(gridcolor='#d1d5db', zerolinecolor='#d1d5db', tickfont=dict(color='#000000'), title_font=dict(color='#000000'), tickvals=list(range(0, int(gov_data['Count'].max()) + 1, 1))),
                                title_font=dict(color='#000000'),
                                showlegend=False,
                            )
                            st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("Please select a governorate.")
                else:
                    st.write("No governorate data available.")
                
                # Most common drugs relative to date (top drug per date)
                st.write("**Most Common Drugs by Date:**")
                date_drug_counts = exploded_df.groupby('Date')['Confirmed Drugs'].value_counts().reset_index(name='Count')
                top_per_date = date_drug_counts.loc[date_drug_counts.groupby('Date')['Count'].idxmax()]
                if not top_per_date.empty:
                    top_per_date = top_per_date.sort_values('Date')
                    if len(top_per_date) > 5:
                        # Show first 5 by default
                        if 'show_more_dates' not in st.session_state:
                            st.session_state.show_more_dates = False
                        
                        display_df = top_per_date.head(5) if not st.session_state.show_more_dates else top_per_date
                        st.table(display_df[['Date', 'Confirmed Drugs', 'Count']])
                        
                        if st.button("Show More" if not st.session_state.show_more_dates else "Show Less"):
                            st.session_state.show_more_dates = not st.session_state.show_more_dates
                            st.rerun()
                    else:
                        st.table(top_per_date[['Date', 'Confirmed Drugs', 'Count']])
                else:
                    st.write("No date-specific drug data.")
                
                # Most common drug combinations
                st.write("**Most Common Drug Combinations:**")
                from itertools import combinations
                
                combo_counter = Counter()
                for drugs in df['Confirmed Drugs']:
                    if drugs:
                        lower_drugs = [d.lower() for d in drugs]
                        for size in range(2, 5):  # Combinations of 2, 3, or 4 drugs
                            for combo in combinations(sorted(lower_drugs), size):
                                combo_counter[', '.join(combo)] += 1
                
                if combo_counter:
                    top_combos = combo_counter.most_common(10)
                    combo_counts = pd.DataFrame(top_combos, columns=['Drug Combo', 'Count'])
                    fig = px.bar(
                        combo_counts,
                        x='Drug Combo',
                        y='Count',
                        title="Top 10 Drug Combinations",
                        color_discrete_sequence=['#e74c3c'],
                        labels={'Drug Combo': 'Drug Combination', 'Count': 'Number of Prescriptions'},
                    )
                    fig.update_layout(
                        plot_bgcolor='#ffffff',
                        paper_bgcolor='#ffffff',
                        font=dict(color='#000000'),
                        xaxis=dict(gridcolor='#d1d5db', zerolinecolor='#d1d5db', tickangle=45, tickfont=dict(color='#000000'), title_font=dict(color='#000000')),
                        yaxis=dict(gridcolor='#d1d5db', zerolinecolor='#d1d5db', tickfont=dict(color='#000000'), title_font=dict(color='#000000'), tickvals=list(range(0, int(combo_counts['Count'].max()) + 1, 1))),
                        title_font=dict(color='#000000'),
                        title_x=0.5,   # <-- centers the title
                        title_y=0.95,
                        showlegend=False,
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.write("No drug combinations found.")
            else:
                st.info("No data available for statistics.")
        st.subheader("📋 Prescription Records")
        if not df.empty:
            if st.session_state.list_mode:
                total = len(df)
                per_page = int(st.session_state.get('records_per_page', 10) or 10)
                if per_page <= 0:
                    per_page = 10
                total_pages = max(1, math.ceil(total / per_page))
                if st.session_state.active_page > total_pages:
                    st.session_state.active_page = 1
                nav_prev, nav_ctr, nav_next = st.columns([1, 2, 1])
                with nav_prev:
                    if st.button("◀ Prev Page", use_container_width=True):
                        st.session_state.active_page = max(1, st.session_state.active_page - 1)
                        st.rerun()
                with nav_ctr:
                    start_idx = (st.session_state.active_page - 1) * per_page
                    end_idx = min(total, start_idx + per_page)
                    st.markdown(f"<div class='record-nav'><span class='pill'>Showing</span><b>{start_idx + 1 if total else 0}</b><span class='pill'>-</span><b>{end_idx}</b><span class='pill'>of</span><b>{total}</b> <span class='pill'>Page</span><b>{st.session_state.active_page}</b><span class='pill'>/</span><b>{total_pages}</b></div>", unsafe_allow_html=True)
                    jump_page = st.number_input("Go to page", min_value=1, max_value=total_pages, value=st.session_state.active_page, key="jump_to_page", help="Jump to a page number")
                    if st.button("Go", key="jump_page_btn"):
                        st.session_state.active_page = int(jump_page)
                        st.rerun()
                with nav_next:
                    if st.button("Next Page ▶", use_container_width=True):
                        st.session_state.active_page = min(total_pages, st.session_state.active_page + 1)
                        st.rerun()
                img_col_ratio = [1, 2] if not st.session_state.compact_view else [1, 1]
                for i in range(start_idx, end_idx):
                    row = df.iloc[i]
                    col1, col2 = st.columns(img_col_ratio)
                    with col1:
                        if isinstance(row['Image URL'], str) and row['Image URL']:
                            img_bytes = fetch_b2_file_bytes(row['Image URL'])
                            if img_bytes:
                                if st.session_state.show_ocr_visualization and row.get('Raw'):
                                    try:
                                        ocr_data = row['Raw']
                                        if isinstance(ocr_data, dict) and (ocr_data.get('textAnnotations') or ocr_data.get('fullTextAnnotation')):
                                            img_bytes = draw_ocr_visualization(img_bytes, ocr_data)
                                    except Exception as e:
                                        st.error(f"Error applying OCR visualization: {str(e)}")
                                st.image(img_bytes, use_container_width=True)
                            else:
                                st.image(row['Image URL'], use_container_width=True)
                    with col2:
                        ts = row['Timestamp'] if isinstance(row['Timestamp'], str) else ''
                        st.write(f"**Date:** {ts.split('T')[0] if ts else '—'}")
                        st.write(f"**Location:** {row.get('Location', '—')}")
                        user_full_name = row.get('User Full Name', '')
                        pharmacy_name = row.get('Pharmacy Name', '')
                        if user_full_name or pharmacy_name:
                            user_info_parts = []
                            if user_full_name:
                                user_info_parts.append(f"**User:** {user_full_name}")
                            if pharmacy_name:
                                user_info_parts.append(f"**Pharmacy:** {pharmacy_name}")
                            for info in user_info_parts:
                                st.write(info)
                        if isinstance(row.get('Confirmed Drugs'), list) and row.get('Confirmed Drugs'):
                            st.write("**Confirmed Drugs:** ")
                            st.markdown("<div>" + "".join([f"<span class='pill'>{_to_english_ascii(str(x))}</span>" for x in row['Confirmed Drugs']]) + "</div>", unsafe_allow_html=True)
                        if row.get('Raw') and isinstance(row['Raw'], dict):
                            ocr_data = row['Raw']
                            if ocr_data.get('textAnnotations') or ocr_data.get('fullTextAnnotation'):
                                text_info = extract_text_from_ocr(ocr_data)
                                if text_info['full_text']:
                                    with st.expander("📝 Extracted Text", expanded=False):
                                        st.text_area("Full Text", text_info['full_text'], height=150, key=f"list_text_{i}")
                                    if text_info['word_count'] > 0:
                                        st.caption(f"📝 {text_info['word_count']} words detected")
                        if row.get('Latitude') is not None and row.get('Longitude') is not None:
                            st.write(f"**Coordinates:** {row['Latitude']}, {row['Longitude']}")
                        map_lat, map_lon = None, None
                        if row.get('Location JSON URL'):
                            loc_bytes = fetch_b2_file_bytes(row['Location JSON URL'])
                            loc_obj = None
                            if loc_bytes:
                                try:
                                    loc_obj = json.loads(loc_bytes.decode('utf-8', errors='ignore'))
                                except Exception:
                                    loc_obj = None
                            if isinstance(loc_obj, dict):
                                loc_ts = _to_datetime(loc_obj.get('timestamp')) or _to_datetime(loc_obj.get('capturedAt'))
                                with st.expander("Location Details", expanded=not st.session_state.compact_view):
                                    if loc_obj.get('textualLocation'):
                                        st.markdown(f"- Text: {loc_obj.get('textualLocation')}")
                                    lat = loc_obj.get('latitude')
                                    lon = loc_obj.get('longitude')
                                    if lat is not None and lon is not None:
                                        st.markdown(f"- Coordinates: {lat}, {lon}")
                                        try:
                                            map_lat, map_lon = float(lat), float(lon)
                                        except Exception:
                                            map_lat, map_lon = None, None
                                    if loc_obj.get('accuracy') is not None:
                                        try:
                                            acc = round(float(loc_obj['accuracy']), 2)
                                        except Exception:
                                            acc = loc_obj.get('accuracy')
                                        st.markdown(f"- Accuracy: {acc} m")
                                    if loc_ts:
                                        st.markdown(f"- Captured At: {loc_ts.isoformat()}")
                            else:
                                st.caption("Location Details unavailable")
                        if map_lat is None or map_lon is None:
                            if row.get('Latitude') is not None and row.get('Longitude') is not None:
                                try:
                                    map_lat, map_lon = float(row['Latitude']), float(row['Longitude'])
                                except Exception:
                                    map_lat, map_lon = None, None
                        if map_lat is not None and map_lon is not None:
                            addr = reverse_geocode(map_lat, map_lon)
                            if addr and isinstance(addr, dict):
                                a = addr.get('address') or {}
                                road = a.get('road') or a.get('pedestrian') or a.get('footway') or a.get('residential')
                                neighbourhood = a.get('neighbourhood') or a.get('suburb') or a.get('village')
                                city = a.get('city') or a.get('town') or a.get('county')
                                postcode = a.get('postcode')
                                country = a.get('country')
                                with st.expander("Address", expanded=not st.session_state.compact_view):
                                    if road:
                                        st.markdown(f"- Street: {road}")
                                    line_parts = [p for p in [neighbourhood, city] if p]
                                    if line_parts:
                                        st.markdown(f"- Area: {', '.join(line_parts)}")
                                    if postcode or country:
                                        st.markdown(f"- {('Postcode: ' + postcode) if postcode else ''}{(' • ' if postcode and country else '')}{('Country: ' + country) if country else ''}")
                            pharmacy = find_nearest_pharmacy(map_lat, map_lon)
                            if pharmacy:
                                with st.expander("Nearest Pharmacy", expanded=False):
                                    st.markdown(f"- Name: {_to_english_ascii(pharmacy.get('name', 'Pharmacy'))}")
                                    st.markdown(f"- Distance: {pharmacy.get('distance_m')} m")
                                    p_tags = pharmacy.get('tags') or {}
                                    p_addr = ", ".join([
                                        p_tags.get('addr:street:en', '') or p_tags.get('addr:street', ''),
                                        p_tags.get('addr:city:en', '') or p_tags.get('addr:city', '') or p_tags.get('addr:town', '') or p_tags.get('addr:village', ''),
                                        p_tags.get('addr:postcode', ''),
                                    ]).strip(', ')
                                    if p_addr:
                                        st.markdown(f"- Address: {p_addr}")
                            if st.session_state.show_map:
                                layers = []
                                point_data = pd.DataFrame([
                                    {"name": "Location", "lat": map_lat, "lon": map_lon, "color": [52, 152, 219]},
                                ])
                                layers.append(pdk.Layer(
                                    "ScatterplotLayer",
                                    data=point_data,
                                    get_position='[lon, lat]',
                                    get_color='color',
                                    get_radius=10,
                                    radius_min_pixels=6,
                                    radius_max_pixels=12,
                                ))
                                if pharmacy:
                                    pharm_data = pd.DataFrame([
                                        {"name": _to_english_ascii(pharmacy.get('name', 'Pharmacy')), "lat": pharmacy['lat'], "lon": pharmacy['lon'], "color": [39, 174, 96]},
                                    ])
                                    layers.append(pdk.Layer(
                                        "ScatterplotLayer",
                                        data=pharm_data,
                                        get_position='[lon, lat]',
                                        get_color='color',
                                        get_radius=10,
                                        radius_min_pixels=6,
                                        radius_max_pixels=12,
                                    ))
                                    line_df = pd.DataFrame([
                                        {"from_lon": map_lon, "from_lat": map_lat, "to_lon": pharmacy['lon'], "to_lat": pharmacy['lat']}
                                    ])
                                    layers.append(pdk.Layer(
                                        "LineLayer",
                                        data=line_df,
                                        get_source_position='[from_lon, from_lat]',
                                        get_target_position='[to_lon, to_lat]',
                                        get_color=[200, 200, 200],
                                        get_width=2,
                                    ))
                                view_state = pdk.ViewState(latitude=map_lat, longitude=map_lon, zoom=14)
                                deck = pdk.Deck(layers=layers, initial_view_state=view_state, tooltip={"text": "{name}"})
                                st.pydeck_chart(deck, use_container_width=True)
                    if i < end_idx - 1:
                        st.divider()
            else:
                total = len(df)
                if st.session_state.active_record > total:
                    st.session_state.active_record = 1
                nav_prev, nav_ctr, nav_next = st.columns([1, 2, 1])
                with nav_prev:
                    if st.button("◀ Previous", use_container_width=True):
                        st.session_state.active_record = max(1, st.session_state.active_record - 1)
                        st.rerun()
                with nav_ctr:
                    st.markdown(f"<div class='record-nav'><span class='pill'>Showing</span><b>{st.session_state.active_record}</b><span class='pill'>/</span><b>{total}</b></div>", unsafe_allow_html=True)
                    jump_val = st.number_input("Go to #", min_value=1, max_value=total, value=st.session_state.active_record, key="jump_to_record", help="Jump directly to a specific record number")
                    if st.button("Go", key="jump_btn"):
                        st.session_state.active_record = int(jump_val)
                        st.rerun()
                with nav_next:
                    if st.button("Next ▶", use_container_width=True):
                        st.session_state.active_record = min(total, st.session_state.active_record + 1)
                        st.rerun()
                idx = st.session_state.active_record - 1
                row = df.iloc[idx]
                img_col_ratio = [1, 2] if not st.session_state.compact_view else [1, 1]
                col1, col2 = st.columns(img_col_ratio)
                with col1:
                    if isinstance(row['Image URL'], str) and row['Image URL']:
                        img_bytes = fetch_b2_file_bytes(row['Image URL'])
                        if img_bytes:
                            if st.session_state.show_ocr_visualization and row.get('Raw'):
                                try:
                                    ocr_data = row['Raw']
                                    if isinstance(ocr_data, dict) and (ocr_data.get('textAnnotations') or ocr_data.get('fullTextAnnotation')):
                                        img_bytes = draw_ocr_visualization(img_bytes, ocr_data)
                                except Exception as e:
                                    st.error(f"Error applying OCR visualization: {str(e)}")
                            st.image(img_bytes, use_container_width=True)
                        else:
                            st.image(row['Image URL'], use_container_width=True)
                with col2:
                    ts = row['Timestamp'] if isinstance(row['Timestamp'], str) else ''
                    st.write(f"**Date:** {ts.split('T')[0] if ts else '—'}")
                    st.write(f"**Location:** {row.get('Location', '—')}")
                    user_full_name = row.get('User Full Name', '')
                    pharmacy_name = row.get('Pharmacy Name', '')
                    if user_full_name or pharmacy_name:
                        user_info_parts = []
                        if user_full_name:
                            user_info_parts.append(f"**User:** {user_full_name}")
                        if pharmacy_name:
                            user_info_parts.append(f"**Pharmacy:** {pharmacy_name}")
                        for info in user_info_parts:
                            st.write(info)
                    if isinstance(row.get('Confirmed Drugs'), list) and row.get('Confirmed Drugs'):
                        st.write("**Confirmed Drugs:** ")
                        st.markdown("<div>" + "".join([f"<span class='pill'>{_to_english_ascii(str(x))}</span>" for x in row['Confirmed Drugs']]) + "</div>", unsafe_allow_html=True)
                    if row.get('Raw') and isinstance(row['Raw'], dict):
                        ocr_data = row['Raw']
                        if ocr_data.get('textAnnotations') or ocr_data.get('fullTextAnnotation'):
                            text_info = extract_text_from_ocr(ocr_data)
                            with st.expander("📝 Extracted Text", expanded=False):
                                if text_info['full_text']:
                                    st.text_area("Full Text", text_info['full_text'], height=100)
                                if text_info['detected_languages']:
                                    st.write("**Detected Languages:**")
                                    for lang in text_info['detected_languages']:
                                        confidence_pct = round(lang['confidence'] * 100, 1)
                                        st.write(f"- {lang['language']}: {confidence_pct}%")
                                if text_info['text_blocks']:
                                    st.write(f"**Text Blocks:** {len(text_info['text_blocks'])} found")
                                    st.write(f"**Word Count:** {text_info['word_count']}")
                                if text_info['text_blocks']:
                                    with st.expander("Individual Text Blocks", expanded=False):
                                        for i, block in enumerate(text_info['text_blocks']):
                                            st.write(f"**Block {i+1}:** {block['text']}")
                    if row.get('Latitude') is not None and row.get('Longitude') is not None:
                        st.write(f"**Coordinates:** {row['Latitude']}, {row['Longitude']}")
                    map_lat, map_lon = None, None
                    if row.get('Location JSON URL'):
                        loc_bytes = fetch_b2_file_bytes(row['Location JSON URL'])
                        loc_obj = None
                        if loc_bytes:
                            try:
                                loc_obj = json.loads(loc_bytes.decode('utf-8', errors='ignore'))
                            except Exception:
                                loc_obj = None
                        if isinstance(loc_obj, dict):
                            loc_ts = _to_datetime(loc_obj.get('timestamp')) or _to_datetime(loc_obj.get('capturedAt'))
                            with st.expander("Location Details", expanded=not st.session_state.compact_view):
                                if loc_obj.get('textualLocation'):
                                    st.markdown(f"- Text: {loc_obj.get('textualLocation')}")
                                lat = loc_obj.get('latitude')
                                lon = loc_obj.get('longitude')
                                if lat is not None and lon is not None:
                                    st.markdown(f"- Coordinates: {lat}, {lon}")
                                    try:
                                        map_lat, map_lon = float(lat), float(lon)
                                    except Exception:
                                        map_lat, map_lon = None, None
                                if loc_obj.get('accuracy') is not None:
                                    try:
                                        acc = round(float(loc_obj['accuracy']), 2)
                                    except Exception:
                                        acc = loc_obj.get('accuracy')
                                    st.markdown(f"- Accuracy: {acc} m")
                                if loc_ts:
                                    st.markdown(f"- Captured At: {loc_ts.isoformat()}")
                        else:
                            st.caption("Location Details unavailable")
                    if map_lat is None or map_lon is None:
                        if row.get('Latitude') is not None and row.get('Longitude') is not None:
                            try:
                                map_lat, map_lon = float(row['Latitude']), float(row['Longitude'])
                            except Exception:
                                map_lat, map_lon = None, None
                    if map_lat is not None and map_lon is not None:
                        addr = reverse_geocode(map_lat, map_lon)
                        if addr and isinstance(addr, dict):
                            a = addr.get('address') or {}
                            road = a.get('road') or a.get('pedestrian') or a.get('footway') or a.get('residential')
                            neighbourhood = a.get('neighbourhood') or a.get('suburb') or a.get('village')
                            city = a.get('city') or a.get('town') or a.get('county')
                            postcode = a.get('postcode')
                            country = a.get('country')
                            with st.expander("Address", expanded=not st.session_state.compact_view):
                                if road:
                                    st.markdown(f"- Street: {road}")
                                line_parts = [p for p in [neighbourhood, city] if p]
                                if line_parts:
                                    st.markdown(f"- Area: {', '.join(line_parts)}")
                                if postcode or country:
                                    st.markdown(f"- {('Postcode: ' + postcode) if postcode else ''}{(' • ' if postcode and country else '')}{('Country: ' + country) if country else ''}")
                        pharmacy = find_nearest_pharmacy(map_lat, map_lon)
                        if pharmacy:
                            with st.expander("Nearest Pharmacy", expanded=False):
                                st.markdown(f"- Name: {_to_english_ascii(pharmacy.get('name', 'Pharmacy'))}")
                                st.markdown(f"- Distance: {pharmacy.get('distance_m')} m")
                                p_tags = pharmacy.get('tags') or {}
                                p_addr = ", ".join([
                                    p_tags.get('addr:street:en', '') or p_tags.get('addr:street', ''),
                                    p_tags.get('addr:city:en', '') or p_tags.get('addr:city', '') or p_tags.get('addr:town', '') or p_tags.get('addr:village', ''),
                                    p_tags.get('addr:postcode', ''),
                                ]).strip(', ')
                                if p_addr:
                                    st.markdown(f"- Address: {p_addr}")
                        if st.session_state.show_map:
                            layers = []
                            point_data = pd.DataFrame([
                                {"name": "Location", "lat": map_lat, "lon": map_lon, "color": [52, 152, 219]},
                            ])
                            layers.append(pdk.Layer(
                                "ScatterplotLayer",
                                data=point_data,
                                get_position='[lon, lat]',
                                get_color='color',
                                get_radius=10,
                                radius_min_pixels=6,
                                radius_max_pixels=12,
                            ))
                            if pharmacy:
                                pharm_data = pd.DataFrame([
                                    {"name": _to_english_ascii(pharmacy.get('name', 'Pharmacy')), "lat": pharmacy['lat'], "lon": pharmacy['lon'], "color": [39, 174, 96]},
                                ])
                                layers.append(pdk.Layer(
                                    "ScatterplotLayer",
                                    data=pharm_data,
                                    get_position='[lon, lat]',
                                    get_color='color',
                                    get_radius=10,
                                    radius_min_pixels=6,
                                    radius_max_pixels=12,
                                ))
                                line_df = pd.DataFrame([
                                    {"from_lon": map_lon, "from_lat": map_lat, "to_lon": pharmacy['lon'], "to_lat": pharmacy['lat']}
                                ])
                                layers.append(pdk.Layer(
                                    "LineLayer",
                                    data=line_df,
                                    get_source_position='[from_lon, from_lat]',
                                    get_target_position='[to_lon, to_lat]',
                                    get_color=[200, 200, 200],
                                    get_width=2,
                                ))
                            view_state = pdk.ViewState(latitude=map_lat, longitude=map_lon, zoom=14)
                            deck = pdk.Deck(layers=layers, initial_view_state=view_state, tooltip={"text": "{name}"})
                            st.pydeck_chart(deck, use_container_width=True)
                st.markdown("**Quick Jump**")
                start = max(0, st.session_state.active_record - 4)
                end = min(total, start + 8)
                thumbs = st.columns(end - start)
                for offset, col in enumerate(thumbs):
                    j = start + offset
                    with col:
                        img_url = df.iloc[j]['Image URL']
                        if isinstance(img_url, str) and img_url:
                            thumb_bytes = fetch_b2_file_bytes(img_url)
                            if thumb_bytes:
                                st.image(thumb_bytes, use_container_width=True)
                            else:
                                st.image(img_url, use_container_width=True)
                        if st.button(f"Open #{j+1}", key=f"open_{j}"):
                            st.session_state.active_record = j + 1
                            st.rerun()
            st.divider()
            st.subheader("📈 Prescription Trends")
            chart_data = df.groupby(df['Timestamp'].fillna('').apply(lambda x: x[:10] if isinstance(x, str) else '')).size().reset_index(name='Count')
            fig = px.bar(
                chart_data,
                x='Timestamp',
                y='Count',
                title="Prescriptions by Date",
                color_discrete_sequence=['#3498db'],
                labels={'Timestamp': 'Date', 'Count': 'Number of Prescriptions'}
            )
            fig.update_layout(
                plot_bgcolor='#ffffff',
                paper_bgcolor='#ffffff',
                font=dict(color='#000000'),
                xaxis=dict(gridcolor='#d1d5db', zerolinecolor='#d1d5db'),
                yaxis=dict(gridcolor='#d1d5db', zerolinecolor='#d1d5db'),
                title_font=dict(color='#000000'),
            )
            st.plotly_chart(fig, use_container_width=True)
