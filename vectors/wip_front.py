from taipy.gui import Gui, State, Markdown
from redis_handler import RedisManager

# Initialize RedisManager
manager = RedisManager()

# Initial state
State.file_urls = ["https://www.google.com", "https://www.google.com"]
State.user_input = ""
State.text = "Hello! How can I assist you today?"

class User:
    def __init__(self, id, name, birth_year):
        self.id, self.name, self.birth_year = (id, name, birth_year)

users = [
    User(231, "Johanna", 1987),

    ]

user_sel = users[0]

# Define Markdown page with dynamic file section using Taipy bindings
page = """
<|layout|type=flexbox|orientation=horizontal|>
    <h1 class="head1">SecondBrain Q&A</h1>
        <center>
            <|{State.user_input}|input|placeholder=Enter your question here...|>
            <|Ask|button|on_action=on_button_action|>
        </center>
            <|{State.text}|

</>
<|SHOW FILES|expandable|
<|{user_sel}|selector|lov={users}|type=User|adapter={lambda u: (u.id, u.name)}|>
|>
"""

# Action handler for the button
def on_button_action():
    print("Button clicked")
    users.append(User(1, "John", 1979))
    State.file_urls.append("https://abc.com")

# Linking the CSS file
css_file = "styles.css"

# Run the GUI with the Markdown page
gui = Gui(page=Markdown(page), css_file=css_file)
gui.run(port=3001)
