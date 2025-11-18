
import unittest
import os
import hashlib
from app.services.extraction_service import extract_data_from_file
from app.services.cleaning_service import clean_and_enrich_blocks
from app.services.chunking_service import chunk_blocks
from app.services.data_processing_service import process_file

class TestProcessingPipeline(unittest.TestCase):

    def setUp(self):
        """Set up a dummy file for testing."""
        self.test_dir = "test_data"
        os.makedirs(self.test_dir, exist_ok=True)
        self.test_file_path = os.path.join(self.test_dir, "test_doc.txt")
        with open(self.test_file_path, "w") as f:
            f.write("This is the first sentence. This is the second sentence, which is a bit longer.")

    def tearDown(self):
        """Clean up the dummy file and directory."""
        os.remove(self.test_file_path)
        os.rmdir(self.test_dir)

    def test_extraction_service(self):
        """
        Tests the extraction service to ensure it correctly reads a file and attaches
        the expected file-derived (provenance) metadata.
        """
        blocks, doc_type = extract_data_from_file(self.test_file_path)
        
        # 1. Verify that content was extracted
        self.assertEqual(len(blocks), 1)
        self.assertIn("first sentence", blocks[0]['text'])
        
        # 2. Verify the document type is correct
        self.assertEqual(doc_type, 'txt')
        
        # 3. Verify that essential provenance metadata is attached
        metadata = blocks[0]['metadata']
        self.assertEqual(metadata['source_filename'], 'test_doc.txt')
        self.assertEqual(metadata['doc_type'], 'txt')
        self.assertEqual(metadata['extraction_method'], 'plain-text')

    def test_cleaning_service(self):
        """
        Tests the cleaning service to ensure it enriches blocks with the expected
        system and quality metadata.
        """
        raw_blocks = [{
            "text": "  Some text with whitespace.  ",
            "metadata": {"source_filename": "test.txt", "doc_type": "txt"}
        }]
        
        enriched_blocks = clean_and_enrich_blocks(raw_blocks)
        
        # 1. Verify text was cleaned
        self.assertEqual(enriched_blocks[0]['text'], "Some text with whitespace.")
        
        # 2. Verify that quality/system metadata was added
        metadata = enriched_blocks[0]['metadata']
        self.assertIn('normalized_text_hash', metadata)
        self.assertIn('language', metadata)
        self.assertIn('cleaning_version', metadata)
        self.assertIn('text_length', metadata)
        
        # 3. Verify the hash is correct
        expected_hash = hashlib.sha256("Some text with whitespace.".encode('utf-8')).hexdigest()
        self.assertEqual(metadata['normalized_text_hash'], expected_hash)

    def test_chunking_service(self):
        """
        Tests the chunking service to ensure it correctly splits a block into smaller
        chunks while preserving all existing metadata.
        """
        enriched_block = [{
            "text": "This is a long piece of text designed to be split into multiple chunks for testing purposes.",
            "metadata": {
                "source_filename": "test.txt",
                "doc_type": "txt",
                "normalized_text_hash": "dummy_hash"
            }
        }]
        
        # Use a small chunk size to guarantee splitting
        final_chunks = chunk_blocks(enriched_block, chunk_size=30, overlap=10)
        
        # 1. Verify the block was split into multiple chunks
        self.assertGreater(len(final_chunks), 1)
        
        # 2. Verify that metadata is preserved in all chunks
        for chunk in final_chunks:
            self.assertEqual(chunk['metadata']['source_filename'], 'test.txt')
            self.assertEqual(chunk['metadata']['normalized_text_hash'], 'dummy_hash')
            
            # 3. Verify that chunk-specific metadata was added
            self.assertIn('chunk_index', chunk['metadata'])
            self.assertIn('ingest_timestamp', chunk['metadata'])
            
        # 4. Verify content is correct
        self.assertTrue(final_chunks[0]['text'].startswith("This is a long piece"))
        self.assertTrue(final_chunks[1]['text'].startswith(" of text designed to"))

    def test_full_pipeline(self):
        """
        Tests the end-to-end data processing pipeline, ensuring a file is correctly
        processed from raw upload to final, metadata-rich chunks.
        """
        final_chunks = process_file(self.test_file_path)
        
        # 1. Verify that we have chunks as the output
        self.assertIsInstance(final_chunks, list)
        self.assertGreater(len(final_chunks), 0)
        
        # 2. Verify a sample chunk for correctness
        sample_chunk = final_chunks[0]
        self.assertIn('text', sample_chunk)
        self.assertIn('metadata', sample_chunk)
        
        # 3. Verify metadata from all stages is present in the final chunk
        metadata = sample_chunk['metadata']
        
        # - From Extraction
        self.assertEqual(metadata['source_filename'], 'test_doc.txt')
        self.assertEqual(metadata['doc_type'], 'txt')
        
        # - From Cleaning
        self.assertIn('normalized_text_hash', metadata)
        self.assertIn('language', metadata)
        
        # - From Chunking
        self.assertIn('chunk_index', metadata)
        self.assertIn('ingest_timestamp', metadata)

if __name__ == '__main__':
    unittest.main()
