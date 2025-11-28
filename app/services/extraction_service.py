
import os
import fitz  # PyMuPDF, installed as PyMuPDF
import docx
import pandas as pd
from trafilatura import extract as trafilatura_extract
import json
import re
from typing import List, Dict, Any, Tuple
from bs4 import BeautifulSoup
import sqlparse

# --- OCR Fallback Service ---
def _ocr_page_image(page_image: bytes) -> Tuple[str, float]:
    """
    Placeholder for a real OCR function to process images of pages.
    In a real implementation, this would use a library like Tesseract (via pytesseract)
    or a cloud-based OCR service (e.g., Google Vision AI, AWS Textract).

    Args:
        page_image (bytes): The image content of a single page.

    Returns:
        A tuple containing the extracted text and a confidence score (0.0 to 1.0).
    """
    # For example: text = pytesseract.image_to_string(Image.open(io.BytesIO(page_image)))
    print("OCR fallback triggered for a page. Implement real OCR for content extraction.")
    return "[OCR fallback: text would be extracted from image here]", 0.5  # Return dummy text and confidence

# --- PDF Extraction Service ---
def _extract_pdf(file_path: str) -> Tuple[List[Dict[str, Any]], str]:
    """
    Extracts text and metadata from a PDF file, page by page.
    It attempts to extract digital text first and uses an OCR fallback for pages
    that appear to be scanned images.

    Args:
        file_path (str): The path to the PDF file.

    Returns:
        A tuple containing a list of content blocks (one per page) and the document type
        (e.g., 'pdf-digital' or 'pdf-ocr').
    """
    blocks = []
    doc_type = "pdf-digital"  # Assume digital by default
    extraction_method = "PyMuPDF"
    try:
        doc = fitz.open(file_path)
        # Iterate through each page of the PDF
        for page_num, page in enumerate(doc):
            # Extract text directly. `sort=True` helps maintain reading order.
            page_text = page.get_text("text", sort=True)
            ocr_confidence = 1.0  # High confidence for direct digital extraction

            # OCR Fallback Check: If a page has very little selectable text, it might be a scanned image.
            if len(page_text.strip()) < 50:  # Arbitrary threshold for text density
                # Confirm there are images on the page before triggering OCR
                if page.get_images():
                    doc_type = "pdf-ocr"
                    extraction_method = "PyMuPDF_OCR_fallback"
                    # Convert the page to an image (pixmap) for OCR processing
                    pix = page.get_pixmap()
                    page_text, ocr_confidence = _ocr_page_image(pix.tobytes("png"))

            # Store the content and metadata for the page
            blocks.append({
                "text": page_text,
                "metadata": {
                    "source_filename": os.path.basename(file_path),
                    "page_number": page_num + 1,
                    "extraction_method": extraction_method,
                    "ocr_confidence": ocr_confidence
                }
            })
        doc.close()
    except Exception as e:
        print(f"Error processing PDF {file_path}: {e}")
        return [], "pdf-error"
    return blocks, doc_type

# --- HTML Extraction Service ---
def _extract_html(file_path: str) -> Tuple[List[Dict[str, Any]], str]:
    """
    Extracts the main article content from an HTML file, stripping out boilerplate
    like navigation, ads, and footers using the 'trafilatura' library.

    Args:
        file_path (str): The path to the HTML file.

    Returns:
        A list containing a single block of the main extracted content and the doc type 'html'.
    """
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        html_content = f.read()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    title = soup.title.string if soup.title else "N/A"

    # Use trafilatura to extract the core article text, keeping tables.
    main_content = trafilatura_extract(html_content, include_comments=False, include_tables=True)
    blocks = [{
        "text": main_content or "",
        "metadata": {
            "source_filename": os.path.basename(file_path),
            "title": title,
            "extraction_method": "trafilatura"
        }
    }]
    return blocks, "html"

# --- DOCX Extraction Service ---
def _extract_docx(file_path: str) -> Tuple[List[Dict[str, Any]], str]:
    """
    Extracts text from a .docx file, preserving paragraphs and their styles (e.g., headings).

    Args:
        file_path (str): The path to the .docx file.

    Returns:
        A list of blocks, where each block is a paragraph with its style, and the doc type 'docx'.
    """
    blocks = []
    try:
        doc = docx.Document(file_path)
        for i, para in enumerate(doc.paragraphs):
            style_name = para.style.name
            # Capture heading levels, default to 'paragraph' if not a heading
            if style_name.startswith('Heading'):
                level = style_name.split(' ')[-1]
                block_type = f"h{level}"
            else:
                block_type = "paragraph"
            
            blocks.append({
                "text": para.text,
                "metadata": {
                    "source_filename": os.path.basename(file_path),
                    "paragraph_index": i,
                    "style": block_type,
                    "extraction_method": "python-docx"
                }
            })

        # Basic table extraction
        for table_idx, table in enumerate(doc.tables):
            for row_idx, row in enumerate(table.rows):
                row_text = " | ".join(cell.text for cell in row.cells)
                blocks.append({
                    "text": f"Table Row: {row_text}",
                    "metadata": {
                        "source_filename": os.path.basename(file_path),
                        "style": "table_row",
                        "table_index": table_idx,
                        "row_index": row_idx,
                        "extraction_method": "python-docx"
                    }
                })

    except Exception as e:
        print(f"Error processing DOCX {file_path}: {e}")
        return [], "docx-error"
    return blocks, "docx"

# --- Spreadsheet Extraction Service ---
def _extract_spreadsheet(file_path: str, file_type: str) -> Tuple[List[Dict[str, Any]], str]:
    """
    Extracts data from spreadsheet files (XLSX, CSV), treating each row as a separate record.
    Filters out NaN values to prevent downstream errors.

    Args:
        file_path (str): The path to the spreadsheet file.
        file_type (str): The type of spreadsheet ('xlsx' or 'csv').

    Returns:
        A list of blocks, where each block is a row formatted as a key-value string.
    """
    blocks = []
    try:
        if file_type == 'xlsx':
            xls = pd.ExcelFile(file_path)
            for sheet_name in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet_name).dropna(how='all')
                # Replace pandas NaN with None for consistent handling
                df = df.where(pd.notna(df), None)
                
                for index, row in df.iterrows():
                    # Create string representation, skipping None values
                    row_text = ", ".join([f'{col}: {val}' for col, val in row.items() if val is not None])
                    if not row_text:  # Skip rows that are entirely empty
                        continue
                    blocks.append({
                        "text": row_text,
                        "metadata": {
                            "source_filename": os.path.basename(file_path),
                            "sheet_name": sheet_name,
                            "row_number": index + 2,  # +2 for 1-based index and header
                            "extraction_method": "pandas"
                        }
                    })
        else:  # For CSV
            df = pd.read_csv(file_path).dropna(how='all')
            df = df.where(pd.notna(df), None)  # Replace NaN with None

            for index, row in df.iterrows():
                row_text = ", ".join([f'{col}: {val}' for col, val in row.items() if val is not None])
                if not row_text:
                    continue
                blocks.append({
                    "text": row_text,
                    "metadata": {
                        "source_filename": os.path.basename(file_path),
                        "row_number": index + 2,
                        "extraction_method": "pandas"
                    }
                })
    except Exception as e:
        print(f"Error processing spreadsheet {file_path}: {e}")
        return [], f"{file_type}-error"
    return blocks, file_type

# --- SQL Dump Extraction Service (Handles both INSERT and COPY) ---
def _extract_sql(file_path: str) -> Tuple[List[Dict[str, Any]], str]:
    """
    Extracts data from SQL dump files, supporting both standard INSERT statements
    and PostgreSQL's 'COPY ... FROM stdin' format.

    Args:
        file_path (str): The path to the .sql file.

    Returns:
        A list of blocks, where each block is a row of data as a JSON string.
    """
    blocks = []
    print(f"--- Starting Unified SQL Extraction for {file_path} ---")
    try:
        # Try to detect encoding first
        encodings_to_try = ['utf-8', 'utf-16', 'utf-16le', 'utf-16be', 'latin-1', 'cp1252']
        content = None
        
        for encoding in encodings_to_try:
            try:
                with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                    test_content = f.read()
                # Check if content looks reasonable (no excessive null bytes)
                if test_content and test_content.count('\x00') / len(test_content) < 0.1:
                    content = test_content
                    print(f"Successfully read SQL file with encoding: {encoding}")
                    break
            except:
                continue
        
        if not content:
            # Fallback to utf-8 with error handling
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

        # --- Process COPY statements using line-by-line parsing ---
        print("\n--- Processing for COPY statements ---")
        found_copy_blocks = 0
        lines = content.split('\n')
        in_copy_block = False
        current_table = None
        current_columns = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Check for start of COPY block
            if line.startswith('COPY ') and 'FROM stdin;' in line:
                copy_match = re.match(r'COPY\s+([\w\.]+)\s*\((.*?)\)\s+FROM\s+stdin;', line, re.IGNORECASE)
                if copy_match:
                    found_copy_blocks += 1
                    current_table = copy_match.group(1).strip()
                    current_columns = [col.strip().strip('"') for col in copy_match.group(2).split(',')]
                    in_copy_block = True
                    print(f"Found COPY block for table '{current_table}' with columns: {current_columns}")
                    
            # Check for end of COPY block
            elif in_copy_block and line == '\\.':
                in_copy_block = False
                current_table = None
                current_columns = []
                
            # Process data lines within COPY block
            elif in_copy_block and line:
                values = line.split('\t')
                if len(current_columns) == len(values):
                    row_data = {col: (val if val != '\\N' else None) for col, val in zip(current_columns, values)}
                    blocks.append({
                        "text": json.dumps(row_data),
                        "metadata": { 
                            "source_filename": os.path.basename(file_path), 
                            "table_name": current_table, 
                            "extraction_method": "psql_copy" 
                        }
                    })
                else:
                    print(f"[WARNING] Column count mismatch in table '{current_table}': expected {len(current_columns)}, got {len(values)}. Skipping row.")
        
        if found_copy_blocks == 0:
            print("No COPY blocks found.")

        # --- Process INSERT statements using sqlparse ---
        print("\n--- Processing for INSERT statements ---")
        found_insert_blocks = 0
        for stmt in sqlparse.parse(content):
            if stmt.get_type() != 'INSERT':
                continue
            
            found_insert_blocks += 1
            table_name = "unknown"
            into_seen = False
            for token in stmt.tokens:
                if into_seen and isinstance(token, sqlparse.sql.Identifier):
                    table_name = token.get_real_name()
                    break
                if token.is_keyword and token.normalized == 'INTO':
                    into_seen = True

            columns_part = next((t for t in stmt.tokens if isinstance(t, sqlparse.sql.Parenthesis)), None)
            column_names = []
            if columns_part:
                id_list = next((t for t in columns_part.tokens if isinstance(t, sqlparse.sql.IdentifierList)), None)
                if id_list:
                    column_names = [col.get_real_name() for col in id_list.get_identifiers()]

            values_part = next((t for t in stmt.tokens if isinstance(t, sqlparse.sql.Values)), None)
            if not values_part:
                continue

            for row_parens in values_part.get_sublists():
                if isinstance(row_parens, sqlparse.sql.Parenthesis):
                    id_list = next((t for t in row_parens.tokens if isinstance(t, sqlparse.sql.IdentifierList)), None)
                    if not id_list: continue
                    
                    row_values = [identifier.normalized.strip("'\"") for identifier in id_list.get_identifiers()]
                    
                    if column_names and len(column_names) == len(row_values):
                        row_data = dict(zip(column_names, row_values))
                    else:
                        row_data = {f"col_{j}": val for j, val in enumerate(row_values)}
                    
                    blocks.append({
                        "text": json.dumps(row_data),
                        "metadata": { "source_filename": os.path.basename(file_path), "table_name": table_name, "extraction_method": "sql_insert" }
                    })
        
        if found_insert_blocks > 0:
            print(f"Found and processed {found_insert_blocks} INSERT statements.")
        else:
            print("No INSERT statements found.")

        print(f"--- SQL Extraction Complete. Found {len(blocks)} total blocks. ---")

    except Exception as e:
        print(f"Error processing SQL file {file_path}: {e}")
        import traceback
        traceback.print_exc()
        return [], "sql-error"
    
    return blocks, "sql"


# --- JSONL Extraction Service ---
def _extract_jsonl(file_path: str) -> Tuple[List[Dict[str, Any]], str]:
    """
    Extracts data from a JSONL (JSON Lines) file, where each line is a separate JSON object.

    Args:
        file_path (str): The path to the .jsonl file.

    Returns:
        A list of blocks, where each block is one line (a JSON object) from the file.
    """
    blocks = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if line.strip():
                    blocks.append({
                        "text": line.strip(), 
                        "metadata": {
                            "source_filename": os.path.basename(file_path),
                            "record_number": i + 1,
                            "extraction_method": "line-by-line"
                        }
                    })
    except Exception as e:
        print(f"Error processing JSONL {file_path}: {e}")
        return [], "jsonl-error"
    return blocks, "jsonl"

# --- Plain Text & Markdown Extraction Service ---
def _extract_text(file_path: str, file_type: str) -> Tuple[List[Dict[str, Any]], str]:
    """
    A generic extractor for plain text files (.txt, .md, etc.). It reads the entire
    file content into a single block.

    Args:
        file_path (str): The path to the text file.
        file_type (str): The type of file ('txt', 'md', etc.).

    Returns:
        A list containing a single block with the file's content.
    """
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    blocks = [{
        "text": content,
        "metadata": {
            "source_filename": os.path.basename(file_path),
            "extraction_method": "plain-text"
        }
    }]
    return blocks, file_type


# --- File Extractor Router ---
# This dictionary maps file extensions to their corresponding extraction functions.
# This acts as a router to select the correct strategy based on file type.
FILE_EXTRACTORS = {
    'pdf': _extract_pdf,
    'html': _extract_html,
    'htm': _extract_html,
    'docx': _extract_docx,
    'xlsx': lambda p: _extract_spreadsheet(p, 'xlsx'),
    'csv': lambda p: _extract_spreadsheet(p, 'csv'),
    'sql': _extract_sql,
    'jsonl': _extract_jsonl,
    'txt': lambda p: _extract_text(p, 'txt'),
    'md': lambda p: _extract_text(p, 'md'),
}

# --- Main Entry Point ---
def extract_data_from_file(file_path: str) -> Tuple[List[Dict[str, Any]], str]:
    """
    Identifies the file type and routes it to the appropriate extraction function.

    Args:
        file_path (str): The path to the file to be processed.

    Returns:
        A tuple containing the list of extracted data blocks and the determined document type.
        If the file type is not supported, it falls back to a plain text extraction.
    """
    # Get the file extension to determine the file type.
    _, file_extension = os.path.splitext(file_path)
    file_type = file_extension.lower().strip('.')

    # Look up the appropriate extractor function from the router dictionary.
    extractor = FILE_EXTRACTORS.get(file_type)
    
    if extractor:
        # If an extractor is found, call it.
        blocks, doc_type = extractor(file_path)
        for block in blocks:
            block["metadata"]["doc_type"] = doc_type
        return blocks, doc_type
    else:
        # If the file type is unknown, use the plain text extractor as a fallback.
        print(f"No specific extractor for file type '{file_type}', using plain text fallback.")
        blocks, doc_type = _extract_text(file_path, 'unknown')
        for block in blocks:
            block["metadata"]["doc_type"] = doc_type
        return blocks, doc_type
