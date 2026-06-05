class ContextInjector:
    """Injects the context of the document into a chunk"""
    @staticmethod
    def inject_context(*,
                       document_title: str,
                       heading_path: list[str],
                       chunk_content: str) -> str:

        """Build each of the blocks/sections that made the enriched chunk"""
        title_section = document_title

        # Build the path only if the element exist
        if heading_path:
            heading_section=" > ".join(heading_path)
        else:
            heading_section = ""

        content_section = chunk_content

        if heading_section:
            return f"{title_section}\n\n{heading_section}\n\n{content_section}"
        else:
            return f"{title_section}\n\n{content_section}"