import streamlit as st
import requests

st.set_page_config(page_title="RAG PDF Search", layout="wide")

st.title("📄 AI Document Search")
st.markdown("Upload a PDF and ask the LLM questions about its content.")

# Settings Sidebar
with st.sidebar:
    st.header("API Settings")
    api_base = st.text_input("Backend URL", "http://localhost:8000")

# Main Interface
col1, col2 = st.columns([1, 1])

with col1:
    uploaded_file = st.file_uploader("Upload PDF", type="pdf")
    query = st.text_area("What would you like to know?")
    search_button = st.button("Submit Query", type="primary")

with col2:
    if search_button:
        if not uploaded_file or not query:
            st.warning("Please upload a file and enter a query.")
        else:
            with st.spinner("Processing PDF and searching vectors..."):
                # Call your existing FastAPI /search endpoint
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                data = {"query": query}
                
                try:
                    response = requests.post(f"{api_base}/search", files=files, data=data)
                    if response.status_code == 200:
                        result = response.json()
                        st.success("Response Generated!")
                        st.markdown(f"### AI Answer:\n{result['response']}")
                        st.info(f"Target Collection: `{result['collection_name']}`")
                    else:
                        st.error(f"Error {response.status_code}: {response.text}")
                except Exception as e:
                    st.error(f"Failed to connect to backend: {e}")