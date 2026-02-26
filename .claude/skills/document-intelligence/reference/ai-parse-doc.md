# AI_PARSE_DOCUMENT Reference - Content Parsing

Reference documentation for full document parsing using Snowflake's `AI_PARSE_DOCUMENT` function.

## Overview

Extract text, layout, and images from documents with high fidelity. Returns Markdown-formatted output.

## Constraints

| Constraint | Limit |
|------------|-------|
| Max file size | 50 MB |
| Max pages | 500 per call |
| Page dimensions | 1200 x 1200 mm max |

## Supported Formats

- **Primary:** PDF
- **Images:** Supported for OCR mode

## Basic Syntax

```sql
SELECT AI_PARSE_DOCUMENT(
  TO_FILE('@stage_path', 'filename'),
  {'mode': 'LAYOUT'}
) AS parsed;
```

## Parsing Modes

| Mode | Best For | Description |
|------|----------|-------------|
| **LAYOUT** | Complex documents | Tables, headers, multi-column, research papers, financial docs |
| **OCR** | Simple text | Quick extraction from manuals, contracts, policies |

```sql
-- LAYOUT mode (recommended for most use cases)
SELECT AI_PARSE_DOCUMENT(
  TO_FILE('@stage', 'document.pdf'),
  {'mode': 'LAYOUT'}
);

-- OCR mode (faster, simpler)
SELECT AI_PARSE_DOCUMENT(
  TO_FILE('@stage', 'document.pdf'),
  {'mode': 'OCR'}
);
```

## Page Options

### page_split - Returns each page separately
```sql
SELECT AI_PARSE_DOCUMENT(
  TO_FILE('@stage', 'document.pdf'),
  {'mode': 'LAYOUT', 'page_split': true}
);
```

### page_filter - Process specific pages (0-indexed)

**Array of page numbers:**
```sql
{'mode': 'LAYOUT', 'page_filter': [0, 1, 2, 5, 10]}
```

**Range of pages:**
```sql
{'mode': 'LAYOUT', 'page_filter': [{'start': 0, 'end': 50}]}
```

**Multiple ranges:**
```sql
{'mode': 'LAYOUT', 'page_filter': [{'start': 0, 'end': 10}, {'start': 50, 'end': 60}]}
```

## Response Format

```json
{
  "metadata": {"pageCount": 19},
  "pages": [
    {"content": "# Heading\n\nMarkdown content...", "index": 0},
    {"content": "More content...", "index": 1}
  ]
}
```

- Content is **Markdown formatted**
- Tables preserved as Markdown tables
- Headers maintain hierarchy
- Reading order preserved

## Common Patterns

### Basic Parsing
```sql
SELECT AI_PARSE_DOCUMENT(
  TO_FILE('@db.schema.stage', 'document.pdf'),
  {'mode': 'LAYOUT'}
) AS parsed;
```

### With All Options
```sql
SELECT AI_PARSE_DOCUMENT(
  TO_FILE('@db.schema.stage', 'document.pdf'),
  {
    'mode': 'LAYOUT',
    'page_split': true,
    'page_filter': [0, 1, 2]
  }
) AS parsed;
```

### Flatten Pages to Rows
```sql
SELECT 
  f.value:index::INT AS page_num,
  f.value:content::STRING AS content
FROM (
  SELECT AI_PARSE_DOCUMENT(
    TO_FILE('@stage', 'doc.pdf'),
    {'mode': 'LAYOUT', 'page_split': true}
  ) AS parsed
), LATERAL FLATTEN(input => parsed:pages) f;
```

### Batch Processing
```sql
ALTER STAGE @db.schema.stage SET DIRECTORY = (ENABLE = TRUE);
ALTER STAGE @db.schema.stage REFRESH;

SELECT 
  relative_path,
  AI_PARSE_DOCUMENT(
    TO_FILE('@db.schema.stage', relative_path),
    {'mode': 'LAYOUT', 'page_split': true}
  ) AS parsed
FROM DIRECTORY(@db.schema.stage)
WHERE relative_path LIKE '%.pdf';
```

## Large Document Chunking (>500 pages)

### Step 1: Get Page Count
```sql
SELECT PARSE_JSON(AI_PARSE_DOCUMENT(
  TO_FILE('@stage', 'large_document.pdf'),
  {'mode': 'OCR', 'page_filter': [{'start': 0, 'end': 1}]}
)):metadata:pageCount::INT AS total_pages;
```

### Step 2: Process in Chunks
```sql
-- Create temp table for results
CREATE OR REPLACE TEMPORARY TABLE chunk_results (
  chunk_id INT,
  start_page INT,
  end_page INT,
  parsed_result VARIANT
);

-- Chunk 1: Pages 0-499
INSERT INTO chunk_results
SELECT 1, 0, 500, PARSE_JSON(AI_PARSE_DOCUMENT(
  TO_FILE('@stage', 'large_document.pdf'),
  {'mode': 'LAYOUT', 'page_filter': [{'start': 0, 'end': 500}], 'page_split': true}
));

-- Chunk 2: Pages 500-999
INSERT INTO chunk_results
SELECT 2, 500, 1000, PARSE_JSON(AI_PARSE_DOCUMENT(
  TO_FILE('@stage', 'large_document.pdf'),
  {'mode': 'LAYOUT', 'page_filter': [{'start': 500, 'end': 1000}], 'page_split': true}
));

-- Chunk 3: Pages 1000-1200
INSERT INTO chunk_results
SELECT 3, 1000, 1200, PARSE_JSON(AI_PARSE_DOCUMENT(
  TO_FILE('@stage', 'large_document.pdf'),
  {'mode': 'LAYOUT', 'page_filter': [{'start': 1000, 'end': 1200}], 'page_split': true}
));
```

### Step 3: Combine Results
```sql
SELECT OBJECT_CONSTRUCT(
  'metadata', OBJECT_CONSTRUCT(
    'pageCount', (SELECT MAX(end_page) FROM chunk_results),
    'chunks_processed', (SELECT COUNT(*) FROM chunk_results)
  ),
  'pages', combined_pages.all_pages
) AS final_result
FROM (
  SELECT ARRAY_AGG(page.value) WITHIN GROUP (ORDER BY page.value:index::INT) AS all_pages
  FROM chunk_results cr,
  LATERAL FLATTEN(input => cr.parsed_result:pages) page
) combined_pages;
```

### Dynamic Chunking Procedure
```sql
CREATE OR REPLACE PROCEDURE parse_large_document(
  stage_path VARCHAR,
  file_name VARCHAR,
  mode VARCHAR DEFAULT 'LAYOUT'
)
RETURNS VARIANT
LANGUAGE SQL
AS
$
DECLARE
  total_pages INT;
  chunk_size INT := 500;
  current_start INT := 0;
  result_array ARRAY := ARRAY_CONSTRUCT();
BEGIN
  -- Get page count
  SELECT PARSE_JSON(AI_PARSE_DOCUMENT(
    TO_FILE(:stage_path, :file_name),
    {'mode': 'OCR', 'page_filter': [{'start': 0, 'end': 1}]}
  )):metadata:pageCount::INT INTO total_pages;
  
  -- Process in chunks
  WHILE (current_start < total_pages) DO
    LET chunk_end INT := LEAST(current_start + chunk_size, total_pages);
    LET chunk_result VARIANT := PARSE_JSON(AI_PARSE_DOCUMENT(
      TO_FILE(:stage_path, :file_name),
      OBJECT_CONSTRUCT('mode', :mode, 'page_filter', 
        ARRAY_CONSTRUCT(OBJECT_CONSTRUCT('start', current_start, 'end', chunk_end)),
        'page_split', TRUE)
    ));
    result_array := ARRAY_CAT(result_array, chunk_result:pages);
    current_start := chunk_end;
  END WHILE;
  
  RETURN OBJECT_CONSTRUCT(
    'metadata', OBJECT_CONSTRUCT('pageCount', total_pages),
    'pages', result_array
  );
END;
$;

-- Usage
CALL parse_large_document('@db.schema.stage', 'large_document.pdf', 'LAYOUT');
```

## Visual Content Analysis

For charts, graphs, blueprints - chain with AI_COMPLETE:

```sql
-- Step 1: Parse document
SELECT AI_PARSE_DOCUMENT(
  TO_FILE('@stage', 'report.pdf'),
  {'mode': 'LAYOUT', 'page_split': true}
) AS parsed;

-- Step 2: Analyze visual content
SELECT AI_COMPLETE(
  'claude-3-5-sonnet',
  [
    {
      'role': 'user',
      'content': [
        {'type': 'text', 'text': 'Analyze this chart. Extract data points, trends, and key insights.'},
        {'type': 'image_url', 'image_url': {'url': '<extracted_image_url>'}}
      ]
    }
  ],
  {}
);
```

### Visual Analysis Prompts

| Content Type | Prompt |
|--------------|--------|
| Charts/Graphs | "Extract chart type, axes labels, all data points, and key trends." |
| Blueprints | "Identify components, dimensions, labels, and scale." |
| Flowcharts | "Describe the process flow, nodes, connections, and endpoints." |
| Tables | "Extract all table data into structured format with headers and rows." |

## RAG Integration

```sql
-- Create chunks table with embeddings
CREATE TABLE doc_chunks (
  doc_id VARCHAR,
  page_num INT,
  content VARCHAR,
  embedding VECTOR(FLOAT, 1024)
);

-- Insert parsed content with embeddings
INSERT INTO doc_chunks
SELECT 
  'doc_001',
  f.value:index::INT,
  f.value:content::STRING,
  SNOWFLAKE.CORTEX.EMBED_TEXT_1024('voyage-multilingual-2', f.value:content::STRING)
FROM (
  SELECT AI_PARSE_DOCUMENT(
    TO_FILE('@stage', 'doc.pdf'),
    {'mode': 'LAYOUT', 'page_split': true}
  ) AS parsed
), LATERAL FLATTEN(input => parsed:pages) f;

-- Search similar content
SELECT 
  doc_id,
  page_num,
  content,
  VECTOR_COSINE_SIMILARITY(embedding, 
    SNOWFLAKE.CORTEX.EMBED_TEXT_1024('voyage-multilingual-2', 'search query')
  ) AS similarity
FROM doc_chunks
ORDER BY similarity DESC
LIMIT 5;
```

## Concatenate All Pages

```sql
-- Combine all pages into single text
SELECT LISTAGG(f.value:content::STRING, '\n\n--- Page Break ---\n\n') 
  WITHIN GROUP (ORDER BY f.value:index::INT) AS full_document
FROM (
  SELECT AI_PARSE_DOCUMENT(
    TO_FILE('@stage', 'doc.pdf'),
    {'mode': 'LAYOUT', 'page_split': true}
  ) AS parsed
), LATERAL FLATTEN(input => parsed:pages) f;
```

## Error Handling

```sql
SELECT 
  relative_path,
  CASE 
    WHEN TRY_PARSE_JSON(parsed) IS NULL THEN 'PARSE_ERROR'
    WHEN parsed:error IS NOT NULL THEN parsed:error::STRING
    ELSE 'SUCCESS'
  END AS status,
  COALESCE(parsed:metadata:pageCount::INT, 0) AS pages_processed
FROM (
  SELECT relative_path, AI_PARSE_DOCUMENT(...) AS parsed
  FROM ...
);
```
