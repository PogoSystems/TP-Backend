import uuid
from supabase import AsyncClient


class SupabaseStorageAdapter:
    """
    Adapter for Supabase storage. Implements StoragePort
    """
    BUCKET = "pogo-storage"

    def __init__(self, client: AsyncClient) -> None:
        self._client = client

    async def upload(self, key: str, data: bytes, content_type: str) -> str:
        await self._client.storage.from_(self.BUCKET).upload(
            path=key,
            file=data,
            file_options={"content-type": content_type},
        )
        return key

    async def delete(self, key: str) -> None:
        await self._client.storage.from_(self.BUCKET).remove([key])