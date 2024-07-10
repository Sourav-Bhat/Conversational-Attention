import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import os
import logging
import time
import random

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize session state
if "user_data" not in st.session_state:
    st.session_state.user_data = {}
if "messages" not in st.session_state:
    st.session_state.messages = []
if "test_stage" not in st.session_state:
    st.session_state.test_stage = "intro"
if "test_results" not in st.session_state:
    st.session_state.test_results = []
if "reaction_test" not in st.session_state:
    st.session_state.reaction_test = {"state": "waiting", "start_time": None}

# Psychometric Test Questions (based on ASRS v1.1)
asrs_questions = [
    "How often do you have trouble wrapping up the final details of a project, once the challenging parts have been done?",
    "How often do you have difficulty getting things in order when you have to do a task that requires organization?",
    "How often do you have problems remembering appointments or obligations?",
    "When you have a task that requires a lot of thought, how often do you avoid or delay getting started?",
    "How often do you fidget or squirm with your hands or feet when you have to sit down for a long time?",
    "How often do you feel overly active and compelled to do things, like you were driven by a motor?"
]

# Helper Functions
def generate_response(messages, model="gpt-3.5-turbo"):
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"Error in generate_response: {e}")
        st.error(f"Error: {e}")
        return "An error occurred while processing your request."

def conduct_asrs_test():
    st.write("Please answer the following questions based on how you've felt and conducted yourself over the past 6 months.")
    st.write("Use the following scale: 0 = Never, 1 = Rarely, 2 = Sometimes, 3 = Often, 4 = Very Often")
    
    scores = []
    for question in asrs_questions:
        score = st.slider(question, 0, 4, 0)
        scores.append(score)
    
    return scores

def conduct_reaction_time_test():
    if st.session_state.reaction_test["state"] == "waiting":
        if st.button("Start Reaction Time Test"):
            st.session_state.reaction_test["state"] = "get_ready"
            st.session_state.reaction_test["start_time"] = time.time() + random.uniform(2, 5)  # Store start time in session state

    elif st.session_state.reaction_test["state"] == "get_ready":
        st.write("Get ready... The button will turn green soon! Remember we are checking your Attention span!")
        if time.time() > st.session_state.reaction_test.get("start_time", 0):  # Check if start_time is set
            st.session_state.reaction_test["state"] = "click_now"

    # This condition is added to handle the rerun scenario
    if st.session_state.reaction_test["state"] == "click_now":
        reaction_start_time = time.time()
        if st.button("Click Now!", key="reaction_button", type="primary"):
            reaction_time = time.time() - reaction_start_time
            st.session_state.reaction_test["state"] = "done"
            return reaction_time

    elif st.session_state.reaction_test["state"] == "done":
        st.write("Test completed!")

    return None

def calculate_attention_score(asrs_scores, reaction_time):
    # Calculate ASRS score (0-24 range)
    asrs_total = sum(asrs_scores)
    asrs_normalized = 1 - (asrs_total / 24)  # Invert so higher is better

    # Normalize reaction time (assuming average human reaction time is ~0.25 seconds)
    reaction_normalized = max(0, min(1, 1 - (reaction_time - 0.15) / 0.2))

    # Combine scores (equal weight)
    combined_score = (asrs_normalized + reaction_normalized) / 2

    # Convert to 0-10 scale
    final_score = round(combined_score * 10, 1)

    # Calculate attention span in seconds (hypothetical mapping)
    attention_span_seconds = int(final_score * 3)  # 0-30 seconds range

    return final_score, attention_span_seconds

# Streamlit App
st.title("FocusForward: Attention Span Assessment")

# Stage-based UI rendering
if st.session_state.test_stage == "intro":
    if "name" not in st.session_state.user_data:
        name = st.text_input("What's your name?")
        if name:
            st.session_state.user_data["name"] = name
    elif "age" not in st.session_state.user_data:
        age = st.text_input("How old are you?")
        if age:
            try:
                st.session_state.user_data["age"] = int(age)
                st.session_state.test_stage = "asrs"  # Transition to the next stage
            except ValueError:
                st.error("Please enter a valid age (number).")

elif st.session_state.test_stage == "asrs":
    st.write("ASRS v1.1 Screener")
    asrs_scores = conduct_asrs_test()
    if st.button("Submit ASRS Test"):
        st.session_state.test_results = asrs_scores
        st.session_state.test_stage = "reaction"  # Transition to the next stage

elif st.session_state.test_stage == "reaction":
    st.write("Reaction Time Test")
    if st.session_state.reaction_test["state"] == "waiting":
        if st.button("Start Reaction Time Test"):
            st.session_state.reaction_test["state"] = "get_ready"
            st.session_state.reaction_test["start_time"] = time.time() + random.uniform(2, 5)  # Store start time in session state
    
    elif st.session_state.reaction_test["state"] == "get_ready":
        st.write("Get ready... The button will turn green soon!")
        if time.time() > st.session_state.reaction_test["start_time"]:
            if st.button("Click Now!", key="reaction_button", type="primary"):
                reaction_time = time.time() - st.session_state.reaction_test["start_time"]
                st.session_state.reaction_test["state"] = "done"
                st.session_state.reaction_test["reaction_time"] = reaction_time  # Store reaction time
                st.session_state.test_stage = "results"  # Transition to the next stage


elif st.session_state.test_stage == "results":
    asrs_scores = st.session_state.test_results[:-1]
    reaction_time = st.session_state.test_results[-1]
    
    final_score, attention_span_seconds = calculate_attention_score(asrs_scores, reaction_time)
    
    st.write(f"Thank you, {st.session_state.user_data['name']}!")
    st.write(f"Your Attention Score: {final_score}/10")
    st.write(f"Estimated Attention Span: {attention_span_seconds} seconds")
    st.write(f"Your reaction time: {reaction_time:.3f} seconds")
    
    if final_score < 3:
        advice = "Your score indicates potential attention difficulties. Consider consulting a healthcare professional for a comprehensive evaluation."
    elif final_score < 7:
        advice = "Your score is in the average range. There are techniques you can use to improve your focus and attention."
    else:
        advice = "Great job! You have a strong attention span. Keep up the good work and continue practicing mindfulness techniques."
    
    st.write(advice)


    if st.button("Restart Test"):
        for key in st.session_state.keys():
            del st.session_state[key]
        st.experimental_rerun()