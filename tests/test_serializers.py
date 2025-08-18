# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory
from rest_framework.test import APITestCase

from drf_tweaks.serializers import ModelSerializer
from drf_tweaks.serializers import Serializer
from tests.models import SampleModel


factory = APIRequestFactory()


# sample serializers
class SampleSerializer(Serializer):
    class Meta:
        model = SampleModel
        fields = ["a"]


class SampleModelSerializer(ModelSerializer):
    class Meta:
        model = SampleModel
        fields = ["a", "b"]


class SampleModelSerializerWithRequired(ModelSerializer):
    required_fields = ["a"]

    class Meta:
        model = SampleModel
        fields = ["a", "b"]


class SampleSerializerForOneStepTest(Serializer):
    a = serializers.CharField(required=True)
    b = serializers.CharField(required=False)
    c = serializers.CharField(required=False)

    def validate_b(self, value):
        if value != "x":
            raise serializers.ValidationError("wrong value")
        return value

    def validate(self, data):
        errors = {}
        if data.get("b") != data.get("c"):
            errors["c"] = ["wrong again"]

        if errors:
            raise serializers.ValidationError(errors)

        return data


class SampleSerializerWithCustomErrors(Serializer):
    required_error = "{fieldname} is required."
    blank_error = "{fieldname} cannot be blank."
    custom_required_errors = {"c": "{fieldname} something something."}
    custom_blank_errors = {"d": "{fieldname} something blank."}
    a = serializers.CharField(required=True)
    b = serializers.CharField(required=True)
    c = serializers.CharField(required=True)
    d = serializers.CharField(required=True)


class SampleSerializerForReadonlyTest(ModelSerializer):
    a = serializers.CharField()

    class Meta:
        model = SampleModel
        fields = ["a", "b"]


class SampleSerializerForReadonlyTest2(SampleSerializerForReadonlyTest):
    class Meta:
        model = SampleModel
        fields = ["a", "b"]
        read_only_fields = ["a", "b"]


class SerializersTestCase(APITestCase):
    def setUp(self):
        self.sample1 = SampleModel.objects.create(a="a", b="b")
        self.sample2 = SampleModel.objects.create(a="a2", b="b2")

    def test_one_step_validation(self):
        # wrong call check
        serializer = SampleSerializerForOneStepTest(data={"a", "b"})
        self.assertFalse(serializer.is_valid())

        # get errors from all three steps
        serializer = SampleSerializerForOneStepTest(data={"b": "y", "c": "x"})
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors,
            {
                "a": ["This field is required."],
                "b": ["wrong value"],
                "c": ["wrong again"],
            },
        )

        # check for proper data
        serializer = SampleSerializerForOneStepTest(data={"a": "a", "b": "x", "c": "x"})
        self.assertTrue(serializer.is_valid())

    def test_making_fields_required(self):
        serializer = SampleModelSerializer(data={})
        self.assertTrue(serializer.is_valid())

        serializer = SampleModelSerializerWithRequired(data={})
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors, {"a": ["This field is required."]})

    def test_overriding_fields_error_messages(self):
        serializer = SampleSerializerWithCustomErrors(data={"b": "", "d": ""})
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors,
            {
                "a": ["A is required."],
                "b": ["B cannot be blank."],
                "c": ["C something something."],
                "d": ["D something blank."],
            },
        )

    def test_control_over_serialization_fields(self):
        # w/o control
        serializer = SampleModelSerializer(instance=self.sample1)
        self.assertEqual(set(serializer.data.keys()), {"a", "b"})

        # pass through context
        serializer = SampleModelSerializer(instance=self.sample1, context={"fields": ("a",)})
        self.assertEqual(set(serializer.data.keys()), {"a"})

        # pass through request
        request = Request(factory.get("/", {"fields": "b,c"}))
        serializer = SampleModelSerializer(instance=self.sample1, context={"request": request})
        self.assertEqual(set(serializer.data.keys()), {"b"})

    def test_enforcing_read_only_fields(self):
        serializer = SampleSerializerForReadonlyTest(data={"a": "a", "b": "b"})
        self.assertTrue(serializer.is_valid())

        self.assertEqual(serializer.validated_data["a"], "a")
        self.assertEqual(serializer.validated_data["b"], "b")

        serializer = SampleSerializerForReadonlyTest2(data={"a": "a", "b": "b"})
        self.assertTrue(serializer.is_valid())

        self.assertEqual(len(serializer.validated_data), 0)
