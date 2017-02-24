# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from rest_framework import serializers
from rest_framework.fields import (api_settings, DjangoValidationError, empty, OrderedDict, set_value, SkipField,
                                   ValidationError)
from rest_framework.serializers import as_serializer_error, PKOnlyObject


class SerializerCustomizationMixin(object):
    # blank/required errors override
    required_error = blank_error = None
    custom_required_errors = custom_blank_errors = {}

    def __init__(self, *args, **kwargs):
        super(SerializerCustomizationMixin, self).__init__(*args, **kwargs)
        self.change_required_message()

    def change_required_message(self):
        def get_field_name(key, field):
            return field.label if field.label else key.title()

        for key, field in self.fields.items():
            if hasattr(field, "error_messages"):
                field_name = str(get_field_name(key, field))
                custom_required_message = self.custom_required_errors.get(key, self.required_error)
                if custom_required_message:
                    field.error_messages["required"] = custom_required_message.format(fieldname=field_name)
                custom_blank_message = self.custom_blank_errors.get(key, self.blank_error)
                if custom_blank_message:
                    field.error_messages["blank"] = custom_blank_message.format(fieldname=field_name)

    # required fields override
    required_fields = []

    def get_fields(self):
        fields = super(SerializerCustomizationMixin, self).get_fields()

        for f in self.required_fields:
            fields[f].required = True
            fields[f].allow_blank = False

        return fields

    # control over which fields get serialized
    def get_fields_for_serialization(self, obj):
        if "fields" in self.context:
            return self.context["fields"]
        if "request" in self.context and "fields" in self.context["request"].query_params:
            return self.context["request"].query_params["fields"].split(",")
        return None

    def to_representation(self, instance):
        """ override of the default to_representation - to filter out fields which are doctors' only without first
            serializing them - so the DB does net get called - important for ManyToMany """
        ret = OrderedDict()
        fields = self._readable_fields
        only_fields = self.get_fields_for_serialization(instance)

        for field in fields:
            # ++ change to the original code from DRF
            if only_fields and field.field_name not in only_fields:
                continue
            # -- change

            try:
                attribute = field.get_attribute(instance)
            except SkipField:
                continue

            check_for_none = attribute.pk if isinstance(attribute, PKOnlyObject) else attribute
            if check_for_none is None:
                ret[field.field_name] = None
            else:
                ret[field.field_name] = field.to_representation(attribute)

        return ret

    # one-step validation
    def to_internal_value(self, data):
        if not isinstance(data, dict):
            message = self.error_messages["invalid"].format(
                datatype=type(data).__name__
            )
            raise ValidationError({
                api_settings.NON_FIELD_ERRORS_KEY: [message]
            })

        ret = OrderedDict()
        errors = OrderedDict()
        fields = self._writable_fields

        for field in fields:
            validate_method = getattr(self, "validate_" + field.field_name, None)
            primitive_value = field.get_value(data)
            try:
                validated_value = field.run_validation(primitive_value)
                if validate_method is not None:
                    validated_value = validate_method(validated_value)
            except ValidationError as exc:
                errors[field.field_name] = exc.detail
            except DjangoValidationError as exc:
                errors[field.field_name] = list(exc.messages)
            except SkipField:
                pass
            else:
                set_value(ret, field.source_attrs, validated_value)

        return ret, errors

    def run_validation(self, data=empty):
        (is_empty_value, data) = self.validate_empty_values(data)
        if is_empty_value:
            return data

        # mapping to internal values
        value, to_internal_errors = self.to_internal_value(data)

        # running validators
        validators_errors = OrderedDict()
        try:
            self.run_validators(value)
        except (ValidationError, DjangoValidationError) as exc:
            validators_errors = as_serializer_error(exc)

        # running final validation
        validation_errors = OrderedDict()
        try:
            value = self.validate(value)
            assert value is not None, ".validate() should return the validated data"
        except (ValidationError, DjangoValidationError) as exc:
            validation_errors = as_serializer_error(exc)

        # if there were any errors - raise the combination of them
        if to_internal_errors or validators_errors or validation_errors:
            # update dicts in reverse - to show most basic error for a given field if errors overlap
            validation_errors.update(validators_errors)
            validation_errors.update(to_internal_errors)
            raise ValidationError(detail=validation_errors)

        return value


class Serializer(SerializerCustomizationMixin, serializers.Serializer):
    pass


class ModelSerializer(SerializerCustomizationMixin, serializers.ModelSerializer):
    pass
