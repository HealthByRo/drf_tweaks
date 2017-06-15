# -*- coding: utf-8 -*-
from django.conf.urls import url
from rest_framework.permissions import AllowAny
from django.test import override_settings
from drf_tweaks import serializers
from rest_framework.serializers import CharField
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.reverse import reverse
from drf_tweaks.optimizator import optimize
from drf_tweaks import test_utils
from tests.models import AutoOptimization1Model, AutoOptimization2Model, AutoOptimization3Model, SampleModel


# serializers for many to one - forward tests (select related)
class SimpleSelectRelated3Serializer(serializers.ModelSerializer):
    class Meta:

        model = AutoOptimization3Model
        fields = ["id", "name"]


class SimpleSelectRelated2Serializer(serializers.ModelSerializer):
    fk_3_1_data = SimpleSelectRelated3Serializer(source="fk_3_1", read_only=True)
    fk_3_2_data = SimpleSelectRelated3Serializer(source="fk_3_2", read_only=True)

    class Meta:
        model = AutoOptimization2Model
        fields = ["id", "name", "fk_3_1", "fk_3_1_data", "fk_3_2", "fk_3_2_data"]


class SimpleSelectRelatedSerializer(serializers.ModelSerializer):
    fk_2_data = SimpleSelectRelated2Serializer(source="fk_2", read_only=True)

    class Meta:
        model = AutoOptimization1Model
        fields = ["id", "name", "fk_2", "fk_2_data"]


# serializers for many to one - reverse tests (prefetch related)
class SimplePrefetchRelated3Serializer(serializers.ModelSerializer):
    class Meta:
        model = AutoOptimization1Model
        fields = ["id", "name"]


class SimplePrefetchRelated2Serializer(serializers.ModelSerializer):
    reverse_1_data = SimplePrefetchRelated3Serializer(source="reverse_1", read_only=True, many=True)

    class Meta:
        model = AutoOptimization2Model
        fields = ["id", "name", "reverse_1", "reverse_1_data"]


class SimplePrefetchRelatedSerializer(serializers.ModelSerializer):
    reverse_2_1_data = SimplePrefetchRelated2Serializer(source="reverse_2_1", read_only=True, many=True)
    reverse_2_2_data = SimplePrefetchRelated2Serializer(source="reverse_2_2", read_only=True, many=True)

    class Meta:
        model = AutoOptimization3Model
        fields = ["id", "name", "reverse_2_1", "reverse_2_2", "reverse_2_1_data", "reverse_2_2_data"]


# serializers for combining prefetch related with select related
class SampleSerializer(serializers.ModelSerializer):
    class Meta:
        model = SampleModel
        fields = ["a", "b"]


class PrefetchWithSelectRelated3Serializer(serializers.ModelSerializer):
    sample_m2m_data = SampleSerializer(source="sample_m2m", read_only=True, many=True)

    class Meta:
        model = AutoOptimization1Model
        fields = ["id", "name", "sample_m2m_data"]
        on_demand_fields = ["sample_m2m_data"]


class PrefetchWithSelectRelated2Serializer(serializers.ModelSerializer):
    reverse_1_data = PrefetchWithSelectRelated3Serializer(source="reverse_1", read_only=True, many=True)
    sample_data = SampleSerializer(source="sample", read_only=True)

    class Meta:
        model = AutoOptimization2Model
        fields = ["id", "name", "reverse_1", "reverse_1_data", "sample_data"]


class PrefetchWithSelectRelatedSerializer(serializers.ModelSerializer):
    reverse_2_1_data = PrefetchWithSelectRelated2Serializer(source="reverse_2_1", read_only=True, many=True)
    reverse_2_2_data = PrefetchWithSelectRelated2Serializer(source="reverse_2_2", read_only=True, many=True)
    sample_data = SampleSerializer(source="sample", read_only=True)

    class Meta:
        model = AutoOptimization3Model
        fields = ["id", "name", "reverse_2_1", "reverse_2_2", "reverse_2_1_data", "reverse_2_2_data", "sample_data"]


# simple serializer for select_related for the source
class SelectRelatedBySourceSerializer(serializers.ModelSerializer):
    fk_2_name = CharField(source="fk_2.name", read_only=True)

    class Meta:
        model = AutoOptimization1Model
        fields = ["id", "name", "fk_2", "fk_2_name"]


# APIs
@optimize()
class SimpleSelectRelatedAPI(ListAPIView):
    queryset = AutoOptimization1Model.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = SimpleSelectRelatedSerializer


@optimize()
class SimplePrefetchRelatedAPI(RetrieveAPIView):
    queryset = AutoOptimization3Model.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = SimplePrefetchRelatedSerializer

    def get_object(self):
        return self.get_queryset().first()


@optimize()
class PrefetchWithSelectRelatedAPI(ListAPIView):
    queryset = AutoOptimization3Model.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = PrefetchWithSelectRelatedSerializer


@optimize()
class SelectRelatedBySourceAPI(ListAPIView):
    queryset = AutoOptimization1Model.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = SelectRelatedBySourceSerializer


urlpatterns = [
    url(r"^autooptimization/simple-select-related$", SimpleSelectRelatedAPI.as_view(), name="simple-select-related"),
    url(r"^autooptimization/simple-prefetch-related$", SimplePrefetchRelatedAPI.as_view(),
        name="simple-prefetch-related"),
    url(r"^autooptimization/prefetch-with-select-related$", PrefetchWithSelectRelatedAPI.as_view(),
        name="prefetch-with-select-related"),
    url(r"^autooptimization/select-related-by-source$", SelectRelatedBySourceAPI.as_view(),
        name="select-related-by-source"),
]


@override_settings(ROOT_URLCONF="tests.test_autooptimization")
class TestAutoOptimization(test_utils.QueryCountingApiTestCase):
    def setUp(self):
        self.sample_models = []
        self.lvl_3_models = []
        self.lvl_2_models = []
        self.lvl_1_models = []
        for dummy in range(0, 3):
            self.sample_models.append(SampleModel.objects.create(a="a", b="b"))

        for dummy in range(0, 3):
            self.lvl_3_models.append(
                AutoOptimization3Model.objects.create(name="m3", sample=self.sample_models[0])
            )
            for dummy_2 in range(0, 3):
                self.lvl_2_models.append(
                    AutoOptimization2Model.objects.create(
                        name="m2", sample=self.sample_models[0],
                        fk_3_1=self.lvl_3_models[-1], fk_3_2=self.lvl_3_models[-1]
                    )
                )
                for dummy_3 in range(0, 3):
                    self.lvl_1_models.append(
                        AutoOptimization1Model.objects.create(
                            name="m1", fk_2=self.lvl_2_models[-1]
                        )
                    )
                    self.lvl_1_models[-1].sample_m2m.add(*self.sample_models)

    def test_select_related(self):
        response = self.client.get(reverse("simple-select-related"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 27)
        self.assertEqual(response.data[0]["name"], "m1")
        self.assertEqual(response.data[0]["fk_2_data"]["name"], "m2")
        self.assertEqual(response.data[0]["fk_2_data"]["fk_3_1_data"]["name"], "m3")
        self.assertEqual(response.data[0]["fk_2_data"]["fk_3_2_data"]["name"], "m3")
        self.assertEqual(test_utils.TestQueryCounter().get_counter(), 1)
        query_stack = test_utils.TestQueryCounter().get_queries_stack()
        self.assertIn("tests_autooptimization1model", query_stack[0][0])
        self.assertIn("tests_autooptimization2model", query_stack[0][0])
        self.assertIn("tests_autooptimization3model", query_stack[0][0])

    def test_select_related_with_filters(self):
        response = self.client.get(reverse("simple-select-related"), {"fields": "name,fk_2_data,fk_2_data__name"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 27)
        self.assertEqual(response.data[0]["name"], "m1")
        self.assertEqual(response.data[0]["fk_2_data"]["name"], "m2")
        self.assertEqual(test_utils.TestQueryCounter().get_counter(), 1)
        query_stack = test_utils.TestQueryCounter().get_queries_stack()
        self.assertIn("tests_autooptimization1model", query_stack[0][0])
        self.assertIn("tests_autooptimization2model", query_stack[0][0])
        self.assertNotIn("tests_autooptimization3model", query_stack[0][0])

    def test_prefetch_related(self):
        response = self.client.get(reverse("simple-prefetch-related"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "m3")
        self.assertEqual(len(response.data["reverse_2_1"]), 3)
        self.assertEqual(len(response.data["reverse_2_2"]), 3)
        self.assertEqual(len(response.data["reverse_2_1_data"]), 3)
        self.assertEqual(len(response.data["reverse_2_2_data"]), 3)
        self.assertEqual(response.data["reverse_2_1_data"][0]["name"], "m2")
        self.assertEqual(response.data["reverse_2_2_data"][0]["name"], "m2")
        self.assertEqual(len(response.data["reverse_2_1_data"][0]["reverse_1"]), 3)
        self.assertEqual(len(response.data["reverse_2_2_data"][0]["reverse_1_data"]), 3)
        self.assertEqual(response.data["reverse_2_2_data"][0]["reverse_1_data"][0]["name"], "m1")

        # main object, reverse_2_1, reverse_2_2, reverse_2_1__reverse_1, reverse_2_2__reverse_1
        self.assertEqual(test_utils.TestQueryCounter().get_counter(), 5)

    def test_prefetch_related_with_filters(self):
        response = self.client.get(reverse("simple-prefetch-related"), {"fields": "name,reverse_2_1,reverse_2_1_data"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "m3")
        self.assertEqual(len(response.data["reverse_2_1"]), 3)
        self.assertEqual(len(response.data["reverse_2_1_data"]), 3)
        self.assertEqual(response.data["reverse_2_1_data"][0]["name"], "m2")
        self.assertEqual(len(response.data["reverse_2_1_data"][0]["reverse_1"]), 3)
        self.assertEqual(response.data["reverse_2_1_data"][0]["reverse_1_data"][0]["name"], "m1")

        # main object, reverse_2_1, reverse_2_1__reverse_1
        self.assertEqual(test_utils.TestQueryCounter().get_counter(), 3)

    def test_prefetch_with_select_related(self):
        response = self.client.get(reverse("prefetch-with-select-related"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 3)
        self.assertEqual(response.data[0]["name"], "m3")
        self.assertEqual(response.data[0]["sample_data"]["a"], "a")
        self.assertEqual(len(response.data[0]["reverse_2_1"]), 3)
        self.assertEqual(len(response.data[0]["reverse_2_2"]), 3)
        self.assertEqual(len(response.data[0]["reverse_2_1_data"]), 3)
        self.assertEqual(len(response.data[0]["reverse_2_2_data"]), 3)
        self.assertEqual(response.data[0]["reverse_2_1_data"][0]["name"], "m2")
        self.assertEqual(response.data[0]["reverse_2_2_data"][0]["name"], "m2")
        self.assertEqual(response.data[0]["reverse_2_1_data"][0]["sample_data"]["a"], "a")
        self.assertEqual(response.data[0]["reverse_2_2_data"][0]["sample_data"]["a"], "a")
        self.assertEqual(len(response.data[0]["reverse_2_1_data"][0]["reverse_1"]), 3)
        self.assertEqual(len(response.data[0]["reverse_2_2_data"][0]["reverse_1_data"]), 3)
        self.assertEqual(response.data[0]["reverse_2_2_data"][0]["reverse_1_data"][0]["name"], "m1")

        # main objects list, reverse_2_1, reverse_2_2, reverse_2_1__sample, reverse_2_2__sample,
        # reverse_2_1__reverse_1, reverse_2_2__reverse_1
        self.assertEqual(test_utils.TestQueryCounter().get_counter(), 7)

    def test_prefetch_with_select_related_with_include_fields(self):
        response = self.client.get(reverse("prefetch-with-select-related"), {
            "include_fields": "reverse_2_1_data__reverse_1_data__sample_m2m_data"
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 3)
        self.assertEqual(response.data[0]["name"], "m3")
        self.assertEqual(response.data[0]["sample_data"]["a"], "a")
        self.assertEqual(len(response.data[0]["reverse_2_1"]), 3)
        self.assertEqual(len(response.data[0]["reverse_2_2"]), 3)
        self.assertEqual(len(response.data[0]["reverse_2_1_data"]), 3)
        self.assertEqual(len(response.data[0]["reverse_2_2_data"]), 3)
        self.assertEqual(response.data[0]["reverse_2_1_data"][0]["name"], "m2")
        self.assertEqual(response.data[0]["reverse_2_2_data"][0]["name"], "m2")
        self.assertEqual(response.data[0]["reverse_2_1_data"][0]["sample_data"]["a"], "a")
        self.assertEqual(response.data[0]["reverse_2_2_data"][0]["sample_data"]["a"], "a")
        self.assertEqual(len(response.data[0]["reverse_2_1_data"][0]["reverse_1"]), 3)
        self.assertEqual(len(response.data[0]["reverse_2_2_data"][0]["reverse_1_data"]), 3)
        self.assertEqual(response.data[0]["reverse_2_2_data"][0]["reverse_1_data"][0]["name"], "m1")

        # main objects list, reverse_2_1, reverse_2_2, reverse_2_1__sample, reverse_2_2__sample,
        # reverse_2_1__reverse_1, reverse_2_2__reverse_1, reverse_2_1__reverse_1__sample_m2m
        self.assertEqual(test_utils.TestQueryCounter().get_counter(), 8)

    def select_related_by_source(self):
        response = self.client.get(reverse("select-related-by-source"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 27)
        self.assertEqual(response.data[0]["name"], "m1")
        self.assertEqual(response.data[0]["fk_2_name"], "m2")
        self.assertEqual(test_utils.TestQueryCounter().get_counter(), 1)
        query_stack = test_utils.TestQueryCounter().get_queries_stack()
        self.assertIn("tests_autooptimization1model", query_stack[0][0])
        self.assertIn("tests_autooptimization2model", query_stack[0][0])
        self.assertNotIn("tests_autooptimization3model", query_stack[0][0])
