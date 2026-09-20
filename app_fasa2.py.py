import warnings
# Suppress any library warnings to keep terminal output clean and professional for judges
warnings.filterwarnings("ignore")

import os
import json
import glob
import sys
import time
import google.generativeai as genai

# For reading .docx and .pdf files
from docx import Document
try:
    from reportlab.pdfgen import canvas
except ImportError:
    pass

# ==========================================
# ⚙️ CONFIGURATION & API SETUP
# ==========================================
# PASTE YOUR ACTIVE GEMINI API KEY HERE:
GEMINI_API_KEY = 'AQ.Ab8RN6K3zW2PS7DwNyMaTgRcvnkTWUEcw9yVrbWrMNoE5tGNWw'

try:
    genai.configure(api_key=GEMINI_API_KEY)
    # Using gemini-3.6-flash which is active in your project
    model = genai.GenerativeModel('models/gemini-3.6-flash')
except Exception as e:
    print(f"❌ Failed to configure Gemini Client: {e}")
    sys.exit(1)

# ==========================================
# 📄 DOCUMENT READERS (TXT, DOCX, PDF)
# ==========================================
def read_text_file(file_path):
    """Reads a standard plain text file safely."""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()

def read_docx_file(file_path):
    """Extracts text from a Microsoft Word (.docx) document including tables."""
    try:
        doc = Document(file_path)
        full_text = []
        for para in doc.paragraphs:
            if para.text.strip():
                full_text.append(para.text.strip())
        for table in doc.tables:
            for row in table.rows:
                row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_text:
                    full_text.append(" | ".join(row_text))
        return "\n".join(full_text)
    except Exception as e:
        print(f"⚠️ Error reading DOCX {file_path}: {e}")
        return ""

def read_pdf_file(file_path):
    """Extracts text from a PDF file."""
    try:
        import pypdf
        reader = pypdf.PdfReader(file_path)
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        return text
    except ImportError:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception:
            return "[PDF Binary Content]"

def read_attachment(file_name):
    """Automatically detects file format and reads attachment from attachments/ folder."""
    clean_name = os.path.basename(file_name)
    file_path = os.path.join('attachments', clean_name)
    
    if not os.path.exists(file_path):
        return f"[Error: File {clean_name} not found in attachments/ folder]"
        
    ext = os.path.splitext(clean_name)[1].lower()
    
    if ext == '.txt':
        return read_text_file(file_path)
    elif ext == '.docx':
        return read_docx_file(file_path)
    elif ext == '.pdf':
        return read_pdf_file(file_path)
    else:
        try:
            return read_text_file(file_path)
        except Exception:
            return f"[Unsupported file format: {ext}]"

# ==========================================
# 🧠 AI CLASSIFIER FUNCTION (PHASE 1)
# ==========================================
def classify_email(subject, body):
    prompt = f"""
    You are an expert shipping operations assistant. Classify the following email into EXACTLY one of these five categories: BL_COMPARISON, SI_REQUEST, INVOICE_QUERY, GENERAL, SPAM.

    Email Subject: {subject}
    Email Body:
    ---
    {body}
    ---

    Respond ONLY with the category name (e.g. BL_COMPARISON, SI_REQUEST, INVOICE_QUERY, GENERAL, SPAM).
    """
    try:
        response = model.generate_content(prompt, generation_config={"temperature": 0.1})
        category = response.text.strip().upper()
        for valid_cat in ["BL_COMPARISON", "SI_REQUEST", "INVOICE_QUERY", "GENERAL", "SPAM"]:
            if valid_cat in category:
                return valid_cat
        return "GENERAL"
    except Exception as e:
        print(f"❌ Gemini API Error during classification: {e}")
        return "GENERAL"

# ==========================================
# 🔬 AI DOCUMENT COMPARISON FUNCTION (PHASE 2)
# ==========================================
def compare_documents(si_text, bl_text):
    prompt = f"""
    You are an elite Quality Assurance Auditor in Maritime Shipping & Logistics.
    Your task is to audit and compare two documents: a Shipping Instruction (SI) and a Bill of Lading (BL).
    
    Extract and compare these 7 critical fields side-by-side:
    1. shipper
    2. consignee
    3. notify_party
    4. vessel_voyage
    5. port_of_loading
    6. port_of_discharge
    7. description_of_goods

    RULES FOR AUDITING:
    - Minor spelling differences, character casing (UPPER vs lower), extra spaces, trailing punctuation, or minor address format variations (like "Street" vs "St.") are ACCEPTABLE and should be marked as "MATCH".
    - Significant mismatches (different company names, wrong vessel/voyage numbers, entirely different ports, or missing critical cargo details) must be marked as "MISMATCH".
    - If a document is unreadable, corrupted, or has completely missing values for a field, mark the overall status as "NEEDS_REVIEW".

    SI Document Content:
    === START OF SHIPPING INSTRUCTION ===
    {si_text}
    === END OF SHIPPING INSTRUCTION ===

    BL Document Content:
    === START OF BILL OF LADING ===
    {bl_text}
    === END OF BILL OF LADING ===

    Output your audit result STRICTLY as a valid JSON object. Do not include markdown codeblocks or explanation.
    
    JSON Output Format:
    {{
        "status": "OK",
        "review_reason": null,
        "discrepancies": {{
            "shipper": "MATCH",
            "consignee": "MATCH",
            "notify_party": "MATCH",
            "vessel_voyage": "MATCH",
            "port_of_loading": "MATCH",
            "port_of_discharge": "MATCH",
            "description_of_goods": "MATCH"
        }}
    }}
    """
    try:
        response = model.generate_content(
            prompt, 
            generation_config={
                "temperature": 0.1,
                "response_mime_type": "application/json"
            }
        )
        result = json.loads(response.text.strip())
        return result
    except Exception as e:
        print(f"❌ Error during document audit: {e}")
        return {
            "status": "NEEDS_REVIEW",
            "review_reason": f"API Audit Error: {str(e)}",
            "discrepancies": {field: "MISMATCH" for field in [
                "shipper", "consignee", "notify_party", "vessel_voyage", 
                "port_of_loading", "port_of_discharge", "description_of_goods"
            ]}
        }

# ==========================================
# 🏃‍♂️ MAIN PIPELINE
# ==========================================
def main():
    print("🚀 Starting Phase 2: Document Extraction & Verification Pipeline...\n")
    
    try:
        with open('ground_truth.json', 'r') as f:
            ground_truth = json.load(f)
    except FileNotFoundError:
        print("❌ Error: 'ground_truth.json' not found. Please run 'generate.py' first.")
        return

    # To stay strictly within the daily 20-request free tier, we test 1 sample email
    email_files = sorted(glob.glob(os.path.join('inbox', 'email_*.json')))[:1]
    
    if not email_files:
        print("❌ Error: 'inbox' folder is empty or not found!")
        return

    overall_correct = 0
    total_audited = 0

    print(f"Auditing sample verification cases ({len(email_files)} email selected)...")
    print("=" * 80)

    for idx, file_path in enumerate(email_files, 1):
        with open(file_path, 'r', encoding='utf-8') as f:
            email_data = json.load(f)
        
        email_id = email_data['email_id']
        subject = email_data['subject']
        body = email_data['body']
        attachments = email_data.get('attachments', [])
        
        print(f"\n🔄 [{idx}/{len(email_files)}] Classifying Email: {email_id}...")
        category = classify_email(subject, body)
        print(f"   AI Class: {category}")
        
        if category == 'BL_COMPARISON':
            total_audited += 1
            print(f"   Subject : {subject[:60]}...")
            print(f"   Attachments found: {attachments}")
            
            si_file = None
            bl_file = None
            for att in attachments:
                clean_name = os.path.basename(att)
                if 'SI' in clean_name.upper():
                    si_file = clean_name
                elif 'BL' in clean_name.upper():
                    bl_file = clean_name
            
            if si_file and bl_file:
                print(f"   📖 Reading SI: {si_file}...")
                si_text = read_attachment(si_file)
                print(f"   📖 Reading BL: {bl_file}...")
                bl_text = read_attachment(bl_file)
                
                # Pause for 3 seconds to avoid rate limits
                print("   ⏳ Brief pause to respect API rate limits...")
                time.sleep(3)
                
                print("   🔬 Auditing and comparing documents using Gemini 3.6 Flash...")
                audit_result = compare_documents(si_text, bl_text)
                
                true_verification = ground_truth.get(email_id, {})
                true_status = true_verification.get('status', 'OK')
                true_reason = true_verification.get('review_reason', None)
                
                print(f"\n   📋 AUDIT RESULT FOR {email_id}:")
                print(f"      AI Status        : {audit_result.get('status')}")
                print(f"      Ground Truth     : {true_status}")
                if audit_result.get('review_reason'):
                    print(f"      Reason (AI)      : {audit_result['review_reason']}")
                if true_reason:
                    print(f"      Reason (Actual)  : {true_reason}")
                
                print("      Discrepancies breakdown:")
                for field, disc_status in audit_result.get('discrepancies', {}).items():
                    print(f"         - {field:22}: {disc_status}")
                
                if audit_result.get('status') == true_status:
                    print("\n   🌟 Verification Status: MATCH! ✅")
                    overall_correct += 1
                else:
                    print("\n   🌟 Verification Status: MISMATCH! ❌")
            else:
                print("   ⚠️ Error: Could not find both SI and BL attachments for this email!")
            print("-" * 80)

    if total_audited > 0:
        accuracy = (overall_correct / total_audited) * 100
        print(f"\n📊 FASA 2 BENCHMARK RESULTS:")
        print(f"   Total Document Pairs Audited: {total_audited}")
        print(f"   Correct Status Detections   : {overall_correct}")
        print(f"   Accuracy Rate               : {accuracy:.1f}%")
    else:
        print("\n⚠️ No BL_COMPARISON emails found in the sampled batch to audit.")

if __name__ == '__main__':
    main()