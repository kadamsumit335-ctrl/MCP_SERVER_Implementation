import sys
import os
import ast
import streamlit as st

# Add parent directories to sys.path to allow imports from app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.mcp_server.mcp_client import MCPClient
from app.agents.agent import stream_answer
from app.agents.tool_agent import decide_tools, execute_tool_plan, build_context_from_results

# --- Page Config ---
st.set_page_config(
    page_title="AWS Docs Q&A",
    page_icon="☁️",
    layout="centered",
)

# --- Clean ChatGPT-style CSS ---
st.markdown("""
<style>
    #MainMenu, footer, header { visibility: hidden; }
    .block-container { padding-top: 2rem; padding-bottom: 5rem; max-width: 750px; }
    
    .user-msg {
        background: #f4f4f4;
        border-radius: 12px;
        padding: 12px 16px;
        margin: 8px 0;
        text-align: right;
        color: #1a1a1a;
        font-size: 15px;
    }
    
    .assistant-msg {
        background: #ffffff;
        border-radius: 12px;
        padding: 12px 16px;
        margin: 8px 0;
        color: #1a1a1a;
        font-size: 15px;
        border: 1px solid #e5e5e5;
    }
    
    .spinner-container {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 12px 0;
    }
    
    .spinner {
        width: 20px;
        height: 20px;
        border: 2px solid #e5e5e5;
        border-top: 2px solid #555;
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    .spinner-text { color: #888; font-size: 14px; }
    
    .source-pill {
        display: inline-block;
        background: #f0f0f0;
        border-radius: 20px;
        padding: 3px 10px;
        font-size: 12px;
        color: #555;
        margin: 2px;
        text-decoration: none;
    }
    
    div[data-testid="stButton"] button {
        background: transparent;
        border: 1px solid #ddd;
        border-radius: 20px;
        color: #555;
        font-size: 13px;
        padding: 4px 14px;
        cursor: pointer;
        margin-top: 4px;
    }
    
    div[data-testid="stButton"] button:hover {
        background: #f4f4f4;
        border-color: #bbb;
    }
</style>
""", unsafe_allow_html=True)

# --- Title ---
st.markdown("## ☁️ AWS Docs Q&A")
st.markdown("<p style='color:#888; font-size:14px; margin-top:-10px;'>Ask anything about any AWS service</p>", unsafe_allow_html=True)
st.divider()

# --- Session State ---
if "messages" not in st.session_state:
    st.session_state.messages = []

if "stop_streaming" not in st.session_state:
    st.session_state.stop_streaming = False

if "mcp_client" not in st.session_state:
    with st.spinner("Connecting to MCP server..."):
        try:
            st.session_state.mcp_client = MCPClient()
        except Exception as e:
            st.error(f"Failed to start MCP server: {e}")
            st.stop()

# Render chat history
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f'<div class="user-msg">{msg["content"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="assistant-msg">{msg["content"]}</div>', unsafe_allow_html=True)
        if msg.get("sources"):
            sources_html = " ".join(
                f'<a class="source-pill" href="{url}" target="_blank">📄 Source {i+1}</a>'
                for i, url in enumerate(msg["sources"])
            )
            st.markdown(sources_html, unsafe_allow_html=True)

# Chat input
query = st.chat_input("Ask anything about AWS...")

if query:
    st.markdown(f'<div class="user-msg">{query}</div>', unsafe_allow_html=True)
    st.session_state.messages.append({"role": "user", "content": query})

    client: MCPClient = st.session_state.mcp_client

    spinner_placeholder = st.empty()

    def show_spinner(text: str):
        spinner_placeholder.markdown(f"""
            <div class="spinner-container">
                <div class="spinner"></div>
                <span class="spinner-text">{text}</span>
            </div>
        """, unsafe_allow_html=True)
    
    # ... (previous code likely includes show_spinner definition)
    available_tools = client.list_tools()
    tool_plan = decide_tools(query, available_tools)

    # Show which tools will be used
    tool_names = [step["tool"] for step in tool_plan]
    show_spinner(f"Using tools: {', '.join(tool_names)}")

    # Execute the tool plan
    results = execute_tool_plan(client, tool_plan, query)
    context = build_context_from_results(results)
    url_list = results.get("sources", [])

    if not context or context == "No relevant information found.":
        spinner_placeholder.empty()
        st.error("Could not find relevant information.")
        st.stop()

    # —— Step 4: Stream answer ————————————————————————————————————————
    spinner_placeholder.empty()
    st.session_state.stop_streaming = False

    answer_placeholder = st.empty()
    stop_placeholder = st.empty()
    full_answer = ""

    with stop_placeholder:
        if st.button("⏹ Stop", key="stop_btn"):
            st.session_state.stop_streaming = True
    
    try:
        for token in stream_answer(query, context):
            if st.session_state.stop_streaming:
                break
            full_answer += token
            answer_placeholder.markdown(
                f'<div class="assistant-msg">{full_answer}▌</div>',
                unsafe_allow_html=True
            )

        answer_placeholder.markdown(
            f'<div class="assistant-msg">{full_answer}</div>',
            unsafe_allow_html=True
        )
        stop_placeholder.empty()

    except Exception as e:
        full_answer = context[:1000]
        answer_placeholder.markdown(
            f'<div class="assistant-msg">{full_answer}</div>',
            unsafe_allow_html=True
        )
        stop_placeholder.empty()

    # —— Sources ————————————————————————————————————————
    sources_html = " ".join(
        f'<a class="source-pill" href="{url}" target="_blank">📄 Source {i+1}</a>'
        for i, url in enumerate(url_list)
    )
    st.markdown(sources_html, unsafe_allow_html=True)

    # ----- Save to history ---------------
    st.session_state.messages.append({
        "role" : "assitant",
        "content" : full_answer,
        "sources" : url_list,
    })