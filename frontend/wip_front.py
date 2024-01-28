from taipy.gui import Gui, Markdown
from vectors.redis_handler import RedisManager
import pandas as pd

# Initialize RedisManager
manager = RedisManager()

# Define the navigation bar and page layout
# nav_bar = """
# <div style='background-color: #333; padding: 10px; color: white; text-align: center;'>
#     <h3>My Website</h3>
# </div>
# """
nav_bar = ""

table_df = pd.DataFrame({
    "File Name": ["first", "second", "third"],
    "Content": ["lorem ipsum", "  File 'src/gevent/_abstract_linkable.py', line 442, in gevent._gevent_c_abstract_linkable.AbstractLinkable._AbstractLinkable__wait_to_be_notified File 'src/gevent/_abstract_linkable.py', line 442, in gevent._gevent_c_abstract_linkable.AbstractLinkable._AbstractLinkable__wait_to_be_notified File 'src/gevent/_abstract_linkable.py', line 442, in gevent._gevent_c_abstract_linkable.AbstractLinkable._AbstractLinkable__wait_to_be_notified", "some text"],

})

page = nav_bar + """
<|layout|type=flexbox|orientation=horizontal|>
    <h1 class="head1">SecondBrain Q&A</h1>
        <center>
            <|{user_input}|input|placeholder=Enter your question here...|>
            <|Ask|button|on_action=on_button_action|>
        </center>
            <|{text}|>

</>
<|SHOW FILES|expandable|
<|{table_df}|table|>
|>
"""

# Initial state
text = ""
user_input = ""

# Action handler for the button
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

# Linking the CSS file
css_file = "styles.css"

# Run the GUI
Gui(page=page, css_file=css_file).run(port=3001)