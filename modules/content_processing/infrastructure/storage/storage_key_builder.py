import uuid


class StorageKeyBuilder:
    @staticmethod
    def build(user_id: int, course_id: int, filename: str) -> str:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
        return f"{user_id}/{course_id}/{uuid.uuid4()}.{ext}"