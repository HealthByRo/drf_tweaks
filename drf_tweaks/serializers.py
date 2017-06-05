# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from rest_framework import serializers
from rest_framework.fields import (api_settings, DjangoValidationError, empty, OrderedDict, set_value, SkipField,
                                   ValidationError)
from rest_framework.serializers import as_serializer_error, PKOnlyObject


class ContextPassing(object):
    @classmethod
    def filter_fields(cls, field_name, fields):
        filtered_fields = set()
        for field in fields:
            parts = field.split("__", 1)
            if len(parts) == 2 and parts[0] == field_name:
                filtered_fields.add(parts[1])
        return filtered_fields

    def __init__(self, field, parent, only_fields, include_fields):
        self.field = field
        self.parent = parent
        self.has_context = hasattr(field, "_context")
        self.old_context = None
        self.only_fields = self.filter_fields(field.field_name, only_fields)
        self.include_fields = self.filter_fields(field.field_name, include_fields)
        self.on_exit_delete_fields = False
        self.on_exit_delete_include_fields = False
        self.old_fields = None
        self.old_include_fields = None

    def __enter__(self):
        if self.has_context:
            # context passing
            self.old_context = self.field._context
            self.field._context = self.parent._context

            # fields filtering
            if "fields" in self.field._context:
                self.old_fields = self.field._context["fields"]
            else:
                self.on_exit_delete_fields = True
            self.field._context["fields"] = self.only_fields

            # on demand fields
            if "include_fields" in self.field._context:
                self.old_include_fields = self.field._context["include_fields"]
            else:
                self.on_exit_delete_include_fields = True
            self.field._context["include_fields"] = self.include_fields

    def __exit__(self, type, value, traceback):
        if self.has_context:
            # modification was done on parent's context, so we roll them back before setting the old contexts
            if self.on_exit_delete_fields:
                del self.field._context["fields"]
            else:
                self.field._context["fields"] = self.old_fields

            if self.on_exit_delete_include_fields:
                del self.field._context["include_fields"]
            else:
                self.field._context["include_fields"] = self.old_include_fields

            # restoring old context
            self.field._context = self.old_context


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
            fields[f].allow_null = False
            fields[f].allow_blank = False

        return fields

    @classmethod
    def add_main_fields_names_from_nested(cls, fields):
        """If you add main_field__secondary_field, main_field should also be in the set."""
        to_add = set()
        for field in fields:
            parts = field.split("__", 1)
            if len(parts) == 2:
                to_add.add(parts[0])
        return fields | to_add

    # control over which fields get serialized
    def get_fields_for_serialization(self, fields_name):
        fields = set()
        if fields_name in self.context:
            fields = set(self.context[fields_name])
        elif "request" in self.context and fields_name in self.context["request"].query_params:
            fields = set(self.context["request"].query_params[fields_name].split(","))
        return self.add_main_fields_names_from_nested(fields)

    def to_representation(self, instance):
        """Override of the default to_representation.

        - Added functionality:
        - context passing
        - fields filtering (w/o touching db when not necessary)
        - on_demand fields.
        """
        ret = OrderedDict()
        fields = self._readable_fields

        # ++ change to the original code from DRF
        only_fields = self.get_fields_for_serialization("fields")
        include_fields = self.get_fields_for_serialization("include_fields")
        on_demand_fields = getattr(self.Meta, "on_demand_fields", set())
        # -- change

        for field in fields:
            # ++ change to the original code from DRF
            if only_fields:
                # if fields are defined for a given level, we ignore "include_fields"
                if field.field_name not in only_fields:
                    continue
            elif field.field_name in on_demand_fields and field.field_name not in include_fields:
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
                # ++ change to the original code from DRF
                with ContextPassing(field, self, only_fields, include_fields):
                    ret[field.field_name] = field.to_representation(attribute)
                # -- change
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
