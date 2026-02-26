# AI_EXTRACT Reference - Structured Extraction

Reference documentation for structured data extraction using Snowflake's `AI_EXTRACT` function.

## Overview

Extract specific fields, tables, and answers from documents. Returns JSON output.

## Constraints

| Constraint | Limit |
|------------|-------|
| Max file size | 100 MB |
| Max pages | 125 per call |
| Entity questions | 100 per call (512 tokens each) |
| Table questions | 10 per call (4096 tokens each) |
| Image dimensions | 50x50 to 10,000x10,000 pixels |

**Note:** 1 table question = 10 entity questions for quota purposes.

## Supported Formats

PDF, PNG, PPTX/PPT, EML, DOC/DOCX, JPEG/JPG, HTM/HTML, TEXT/TXT, TIF/TIFF, BMP, GIF, WEBP, MD

## Basic Syntax

```sql
SELECT AI_EXTRACT(
  file => TO_FILE('@stage_path', 'filename'),
  responseFormat => {
    'field_name': 'extraction question'
  }
) AS result;
```

## Response Format Types

### Single Values
```sql
responseFormat => {
  'invoice_number': 'What is the invoice number?',
  'date': 'What is the invoice date?',
  'total': 'What is the total amount?'
}
```

### Tables (JSON Schema)
```sql
responseFormat => {
  'schema': {
    'type': 'object',
    'properties': {
      'line_items': {
        'description': 'Invoice line items',
        'type': 'object',
        'column_ordering': ['item', 'qty', 'price'],
        'properties': {
          'item': {'type': 'array'},
          'qty': {'type': 'array'},
          'price': {'type': 'array'}
        }
      }
    }
  }
}
```

## Common Templates

### Invoice Extraction
```sql
SELECT AI_EXTRACT(
  file => TO_FILE('@stage', 'invoice.pdf'),
  responseFormat => {
    'schema': {
      'type': 'object',
      'properties': {
        'invoice_number': {'type': 'string', 'description': 'Invoice number'},
        'date': {'type': 'string', 'description': 'Invoice date'},
        'vendor': {'type': 'string', 'description': 'Vendor name'},
        'total': {'type': 'string', 'description': 'Total amount'},
        'line_items': {
          'type': 'object',
          'description': 'Line items',
          'column_ordering': ['description', 'qty', 'price', 'amount'],
          'properties': {
            'description': {'type': 'array'},
            'qty': {'type': 'array'},
            'price': {'type': 'array'},
            'amount': {'type': 'array'}
          }
        }
      }
    }
  }
);
```

### Contract Extraction
```sql
SELECT AI_EXTRACT(
  file => TO_FILE('@stage', 'contract.pdf'),
  responseFormat => {
    'parties': 'Who are the parties in this agreement?',
    'effective_date': 'What is the effective date?',
    'termination_date': 'What is the termination date?',
    'payment_terms': 'What are the payment terms?',
    'governing_law': 'What jurisdiction governs this agreement?'
  }
);
```

### Receipt/Expense
```sql
SELECT AI_EXTRACT(
  file => TO_FILE('@stage', 'receipt.pdf'),
  responseFormat => {
    'merchant': 'What is the merchant or store name?',
    'date': 'What is the transaction date?',
    'total': 'What is the total amount paid?',
    'payment_method': 'What payment method was used?',
    'items': 'List all purchased items'
  }
);
```

## Batch Processing

```sql
-- Enable directory table
ALTER STAGE @db.schema.stage SET DIRECTORY = (ENABLE = TRUE);
ALTER STAGE @db.schema.stage REFRESH;

-- Process all files
SELECT 
  relative_path,
  AI_EXTRACT(
    file => TO_FILE('@db.schema.stage', relative_path),
    responseFormat => {
      'invoice_number': 'What is the invoice number?',
      'total': 'What is the total amount?'
    }
  ) AS result
FROM DIRECTORY(@db.schema.stage)
WHERE relative_path LIKE '%.pdf';
```

## Parsing Results

```sql
-- Extract fields from JSON response
SELECT 
  relative_path,
  result:response:invoice_number::STRING AS invoice_number,
  result:response:total::STRING AS total_amount,
  result:response:line_items AS line_items
FROM (
  SELECT 
    relative_path,
    AI_EXTRACT(...) AS result
  FROM ...
);
```

## Large Document Strategies (>125 pages)

AI_EXTRACT does not support `page_filter`. For large documents, use one of these approaches:

### Option A: Parse-Then-Extract (Recommended)

Use AI_PARSE_DOCUMENT to chunk, then AI_COMPLETE to extract:

```sql
-- Step 1: Parse document in chunks
CREATE OR REPLACE TEMPORARY TABLE doc_chunks AS
SELECT 
  page.value:index::INT AS page_num,
  page.value:content::STRING AS content
FROM (
  SELECT PARSE_JSON(AI_PARSE_DOCUMENT(
    TO_FILE('@stage', 'large_doc.pdf'),
    {'mode': 'LAYOUT', 'page_filter': [{'start': 0, 'end': 125}], 'page_split': true}
  )) AS parsed
  UNION ALL
  SELECT PARSE_JSON(AI_PARSE_DOCUMENT(
    TO_FILE('@stage', 'large_doc.pdf'),
    {'mode': 'LAYOUT', 'page_filter': [{'start': 125, 'end': 250}], 'page_split': true}
  )) AS parsed
) chunks,
LATERAL FLATTEN(input => chunks.parsed:pages) page;

-- Step 2: Extract from each chunk using AI_COMPLETE
SELECT 
  page_num,
  PARSE_JSON(AI_COMPLETE(
    'claude-3-5-sonnet',
    'Extract invoice_number, date, and amounts from:\n\n' || content ||
    '\n\nReturn as JSON.'
  )) AS extracted
FROM doc_chunks;
```

### Option B: Split PDF Externally

```python
# split_pdf.py - requires: pip install pypdf
from pypdf import PdfReader, PdfWriter
import sys, os

def split_pdf(input_path, output_dir, chunk_size=125):
    reader = PdfReader(input_path)
    total_pages = len(reader.pages)
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    
    for start in range(0, total_pages, chunk_size):
        end = min(start + chunk_size, total_pages)
        writer = PdfWriter()
        for page_num in range(start, end):
            writer.add_page(reader.pages[page_num])
        chunk_path = os.path.join(output_dir, f"{base_name}_pages_{start+1}_to_{end}.pdf")
        with open(chunk_path, 'wb') as f:
            writer.write(f)
        print(f"Created: {chunk_path}")

if __name__ == "__main__":
    split_pdf(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 125)
```

Then upload and process:
```sql
PUT file://./chunks/*.pdf @stage/chunks/;

SELECT relative_path, AI_EXTRACT(...) AS result
FROM DIRECTORY(@stage)
WHERE relative_path LIKE 'chunks/%.pdf';
```

### Option C: Merge Chunk Results

```sql
-- Combine entity extractions
SELECT 
  COALESCE(MAX(CASE WHEN result:response:invoice_number != '' 
      THEN result:response:invoice_number END), 'Not found')::STRING AS invoice_number,
  MIN(result:response:date)::STRING AS earliest_date,
  SUM(TRY_TO_DECIMAL(result:response:total, 10, 2)) AS combined_total
FROM chunk_extraction_results;
```

## Supported Languages

Arabic, Bengali, Burmese, Cebuano, Chinese, Czech, Dutch, English, French, German, Hebrew, Hindi, Indonesian, Italian, Japanese, Khmer, Korean, Lao, Malay, Persian, Polish, Portuguese, Russian, Spanish, Tagalog, Thai, Turkish, Urdu, Vietnamese

## Error Handling

```sql
-- Handle extraction errors gracefully
SELECT 
  relative_path,
  CASE 
    WHEN TRY_PARSE_JSON(result) IS NULL THEN 'PARSE_ERROR'
    WHEN result:error IS NOT NULL THEN result:error::STRING
    ELSE 'SUCCESS'
  END AS status,
  result
FROM (
  SELECT relative_path, AI_EXTRACT(...) AS result
  FROM ...
);
```
