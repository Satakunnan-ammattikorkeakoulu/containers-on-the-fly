"""Integration tests for helpers/tables/container.py CRUD operations."""

from helpers.tables.container import (
    get_containers, add_container, remove_container, edit_container,
)


class TestGetContainers:

    def test_returns_all(self, seed_test_data):
        result = get_containers()
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_filter_by_name(self, seed_test_data):
        result = get_containers(filter="Ubuntu Base")
        assert result is not None
        assert len(result) == 1
        assert result[0].name == "Ubuntu Base"

    def test_filter_by_id(self, seed_test_data):
        all_conts = get_containers()
        cont_id = all_conts[0].containerId
        result = get_containers(filter=str(cont_id))
        assert result is not None
        assert result[0].containerId == cont_id

    def test_filter_no_match(self):
        result = get_containers(filter="nonexistent")
        assert result is None


class TestAddContainer:

    def test_creates_container(self):
        cont = add_container("test-cont", True, "A test container", "test-image")
        assert cont is not None
        assert cont.name == "test-cont"
        assert cont.imageName == "test-image"
        assert cont.description == "A test container"

    def test_duplicate_returns_none(self):
        add_container("dup-cont", True, "desc", "img")
        result = add_container("dup-cont", False, "other", "img2")
        assert result is None


class TestRemoveContainer:

    def test_removes_container(self):
        cont = add_container("to-remove", True, "desc", "img")
        remove_container(cont.containerId)
        result = get_containers(filter="to-remove")
        assert result is None


class TestEditContainer:

    def test_edit_name(self):
        cont = add_container("old-name", True, "desc", "img")
        edit_container(cont.containerId, new_name="new-name")
        result = get_containers(filter="new-name")
        assert result is not None

    def test_edit_public(self):
        cont = add_container("pub-test", True, "desc", "img")
        edit_container(cont.containerId, new_public=False)
        result = get_containers(filter="pub-test")
        assert result[0].public is False

    def test_edit_description(self):
        cont = add_container("desc-test", True, "old desc", "img")
        edit_container(cont.containerId, new_description="new desc")
        result = get_containers(filter="desc-test")
        assert result[0].description == "new desc"

    def test_edit_image_name(self):
        cont = add_container("img-test", True, "desc", "old-img")
        edit_container(cont.containerId, new_image_name="new-img")
        result = get_containers(filter="img-test")
        assert result[0].imageName == "new-img"
