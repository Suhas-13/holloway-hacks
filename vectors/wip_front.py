from taipy.gui import Gui, State, Markdown
from redis_handler import RedisManager
import os
from taipy.gui import navigate


# Initialize RedisManager
manager = RedisManager()

# Initial state
text = "Hello! How can I assist you today?"
user_input = ""

class File:
    def __init__(self, file_name, url):
        self.file_name = file_name
        self.url = "http://127.0.0.1:3001/pdfs/" + self.file_name


files = []

files_sel = None

def on_button_action(state):
    try:
        state.text = "Loading..."
        query = state.user_input
        response = manager.ask_gpt(query)
        state.text = response
    except Exception as e:
        state.text = f"Error: {str(e)}"
    finally:
        state.user_input = ""

# Define Markdown page with dynamic file section using Taipy bindings
page = """
<|layout|type=flexbox|orientation=horizontal|>
    <h1 class="head1">SecondBrain Q&A</h1>
        <center>
            <|{user_input}|input|placeholder=Enter your question here...|>
            <|Ask|button|on_action=on_button_action|>
        </center>
        <br />
        <center>
            <|{text}|>
        </center>

</>

<br />
<|SHOW FILES|expandable|
<|{files_sel}|selector|on_change=on_select_change|class_name=test|lov={files}|type=File|adapter={lambda u: (u.file_name)}|>
|>
"""

def on_select_change(state, var_name, value):
    print(value.url)
    navigate(state, value.url)
    
def get_pdf_files():
    file_names = os.listdir("pdfs/")
    global files
    files.clear()
    for file in file_names:
        if file.endswith(".pdf") and file.split(".pdf")[0]:
            files.append(File(file, os.path.realpath("pdfs/" + file)))
    
# Action handler for the button

def on_navigate(state, page_name):
    get_pdf_files()
    return page_name

# Linking the CSS file
css_file = "styles.css"

# Run the GUI with the Markdown page
gui = Gui(page=Markdown(page), css_file=css_file, path_mapping = {"pdfs": os.getcwd() + "/pdfs"})
gui.run(port=3001)
