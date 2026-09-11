import pytest

from poller import s3_listing

_PAGE_1 = """<?xml version="1.0" encoding="UTF-8"?>
<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
  <Name>cdn.pbc.org</Name>
  <Prefix>Main_Service/</Prefix>
  <IsTruncated>true</IsTruncated>
  <NextContinuationToken>token-2</NextContinuationToken>
  <Contents>
    <Key>Main_Service/2019/01/06/20190106.mp3</Key>
    <LastModified>2019-01-07T18:00:00.000Z</LastModified>
  </Contents>
  <Contents>
    <Key>Main_Service/2019/01/06/SE_20190106.pdf</Key>
    <LastModified>2019-01-07T18:00:00.000Z</LastModified>
  </Contents>
</ListBucketResult>
"""

_PAGE_2 = """<?xml version="1.0" encoding="UTF-8"?>
<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
  <Name>cdn.pbc.org</Name>
  <Prefix>Main_Service/</Prefix>
  <IsTruncated>false</IsTruncated>
  <Contents>
    <Key>Main_Service/2019/01/13/20190113.mp3</Key>
    <LastModified>2019-01-14T18:00:00.000Z</LastModified>
  </Contents>
</ListBucketResult>
"""

_MALFORMED = "<ListBucketResult><IsTruncated>false</Broken></ListBucketResult>"


def test_list_objects_follows_continuation_token_across_pages():
    pages = [_PAGE_1, _PAGE_2]
    fetched_urls = []

    def fake_get(url: str) -> bytes:
        fetched_urls.append(url)
        return pages.pop(0).encode("utf-8")

    results = list(
        s3_listing.list_objects("https://example.org/bucket", prefix="Main_Service/", get=fake_get)
    )

    assert [key for key, _ in results] == [
        "Main_Service/2019/01/06/20190106.mp3",
        "Main_Service/2019/01/06/SE_20190106.pdf",
        "Main_Service/2019/01/13/20190113.mp3",
    ]
    assert results[0][1].isoformat() == "2019-01-07T18:00:00+00:00"
    assert len(fetched_urls) == 2
    assert "continuation-token=token-2" in fetched_urls[1]
    assert "continuation-token" not in fetched_urls[0]


def test_list_objects_raises_on_malformed_xml():
    def fake_get(url: str) -> bytes:
        return _MALFORMED.encode("utf-8")

    with pytest.raises(s3_listing.S3ListingError):
        list(s3_listing.list_objects("https://example.org/bucket", prefix="Main_Service/", get=fake_get))
