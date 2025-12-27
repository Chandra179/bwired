import streamlit as st
import requests
import json
import re
from pathlib import Path

st.set_page_config(page_title="RAG PDF Search", layout="wide")

st.title("📄 AI Document Search")
st.markdown("Upload PDFs or search existing collections using RAG.")

# Settings Sidebar
with st.sidebar:
    st.header("⚙️ API Settings")
    api_base = st.text_input("Backend URL", "http://localhost:8000")
    
    st.divider()
    
    st.header("🔍 Search Settings")
    search_limit = st.slider("Results to retrieve", min_value=1, max_value=20, value=5)
    
    st.divider()
    
    # Health check
    if st.button("Check API Health"):
        try:
            response = requests.get(f"{api_base}/health", timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                st.success("✅ API is healthy")
                with st.expander("Details"):
                    st.json(health_data)
            else:
                st.error(f"❌ API returned {response.status_code}")
        except Exception as e:
            st.error(f"❌ Cannot connect: {e}")

# Initialize session state
if 'recent_collections' not in st.session_state:
    st.session_state.recent_collections = []

# Helper function to sanitize collection name
def sanitize_collection_name(filename: str) -> str:
    """Sanitize filename to match backend logic"""
    if not filename:
        return "unnamed_document"
    name = Path(filename).stem
    sanitized = re.sub(r'[^\w\-]', '_', name)
    sanitized = re.sub(r'_+', '_', sanitized)
    sanitized = sanitized.strip('_').lower()
    return sanitized

# Create tabs for Upload and Search
tab1, tab2 = st.tabs(["📤 Upload Document", "🔍 Search Collection"])

# ============== UPLOAD TAB ==============
with tab1:
    st.header("Upload PDF Document")
    
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf", key="pdf_uploader")
    
    if uploaded_file:
        # Show what the collection name will be
        predicted_collection = sanitize_collection_name(uploaded_file.name)
        st.info(f"📚 This will create collection: `{predicted_collection}`")
        
        if st.button("📤 Process and Upload PDF", type="primary"):
            with st.spinner("Processing PDF... This may take a moment..."):
                try:
                    # Upload to /upload endpoint
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                    data = {"collection_name": predicted_collection}
                    
                    response = requests.post(
                        f"{api_base}/upload",
                        files=files,
                        data=data,
                        timeout=120
                    )
                    
                    if response.status_code == 200:
                        num_chunks = response.json()
                        
                        # Add to recent collections
                        if predicted_collection not in st.session_state.recent_collections:
                            st.session_state.recent_collections.insert(0, predicted_collection)
                            # Keep only last 10
                            st.session_state.recent_collections = st.session_state.recent_collections[:10]
                        
                        st.success(f"✅ Successfully processed {num_chunks} chunks!")
                        st.info(f"📚 Collection: `{predicted_collection}`")
                        st.info("💡 Go to 'Search Collection' tab to query this document")
                    else:
                        st.error(f"❌ Upload failed ({response.status_code}): {response.text}")
                        
                except requests.exceptions.Timeout:
                    st.error("⏱️ Request timed out. The PDF may be too large.")
                except Exception as e:
                    st.error(f"❌ Error: {e}")

# ============== SEARCH TAB ==============
with tab2:
    st.header("Search Document Collection")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Collection name input
        collection_name = st.text_input(
            "Collection Name",
            placeholder="e.g., my_document",
            help="Enter the exact collection name you want to search"
        )
    
    with col2:
        st.write("")  # Spacing
        # Show recent collections if any
        if st.session_state.recent_collections:
            recent_collection = st.selectbox(
                "Or select recent:",
                options=[""] + st.session_state.recent_collections,
                index=0
            )
            if recent_collection:
                collection_name = recent_collection
    
    # Query input
    query = st.text_area(
        "What would you like to know?",
        placeholder="e.g., What are the main findings in this document?",
        height=100
    )
    
    # Search button
    search_button = st.button("🔍 Search", type="primary", use_container_width=True)
    
    # Search functionality
    if search_button:
        if not query:
            st.warning("⚠️ Please enter a question.")
        elif not collection_name:
            st.warning("⚠️ Please enter a collection name.")
        else:
            with st.spinner("🔎 Searching and generating response..."):
                try:
                    # Call /search endpoint with JSON body
                    payload = {
                        "query": query,
                        "collection_name": collection_name,
                        "limit": search_limit
                    }
                    
                    response = requests.post(
                        f"{api_base}/search",
                        json=payload,
                        headers={"Content-Type": "application/json"},
                        timeout=60
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        st.divider()
                        st.subheader("💡 AI Response")
                        st.markdown(result['response'])
                        
                        with st.expander("ℹ️ Search Details"):
                            st.write(f"**Collection:** `{collection_name}`")
                            st.write(f"**Results Retrieved:** {search_limit}")
                            st.write(f"**Query:** {query}")
                    else:
                        st.error(f"❌ Search failed ({response.status_code}): {response.text}")
                        if response.status_code == 404:
                            st.info("💡 Collection not found. Make sure the collection name is correct or upload a document first.")
                        
                except requests.exceptions.Timeout:
                    st.error("⏱️ Search timed out. Try reducing the result limit.")
                except Exception as e:
                    st.error(f"❌ Error during search: {e}")
                    st.exception(e)

# Footer
st.divider()
st.caption("🤖 Powered by RAG (Retrieval-Augmented Generation)")

# Show recent collections in sidebar if any
if st.session_state.recent_collections:
    with st.sidebar:
        st.divider()
        st.subheader("📚 Recent Collections")
        for coll in st.session_state.recent_collections[:5]:
            st.text(f"• {coll}")