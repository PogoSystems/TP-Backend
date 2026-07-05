import re

class TokenCounter:
    def count_tokens(self,text: str) -> int:
        """Calculate the number of tokens in a given text"""
        if not text:
            return 0
        tokens = re.findall(r"\w+|[^\w\s]", text)
        return len(tokens)

    def tokenize(self,text: str) -> list[str]:
        """
        Returns the tokens of the given text
        For example: ['Hello', 'world'] for the input "Hello world"
        """
        if not text:
            return []

        return re.findall(r"\w+|[^\w\s]", text)