# Local Chat Application with Ollama

This project is a simple, self-contained chat application that runs locally on your machine. It uses a Python Flask backend to connect to a local Ollama instance for generating AI responses and saves all conversation history in a SQLite database.


---

## Features

- **Private & Local**: All components (frontend, backend, AI model) can run entirely on your local machine.
- **Conversation History**: Automatically saves and loads all your chats from a local database.
- **Persistent Storage**: Uses SQLite to store conversations, so your data is saved between sessions.
- **Clean UI**: A simple, modern user interface built with Tailwind CSS.
- **Full Chat Functionality**:
    - Create new conversations.
    - Switch between existing conversations.
    - Delete unwanted conversations.

---

## Project Structure


.
├── app.py          # The Python Flask backend
├── index.html      # The HTML/JS frontend
└── chat_app.db     # The SQLite database (created automatically)


---

## Prerequisites

Before you begin, ensure you have the following installed:

1.  **Python 3.10+**: [Download Python](https://www.python.org/downloads/)
2.  **Ollama**: You must have the Ollama service installed. [Download Ollama](https://ollama.com/)
3.  **An Ollama Model**: Pull a model to use with the application. The code defaults to `phi3:latest`.
    ```bash
    ollama pull phi3:latest
    ```

---

## How to Run the Chat Application

To run this application, you will need to open **three separate terminal windows**. Each one will run a different part of the stack.

### Terminal 1: Start the Ollama Service

This terminal ensures the AI model is running and ready to receive requests.

```bash
# Start the Ollama server
ollama serve

Leave this terminal running.

Terminal 2: Start the Python Backend
This terminal runs the Flask application, which handles the logic for saving and retrieving chats.

# Navigate to the project directory
cd /path/to/your/project

# Install the required Python libraries
pip3.10 install Flask Flask-Cors requests

# Run the Python backend server
python3.10 app.py

The server will start on http://localhost:5000. It will also automatically create the chat_app.db database file on its first run. Leave this terminal running.

Terminal 3: Start the Frontend Server
This terminal serves the index.html file to your browser.

# Navigate to the same project directory
# This command starts a simple web server on port 8000
python3.10 -m http.server 8000

Leave this terminal running.

Access the Application
Now, open your web browser and go to the following address:

http://localhost:8000

You can now use the chat application.

Database Management
You can directly inspect the chat database using the sqlite3 command-line tool.

# Navigate to the project directory and open the database
sqlite3 chat_app.db

Once inside the sqlite> prompt, you can run queries:

-- Show all tables
.tables

-- View all conversations
SELECT * FROM conversations;

-- View all messages from a specific chat (e.g., ID 1)
SELECT * FROM messages WHERE conversation_id = 1;

-- Exit the tool
.quit
