#!/usr/bin/env python3
"""
End-to-end Invoice Processing Workflow
Image (PDF/JPG/PNG) → Vision API → JSON → Tally XML → TallyPrime
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import List, Dict

from invoice_extractor import process_invoice_image
from tally_converter import TallyXMLConverter, save_xml_files


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class InvoiceProcessingPipeline:
    """Main pipeline for processing invoices end-to-end."""
    
    SUPPORTED_FORMATS = ['.jpg', '.jpeg', '.png', '.pdf']
    
    def __init__(self, output_dir: str = "output"):
        """
        Initialize the pipeline.
        
        Args:
            output_dir: Directory to store output files
        """
        self.output_dir = output_dir
        self.json_output_dir = os.path.join(output_dir, "json")
        self.xml_output_dir = os.path.join(output_dir, "xml")
        
        os.makedirs(self.json_output_dir, exist_ok=True)
        os.makedirs(self.xml_output_dir, exist_ok=True)
        
        logger.info(f"Pipeline initialized. Output directory: {output_dir}")
    
    def is_supported_format(self, file_path: str) -> bool:
        """Check if file format is supported."""
        ext = Path(file_path).suffix.lower()
        return ext in self.SUPPORTED_FORMATS
    
    def process_single_invoice(self, image_path: str) -> Dict:
        """
        Process a single invoice image.
        
        Args:
            image_path: Path to invoice image
            
        Returns:
            Dictionary with processing results
        """
        logger.info(f"Processing: {image_path}")
        
        result = {
            "file": image_path,
            "status": "pending",
            "extracted_data": None,
            "tally_xml": None,
            "error": None
        }
        
        try:
            # Validate file format
            if not self.is_supported_format(image_path):
                raise ValueError(f"Unsupported file format: {image_path}")
            
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"File not found: {image_path}")
            
            # Step 1: Extract invoice data from image
            logger.info(f"  [1/3] Extracting data via Vision API...")
            invoices = process_invoice_image(image_path)
            
            if not invoices or (invoices and 'error' in invoices[0]):
                raise Exception(f"Failed to extract invoice data: {invoices}")
            
            result["extracted_data"] = invoices
            logger.info(f"  [1/3] Success - Extracted {len(invoices)} invoice(s)")
            
            # Step 2: Save JSON output
            logger.info(f"  [2/3] Converting to Tally XML...")
            json_file = os.path.join(
                self.json_output_dir,
                f"{Path(image_path).stem}_extracted.json"
            )
            with open(json_file, 'w') as f:
                json.dump(invoices, f, indent=2)
            logger.info(f"  [2/3] Success - Saved JSON: {json_file}")
            
            # Step 3: Convert to Tally XML
            xml_dict = TallyXMLConverter.convert_invoices_to_xml(invoices)
            
            # Save XML files
            for invoice_num, xml_content in xml_dict.items():
                xml_file = os.path.join(
                    self.xml_output_dir,
                    f"voucher_{invoice_num}.xml"
                )
                with open(xml_file, 'w', encoding='utf-8') as f:
                    f.write(xml_content)
                logger.info(f"  [3/3] Success - Saved XML: {xml_file}")
            
            result["tally_xml"] = xml_dict
            result["status"] = "success"
            
            return result
            
        except Exception as e:
            logger.error(f"  ERROR processing {image_path}: {str(e)}")
            result["status"] = "failed"
            result["error"] = str(e)
            return result
    
    def process_directory(self, directory: str) -> List[Dict]:
        """
        Process all invoice images in a directory.
        
        Args:
            directory: Path to directory containing images
            
        Returns:
            List of processing results
        """
        results = []
        
        logger.info(f"Scanning directory: {directory}")
        
        # Find all supported image files
        image_files = []
        for ext in self.SUPPORTED_FORMATS:
            image_files.extend(Path(directory).glob(f"*{ext}"))
            image_files.extend(Path(directory).glob(f"*{ext.upper()}"))
        
        if not image_files:
            logger.warning(f"No invoice images found in {directory}")
            return results
        
        logger.info(f"Found {len(image_files)} invoice image(s)")
        
        # Process each file
        for i, image_file in enumerate(image_files, 1):
            logger.info(f"\n[{i}/{len(image_files)}] Processing invoice...")
            result = self.process_single_invoice(str(image_file))
            results.append(result)
        
        return results
    
    def generate_report(self, results: List[Dict]) -> str:
        """
        Generate a processing report.
        
        Args:
            results: List of processing results
            
        Returns:
            Report string
        """
        successful = sum(1 for r in results if r["status"] == "success")
        failed = sum(1 for r in results if r["status"] == "failed")
        
        report = f"""
╔════════════════════════════════════════════════════════════╗
║         INVOICE PROCESSING PIPELINE - SUMMARY REPORT       ║
╚════════════════════════════════════════════════════════════╝

Total Processed:  {len(results)}
Successful:       {successful}
Failed:           {failed}

Output Locations:
  JSON Files:     {os.path.abspath(self.json_output_dir)}
  Tally XML:      {os.path.abspath(self.xml_output_dir)}

Details:
"""
        for result in results:
            status_symbol = "[OK]" if result["status"] == "success" else "[FAIL]"
            report += f"\n{status_symbol} {result['file']}"
            if result["status"] == "success" and result["extracted_data"]:
                for invoice in result["extracted_data"]:
                    if "invoice_number" in invoice:
                        report += f"\n    Invoice: {invoice['invoice_number']}"
                        report += f" | Customer: {invoice.get('customer_name', 'N/A')}"
                        report += f" | Amount: {invoice.get('amount', 'N/A')}"
            elif result["error"]:
                report += f"\n    Error: {result['error']}"
        
        report += "\n"
        return report


def main():
    """Main entry point."""
    
    # Create pipeline
    pipeline = InvoiceProcessingPipeline(output_dir="invoice_output")
    
    # Check command line arguments
    if len(sys.argv) > 1:
        input_path = sys.argv[1]
    else:
        input_path = "."  # Current directory
    
    # Process files
    if os.path.isfile(input_path):
        # Single file
        results = [pipeline.process_single_invoice(input_path)]
    else:
        # Directory
        results = pipeline.process_directory(input_path)
    
    # Generate and print report
    report = pipeline.generate_report(results)
    print(report)
    
    # Save report to file
    report_file = os.path.join(pipeline.output_dir, "processing_report.txt")
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    logger.info(f"Report saved: {report_file}")
    
    return 0 if all(r["status"] == "success" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
