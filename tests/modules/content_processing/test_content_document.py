import pytest
from modules.content_processing.domain.aggregates.content_document import ContentDocumentAggregate


def test_content_document_requires_title_and_keys() -> None:
    with pytest.raises(ValueError, match="title is required"):
        ContentDocumentAggregate(title="", storage_key="s3://doc", course_id=1, user_id=1)
    with pytest.raises(ValueError, match="storage_key is required"):
        ContentDocumentAggregate(title="Intro", storage_key="", course_id=1, user_id=1)


def test_content_document_defaults() -> None:
    aggregate = ContentDocumentAggregate(title="Intro", storage_key="s3://doc", course_id=1, user_id=1)
    assert aggregate.created_at is not None
