import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
from typing import List, Dict
import json
from datetime import datetime


class TallyXMLConverter:
    """Convert extracted invoice JSON to Tally-friendly XML format."""

    @staticmethod
    def create_tally_voucher(invoice_data: Dict) -> str:
        """
        Convert invoice JSON to Tally import XML that TallyPrime accepts.

        Uses the IMPORTDATA -> REQUESTDATA -> TALLYMESSAGE -> VOUCHER structure.
        """
        root = ET.Element('ENVELOPE')

        # Header
        header = ET.SubElement(root, 'HEADER')
        tally_request = ET.SubElement(header, 'TALLYREQUEST')
        tally_request.text = 'Import Data'

        # Body / Import data
        body = ET.SubElement(root, 'BODY')
        importdata = ET.SubElement(body, 'IMPORTDATA')

        requestdesc = ET.SubElement(importdata, 'REQUESTDESC')
        reportname = ET.SubElement(requestdesc, 'REPORTNAME')
        reportname.text = 'Vouchers'

        requestdata = ET.SubElement(importdata, 'REQUESTDATA')

        # Tally message wrapper
        tallymessage = ET.SubElement(requestdata, 'TALLYMESSAGE')

        # Voucher element
        voucher = ET.SubElement(tallymessage, 'VOUCHER')
        voucher.set('VCHTYPE', 'Sales')
        voucher.set('ACTION', 'Create')

        # Core fields
        # TallyPrime commonly expects DATE/VOUCHERDATE in DD MM YYYY format
        # Provide multiple date representations to satisfy different Tally import expectations
        date_ddmmyyyy = TallyXMLConverter._parse_date(invoice_data.get('invoice_date', ''))
        date_yyyymmdd = TallyXMLConverter._parse_date_numeric(invoice_data.get('invoice_date', ''))

        # <DATE> as numeric (YYYYMMDD) and <VOUCHERDATE>/<EFFECTIVEDATE> as DD MM YYYY
        date_el = ET.SubElement(voucher, 'DATE')
        date_el.text = date_yyyymmdd

        vch_date_el = ET.SubElement(voucher, 'VOUCHERDATE')
        vch_date_el.text = date_ddmmyyyy

        eff_date_el = ET.SubElement(voucher, 'EFFECTIVEDATE')
        eff_date_el.text = date_ddmmyyyy

        vch_type = ET.SubElement(voucher, 'VOUCHERTYPENAME')
        vch_type.text = 'Sales'

        vch_number = ET.SubElement(voucher, 'VOUCHERNUMBER')
        vch_number.text = str(invoice_data.get('invoice_number', ''))

        party = ET.SubElement(voucher, 'PARTYLEDGERNAME')
        party.text = invoice_data.get('customer_name', 'Unknown')

        narration = ET.SubElement(voucher, 'NARRATION')
        narration.text = f"Imported via Tally Connector - Invoice {invoice_data.get('invoice_number', '')}"

        # Ledger entries (ALLLEDGERENTRIES.LIST)
        amount_value = TallyXMLConverter._parse_amount(invoice_data.get('amount', '0'))

        # Customer ledger entry (debit/negative)
        ledger1 = ET.SubElement(voucher, 'ALLLEDGERENTRIES.LIST')
        ledgername1 = ET.SubElement(ledger1, 'LEDGERNAME')
        ledgername1.text = invoice_data.get('customer_name', 'Unknown')
        amt1 = ET.SubElement(ledger1, 'AMOUNT')
        # Tally expects negative amount for debit side in this layout (prefix '-')
        amt1.text = f"-{amount_value:.2f}"

        # Sales ledger entry (credit/positive)
        ledger2 = ET.SubElement(voucher, 'ALLLEDGERENTRIES.LIST')
        ledgername2 = ET.SubElement(ledger2, 'LEDGERNAME')
        ledgername2.text = 'Sales'
        amt2 = ET.SubElement(ledger2, 'AMOUNT')
        amt2.text = f"{amount_value:.2f}"

        # Inventory entries (optional)
        if 'items' in invoice_data and invoice_data['items']:
            for item in invoice_data['items']:
                inv = ET.SubElement(voucher, 'ALLINVENTORYENTRIES.LIST')
                stockitem = ET.SubElement(inv, 'STOCKITEMNAME')
                stockitem.text = item.get('description', 'Item')

                # ACTUALQTY: Tally often expects quantity with unit (e.g., 3.00 Nos)
                # Keep it simple here as a plain number; adjust if you have units in your company config
                qty = ET.SubElement(inv, 'ACTUALQTY')
                qty.text = str(item.get('quantity', 1))

                rate = ET.SubElement(inv, 'RATE')
                try:
                    rate_val = float(str(item.get('unit_price', '0')).replace(',', ''))
                except Exception:
                    rate_val = 0.0
                rate.text = f"{rate_val:.2f}"

        # Convert to pretty XML string
        xml_str = minidom.parseString(ET.tostring(root, encoding='utf-8')).toprettyxml(indent="  ")
        # Remove XML declaration line (Tally doesn't require it in many cases)
        xml_lines = xml_str.split('\n')
        if xml_lines and xml_lines[0].startswith('<?xml'):
            xml_lines = xml_lines[1:]
        xml_str = '\n'.join(line for line in xml_lines if line.strip())
        return xml_str

    @staticmethod
    def _parse_date(date_str: str) -> str:
        """
        Parse date string and return date in DD MM YYYY format (space-separated).
        """
        try:
            if not date_str or not str(date_str).strip():
                return datetime.now().strftime('%d %m %Y')

            s = str(date_str).strip()

            # try common input formats
            for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%m/%d/%Y', '%d%m%Y', '%Y%m%d']:
                try:
                    parsed_date = datetime.strptime(s, fmt)
                    return parsed_date.strftime('%d %m %Y')
                except ValueError:
                    continue

            # fallback: extract digits and heuristically parse
            digits = ''.join(ch for ch in s if ch.isdigit())
            if len(digits) == 8:
                # If digits look like YYYYMMDD (starts with 19/20)
                if digits.startswith('20') or digits.startswith('19'):
                    return digits[6:8] + ' ' + digits[4:6] + ' ' + digits[0:4]
                # Assume DDMMYYYY
                return digits[0:2] + ' ' + digits[2:4] + ' ' + digits[4:8]

            # final fallback: today's date
            return datetime.now().strftime('%d %m %Y')
        except Exception as e:
            print(f"Warning: Could not parse date '{date_str}': {e}")
            return datetime.now().strftime('%d %m %Y')

    @staticmethod
    def _parse_date_numeric(date_str: str) -> str:
        """
        Return date as numeric YYYYMMDD (no separators) which some Tally imports expect.
        """
        try:
            if not date_str or not str(date_str).strip():
                return datetime.now().strftime('%Y%m%d')
            s = str(date_str).strip()
            for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%m/%d/%Y', '%d%m%Y', '%Y%m%d']:
                try:
                    parsed_date = datetime.strptime(s, fmt)
                    return parsed_date.strftime('%Y%m%d')
                except ValueError:
                    continue
            digits = ''.join(ch for ch in s if ch.isdigit())
            if len(digits) == 8:
                if digits.startswith('20') or digits.startswith('19'):
                    return digits
                return digits[4:8] + digits[2:4] + digits[0:2]
            return datetime.now().strftime('%Y%m%d')
        except Exception as e:
            print(f"Warning: Could not parse date '{date_str}': {e}")
            return datetime.now().strftime('%Y%m%d')

    @staticmethod
    def _parse_amount(amount_str: str) -> float:
        """
        Parse amount string to float (units, e.g., rupees/dollars).
        Returns float rounded to 2 decimals.
        """
        try:
            # Remove common currency symbols and whitespace
            clean_amount = str(amount_str).replace('$', '').replace('₹', '').strip()
            # Remove commas
            clean_amount = clean_amount.replace(',', '')
            amount_value = float(clean_amount)
            return round(amount_value, 2)
        except Exception as e:
            print(f"Warning: Could not parse amount '{amount_str}': {e}")
            return 0.0

    @staticmethod
    def _add_line_items(voucher: ET.Element, items: List[Dict]) -> None:
        """
        Add line items to voucher (not used in main flow currently; kept for future use).
        """
        bill_allocations = ET.SubElement(voucher, 'BILLALLOCATIONS.LIST')

        for item in items:
            bill_alloc = ET.SubElement(bill_allocations, 'BILLALLOCATION')
            bill_alloc.set('NAME', item.get('description', 'Item'))

            qty = ET.SubElement(bill_alloc, 'QUANTITY')
            qty.text = str(item.get('quantity', '1'))

            rate = ET.SubElement(bill_alloc, 'RATE')
            amount = TallyXMLConverter._parse_amount(str(item.get('unit_price', '0')))
            rate.text = str(amount)

    @staticmethod
    def convert_invoices_to_xml(invoices: List[Dict]) -> Dict[str, str]:
        """
        Convert multiple invoices to Tally XML.
        """
        result = {}
        for invoice in invoices:
            if 'error' not in invoice:
                invoice_num = invoice.get('invoice_number', 'UNKNOWN')
                xml_content = TallyXMLConverter.create_tally_voucher(invoice)
                result[invoice_num] = xml_content
            else:
                print(f"Skipping invoice with error: {invoice.get('error')}")
        return result


def save_xml_files(xml_dict: Dict[str, str], output_dir: str = "tally_xmls") -> None:
    """
    Save XML files to disk.
    """
    import os

    os.makedirs(output_dir, exist_ok=True)

    for invoice_num, xml_content in xml_dict.items():
        filename = f"{output_dir}/voucher_{invoice_num}.xml"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(xml_content)
        print(f"✓ Saved: {filename}")


if __name__ == "__main__":
    # Test with sample invoice
    sample_invoice = {
        "invoice_number": "IN-001",
        "invoice_date": "29/01/2019",
        "customer_name": "Kavindra Mannan",
        "amount": "13,715.52",
        "currency": "₹",
        "items": [
            {
                "description": "Frontend design restructure",
                "quantity": 1,
                "unit_price": "9,999.00"
            },
            {
                "description": "Custom icon package",
                "quantity": 2,
                "unit_price": "975.00"
            },
            {
                "description": "Gandhi mouse pad",
                "quantity": 3,
                "unit_price": "99.00"
            }
        ]
    }

    # Convert to XML
    xml_content = TallyXMLConverter.create_tally_voucher(sample_invoice)
    print("Generated Tally XML:")
    print(xml_content)

    # Save to file
    xml_dict = {sample_invoice['invoice_number']: xml_content}
    save_xml_files(xml_dict)