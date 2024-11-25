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

levels_choose = data_cluster['level'].unique()
selected_level = st.selectbox("Select a level", levels_choose, key='level_selector')

# Reset index when topic changes
if 'prev_topic' not in st.session_state or st.session_state.prev_topic != selected_topic:
    st.session_state.idx = 0
    st.session_state.prev_topic = selected_topic

# Filter data for the selected topic
topic_data = data_cluster[(data_cluster['topic'] == selected_topic) & (data_cluster['level'] == selected_level)]
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
    st.session_state.idx = st.slider("Select cluster index", 0, len(list_cluster) - 1, st.session_state.idx)
    current_cluster = list_cluster[st.session_state.idx]
    st.subheader(f"Cluster: {current_cluster}")
    # Calculate the progress percentage
    progress_percentage = (st.session_state.idx + 1) / len(list_cluster) * 100

    # Display the progress bar with the percentage
    st.write(f"Progress: {st.session_state.idx + 1}/{len(list_cluster)}")
    st.progress(progress_percentage / 100)

    # Get texts and metadata for the selected cluster
    cluster_data = topic_data[topic_data.index == current_cluster]
    source = cluster_data['key_name'].tolist()[0]
    file_path = cluster_data['file_path'].tolist()[0].split("/")[-1]
    question = cluster_data['Q'].tolist()[0]
    answer = cluster_data['A'].tolist()[0]
    citation = cluster_data['C'].tolist()[0]
    level = cluster_data['level'].tolist()[0]

    law_domain_part1 = "law_domain_part1/"
    law_domain_part2 = "law_domain_part2/"

    full_path_part1 = law_domain_part1 + file_path
    full_path_part2 = law_domain_part2 + file_path

    if os.path.exists(full_path_part1):
        file_path = full_path_part1
    else:
        file_path = full_path_part2


   
    displayPDF(file_path)

st.subheader("Evaluator")
# Text input for the question
question = st.text_area("Question:", value=question)
st.sidebar.subheader("Question Review")
q_1 = st.sidebar.checkbox("Câu hỏi độc lập và dễ hiểu mà không cần phải đọc qua tài liệu.")
q_2 = st.sidebar.checkbox("Câu hỏi không chứa thông tin sai lệch, không có trong văn bản.")
q_3 = st.sidebar.checkbox("Câu hỏi không cứa các từ tham chiếu không rõ ràng.")



answer = st.text_area("Answer:", value=answer)
st.sidebar.subheader("Answer Review")
a_1 = st.sidebar.checkbox("Câu trả lời chính xác và đầy đủ")
a_2 = st.sidebar.checkbox("Câu trả lời không chứa thông tin sai lệch, không có trong văn bản.")
a_3 = st.sidebar.checkbox("Câu trả lời không cứa các từ tham chiếu không rõ ràng.")

citation = st.text_area("Citation:", value=citation)
st.sidebar.subheader("Citation Review")
c_1 = st.sidebar.checkbox("Trích dẫn chính xác từng chữ, liên quan và đầy đủ.")


st.markdown("---")
st.markdown("### Chấm điểm")
grading = st.radio(
    "Choose the appropriate grading category:",
    options=[
        "Câu hỏi không phù hợp với mức độ ❌", 
        "Bài báo không có khả năng tạo ra loại câu hỏi này ❌", 
        "Không Cần Chỉnh Sửa ✅", 
        "Cần Chỉnh Sửa Nhẹ ✅ - *Bạn cần chỉnh sửa hết các lỗi sai trước khi Submit*", 
        "Cần chỉnh Sửa Nhiều ✅- *Câu hỏi hiện tại không khả thi, nhưng nó cung cấp cho bạn ý tưởng để tạo ra các câu hỏi và câu trả lời tương tự.*",
        "Không thể chỉnh sửa ❌ - *câu hỏi và câu trả lời không gợi bất kỳ ý tưởng nào và đòi hỏi phải nghĩ ra câu hỏi-câu trả lời mới khác hoàn toàn so với bản gốc.*"
    ]
)

st.markdown("---")

if grading =="Cần Chỉnh Sửa Nhẹ ✅ - *Bạn cần chỉnh sửa hết các lỗi sai trước khi Submit*":
    st.markdown("##### Cần Chỉnh Sửa Nhẹ (Đạt) - **Bạn cần chỉnh sửa hết các lỗi sai trước khi Submit**")
    correct_1 = st.checkbox("Cần viết lại câu hỏi (giữ nguyên nội dung được hỏi, có thể thêm một vài thông tin bổ sung) cho phù hợp.")
    correct_2 = st.checkbox("Cần viết lại câu trả lời (giữ nguyên nội dung, có thể thêm một vài thông tin bổ sung) cho phù hợp.")
    correct_3 = st.checkbox("Cần viết lại trích dẫn cho phù hợp")

# # Show definitions
# if st.button("Show Grading Category Definitions"):
#     st.session_state.show_definitions = not st.session_state.show_definitions

# if st.session_state.show_definitions:
#     display_grading_definitions()


col1_final, col2_final = st.columns(2)

submission_data = {
    "question": question,
    "answer": answer,
    "citation": {"source": source, "sentences": citation, "file_path": file_path},
    'index': st.session_state.idx,
    'level': level,
    'domain': "law",
    'topic': selected_topic,
    'meta_human': {
        "question": [q_1, q_2, q_3],
        "answer": [a_1, a_2, a_3],
        "citation": [c_1],
        "grading": grading,
        "reason_correct": [correct_1, correct_2, correct_3] if grading == "Cần Chỉnh Sửa Nhẹ **Đạt** - *Bạn cần chỉnh sửa hết các lỗi sai trước khi Submit*" else None
    }
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
