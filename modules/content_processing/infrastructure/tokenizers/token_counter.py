from tokenizers import Tokenizer

class TokenCounter:
    def __init__(self) -> None:
        # Call the tokenizer
        self._tokenizer = Tokenizer.from_pretrained("bert-base-uncased")

    def count_tokens(self,text: str) -> int:
        """Calculate the number of tokens in a given text"""
        if not text:
            return 0
        return len(self._tokenizer.encode(text, add_special_tokens=False).ids)

    def tokenize(self,text: str) -> list[str]:
        """
        Returns the tokens of the given text
        For example: ['Hello', 'world'] for the input "Hello world"
        """
        if not text:
            return []

        encoding= self._tokenizer.encode(text, add_special_tokens=False)
        return encoding.tokens