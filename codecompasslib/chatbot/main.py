"""
The entry point of application that brings everything together and runs the chatbot.
"""
from secrets_manager import load_openai_key, load_github_token, load_assistant_instructions
from chatbot_management import initialize_client, create_assistant, load_tools, retrieve_assistant, run_chatbot

# Load secrets
openAI_key = load_openai_key(file_path='./secrets/openAI_key')
github_token = load_github_token(file_path='./secrets/github_token')

# Initialize the OpenAI client
client = initialize_client(openAI_key)

# Create an assistant (This should not be used if the assistant already exists)
"""
instructions = load_assistant_instructions(file_path='secrets/instructions')
new_assistant = create_assistant(
    client=client,
    name="CodeCompass",
    instructions=instructions,
    model="gpt-4-0125-preview",
    tools=load_tools('codecompasslib/chatbot/tools.json'))
"""
# Retrieve assistant using GPT-4 (This should be used for final demo)
#assistant = retrieve_assistant(client, 'asst_lfVLtdNac9aVUvDIIlw5c1nY')

# Retrieve assistant using GPT-3.5
assistant = retrieve_assistant(client, 'asst_cibfhJsvFEKbAo7EmaS34oQD')

# Run the chatbot
run_chatbot(client, assistant=assistant)