# app.py

import streamlit as st
from agents import RealEstateAgent
from prompts import GREETING_PROMPT, FOLLOW_UP_PROMPT, COMPLETION_PROMPT, ERROR_PROMPT
import json

# Optional: ElevenLabs TTS (uncomment if you enable audio)
# from elevenlabs import generate, play, set_api_key
# set_api_key(os.getenv("ELEVEN_API_KEY"))

# Set up page
st.set_page_config(
    page_title="Real Estate Assistant",
    page_icon="🏠",
    layout="wide"
)

# Add custom CSS
st.markdown("""
    <style>
    .stTextInput>div>div>input {
        background-color: #f0f2f6;
    }
    .stButton>button {
        width: 100%;
        background-color: #4CAF50;
        color: white;
        border: none;
        padding: 10px;
        border-radius: 5px;
    }
    .stButton>button:hover {
        background-color: #45a049;
    }
    </style>
    """, unsafe_allow_html=True)

# Header
st.title("🏠 Real Estate Assistant")
st.markdown("""
    Welcome! I'm here to help you find the perfect property. 
    Whether you're looking for a home or commercial space, I'll guide you through the process.
""")

# Initialize session state
if 'agent' not in st.session_state:
    st.session_state.agent = RealEstateAgent()
if 'messages' not in st.session_state:
    st.session_state.messages = []
    # Add initial greeting
    initial_message = st.session_state.agent.process_message("")
    st.session_state.messages.append({"role": "assistant", "content": initial_message})

# Chat interface
chat_container = st.container()
with chat_container:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# User input
if prompt := st.chat_input("Type your message here..."):
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Process message and get response (extraction happens inside process_message now)
    response = st.session_state.agent.process_message(prompt)
    
    # Add assistant response to chat
    st.session_state.messages.append({"role": "assistant", "content": response})
    with st.chat_message("assistant"):
        st.markdown(response)
    
    # Check if we have enough information to log
    if st.session_state.agent.is_ready_to_log():
        if st.session_state.agent.log_to_sheet():
            st.success("✅ Lead information has been saved! Our team will contact you soon.")
        else:
            # Still show success but with a different message since we save locally as backup
            st.success("✅ Lead information has been saved locally. Our team will review it soon.")

# Sidebar with information
with st.sidebar:
    st.header("Information Gathered")
    if st.session_state.agent.required_fields:
        # Group fields by category based on sheets column order
        lead_info = ["Name", "Email", "Phone"]
        property_info = ["Location", "Budget Range", "Property Type", "Property Size", "Timeline"]
        status_info = ["Interest Level", "Status", "Created Date", "Last Contact Date"]
        business_info = ["Company", "Position", "Industry", "Company Size", "Decision Maker"]
        additional_info = ["Use Case", "Competitors", "Call Outcome", "Notes", "Lead Source", "Follow-up Required", "Next Follow-up"]
        
        # Display fields by category
        st.subheader("Lead Information")
        for field in lead_info:
            value = st.session_state.agent.required_fields.get(field, "Not provided")
            st.text(f"{field}: {value}")
        
        st.subheader("Property Details")
        for field in property_info:
            value = st.session_state.agent.required_fields.get(field, "Not provided")
            st.text(f"{field}: {value}")
            
        st.subheader("Lead Status")
        # Add Lead Type (residential/commercial)
        st.text(f"Lead Type: {st.session_state.agent.lead_type or 'Not determined'}")
        for field in status_info:
            value = st.session_state.agent.required_fields.get(field, "Not provided")
            st.text(f"{field}: {value}")
        
        st.subheader("Business Information")
        for field in business_info:
            value = st.session_state.agent.required_fields.get(field, "Not provided")
            st.text(f"{field}: {value}")
        
        st.subheader("Additional Details")
        for field in additional_info:
            value = st.session_state.agent.required_fields.get(field, "Not provided")
            st.text(f"{field}: {value}")
        
        # Show completion status
        essential_fields = ["Name", "Email", "Phone", "Location", "Budget Range", "Property Type", "Property Size", "Timeline"]
        missing_essential = [f for f in essential_fields if not st.session_state.agent.required_fields.get(f) or st.session_state.agent.required_fields.get(f) == "Not provided"]
        
        if missing_essential:
            st.warning(f"Still need: {', '.join(missing_essential)}")
        else:
            st.success("All essential information gathered!")
