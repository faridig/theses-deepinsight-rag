import os
import glob
from dotenv import load_dotenv
from src.processing.parser import ThesisParser

def verify_parsing():
    # 1. Load environment variables
    load_dotenv()
    api_key = os.getenv("LLAMA_CLOUD_API_KEY")
    
    if not api_key:
        print("❌ Error: LLAMA_CLOUD_API_KEY not found in .env")
        return

    # 2. Find the first PDF in data_final/ (as data/ was empty)
    pdf_files = glob.glob("data_final/*.pdf")
    if not pdf_files:
        # Fallback to data/ just in case
        pdf_files = glob.glob("data/*.pdf")
        
    if not pdf_files:
        print("❌ Error: No PDF files found in data_final/ or data/")
        return
    
    target_pdf = pdf_files[0]
    print(f"📄 Found PDF: {target_pdf}")

    # 3. Initialize Parser
    parser = ThesisParser(api_key=api_key)
    
    # 4. Attempt to parse only the first page
    print("⏳ Starting live parsing of the first page...")
    try:
        from llama_parse import LlamaParse
        
        lp = LlamaParse(
            api_key=api_key,
            result_type="markdown",
            target_pages="0",
            verbose=True
        )
        
        documents = lp.load_data(target_pdf)
        
        if not documents:
            print("❌ Error: No documents returned from LlamaParse")
            return
            
        print("\n✅ Parsing successful!")
        print("-" * 50)
        print("📝 Markdown Content Preview (First 500 characters):")
        print("-" * 50)
        print(documents[0].text[:500] + "...")
        print("-" * 50)
        
    except Exception as e:
        print(f"❌ Error during parsing: {str(e)}")

if __name__ == "__main__":
    verify_parsing()
