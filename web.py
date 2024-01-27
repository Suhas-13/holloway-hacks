from taipy import Gui
from taipy.gui import notify, State
import pandas as pd
import numpy as np


context = "The following is a conversation with an AI assistant. The assistant is helpful, creative, clever, and very friendly.\n\nHuman: Hello, who are you?\nAI: I am an AI created by OpenAI. How can I help you today? "
conversation = {
    "Conversation": ["Who are you?", "Hi! I am GPT-3. How can I help you today?"]
}

current_user_message = ""
path = ""

flash = "Empty flashcard"
back = "This is the answer"

upload = """
# File Upload Page
This page includes a file upload button.
<form action="your-server-side-script-url" method="post" enctype="multipart/form-data">
    <input type="file" name="fileToUpload" id="fileToUpload">
    <input type="submit" value="Upload File" name="submit">
</form>
"""

page_file = """
<|{path}|file_selector|extensions=.pdf|label=Upload .pdf file|on_action=analyze_file|>
"""

page = "## This is page 1"
chat = """
<|{conversation}|table|show_all|width=100%|>
<|{current_user_message}|input|label=Write your message here...|on_action=send_message|class_name=fullwidth|>
"""

statistics_page = "This is your progress"


def send_message(state: State) -> None:
    """
    Send the user's message to the API and update the conversation.

    Args:
        - state: The current state.
    """
    # Add the user's message to the context
    state.context += f"Human: \n {state.current_user_message}\n\n AI:"
    # Send the user's message to the API and get the response
    print(state.context)
    # Add the response to the context for future messages
    # state.context += answer
    # Update the conversation
    conv = state.conversation._dict.copy()
    # conv["Conversation"] += [state.current_user_message, answer]
    state.conversation = conv
    # Clear the input field
    state.current_user_message = ""

def analyze_file(state):
    print(state.path)
    state.dataframe2 = dataframe2
    state.treatment = 0
    with open(state.path,"r", encoding="utf-8") as f:
        data = f.read()
        # split lines and eliminates duplicates
        file_list = list(dict.fromkeys(data.replace("\n", " ").split(".")[:-1]))
    
    notify(state, 'info', f'The text is: {state.path}')
    state.text = "Button Pressed"

    state.path = None

# One root page for common content
# The two pages that were created
pages = {"/":"<|toggle|theme|>\n<center>\n<|navbar|>\n</center>",
         "Chat":chat,
         "FlashCards":page,
         "Statistics":statistics_page}

Gui(pages=pages).run()