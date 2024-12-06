import streamlit as st
import pandas as pd
import numpy as np
import re
from pymongo import MongoClient
from pymongo.server_api import ServerApi
import random
import streamlit.components.v1 as components
import os
import json
import datetime
import base64

username = os.getenv('MONGO_USERNAME')
password = os.getenv('MONGO_PASSWORD')

st.write(username)

@st.cache_data
def load_data():
    # Load the CSV data
    data = pd.read_csv("combined_law_data.csv")
    
    # Load the JSON metadata
    with open("law_metadata.json", "r", encoding="utf-8") as file:
        law_metadata = json.load(file)
    
    # Create a mapping of file_path to key_name from the JSON metadata
    file_path_to_key_name = {
        metadata["file_path"]: key_name
        for key_name, metadata in law_metadata.items()
    }
    
    # Add a new column 'key_name' to the DataFrame based on the file_path column
    data["key_name"] = data["file_path"].map(file_path_to_key_name)
    
    return data

def displayPDF(file):
    # Opening file from file path
    with open(file, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')

    # Embedding PDF in HTML
    pdf_display =  f"""<embed
    class="pdfobject"
    type="application/pdf"
    title="Embedded PDF"
    src="data:application/pdf;base64,{base64_pdf}"
    style="overflow: auto; width: 100%; height: 70vh;">"""

    # Displaying File
    st.markdown(pdf_display, unsafe_allow_html=True)

    
# Load the data
data_cluster = load_data()

if 'start_time' not in st.session_state:
    st.session_state.start_time = datetime.datetime.now()

# Streamlit app
st.title("ViRAG-Bloom Human Evaluator")

# Topic selection
topics = sorted(data_cluster['topic'].unique())
selected_topic = st.selectbox("Select a topic", topics, key='topic_selector')
# Reset index when topic changes
if 'prev_topic' not in st.session_state or st.session_state.prev_topic != selected_topic:
    st.session_state.idx = 0
    st.session_state.prev_topic = selected_topic
# Filter data for the selected topic
topic_data = data_cluster[(data_cluster['topic'] == selected_topic)]
st.write("Length of topic: ", len(topic_data))
list_cluster = sorted(topic_data.index.unique().tolist())

col1, col2 = st.columns(2)

with col1:
    if st.button("Previous"):
        if st.session_state.idx > 0:
            st.session_state.idx -= 1
        else:
            st.session_state.idx = len(list_cluster) - 1  # Loop back to end

        st.session_state.start_time = datetime.datetime.now()

with col2:
    if st.button("Next"):
        if st.session_state.idx < len(list_cluster) - 1:
            st.session_state.idx += 1
        else:
            st.session_state.idx = 0  # Loop back to start

        st.session_state.start_time = datetime.datetime.now()

# Display selected cluster
st.subheader(f"Topic: {selected_topic}")
if list_cluster:
    # Initialize file paths in session state if not already present
    if 'file_paths' not in st.session_state:
        st.session_state.file_paths = []
    
    # Randomly select two different clusters
    selected_clusters = random.sample(list_cluster, 2)
    st.session_state.file_paths = []  # Reset file paths for new selection
    
    col1, col2 = st.columns(2)
    for idx, cluster in enumerate(selected_clusters):
        with col1 if idx == 0 else col2:
            st.subheader(f"Cluster: {cluster}")
            cluster_data = topic_data[topic_data.index == cluster]
            
            if not cluster_data.empty:
                file_path = cluster_data['file_path'].tolist()[0].split("/")[-1]
                source = cluster_data['key_name'].tolist()[0]
                st.session_state.file_paths.append({"source": source, "file_path": file_path})
                law_domain_part1 = "law_domain_part1/"
                law_domain_part2 = "law_domain_part2/"

                full_path_part1 = law_domain_part1 + file_path
                full_path_part2 = law_domain_part2 + file_path

                if os.path.exists(full_path_part1):
                    file_path = full_path_part1
                else:
                    file_path = full_path_part2
                
                # Store the file path
                
                displayPDF(file_path)


question = st.text_area("Question")
answer = st.text_area("Answer")

col1_final, col2_final = st.columns(2)

submission_data = {
    "question": question,
    "answer": answer,
    "citation": st.session_state.file_paths,
    'level': "Analyze",
    'domain': "law",
    'topic': selected_topic,
}

with col1_final:
    if st.button("Preview"):
        # Format data into JSON
        
            # if submission_data['task'] == 'Read':
            #     submission_data['question_type'] = question_type
            #     submission_data['answer_type'] = answer_type
            #     submission_data['reason_type'] = reason_type
            st.write(submission_data)

if 'mongo_client' not in st.session_state:
    mongo_uri = f"mongodb+srv://{username}:{password}@cluster0.wbusr.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    st.session_state.mongo_client = MongoClient(mongo_uri, server_api=ServerApi('1'))
    st.session_state.db = st.session_state.mongo_client["localhost"]
    st.session_state.collection = st.session_state.db["Human_check_law_domain"]
  
with col2_final:
  # Submit button
  if st.button("Submit"):
    end_time = datetime.datetime.now()
    time_taken = (end_time - st.session_state.start_time).total_seconds()
    submission_data['time_taken_seconds'] = time_taken
    st.write(st.session_state.collection.insert_one(submission_data))

def cleanup():
    if 'mongo_client' in st.session_state:
        st.session_state.mongo_client.close()

# Register the cleanup function to be called on app exit
st.cache_resource(cleanup)
