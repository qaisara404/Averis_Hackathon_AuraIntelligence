import warnings
# Suppress any library warnings to keep terminal output clean and professional for judges
warnings.filterwarnings("ignore")

import os
import json
import glob
import sys
import google.generativeai as genai

# ==========================================
# ⚙️ CONFIGURATION & API SETUP
# ==========================================
# YOUR ACTIVE GEMINI API KEY:
GEMINI_API_KEY = 'AQ.Ab8RN6K3zW2PS7DwNyMaTgRcvnkTWUEcw9yVrbWrMNoE5tGNWw'

# Configure the traditional SDK
try:
    genai.configure(api_key=GEMINI_API_KEY)
    # Using the strict fully-qualified name to fix the 404/v1beta issue
    model = genai.GenerativeModel('models/gemini-3.6-flash')
except Exception as e:
    print(f"❌ Failed to configure Gemini Client. This is likely an API Key or Network issue.")
    print(f"   Error Details: {e}")
    sys.exit(1)

# ==========================================
# 🧠 AI CLASSIFIER FUNCTION
# ==========================================
def classify_email(subject, body):
    """
    Uses the Gemini API to analyze the email subject and body,
    then classifies it into one of the 5 categories required by Averis.
    """
    prompt = f"""
    You are an expert shipping operations assistant.
    Your task is to classify the following email into EXACTLY one of these five categories:
    - BL_COMPARISON : The email asks to verify, check, compare, or confirm a draft Bill of Lading (BL) against a Shipping Instruction (SI). (e.g., "please check draft BL against SI", "confirm docs", "revert with discrepancy").
    - SI_REQUEST : The email is a request to create or submit a new Shipping Instruction (SI).
    - INVOICE_QUERY : The email asks about invoices, payments, billing, or financial statements.
    - GENERAL : General business communications, greeting messages, or standard shipping inquiries that do NOT ask for document verification or invoice queries.
    - SPAM : Unsolicited marketing emails, system notifications, or completely irrelevant junk mail.

    Email Subject: {subject}
    Email Body:
    ---
    {body}
    ---

    Respond ONLY with the category name (e.g., BL_COMPARISON, SI_REQUEST, INVOICE_QUERY, GENERAL, or SPAM). Do not include any other text, markdown formatting, or explanations.
    """
    
    try:
        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.1}
        )
        category = response.text.strip().upper()
        
        # Validation fallback to ensure safe category parsing
        for valid_cat in ["BL_COMPARISON", "SI_REQUEST", "INVOICE_QUERY", "GENERAL", "SPAM"]:
            if valid_cat in category:
                return valid_cat
                
        return "GENERAL"  # Fallback default
    except Exception as e:
        print(f"❌ Gemini API Error during classification: {e}")
        return "GENERAL"

# ==========================================
# 🏃‍♂️ RUN SIMULATION & TEST AGAINST GROUND TRUTH
# ==========================================
def main():
    print("🚀 Starting Phase 1: Email Classification Benchmark...\n")
    
    # 0. Quick Connection Check
    print("🔗 Checking Gemini API Connection...")
    try:
        test_response = model.generate_content("Say 'Connection Successful!' if you can read this.")
        print(f"📡 API Status: {test_response.text.strip()}\n")
    except Exception as e:
        print(f"❌ Connection Failed: Could not connect to Gemini API. Error: {e}")
        print("💡 Troubleshoot Steps:")
        print("   1. Check your internet connection (try switching to mobile hotspot).")
        print("   2. Verify that your API Key is correct and active.\n")
        return

    # 1. Load Ground Truth (Answer Key)
    try:
        with open('ground_truth.json', 'r') as f:
            ground_truth = json.load(f)
    except FileNotFoundError:
        print("❌ Error: 'ground_truth.json' not found. Please run 'generate.py' first.")
        return

    # 2. Get email files from the 'inbox' directory (testing the first 10 files)
    email_files = sorted(glob.glob(os.path.join('inbox', 'email_*.json')))[:10]
    
    if not email_files:
        print("❌ Error: 'inbox' folder is empty or not found!")
        return

    correct_predictions = 0
    incorrect_predictions = 0

    print(f"Testing {len(email_files)} sample emails from 'inbox'...")
    print("-" * 70)

    for i, file_path in enumerate(email_files, 1):
        # Read the email JSON file
        with open(file_path, 'r', encoding='utf-8') as f:
            email_data = json.load(f)
        
        email_id = email_data['email_id']
        subject = email_data['subject']
        body = email_data['body']
        
        print(f"🔄 [{i}/10] Sending Email {email_id} to Gemini API...")
        
        # Get AI Prediction
        predicted_cat = classify_email(subject, body)
        
        # Compare with ground truth
        actual_cat = ground_truth.get(email_id, {}).get('category', 'UNKNOWN')
        
        if predicted_cat == actual_cat:
            status = "✅ MATCH!"
            correct_predictions += 1
        else:
            status = f"❌ MISMATCH! (Actual: {actual_cat})"
            incorrect_predictions += 1
            
        print(f"📬 Email ID : {email_id}")
        print(f"   Subject  : {subject[:50]}...")
        print(f"   AI Pred  : {predicted_cat}")
        print(f"   Status   : {status}")
        print("-" * 70)

    # Calculate Accuracy
    total = correct_predictions + incorrect_predictions
    accuracy = (correct_predictions / total) * 100
    performance_tag = "🏆 EXCELLENT ACCURACY!" if accuracy == 100 else "👍 Good Job!"
    
    print(f"\n📊 FINAL BENCHMARK RESULTS:")
    print(f"   Total Emails Tested: {total}")
    print(f"   Accuracy Rate      : {accuracy:.1f}% - {performance_tag}")

if __name__ == '__main__':
    main()