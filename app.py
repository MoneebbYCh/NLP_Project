# app.py

import streamlit as st
import re
from agents import RealEstateAgent
from prompts import GREETING_PROMPT, FOLLOW_UP_PROMPT, COMPLETION_PROMPT, ERROR_PROMPT
import json
from speech import speak, listen
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize ElevenLabs
from elevenlabs import ElevenLabs
client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

def validate_phone(phone):
    # Remove any non-digit characters
    phone = re.sub(r'\D', '', phone)
    
    # Check if it's a valid length (7-15 digits)
    if len(phone) < 7 or len(phone) > 15:
        return False
    return phone

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
    .voice-button {
        background-color: #2196F3 !important;
    }
    .voice-button:hover {
        background-color: #1976D2 !important;
    }
    /* Make audio player visible */
    .stAudio {
        display: block !important;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'phone_number' not in st.session_state:
    st.session_state.phone_number = None
if 'agent' not in st.session_state:
    st.session_state.agent = None
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'voice_enabled' not in st.session_state:
    st.session_state.voice_enabled = True  # Enable voice by default
if 'voice_settings' not in st.session_state:
    st.session_state.voice_settings = {
        "stability": 0.5,
        "similarity_boost": 0.75,
        "style": 0.0,
        "use_speaker_boost": True
    }

# Phone number input screen
if not st.session_state.phone_number:
    st.title("🏠 Real Estate Assistant")
    st.markdown("### Enter Phone Number to Start Call")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        phone_input = st.text_input("Phone Number", placeholder="Enter phone number (7-15 digits)")
    with col2:
        if st.button("Start Call", use_container_width=True):
            phone = validate_phone(phone_input)
            if phone:
                st.session_state.phone_number = phone
                st.session_state.agent = RealEstateAgent(initial_phone=phone)
                st.rerun()
            else:
                st.error("Please enter a valid phone number (7-15 digits)")

# Main chat interface
else:
    # Header
    st.title("🏠 Real Estate Assistant")
    st.markdown("""
        Welcome! I'm here to help you find the perfect property. 
        Whether you're looking for a home or commercial space, I'll guide you through the process.
    """)
    
    # Display phone number
    st.markdown(f"**Calling:** {st.session_state.phone_number}")
    
    # Voice settings in sidebar
    with st.sidebar:
        st.session_state.voice_enabled = st.checkbox("Enable Voice", value=st.session_state.voice_enabled)
        if st.session_state.voice_enabled:
            st.info("Voice mode is enabled. You can speak or type your messages.")
            
            # Voice settings controls
            st.subheader("Voice Settings")
            st.session_state.voice_settings["stability"] = st.slider(
                "Stability", 0.0, 1.0, 
                st.session_state.voice_settings["stability"], 0.1
            )
            st.session_state.voice_settings["similarity_boost"] = st.slider(
                "Similarity Boost", 0.0, 1.0, 
                st.session_state.voice_settings["similarity_boost"], 0.1
            )
            st.session_state.voice_settings["style"] = st.slider(
                "Style", 0.0, 1.0, 
                st.session_state.voice_settings["style"], 0.1
            )
            st.session_state.voice_settings["use_speaker_boost"] = st.checkbox(
                "Speaker Boost", 
                value=st.session_state.voice_settings["use_speaker_boost"]
            )
    
    # Add initial greeting if this is the first message
    if not st.session_state.messages:
        initial_message = st.session_state.agent.process_message("")
        print("[DEBUG] Generating initial greeting audio...")
        audio_data = speak(initial_message)
        if audio_data:
            print(f"[DEBUG] Initial greeting audio size: {len(audio_data)} bytes")
            st.session_state.messages.append({
                "role": "assistant", 
                "content": initial_message,
                "audio": audio_data
            })
            # Play the initial greeting
            st.audio(audio_data, format="audio/mp3", start_time=0)
            # Add HTML audio element for autoplay
            st.markdown(f"""
                <audio autoplay>
                    <source src="data:audio/mp3;base64,{audio_data.hex()}" type="audio/mp3">
                </audio>
            """, unsafe_allow_html=True)
        else:
            print("[DEBUG] Failed to generate initial greeting audio")
            st.session_state.messages.append({
                "role": "assistant", 
                "content": initial_message
            })

    chat_container = st.container()
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if message["role"] == "assistant" and "audio" in message:
                    st.audio(message["audio"], format="audio/mp3", start_time=0)
                    # Add HTML audio element for autoplay
                    st.markdown(f"""
                        <audio autoplay>
                            <source src="data:audio/mp3;base64,{message['audio'].hex()}" type="audio/mp3">
                        </audio>
                    """, unsafe_allow_html=True)

    # Voice input button
    if st.session_state.voice_enabled:
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🎤 Speak", use_container_width=True, key="voice_button"):
                with st.spinner("Listening..."):
                    user_input = listen()
                    if user_input and user_input not in ["Sorry, I didn't hear anything.", "Sorry, I didn't catch that.", "Sorry, speech recognition service failed."]:
                        # Add user message to chat
                        st.session_state.messages.append({"role": "user", "content": user_input})
                        with st.chat_message("user"):
                            st.markdown(user_input)
                        
                        # Process message and get response
                        response = st.session_state.agent.process_message(user_input)
                        
                        # Add assistant response to chat with audio
                        audio_data = speak(response)
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": response,
                            "audio": audio_data
                        })
                        with st.chat_message("assistant"):
                            st.markdown(response)
                            # Auto-play the response
                            st.audio(audio_data, format="audio/mp3", start_time=0)
                        
                        # Check if we have enough information to log
                        if st.session_state.agent.is_ready_to_log():
                            if st.session_state.agent.log_to_sheet():
                                st.success("✅ Lead information has been saved! Our team will contact you soon.")
                            else:
                                st.success("✅ Lead information has been saved locally. Our team will review it soon.")
                        st.rerun()

    # Text input
    if prompt := st.chat_input("Type your message here..."):
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Process message and get response
        response = st.session_state.agent.process_message(prompt)
        
        # Add assistant response to chat with audio
        audio_data = speak(response)
        st.session_state.messages.append({
            "role": "assistant", 
            "content": response,
            "audio": audio_data
        })
        with st.chat_message("assistant"):
            st.markdown(response)
            # Auto-play the response
            st.audio(audio_data, format="audio/mp3", start_time=0)
        
        # Check if we have enough information to log
        if st.session_state.agent.is_ready_to_log():
            if st.session_state.agent.log_to_sheet():
                st.success("✅ Lead information has been saved! Our team will contact you soon.")
            else:
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
        
        # Add a button to end call
        if st.button("End Call", type="primary"):
            st.session_state.phone_number = None
            st.session_state.agent = None
            st.session_state.messages = []
            st.session_state.voice_enabled = False
            st.rerun()