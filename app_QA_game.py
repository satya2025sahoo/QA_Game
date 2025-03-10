API = "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"  # Replace with your Groq API Key

import streamlit as st
from groq import Groq
import pdfplumber
import os
import random
import json

# Function to extract text from PDF
def extract_text_from_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() or ""
        return text.strip() if text.strip() else "No text found in the PDF."

# Function to generate MCQs based on difficulty level
def generate_mcq(pdf_text, difficulty):
    client = Groq(api_key=API)
    example_json = '''
    {
        "question": "What is the capital of France?",
        "options": ["A) Paris", "B) London", "C) Berlin", "D) Madrid"],
        "answer": "A) Paris"
    }
    '''
    if difficulty == "Easy":
        prompt = f"Based on this text: '{pdf_text[:2000]}', generate an easy multiple-choice question (MCQ) with 4 options (A, B, C, D) and provide the correct answer. Format the response as JSON like this: {example_json}. Ensure options are meaningful and related to the text."
    elif difficulty == "Medium":
        prompt = f"Based on this text: '{pdf_text[:2000]}', generate a medium-difficulty multiple-choice question (MCQ) with 4 options (A, B, C, D) and provide the correct answer. Use moderate complexity. Format the response as JSON like this: {example_json}. Ensure options are meaningful and related to the text."
    else:  # Hard
        prompt = f"Based on this text: '{pdf_text[:2000]}', generate a hard multiple-choice question (MCQ) with 4 options (A, B, C, D) and provide the correct answer. Use twisted language and intricate phrasing. Format the response as JSON like this: {example_json}. Ensure options are meaningful and related to the text."

    response = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="mixtral-8x7b-32768",
        temperature=0.7,
        max_completion_tokens=500,
        stream=False,
    )
    raw_response = response.choices[0].message.content
    st.write(f"Debug: Raw API response: {raw_response}")  # Debugging output

    try:
        mcq_data = json.loads(raw_response)
        # Validate JSON structure
        if "question" not in mcq_data or "options" not in mcq_data or "answer" not in mcq_data or len(mcq_data["options"]) != 4:
            raise ValueError("Invalid MCQ format")
        return mcq_data
    except (json.JSONDecodeError, ValueError):
        # Fallback: Extract meaningful content from raw response if possible
        lines = raw_response.split("\n")
        question = "Generated question failed. What’s in the text?"
        options = ["A) Unknown", "B) Check text", "C) Try again", "D) Skip"]
        answer = "A) Unknown"
        for line in lines:
            if line.strip().startswith("Question:") or "what" in line.lower():
                question = line.strip()
            elif any(line.strip().startswith(x) for x in ["A)", "B)", "C)", "D)"]):
                options = [f"{opt.strip()}" for opt in lines if opt.strip().startswith(("A)", "B)", "C)", "D)"))][:4]
                if len(options) < 4:
                    options.extend([f"{chr(65+i)}) Fallback" for i in range(4 - len(options))])
            elif "answer" in line.lower():
                answer = line.strip().split(":")[-1].strip()
        return {"question": question, "options": options, "answer": answer}

# Streamlit UI setup
st.title("PDF Quiz AI - Test Your Knowledge")

# Initialize session state
if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = None
if "level" not in st.session_state:
    st.session_state.level = None
if "questions_asked" not in st.session_state:
    st.session_state.questions_asked = 0
if "correct_streak" not in st.session_state:
    st.session_state.correct_streak = 0
if "score" not in st.session_state:
    st.session_state.score = 0
if "current_question" not in st.session_state:
    st.session_state.current_question = None
if "user_answer" not in st.session_state:
    st.session_state.user_answer = None
if "show_result" not in st.session_state:
    st.session_state.show_result = False

# Sidebar for PDF upload
with st.sidebar:
    st.header("Upload PDF")
    uploaded_file = st.file_uploader("Choose a PDF", type=["pdf"])

# Process PDF upload
if uploaded_file and not st.session_state.pdf_text:
    temp_path = "temp_pdf.pdf"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.read())
    st.session_state.pdf_text = extract_text_from_pdf(temp_path)
    os.remove(temp_path)
    st.success("PDF uploaded successfully! Please choose a difficulty level.")

# Difficulty selection
if st.session_state.pdf_text and st.session_state.level is None:
    st.subheader("Choose Difficulty Level")
    level = st.radio("Select a starting level:", ("Easy", "Medium", "Hard"))
    if st.button("Start Quiz"):
        st.session_state.level = level
        st.rerun()

# Quiz logic
if st.session_state.level and st.session_state.questions_asked < 10:
    # Generate new question if none exists
    if not st.session_state.current_question:
        mcq = generate_mcq(st.session_state.pdf_text, st.session_state.level)
        st.session_state.current_question = mcq
        st.session_state.show_result = False

    # Display question
    st.subheader(f"Question {st.session_state.questions_asked + 1} ({st.session_state.level})")
    st.write(st.session_state.current_question["question"])
    options = st.session_state.current_question["options"]
    user_answer = st.radio("Select your answer:", options, key=f"q{st.session_state.questions_asked}")

    if st.button("Submit Answer"):
        st.session_state.user_answer = user_answer
        st.session_state.questions_asked += 1
        correct_answer = st.session_state.current_question["answer"]
        st.session_state.show_result = True

        if user_answer == correct_answer:
            st.session_state.correct_streak += 1
            points = {"Easy": 1, "Medium": 2, "Hard": 3}[st.session_state.level]
            st.session_state.score += points
            st.markdown("""
                <div style='text-align: center;'>
                    <h3>Congratulations! 🎉</h3>
                    <img src='https://media.giphy.com/media/3o6Zt6KHxJTbXCnSso/giphy.gif' width='200'>
                </div>
            """, unsafe_allow_html=True)

            # Level up logic
            if st.session_state.correct_streak >= 3:
                if st.session_state.level == "Easy":
                    st.session_state.level = "Medium"
                    st.success("Level increased to Medium!")
                elif st.session_state.level == "Medium":
                    st.session_state.level = "Hard"
                    st.success("Level increased to Hard!")
                st.session_state.correct_streak = 0  # Reset streak after level up
        else:
            st.session_state.correct_streak = 0
            st.error(f"Wrong answer! Correct answer was: {correct_answer}")
        
        st.session_state.current_question = None  # Clear current question for next one
        st.rerun()

# Show final score after 10 questions
if st.session_state.questions_asked >= 10:
    st.subheader("Quiz Completed!")
    st.write(f"Your final score: {st.session_state.score}/30")
    if st.session_state.score >= 25:
        st.balloons()
        st.success("Excellent performance! You’re a quiz master!")
    elif st.session_state.score >= 15:
        st.success("Good job! Solid effort!")
    else:
        st.info("Nice try! Practice makes perfect!")
    if st.button("Restart Quiz"):
        for key in st.session_state.keys():
            del st.session_state[key]
        st.rerun()
