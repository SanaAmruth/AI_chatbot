import os
import sqlite3
from flask import Flask, request, jsonify, send_from_directory, g
from flask_cors import CORS # Import CORS
import requests
import traceback

# --- Configuration ---
DB_FILE = "chat_app.db"
OLLAMA_API_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "phi3:latest"

# --- Flask App Initialization ---
app = Flask(__name__)
app.config['DATABASE'] = DB_FILE

# --- Enable CORS ---
CORS(app)

# --- Database Schema (Embedded) ---
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    sender TEXT NOT NULL CHECK (sender IN ('user', 'bot')),
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
);
"""

# --- Database Handling ---

def get_db():
    """Opens a new database connection for the current request context."""
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    """Closes the database at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Initializes the database using the embedded schema."""
    with app.app_context():
        db = get_db()
        print("Initializing database schema...")
        db.cursor().executescript(SCHEMA_SQL)
        db.commit()
        print("Database initialized.")

# --- API Endpoints ---

@app.route('/')
def index():
    """Serves the main HTML page."""
    return send_from_directory('.', 'index.html')

@app.route('/api/conversations', methods=['GET', 'POST'])
def handle_conversations():
    """Handles getting all conversations and creating a new one."""
    db = get_db()
    cursor = db.cursor()

    if request.method == 'POST':
        try:
            data = request.get_json() or {}
            title = data.get('title', 'New Conversation')
            cursor.execute("INSERT INTO conversations (title) VALUES (?)", (title,))
            db.commit()
            new_id = cursor.lastrowid
            return jsonify({"id": new_id, "title": title}), 201
        except Exception as e:
            traceback.print_exc()
            return jsonify({"error": f"Failed to create conversation: {str(e)}"}), 500

    # Default to GET
    try:
        cursor.execute("SELECT * FROM conversations ORDER BY created_at DESC")
        conversations = [dict(row) for row in cursor.fetchall()]
        return jsonify(conversations)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Failed to retrieve conversations: {str(e)}"}), 500

@app.route('/api/conversations/<int:conversation_id>', methods=['PUT'])
def update_conversation_title(conversation_id):
    """Updates the title of a specific conversation."""
    try:
        data = request.get_json()
        new_title = data.get('title')
        if not new_title:
            return jsonify({"error": "Title is required"}), 400
        db = get_db()
        cursor = db.cursor()
        cursor.execute("UPDATE conversations SET title = ? WHERE id = ?", (new_title, conversation_id))
        db.commit()
        return jsonify({"success": True, "id": conversation_id, "title": new_title})
    except Exception as e:
        print(f"Error updating conversation title: {e}")
        return jsonify({"error": f"Failed to update title: {str(e)}"}), 500

@app.route('/api/conversations/<int:conversation_id>', methods=['PUT', 'DELETE'])
def manage_single_conversation(conversation_id):
    """Updates a conversation's title or deletes it."""
    db = get_db()
    cursor = db.cursor()

    if request.method == 'PUT':
        try:
            data = request.get_json()
            new_title = data.get('title')
            if not new_title:
                return jsonify({"error": "Title is required"}), 400
            
            cursor.execute("UPDATE conversations SET title = ? WHERE id = ?", (new_title, conversation_id))
            db.commit()
            return jsonify({"success": True, "id": conversation_id, "title": new_title})
        except Exception as e:
            print(f"Error updating conversation title: {e}")
            return jsonify({"error": f"Failed to update title: {str(e)}"}), 500
    
    if request.method == 'DELETE':
        try:
            # The ON DELETE CASCADE in the schema will automatically delete associated messages.
            cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
            db.commit()
            
            if cursor.rowcount == 0:
                return jsonify({"error": "Conversation not found"}), 404
                
            return jsonify({"success": True, "message": "Conversation deleted."})
        except Exception as e:
            traceback.print_exc()
            return jsonify({"error": f"Failed to delete conversation: {str(e)}"}), 500

@app.route('/api/conversations/<int:conversation_id>/messages', methods=['GET', 'POST'])
def handle_messages(conversation_id):
    """Handles getting messages and adding a new one to a conversation."""
    db = get_db()
    cursor = db.cursor()

    if request.method == 'POST':
        try:
            data = request.get_json()
            user_message = data.get('message')
            if not user_message:
                return jsonify({"error": "Message is required"}), 400

            # Save user message
            cursor.execute("INSERT INTO messages (conversation_id, sender, content) VALUES (?, ?, ?)",
                           (conversation_id, 'user', user_message))
            db.commit()

            # Get history and call Ollama
            cursor.execute("SELECT sender, content FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC", (conversation_id,))
            history = [{"role": row["sender"], "content": row["content"]} for row in cursor.fetchall()]
            
            ollama_payload = {"model": MODEL_NAME, "messages": history, "stream": False}
            response = requests.post(OLLAMA_API_URL, json=ollama_payload, timeout=60)
            response.raise_for_status()
            bot_message = response.json()['message']['content']

            # Save bot message
            cursor.execute("INSERT INTO messages (conversation_id, sender, content) VALUES (?, ?, ?)",
                           (conversation_id, 'bot', bot_message))
            db.commit()
            return jsonify({"user_message": user_message, "bot_message": bot_message})

        except requests.exceptions.RequestException as e:
            return jsonify({"error": f"Ollama API error: {e}"}), 500
        except Exception as e:
            traceback.print_exc()
            return jsonify({"error": f"An internal error occurred: {str(e)}"}), 500

    # Default to GET
    try:
        cursor.execute("SELECT * FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC", (conversation_id,))
        messages = [dict(row) for row in cursor.fetchall()]
        return jsonify(messages)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Failed to retrieve messages: {str(e)}"}), 500

# --- App Startup ---
if __name__ == '__main__':
    # Ensure the database file exists and has the correct schema
    if not os.path.exists(DB_FILE):
        print(f"Database file not found. Creating and initializing at {DB_FILE}...")
        init_db()
    
    app.run(debug=True, host='0.0.0.0', port=5000)
