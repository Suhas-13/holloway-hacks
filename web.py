from taipy import Gui
from taipy.gui import notify, State
import pandas as pd
import numpy as np
import flashcard as fc
import openai



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

## This needs to be updated regurlrly
all_flashcards = fc.all_flashcards()
flashcards = [Flashcard(question=i[0], answer= i[1]) for i in all_flashcards]
current_card = 0
max_card = len(flashcards)

dataset = pd.read_csv("pdf.csv")
context = ""
current_user_message = ""
conversation = {"Conversation": ["Converse with your Documents"]}

current_card = 0
answer = ""


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

<|layout|s

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

def style_conv(state: State, idx: int, row: int) -> str:
        if idx is None:
            return None
        elif idx % 2 == 0:
            return "user_message"
        else:
            return "gpt_message"

def show_answer(state: State):
        state.answer = state.flashcards[state.current_card].answer

def next_card(state: State):
    state.answer = ""
    state.current_card = (state.current_card + 1) % len(state.flashcards)
    state.flashcards[state.current_card].show_answer = False

def send_message(state: State):
    # Add the user's message to the context
    state.context = f"\n {state.current_user_message}\n"
    # Replace with your function
    answer = ask_openai(state.current_user_message)

    state.context += answer
    # Update the conversation
    conv = state.conversation._dict.copy()
    conv["Conversation"] += [state.current_user_message, answer]
    state.conversation = conv
    # Clear the input field
    state.current_user_message = ""


pages = {"/":"<|toggle|theme|>\n<center>\n<|navbar|>\n</center>",
         "Chat":chat,
         "FlashCards":flashcard_page,
         "Statistics":statistics_page}

if __name__ == "__main__":
    Gui(pages=pages, css_file="main.css").run()