from modules.content_processing.domain.value_objects import StructuredSection


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

            #Root level content (level 0 in the json)
            if section.level == 0:
                current_hierarchy.clear()
                current_path = [section.heading]

            else:
                # Remove invalid hierarchy levels before inserting new node
                HierarchyBuilder._trim_hierarchy(current_hierarchy, section.level)

                current_hierarchy.append((section.level, section.heading))

                # Build full path from current hierarchy state
                current_path = HierarchyBuilder._extract_path(current_hierarchy)

            # Attach resolved hierarchy path to section
            processed_sections.append((section, current_path))

        return processed_sections

    @staticmethod
    def _trim_hierarchy(current_hierarchy: list[tuple[int,str]], current_level:int) -> None:
        """Removes hierarchy levels that are no longer valid"""
        while current_hierarchy and current_hierarchy[-1][0] >= current_level:
            current_hierarchy.pop()

    @staticmethod
    def _extract_path(current_hierarchy: list[tuple[int,str]]) -> list[str]:
        """Returns only the heading text from the current hierarchy state"""
        return [heading for _, heading in current_hierarchy]