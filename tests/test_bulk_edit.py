from django.conf.urls import url
from django.db import models
from django.test import override_settings
from django.urls import reverse
from rest_framework import serializers
from rest_framework.generics import ListCreateAPIView
from rest_framework.test import APITestCase

from drf_tweaks.mixins import BulkEditAPIMixin


class FakeModel(models.Model):
    value = models.IntegerField()

    class Meta:
        ordering = ("id",)


class FakeSerializer(serializers.ModelSerializer):
    class Meta:
        model = FakeModel
        fields = ["id", "value"]


class BulkEditAPI(BulkEditAPIMixin, ListCreateAPIView):
    queryset = FakeModel.objects.all()
    serializer_class = FakeSerializer
    details_serializer_class = FakeSerializer
    permission_classes = []
    BULK_EDIT_ALLOW_DELETE_ITEMS = True
    BULK_EDIT_MAX_ITEMS = 10


urlpatterns = [
    url(r"^fakeapi$", BulkEditAPI.as_view(), name="bulkedit"),
]


@override_settings(ROOT_URLCONF="tests.test_bulk_edit")
class BulkEditMixinTestCase(APITestCase):
    def setUp(self):
        self.url = reverse("bulkedit")
        self.first_item = FakeModel.objects.create(value=1)
        self.second_item = FakeModel.objects.create(value=2)

    def _call_api(self, url, method, expected_status_code=200, data=None):
        response = getattr(self.client, method)(url, data or {}, format="json")
        self.assertEqual(response.status_code, expected_status_code, response.content)
        return response

    def test_api(self):
        # check payload
        response = self._call_api(self.url, "put", 400)
        self.assertEqual(
            response.data, {"non_field_errors": ["Payload for bulk edit must be a list of objects to edit."]}
        )

        # test incorrect payload (id must be present, otherwise the item is skipped)
        data = [{"medication": "Test"}, {"id": "sdsdads"}]
        response = self._call_api(self.url, "put", 200, data)
        self.assertEqual(len(response.data), 2)

        # test editing item that does not exist
        data = [{"id": 99, "value": 5}]
        self._call_api(self.url, "put", 404, data)

        data = [
            # incorrect item, should not be interpreted
            {"name": "LOL"},
            # item to create, but incorrect (validation failed)
            {"temp_id": 666},
            # correct item, but validation for above items failed, so it should NOT be changed
            {"id": self.first_item.pk, "value": 1},
            {"id": self.first_item.pk, "value": 1},  # send one item twice
        ]
        response = self._call_api(self.url, "put", 400, data)
        self.assertEqual(response.data, [{"temp_id": "666", "value": ["This field is required."]}])

        # editing more than "BULK_EDIT_MAX_ITEMS" cannot be allowed
        data = [{"id": self.first_item.pk, "value": 1}] * 11
        response = self._call_api(self.url, "put", 400, data)
        self.assertEqual(response.data, {"non_field_errors": ["Cannot edit more than 10 items at once."]})

        # test correct create + edit + delete
        data = [
            {"temp_id": -1, "value": -1},  # item to be created
            {"id": self.first_item.pk, "value": 100},  # item to be changed
            {"id": self.second_item.pk, "delete_object": True}  # item to be deleted
        ]
        response = self._call_api(self.url, "put", 200, data)
        self.assertEqual(response.data, [
            {"id": self.first_item.pk, "value": 100},
            {"id": 3, "value": -1}
        ])
