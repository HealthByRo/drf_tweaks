# -*- coding: utf-8 -*-
from django.conf.urls import url
from rest_framework.permissions import AllowAny
from django.test import override_settings
from drf_tweaks import serializers
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
# TODO
class SimplePrefetchRelatedSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutoOptimization3Model
        fields = ["id"]


# serializers for combining prefetch related with select related
# TODO
class PrefetchWithSelectRelatedSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutoOptimization3Model
        fields = ["id"]


@optimize()
class SimpleSelectRelatedAPI(ListAPIView):
    queryset = AutoOptimization1Model.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = SimpleSelectRelatedSerializer


@optimize()
class SimplePrefetchRelatedAPI(RetrieveAPIView):
    queryset = AutoOptimization3Model.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = SimpleSelectRelatedSerializer

    def get_object(self):
        return self.get_queryset().first()


@optimize()
class PrefetchWithSelectRelatedAPI(ListAPIView):
    queryset = AutoOptimization3Model.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = PrefetchWithSelectRelatedSerializer


urlpatterns = [
    url(r"^autooptimization/simple-select-related$", SimpleSelectRelatedAPI.as_view(), name="simple-select-related"),
    url(r"^autooptimization/simple-prefetch-related$", SimplePrefetchRelatedAPI.as_view(),
        name="simple-prefetch-related"),
    url(r"^autooptimization/prefetch-with-select-related$", PrefetchWithSelectRelatedAPI.as_view(),
        name="prefetch-with-select-related"),
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
        # self.assertNotIn("tests_autooptimization3model", query_stack[0][0])

    def test_prefetch_related(self):
        pass  # TODO

    def test_prefetch_related_with_filters(self):
        pass  # TODO

    def test_prefetch_with_select_related(self):
        pass  # TODO

    def test_prefetch_with_select_related_with_filters(self):
        pass  # TODO
