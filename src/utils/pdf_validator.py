import os
import logging
from typing import Optional, Any
try:
    import fitz # PyMuPDF
except ImportError:
    fitz = None

logger = logging.getLogger(__name__)

class PDFValidator:
    """
    Validates PDF files for size and integrity (PBI-027).
    """
    
    @staticmethod
    def validate(file_path: str, fs: Optional[Any] = None) -> bool:
        """
        Validates a PDF file.
        - Size must be > 10KB.
        - Must be a valid PDF (openable by PyMuPDF).
        """
        try:
            # 1. Check size
            if fs:
                size = fs.size(file_path)
            else:
                size = os.path.getsize(file_path)
            
            if size < 10 * 1024: # 10KB
                logger.warning(f"File {file_path} is too small ({size} bytes). Minimum 10KB required.")
                return False
            
            # 2. Check integrity with PyMuPDF
            if fitz:
                try:
                    if fs:
                        with fs.open(file_path, "rb") as f:
                            # Use stream to avoid downloading if possible, though fitz.open(stream=...)
                            # will still load it in memory.
                            doc = fitz.open(stream=f.read(), filetype="pdf")
                    else:
                        doc = fitz.open(file_path)
                    
                    page_count = doc.page_count
                    doc.close()
                    if page_count == 0:
                        logger.warning(f"File {file_path} has 0 pages.")
                        return False
                    return True
                except Exception as e:
                    logger.warning(f"File {file_path} is corrupted or not a valid PDF: {e}")
                    return False
            else:
                logger.warning("PyMuPDF (fitz) not installed. Skipping integrity check.")
                return True # Fallback
        except Exception as e:
            logger.error(f"Error validating PDF {file_path}: {e}")
            return False
