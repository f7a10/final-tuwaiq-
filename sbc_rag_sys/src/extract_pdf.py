"""
PDF Extraction using Mistral OCR API
Extracts text from Arabic PDF documents with high accuracy
"""

import os
import json
import base64
from pathlib import Path
from typing import List, Dict
from mistralai import Mistral
from tqdm import tqdm
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config


class MistralPDFExtractor:
    """Extract text from PDFs using Mistral OCR API"""
    
    def __init__(self, api_key: str = None):
        """Initialize Mistral client"""
        self.api_key = api_key or Config.MISTRAL_API_KEY
        if not self.api_key:
            raise ValueError("Mistral API key is required")
        
        self.client = Mistral(api_key=self.api_key)
        self.model = Config.MISTRAL_MODEL
    
    def encode_pdf_to_base64(self, pdf_path: str) -> str:
        """Encode PDF file to base64 string"""
        with open(pdf_path, "rb") as pdf_file:
            return base64.b64encode(pdf_file.read()).decode('utf-8')
    
    def extract_text_from_pdf(self, pdf_path: str) -> Dict[str, any]:
        """
        Extract text from a single PDF using Mistral OCR
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary containing extracted text and metadata
        """
        print(f"Processing: {pdf_path}")
        
        # Encode PDF to base64
        pdf_base64 = self.encode_pdf_to_base64(pdf_path)
        
        # Create message with PDF
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "استخرج كل النص من هذا المستند بدقة. احتفظ بالتنسيق والهيكل الأصلي قدر الإمكان. Extract all text from this document accurately, preserving the original formatting and structure."
                    },
                    {
                        "type": "document",
                        "document": {
                            "data": pdf_base64,
                            "media_type": "application/pdf"
                        }
                    }
                ]
            }
        ]
        
        try:
            # Call Mistral OCR
            response = self.client.chat.complete(
                model=self.model,
                messages=messages
            )
            
            extracted_text = response.choices[0].message.content
            
            return {
                "filename": os.path.basename(pdf_path),
                "text": extracted_text,
                "success": True,
                "error": None
            }
            
        except Exception as e:
            print(f"Error extracting text from {pdf_path}: {str(e)}")
            return {
                "filename": os.path.basename(pdf_path),
                "text": "",
                "success": False,
                "error": str(e)
            }
    
    def process_directory(self, input_dir: str, output_dir: str) -> List[Dict]:
        """
        Process all PDFs in a directory
        
        Args:
            input_dir: Directory containing PDF files
            output_dir: Directory to save extracted text
            
        Returns:
            List of extraction results
        """
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Get all PDF files
        pdf_files = list(Path(input_dir).glob("*.pdf"))
        
        if not pdf_files:
            print(f"No PDF files found in {input_dir}")
            return []
        
        results = []
        
        # Process each PDF
        for pdf_path in tqdm(pdf_files, desc="Extracting PDFs"):
            result = self.extract_text_from_pdf(str(pdf_path))
            results.append(result)
            
            # Save extracted text
            if result["success"]:
                output_file = os.path.join(
                    output_dir,
                    f"{Path(pdf_path).stem}.txt"
                )
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(result["text"])
                
                print(f"✓ Saved: {output_file}")
        
        # Save summary
        summary_file = os.path.join(output_dir, "extraction_summary.json")
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        # Print summary
        successful = sum(1 for r in results if r["success"])
        print(f"\n{'='*50}")
        print(f"Extraction complete!")
        print(f"Total files: {len(results)}")
        print(f"Successful: {successful}")
        print(f"Failed: {len(results) - successful}")
        print(f"{'='*50}")
        
        return results


def main():
    """Main extraction function"""
    # Validate config
    Config.validate()
    
    # Create directories
    os.makedirs(Config.PDF_DIR, exist_ok=True)
    os.makedirs(Config.EXTRACTED_DIR, exist_ok=True)
    
    # Initialize extractor
    extractor = MistralPDFExtractor()
    
    # Process PDFs
    results = extractor.process_directory(
        input_dir=Config.PDF_DIR,
        output_dir=Config.EXTRACTED_DIR
    )
    
    return results


if __name__ == "__main__":
    main()
