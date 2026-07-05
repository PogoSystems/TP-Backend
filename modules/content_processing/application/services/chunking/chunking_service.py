
from llama_index.core.node_parser import SentenceSplitter

from modules.content_processing.application.services.chunking.context_injector import ContextInjector
from modules.content_processing.application.services.chunking.hierarchy_builder import HierarchyBuilder
from modules.content_processing.domain.value_objects import PreparedDocument, StructuredSection
from modules.content_processing.domain.value_objects.chunk import ChunkedDocument, Chunk
from modules.content_processing.infrastructure.tokenizers.token_counter import TokenCounter

from core.settings import settings

class ChunkingService:
    """
    Service responsible for orchestrating the chunking pipeline
    """

    def __init__(self,*,
                 token_counter:TokenCounter,
                 max_chunk_tokens: int = settings.CHUNK_SIZE,
                 chunk_overlap: int = settings.CHUNK_OVERLAP) -> None:
        self._token_counter = token_counter
        self._max_tokens = max_chunk_tokens

        # LlamaIndex splitter for the sections that exceeds the token limits
        self._sentence_splitter = SentenceSplitter(
            chunk_size=max_chunk_tokens,
            chunk_overlap=chunk_overlap,
            tokenizer=token_counter.tokenize
        )

    def chunk_document(self,prepared_doc: PreparedDocument) -> ChunkedDocument:
        """
        Orchestrate the conversion of a structured document into a list of chunks
        """
        list_chunks : list[Chunk] = []

        # convert flat sections into hierarchical paths
        sections_with_paths = HierarchyBuilder.process_heading_paths(prepared_doc.sections)

        global_index=0

        # process each section and apply the chunking strategy
        for sections, path in sections_with_paths:
            section_chunks = self._chunk_section(
                prepared_doc,
                sections,
                path,
                start_index=global_index
            )

            list_chunks.extend(section_chunks)
            global_index += len(section_chunks)

        # wrap the result into a chunkDocument object for the embedding model
        return ChunkedDocument(document_title=prepared_doc.raw.title,
                               chunks=list_chunks)

    def _chunk_section(self,
                       prepared_doc: PreparedDocument,
                       section: StructuredSection,
                       heading_path: list[str],
                       start_index: int) -> list[Chunk]:

        """
        Applies the chunking strategy to a structured section
        If it has less than 512 tokens -> single chunk
        If it has more than 512 tokens -> semantic splitting in multiple chunks
        """
        text=section.text
        token_count = self._token_counter.count_tokens(text)

        # is the section has fewer tokens than the token limit
        if token_count <= self._max_tokens:
            return [
                self._create_chunk(
                    prepared_doc,
                    section,
                    heading_path,
                    text,
                    index=start_index,
                    token_count=token_count
                )
            ]

            #if the section exceeds the token limit
        splits=self._sentence_splitter.split_text(text)
        # each split becomes an independent chunk
        return [
            self._create_chunk(
                 prepared_doc,
                section,
                heading_path,
                split,
                index=start_index + i,
                token_count=self._token_counter.count_tokens(split),
            )
            for i, split in enumerate(splits)
        ]

    def _create_chunk(self,
                      prepared_doc: PreparedDocument,
                       section: StructuredSection,
                      heading_path: list[str],
                      chunk_text: str,
                      index: int,
                      token_count: int) -> Chunk:

        """
        Constructs the final chunk object.
        It combines: Raw text of the document, the enriched text after the context injection, metadata and id (UUID)
        """

        enriched_text = ContextInjector.inject_context(
            document_title=prepared_doc.raw.title,
            heading_path=heading_path,
            chunk_content=chunk_text,
        )

        # data for the vectorial database
        metadata = {
            **section.metadata,
            "storage_key": prepared_doc.raw.storage_key,
            "document_type": prepared_doc.raw.document_type,
            "section_index": section.index
        }

        # final chunk object
        return Chunk(
            document_title=prepared_doc.raw.title,
            chunk_index=index,
            heading_path=heading_path,
            raw_content=chunk_text,
            enriched_text=enriched_text,
            token_count=token_count,
            metadata=metadata
        )