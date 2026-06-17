from typing import Protocol


"""
Port for any storage service 
"""
class StoragePort(Protocol):

    """ The document is uploaded, and it returns a storage_key"""
    async def upload(self, key:str, data:bytes, content_type:str) -> str:
        ...

    """ Delete the document from the storage"""
    async def delete(self, key:str) -> None:
        ...