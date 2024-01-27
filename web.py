from taipy import Gui
from taipy.gui import notify, State
import pandas as pd
import numpy as np
import flashcard as fc


context = "The following is a conversation with an AI assistant. The assistant is helpful, creative, clever, and very friendly.\n\nHuman: Hello, who are you?\nAI: I am an AI created by OpenAI. How can I help you today? "
conversation = {
    "Conversation": ["Who are you?", "Hi! I am GPT-3. How can I help you today?"]
}

current_user_message = ""
path = ""

chat = """
<|{conversation}|table|show_all|width=100%|>
<|{current_user_message}|input|label=Write your message here...|on_action=send_message|class_name=fullwidth|>
"""

page_file = """
<|{path}|file_selector|extensions=.pdf|label=Upload .pdf file|on_action=analyze_file|>
"""
"""## Flashcards

### 1. Question: What is the capital of France?
<details><summary>Answer</summary>
Paris
</details>
"""

# Define the state
class Flashcard:
    def __init__(self, question, answer):
        self.question = question
        self.answer = answer
        self.show_answer = False

# Create a list of flashcards
flashcards = [
    Flashcard("What is the capital of France?", "Paris"),
    Flashcard("What is the chemical formula for water?", "H2O"),
    Flashcard("Who wrote 'To Kill a Mockingbird'?", "Harper Lee"),
]


current_card = 0
answer = ""

# Define actions
def show_answer(state: State):
    state.answer = state.flashcards[state.current_card].answer

def next_card(state: State):
    state.answer = ""
    state.current_card = (state.current_card + 1) % len(state.flashcards)
    state.flashcards[state.current_card].show_answer = False


show_pane = False

"""
<|d-flex|
<|{show_pane}|pane|persistent|width=100px|>


This button can be pressed to open the persistent pane:
<|Open|button|on_action={lambda s: s.assign("show_pane", True)}|>
|>

"""

visibility = False

flashcard_page = """

<|layout|

<|card flash_question |  
<|{flashcards[current_card].question} |>
|>


<| card flash_answer |
<|{answer} |> 

|>

|>

<|Show Answer|button|on_action=show_answer|>
<|Next_Card|button|on_action=next_card|>

"""

dataset = pd.read_csv("pdf.csv")
statistics_page = """

## All PDFs Progress

<|{dataset}|table|height=300px|width=50%|>

"""

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
         "FlashCards":flashcard_page,
         "Statistics":statistics_page}

Gui(pages=pages).run()