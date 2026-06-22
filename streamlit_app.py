import streamlit as st
from google import genai
from google.genai import types
import requests
import os

# Mobile-first view setup
st.set_page_config(page_title="SoFlo Event Agent", page_icon="📍", layout="centered")

st.title("📍 SoFlo Event Concierge")
st.caption("Scan and pivot weekend events across South Florida")

# Clean, thumb-friendly sidebar controls for the S24 screen
st.sidebar.header("Navigation Settings")
base_city = st.sidebar.selectbox(
    "Your Current Base City:",
    ["Boca Raton", "Delray Beach", "West Palm Beach", "Fort Lauderdale", "Miami"]
)

max_drive = st.sidebar.slider("Max Drive Time (Mins):", 15, 90, 45, step=15)

category_pref = st.sidebar.radio(
    "Interest Vector Profile:",
    ["All Events", "Family & Kids Activities", "Local Markets & Festivals", "Sports & High-Performance Training"]
)

# Fetch Gemini API Key safely from Streamlit Cloud Secrets dashboard configuration
# The new google-genai library accepts api_key passed directly into the Client constructor
api_key = os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")

if not api_key:
    st.error("⚠️ Gemini API Key not found! Please set GEMINI_API_KEY in Streamlit Secrets.")
    st.stop()

# Initialize the Gemini Client passing the explicit API key
client = genai.Client(api_key=api_key)

# Initialize persistent message logs for conversational consistency
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": f"Hi! I'm ready to analyze weekend events surrounding **{base_city}**. Ask me what's happening or request specific recommendations!"}]

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Interactive chat input bar at the bottom of the device screen
if user_query := st.chat_input("What should we do this Saturday?"):
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.markdown(user_query)
        
    with st.chat_message("assistant"):
        with st.spinner("Querying cloud event infrastructure..."):
            pref = None if category_pref == "All Events" else category_pref
            
            # Pointing directly to your live, successful Render deployment instance
            backend_url = "https://soflo-event-api.onrender.com/api/recommendations"
            payload = {"base_city": base_city, "max_drive_time": max_drive, "category_preference": pref}
            
            try:
                # 1. Fetch filtered regional events from Render API
                api_response = requests.get(backend_url, params=payload).json()
                
                # Check if backend successfully found matching events
                events_list = api_response.get("recommendations", [])
                
                if not events_list:
                    response_text = "No events matched your exact drive time and category limits. Try increasing your driving range in the sidebar!"
                else:
                    # 2. Contextual prompt engineering instructing Gemini to display clickable markdown URLs
                    prompt = f"""
                    The user is asking: '{user_query}'. 
                    Here is the real-time filtered JSON event data matching their current mobile parameters: {str(api_response)}. 
                    
                    Present the matching options clearly. For every single event returned, you MUST include a clean markdown hyperlink using the exact 'source_url' provided so it is clickable on a phone screen.
                    Example format: **[Click Here to View Event Source Site](url)**
                    """
                    
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            system_instruction="You are a mobile event layout generator. Keep descriptions concise for phone viewing and maximize bold headings and bullet points. Always ensure URLs are wrapped inside standard clickable markdown link formatting."
                        )
                    )
                    response_text = response.text
                
                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
                
            except Exception as e:
                st.error(f"Could not reach backend or Gemini service. Error: {e}")
