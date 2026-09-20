import google.generativeai as genai

# --- MASUKKAN KUNCI API ANDA DI SINI ---
GEMINI_API_KEY = 'AQ.Ab8RN6K3zW2PS7DwNyMaTgRcvnkTWUEcw9yVrbWrMNoE5tGNWw'
# ------------------------------------

try:
    genai.configure(api_key=GEMINI_API_KEY)
    print("✅ berjaya berhubung dengan Google. Mencari model yang tersedia...\n")
    
    found_model = False
    for m in genai.list_models():
        # Kita hanya mahu model yang boleh 'generateContent'
        if 'generateContent' in m.supported_generation_methods:
            print(f"👉 Model Aktif Ditemui: {m.name}")
            found_model = True
    
    if not found_model:
        print("❌ Tiada model yang menyokong 'generateContent' ditemui untuk kunci API ini.")

except Exception as e:
    print(f"❌ Ralat semasa cuba berhubung: {e}")