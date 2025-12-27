import streamlit as st
import requests

# --- Configuration ---
# Default to localhost:8000 as defined in your server.py
API_BASE_URL = "http://localhost:8000" 

# --- Page Config ---
st.set_page_config(
    page_title="Agentic RAG Chat",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 Document Search Agent")

# --- Sidebar: Document Upload ---
with st.sidebar:
    st.header("📂 Upload Documents")
    st.markdown("Upload a PDF to index it into the vector database.")
    
    # File Uploader
    uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])
    
    # Optional Collection Name Input
    collection_name = st.text_input(
        "Collection Name (Optional)", 
        placeholder="Leave empty to auto-generate"
    )
    
    # Upload Button
    if st.button("Upload", type="primary"):
        if uploaded_file is not None:
            with st.spinner("Uploading..."):
                try:
                    # prepare multipart/form-data
                    files = {
                        "file": (uploaded_file.name, uploaded_file, "application/pdf")
                    }
                    data = {
                        "collection_name": collection_name
                    }
                    
                    # POST to /upload endpoint
                    response = requests.post(
                        f"{API_BASE_URL}/upload", 
                        files=files, 
                        data=data
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        st.success("✅ Document indexed successfully!")
                        st.json(result)
                    else:
                        st.error(f"❌ Upload failed: {response.status_code}")
                        st.error(response.text)
                        
                except requests.exceptions.ConnectionError:
                    st.error("❌ Could not connect to backend. Is the server running?")
                except Exception as e:
                    st.error(f"❌ An error occurred: {str(e)}")
        else:
            st.warning("⚠️ Please select a file first.")

    st.divider()
    
    # System Status Check
    if st.button("Check System Health"):
        try:
            res = requests.get(f"{API_BASE_URL}/health")
            if res.status_code == 200:
                st.success("System Online")
                st.json(res.json())
            else:
                st.error("System Unhealthy")
        except:
            st.error("Server Offline")

# --- Main Interface: Chat ---
st.subheader("Chat with your Documents")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("Ask a question regarding your uploaded documents..."):
    # 1. Display user message
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 2. Send to Backend
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        try:
            with st.spinner("Agent is thinking..."):
                # POST to /chat endpoint
                payload = {"message": prompt}
                response = requests.post(f"{API_BASE_URL}/chat", json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    bot_response = data.get("response", "No response content.")
                    message_placeholder.markdown(bot_response)
                    
                    # Add assistant response to history
                    st.session_state.messages.append({"role": "assistant", "content": bot_response})
                else:
                    error_msg = f"Error {response.status_code}: {response.text}"
                    message_placeholder.error(error_msg)
        except requests.exceptions.ConnectionError:
            message_placeholder.error("❌ Connection refused. Ensure the FastAPI backend is running.")