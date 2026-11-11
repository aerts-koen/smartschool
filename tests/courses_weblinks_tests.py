import pytest
from requests_mock import Mocker

from smartschool import CourseCondensed, Smartschool, SmartSchoolException, SmartSchoolParsingError, Weblink, WeblinkFolder
from smartschool._common import bs4_html


@pytest.fixture
def course(session: Smartschool) -> CourseCondensed:
    return CourseCondensed(session=session, name="Course", teacher="Teacher", url="url", id=1975, platform_id=49)


def test_weblinks_root(course: CourseCondensed):
    sut = course.weblinks

    assert [type(item) for item in sut] == [WeblinkFolder, Weblink, Weblink]
    assert [item.name for item in sut] == ["Oefeningen", "Atlas", "Woordenboek"]

    folder = sut[0]
    assert isinstance(folder, WeblinkFolder)
    assert folder.id == 201
    assert folder.description == "Extra oefeningen per hoofdstuk"
    assert folder.browse_url == "/Weblinks/Index/Index/courseID/1975/parentID/201/ssID/49"

    link = sut[1]
    assert isinstance(link, Weblink)
    assert link.id == 102
    assert link.description == ""
    assert link.show_url == "/Weblinks/Showlink/Index/courseID/1975/linkID/102/ssID/49"


def test_weblinks_subfolder(course: CourseCondensed):
    folder = course.weblinks[0]
    assert isinstance(folder, WeblinkFolder)

    sut = folder.items

    assert len(sut) == 1
    assert isinstance(sut[0], Weblink)
    assert sut[0].name == "Hoofdstuk 3"
    assert sut[0].description == "Oefeningen op breuken"
    assert sut[0].parent is folder


def test_weblink_url_follows_the_redirect(course: CourseCondensed, requests_mock: Mocker):
    link = course.weblinks[1]
    assert isinstance(link, Weblink)
    requests_mock.get(link.show_url, status_code=302, headers={"Location": "https://example.com/atlas"})

    assert link.url == "https://example.com/atlas"


def test_weblink_url_without_redirect(course: CourseCondensed, requests_mock: Mocker):
    link = course.weblinks[1]
    assert isinstance(link, Weblink)
    requests_mock.get(link.show_url, text="<html></html>")

    assert link.url == course.session.create_url(link.show_url)


def test_weblinks_fetch_error(course: CourseCondensed, requests_mock: Mocker):
    folder = WeblinkFolder(session=course.session, parent=None, course=course, name="(Root)")
    requests_mock.get(folder.browse_url, status_code=500)

    with pytest.raises(SmartSchoolException, match="Failed to fetch weblinks HTML"):
        _ = folder.items


def test_weblinks_unknown_row(course: CourseCondensed):
    folder = WeblinkFolder(session=course.session, parent=None, course=course, name="(Root)")
    row = bs4_html('<div class="smsc_cm_body_row"><div class="name"><a href="/somewhere/else">x</a></div></div>').select_one("div")
    assert row is not None

    with pytest.raises(SmartSchoolParsingError, match="Unknown weblink row"):
        folder._parse_row(row)  # pylint: disable=protected-access  # white-box test
