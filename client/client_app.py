import streamlit as st
import requests
import json

st.set_page_config(page_title="RAG PDF Search", layout="wide")

st.title("📄 AI Document Search")
st.markdown("Upload a PDF and ask questions about its content using RAG.")

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
if 'collection_name' not in st.session_state:
    st.session_state.collection_name = None
if 'uploaded' not in st.session_state:
    st.session_state.uploaded = False

# Main Interface
st.header("1️⃣ Upload PDF Document")

uploaded_file = st.file_uploader("Choose a PDF file", type="pdf", key="pdf_uploader")

if uploaded_file and not st.session_state.uploaded:
    if st.button("📤 Process and Upload PDF", type="primary"):
        with st.spinner("Processing PDF... This may take a moment..."):
            try:
                # Upload to /upload endpoint
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                
                # Note: collection_name is auto-generated from filename in the backend
                # We're sending it as a form field but it will be overridden
                data = {"collection_name": uploaded_file.name.replace(".pdf", "").lower()}
                
                response = requests.post(
                    f"{api_base}/upload",
                    files=files,
                    data=data,
                    timeout=120
                )
                
                if response.status_code == 200:
                    num_chunks = response.json()
                    # Generate collection name same way as backend
                    import re
                    from pathlib import Path
                    
                    name = Path(uploaded_file.name).stem
                    collection_name = re.sub(r'[^\w\-]', '_', name)
                    collection_name = re.sub(r'_+', '_', collection_name)
                    collection_name = collection_name.strip('_').lower()
                    
                    st.session_state.collection_name = collection_name
                    st.session_state.uploaded = True
                    
                    st.success(f"✅ Successfully processed {num_chunks} chunks!")
                    st.info(f"📚 Collection: `{collection_name}`")
                else:
                    st.error(f"❌ Upload failed ({response.status_code}): {response.text}")
                    
            except requests.exceptions.Timeout:
                st.error("⏱️ Request timed out. The PDF may be too large.")
            except Exception as e:
                st.error(f"❌ Error: {e}")

# Show current collection if uploaded
if st.session_state.uploaded and st.session_state.collection_name:
    st.success(f"📚 Active Collection: `{st.session_state.collection_name}`")
    if st.button("🔄 Upload New Document"):
        st.session_state.uploaded = False
        st.session_state.collection_name = None
        st.rerun()

st.divider()

# Search Interface
st.header("2️⃣ Ask Questions")

col1, col2 = st.columns([3, 1])

with col1:
    query = st.text_area(
        "What would you like to know?",
        placeholder="e.g., What are the main findings in this document?",
        height=100
    )

with col2:
    st.write("")  # Spacing
    st.write("")  # Spacing
    search_button = st.button("🔍 Search", type="primary", use_container_width=True)

# Search functionality
if search_button:
    if not query:
        st.warning("⚠️ Please enter a question.")
    elif not st.session_state.collection_name:
        st.warning("⚠️ Please upload a PDF document first.")
    else:
        with st.spinner("🔎 Searching and generating response..."):
            try:
                # Call /search endpoint with JSON body
                payload = {
                    "query": query,
                    "collection_name": st.session_state.collection_name,
                    "limit": search_limit
                }
                
                response = requests.post(
                    f"{api_base}/search",
                    json=payload,  # Send as JSON, not form data
                    headers={"Content-Type": "application/json"},
                    timeout=60
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    st.divider()
                    st.subheader("💡 AI Response")
                    st.markdown(result['response'])
                    
                    with st.expander("ℹ️ Search Details"):
                        st.write(f"**Collection:** `{st.session_state.collection_name}`")
                        st.write(f"**Results Retrieved:** {search_limit}")
                        st.write(f"**Query:** {query}")
                else:
                    st.error(f"❌ Search failed ({response.status_code}): {response.text}")
                    
            except requests.exceptions.Timeout:
                st.error("⏱️ Search timed out. Try reducing the result limit.")
            except Exception as e:
                st.error(f"❌ Error during search: {e}")
                st.exception(e)

# Footer
st.divider()
st.caption("🤖 Powered by RAG (Retrieval-Augmented Generation)")