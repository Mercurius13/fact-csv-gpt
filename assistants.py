import openai
import streamlit as st
import time

from openai import OpenAI


# Initialize session state variables
if "file_id_list" not in st.session_state:
    st.session_state.file_id_list = []

if "file_id_check" not in st.session_state:
    st.session_state.file_id_check = []

if "start_chat" not in st.session_state:
    st.session_state.start_chat = False

if "assistant_id" not in st.session_state:
    st.session_state.assistant_id = None


# Set up the Streamlit page
st.set_page_config(page_title="FACT-CSV-GPT", page_icon=":speech_balloon:")


# Function to create a new assistant
def create_new_assistant(name, instructions, model):
    try:
        response = client.beta.assistants.create(
            name=name,
            instructions=instructions,
            model=model,
            tools=[{"type": "code_interpreter"}],
            file_ids=st.session_state.file_id_list
        )
        st.session_state.assistant_id = response.id  # Update assistant ID in session state
        return response.id
    except Exception as e:
        st.error(f"Failed to create new assistant: {e}")
        return None


# Function to delete an existing assistant
def delete_existing_assistant():
    if st.session_state.assistant_id:
        try:
            client.beta.assistants.delete(assistant_id=st.session_state.assistant_id)
            st.session_state.assistant_id = None  # Reset assistant ID in session state
        except Exception as e:
            st.error(f"Failed to delete assistant: {e}")


# Function to reset the chat with a new file
def reset_chat_with_new_file(new_file_id):
    delete_existing_assistant()
    st.session_state.file_id_list.append(new_file_id)
    create_new_assistant(
        name="CSV Data Assistant for FACT",
        instructions="You are a helpful assistant. Users upload CSV files and based on that, you answer their questions.",
        model="gpt-4-1106-preview"
    )


# Function to upload a file to OpenAI
def upload_to_openai(file):
    response = client.files.create(file=file, purpose="assistants")
    return response.id


# Sidebar for API key and file upload
st.sidebar.header("Configuration")
api_key = st.sidebar.text_input("Enter your OpenAI API key", type="password")

# Access to the rest of the app given after the API key is verified
if api_key:
    openai.api_key = api_key
    client = OpenAI(api_key=openai.api_key)
    # Verifying the api key
    try:
        client.models.list()
    except:
        st.sidebar.error("Invalid API key. Please try again.")
        st.stop()
else:
    st.info("Please enter your OpenAI API key in the side bar to continue.")
    st.stop()


# File uploading mechanism
uploaded_file = st.sidebar.file_uploader("Upload a file to train the bot on", key="file_uploader", type=["csv", "txt"])
if st.sidebar.button("Upload File", disabled=len(st.session_state.file_id_list)):
    if uploaded_file:
        if uploaded_file.file_id in st.session_state.file_id_check:
            st.sidebar.warning("File already uploaded.")
        else:
            file_id = upload_to_openai(uploaded_file)
            reset_chat_with_new_file(file_id)
            st.session_state.file_id_check.append(uploaded_file.file_id)
            st.sidebar.success("File uploaded and chat reset.")

    else:
        st.sidebar.warning("Please upload at least one file to start the chat.")

# Starting the chat
if st.session_state.file_id_list:
    if st.sidebar.button("Start Chat", disabled=st.session_state.start_chat):
        if st.session_state.file_id_list:
            st.session_state.start_chat = True
            st.rerun()

# Chat interface (available only after the chat is started)
st.title("FACT CSV-GPT")
st.write("An application which uses OpenAI to answer questions based on QuickSumm by ZeroAndOne Developers.")

if st.session_state.start_chat:
    st.sidebar.markdown("Please reload the page to upload a new file")
    # Initialize more session state variables
    if "openai_model" not in st.session_state:
        st.session_state.openai_model = "gpt-4-1106-preview"
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = client.beta.threads.create().id

    # Display older messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat logic
    if prompt := st.chat_input("What's this file about"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Thread Creation
        thread_message = client.beta.threads.messages.create(
            thread_id=st.session_state.thread_id,
            role="user",
            content=prompt
        )

        # Run instructions
        run = client.beta.threads.runs.create(
            thread_id=st.session_state.thread_id,
            assistant_id=st.session_state.assistant_id,
            instructions="Please answer the queries using the knowledge provided in the files."
        )

        # Retrieve the run response
        while run.status != 'completed':
            time.sleep(1)
            run = client.beta.threads.runs.retrieve(
                thread_id=st.session_state.thread_id,
                run_id=run.id
            )
        messages = client.beta.threads.messages.list(st.session_state.thread_id)

        # obtaining message content from the assistant
        assistant_messages_for_run = [
            message.content[0].text.value for message in messages
            if message.run_id == run.id and message.role == "assistant"
        ][::-1]
        # Displaying new messages
        for message in assistant_messages_for_run:
            st.session_state.messages.append({"role": "assistant", "content": message})
            with st.chat_message("assistant"):
                st.markdown(message)
else:
    st.write("Please upload files and click 'Start Chat' to begin the conversation.")

st.sidebar.markdown("<h5>Made by ZeroAndOne Developers</h5>", unsafe_allow_html=True)
