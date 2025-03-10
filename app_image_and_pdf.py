API = "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"  # Replace with your Groq API Key

import streamlit as st
from groq import Groq
import base64
import os
from gtts import gTTS
import time
import uuid
import pdfplumber

# Function to encode the image
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

# Function to extract text from PDF
def extract_text_from_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() or ""  # Handle cases where extract_text() returns None
        return text.strip() if text.strip() else "No text found in the PDF."

# Function to analyze content (image or text)
def analyze_content(messages, is_image=False):
    client = Groq(api_key=API)
    model = "llama-3.2-11b-vision-preview" if is_image else "mixtral-8x7b-32768"
    chat_completion = client.chat.completions.create(
        messages=messages,
        model=model,
        temperature=0.7,
        max_completion_tokens=1024,
        stream=False,
    )
    return chat_completion.choices[0].message.content

# Function to convert text to speech and save as an audio file with a unique name
def text_to_speech(text, filename=None):
    if filename is None:
        filename = f"response_{uuid.uuid4().hex}.mp3"  # Unique filename
    tts = gTTS(text=text, lang="en")
    tts.save(filename)
    time.sleep(0.5)  # Ensure file is fully written
    return filename

# Streamlit UI setup
st.title("Grok Vision AI - Chat Interface with Voice")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "content_processed" not in st.session_state:
    st.session_state.content_processed = False
if "last_audio" not in st.session_state:
    st.session_state.last_audio = None
if "audio_ready" not in st.session_state:
    st.session_state.audio_ready = False
if "is_image" not in st.session_state:
    st.session_state.is_image = False

# Sidebar for content upload
with st.sidebar:
    st.header("Upload Content")
    upload_type = st.radio("Choose upload type:", ("Image", "PDF"))
    if upload_type == "Image":
        uploaded_file = st.file_uploader("Choose an image", type=["png", "jpg", "jpeg"])
    else:  # PDF
        uploaded_file = st.file_uploader("Choose a PDF", type=["pdf"])

# Process uploaded content (image or PDF) only once
if uploaded_file and not st.session_state.content_processed:
    if upload_type == "Image":
        temp_path = "temp_image.jpg"
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.read())
        image_base64 = encode_image(temp_path)
        st.session_state.messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": "Analyze this image and tell me what it contains."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
            ]
        })
        st.session_state.is_image = True
        os.remove(temp_path)
    else:  # PDF
        temp_path = "temp_pdf.pdf"
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.read())
        pdf_text = extract_text_from_pdf(temp_path)
        st.session_state.messages.append({
            "role": "user",
            "content": f"Analyze this PDF content and summarize it:\n\n{pdf_text}"
        })
        st.session_state.is_image = False
        os.remove(temp_path)

    with st.spinner(f"Analyzing {upload_type}..."):
        initial_response = analyze_content(st.session_state.messages, is_image=st.session_state.is_image)
        st.session_state.messages.append({"role": "assistant", "content": initial_response})

        # Generate audio for the initial response
        audio_file = text_to_speech(initial_response)
        st.session_state.last_audio = audio_file
        st.session_state.audio_ready = True

    st.session_state.content_processed = True
    st.rerun()

# Chat interface
chat_container = st.container(height=400)  # Scrollable chat area
with chat_container:
    for idx, message in enumerate(st.session_state.messages):
        if message["role"] == "user":
            if isinstance(message["content"], list):  # Image case
                with st.chat_message("user"):
                    st.write(message["content"][0]["text"])
                    if "image_base64" in locals():
                        st.image(f"data:image/jpeg;base64,{image_base64}", width=200)
            else:  # Text or PDF case
                with st.chat_message("user"):
                    st.write(message["content"])
        else:  # Assistant response
            with st.chat_message("assistant"):
                st.write(message["content"])

# Display and play the latest audio response with a 2-second delay
if st.session_state.last_audio and st.session_state.audio_ready and os.path.exists(st.session_state.last_audio):
    try:
        audio_bytes = open(st.session_state.last_audio, "rb").read()
        st.audio(audio_bytes, format="audio/mp3")
        st.markdown(
            """
            <script>
            setTimeout(function() {
                document.querySelector('audio').play();
            }, 2000);
            </script>
            """,
            unsafe_allow_html=True,
        )
    except FileNotFoundError:
        st.warning("Audio file not found. Retrying on next refresh.")

# Input area at the bottom
user_input = st.chat_input("Ask more about the content or continue the conversation...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.spinner("Thinking..."):
        response = analyze_content(st.session_state.messages, is_image=st.session_state.is_image)
        st.session_state.messages.append({"role": "assistant", "content": response})

        # Generate audio for the new response with a unique filename
        audio_file = text_to_speech(response)
        if st.session_state.last_audio and os.path.exists(st.session_state.last_audio) and st.session_state.last_audio != audio_file:
            os.remove(st.session_state.last_audio)
        st.session_state.last_audio = audio_file
        st.session_state.audio_ready = True

    st.rerun()
