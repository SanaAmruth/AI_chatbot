import os
import sqlite3
from flask import Flask, request, jsonify, g
from flask_cors import CORS
import traceback
import google.generativeai as genai

# --- Configuration ---
DB_FILE = "chat_app.db"

# --- Flask App Initialization ---
app = Flask(__name__)
app.config['DATABASE'] = DB_FILE
CORS(app)

# --- Gemini API Configuration ---
# The script will look for the API key in your environment variables.
try:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set.")
    genai.configure(api_key=api_key)
    print("Gemini API key configured successfully.")
except Exception as e:
    print(f"FATAL: Error configuring Gemini API: {e}")


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
    """Handles getting messages and adding a new one using the Gemini API."""
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

            # --- Gemini API Call ---
            # 1. Get history from DB
            cursor.execute("SELECT sender, content FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC", (conversation_id,))
            
            # 2. Format history for Gemini API. The 'bot' role must be 'model'.
            gemini_history = []
            for row in cursor.fetchall():
                role = "model" if row["sender"] == "bot" else "user"
                gemini_history.append({"role": role, "parts": [{"text": row["content"]}]})

            # 3. Initialize the model and generate content
            model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
            response = model.generate_content(gemini_history)
            
            bot_message = response.text

            # 4. Save bot message to DB
            cursor.execute("INSERT INTO messages (conversation_id, sender, content) VALUES (?, ?, ?)",
                           (conversation_id, 'bot', bot_message))
            db.commit()
            return jsonify({"user_message": user_message, "bot_message": bot_message})

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
    if not os.path.exists(DB_FILE):
        print(f"Database file not found. Creating and initializing at {DB_FILE}...")
        init_db()
    
    app.run(debug=True, host='0.0.0.0', port=5000)
