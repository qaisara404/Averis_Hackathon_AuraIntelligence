# File: test_api.py
# Purpose: A simple script to test the core connection to the Gemini API.

import warnings
warnings.filterwarnings("ignore") # Try to suppress warnings one last time

from google import genai
from google.genai import types

# --- IMPORTANT ---
# PASTE YOUR ACTUAL GEMINI API KEY HERE
GEMINI_API_KEY = 'AQ.Ab8RN6K3zW2PS7DwNyMaTgRcvnkTWUEcw9yVrbWrMNoE5tGNWw'
# -----------------

try:
    print("1. Configuring Gemini API client...")
    genai.configure(api_key=GEMINI_API_KEY)

    print("2. Creating the model...")
    # We use gemini-1.5-flash as it's very fast
    model = genai.GenerativeModel('gemini-1.5-flash')

    print("3. Sending a simple test message to the API...")
    response = model.generate_content("Hello, world!")

    print("\n--- RESULTS ---")
    if response.text:
        print("✅ SUCCESS! The API connection is working.")
        print(f"   Gemini's Response: {response.text}")
    else:
        print("❌ FAILED! The API call did not return any text, but there was no error.")

except Exception as e:
    print("\n--- ERROR ---")
    print(f"❌ An error occurred during the API test: {e}")
    print("\n   Possible Causes:")
    print("   - The API Key might be incorrect or expired.")
    print("   - There might be a network issue (firewall, proxy, or unstable connection).")
    print("   - The 'google-generativeai' library might have an issue.")