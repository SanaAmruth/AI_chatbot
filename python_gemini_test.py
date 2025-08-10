# Make sure you have the library installed:
# pip install google-generativeai

import os
import google.generativeai as genai

def run_gemini_inference():
    """
    A simple script to run inference with the Gemini API.
    It reads the API key from the environment variable GEMINI_API_KEY.
    """
    try:
        # --- 1. Configure the API Key ---
        # The library automatically looks for the API key in the
        # GOOGLE_API_KEY or GEMINI_API_KEY environment variables.
        # You can also pass it directly: genai.configure(api_key="YOUR_KEY")
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not found.")
        
        genai.configure(api_key=api_key)
        print("Successfully configured the Gemini API key.")

        # --- 2. Initialize the Model ---
        # We'll use the 'gemini-pro' model which is suitable for a wide
        # range of natural language tasks.
        print("Initializing the Gemini Pro model...")
        model = genai.GenerativeModel('gemini-2.5-flash-lite')

        # --- 3. Send a Prompt and Get the Response ---
        prompt = "In simple terms, what is a large language model?"
        print(f"\nSending prompt: '{prompt}'")
        
        # The generate_content method sends your prompt to the API
        response = model.generate_content(prompt)

        # --- 4. Print the Result ---
        print("\n--- Gemini's Response ---")
        # The response text is available in the 'text' attribute.
        # We add basic error handling in case the response is empty or blocked.
        if response.parts:
            print(response.text)
        else:
            print("The model did not return a valid response.")
            # You can inspect the 'prompt_feedback' for more details if needed
            print("Prompt Feedback:", response.prompt_feedback)

    except Exception as e:
        print(f"\nAn error occurred: {e}")

# --- Run the script ---
if __name__ == "__main__":
    run_gemini_inference()
