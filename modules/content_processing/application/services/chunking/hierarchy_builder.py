from modules.content_processing.domain.value_objects import StructuredSection
import re

class HierarchyBuilder:
    """Reconstructs hierarchical heading paths from a list of structured sections
        Example output:
        ["Chapter 1", "Section 1.2", "Subsection 1.2.1"]
    """

    @staticmethod
    def process_heading_paths(sections: list[StructuredSection]
                              ) -> list [tuple[StructuredSection,list[str]]]:

        processed_sections: list[tuple[StructuredSection,list[str]]] = []

        current_hierarchy: list[tuple[int,str]] = []

        for section in sections:
            current_level = HierarchyBuilder._get_level(section)
            #Root level content (level 0 in the json)
            if current_level == 0:
                current_hierarchy.clear()
                current_path = [section.heading]

            else:
                # Remove invalid hierarchy levels before inserting new node
                HierarchyBuilder._trim_hierarchy(current_hierarchy, current_level)

                current_hierarchy.append((current_level, section.heading))

                # Build full path from current hierarchy state
                current_path = HierarchyBuilder._extract_path(current_hierarchy)

            # Attach resolved hierarchy path to section
            processed_sections.append((section, current_path))

        return processed_sections

    @staticmethod
    def _get_level(section: StructuredSection) -> int:
        """
        Extracts the heading format of the current hierarchy level
        If it's Numeric hierarchy (3.1.2)
        or Markdown heading level (###)

        """

        numeric_level = (HierarchyBuilder._extract_numeric_depth(section.heading))

        if numeric_level is not None:
            return numeric_level

        return section.level

    @staticmethod
    def _extract_numeric_depth(heading:str) -> int | None:
        """
         Extract hierarchy depth from numbered headings.
             Examples: '3. Introduction' -> 1
                        '3.1 Utility' -> 2
                        'Introduction' -> None
         """
        match=re.match( r"^(\d+(?:\.\d+)*)", heading.strip())

        if not match:
            return None

        numbering=match.group(1)
        return len(numbering.split("."))

    @staticmethod
    def _trim_hierarchy(current_hierarchy: list[tuple[int,str]], current_level:int) -> None:
        """Removes hierarchy levels that are no longer valid"""
        while current_hierarchy and current_hierarchy[-1][0] >= current_level:
            current_hierarchy.pop()

    @staticmethod
    def _extract_path(current_hierarchy: list[tuple[int,str]]) -> list[str]:
        """Returns only the heading text from the current hierarchy state"""
        return [heading for _, heading in current_hierarchy]