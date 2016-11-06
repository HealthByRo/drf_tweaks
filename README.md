# DRF Tweaks

[![build-status-image]][travis]
[![requires-io]][requires-io]
[![coverage-status-image]][codecov]

**Set of tweaks for [Django Rest Framework][drf]**

This project is intended to contain a set of improvements/addons for DRF that we've developed during using DRF.

# Current tweaks
* [Extended Serializers](#serializers)
* [Pagination without counts](#pagination)
* [Versioning extension](#versioning)
* [Autodocumentation](#autodocumentation) - extension for [Django Rest Swagger][drs]

---

# Serializers
There are a few improvements that the standard DRF Serializer could benefit from. Each improvement, how to use it
& rationale for it is described in the sections below.

### One-step validation
Standard serializer is validating the data in three steps:
* field-level validation (required, blank, validators)
* custom field-level validation (method validate_fieldname(...))
* custom general validation (method validate(...))

So for example if you have a serializer with 4 required fields: first_name, email, password & confirm_password and you
pass data without first_name and with wrong confirm_password, you'll get first the error for first_name, and then, after
you correct it you'll get error for confirm_password, instead of getting both errors at once. This results in bad user
experience, and that's why we've changed all validation to be run in one step.

Validation of our Serializer runs all three phases, and merges errors from all of them. However if a given field
generated an error on two different stages, it returns the error only from the former one.

When using our Serializer/ModelSerializer, when writing "validate" method, you need to remember that given field may
not be in a dictionary, so the validation must be more sophisticated:
```python
    def validate(self, data):
        errors = {}
        # wrong - password & confirm_password may raise KeyError
        if data["password"] != data["confirm_password"]:
            errors["confirm_password"] = [_("This field must match")]

        # correct
        if data.get("password") != data.get("confirm_password"):
            errors["confirm_password"] = [_("Passwords")]

        if errors:
            raise serializer.ValidationError(errors)

        return data
```

### Making fields required
Standard ModelSerializer is taking the "required" state from the corresponding Model field. To make not-required model
field required in serializer, you have to declare it explicitly on serializer, so if the field first_name is not
required in the model, you need to do:
```python
    class MySerializer(serializers.ModelSerializer):
        first_name = serializers.CharField(..., required=True)
```
This is quite annoying when you have to do it often, that's why our ModelSerializer allows you to override this by simple
specifying the list of fields you want to make required:
```python
    from drf_tweaks.serializers import ModelSerializer

    class MySerializer(ModelSerializer):
        required_fields = ["first_name"]
```

### Custom errors
Our serializers provide a simple way to override blank & required error messages, by either specifying default error for
all fields or specifying error for specific field. To each error message "fieldname" is passed as format parameter.
Example:
```python
    from drf_tweaks.serializers import ModelSerializer

    class MySerializer(ModelSerializer):
        required_error = blank_error = "{fieldname} is required"
        custom_required_errors = custom_blank_errors = {
            "credit_card_number": "You make me a saaaad Panda."
        }
```

### Control over serialized fields
Our serializers provide control over serialized fields. It may be useful in following cases:
* You have quite heavy serializer (many fields, foreign keys, db calls, etc.), that you need in one place, but in the
other place you just need some basic data from it - say just name & id. You could provide separate serializer for such
case, or even separate endpoint, but it would be easier if the client can have control over which fields get serialized.
* You have some fields that should be serialized only for some state of the serialized object, and not for other.

Both things can be achieved with our serializer. By default they check if the "fields" were passed in the context or if
"fields" were passed as a GET parameter (in such case "request" must be present in the context), but you can define
custom behaviour by overriding the followin method in the Serializer:
```python
    def get_fields_for_serialization(self, obj):
        return {"name", "id"}
```

# Pagination

### Rationale

Calling "count" each time a queryset gets paginated is inefficient - especialy for large datasets. Moreover, in most
cases it is unnecessary to have counts (for example for endless scrolls). The fastest pagination in such case is
CursorPaginator, however it is not as easy to use as LimitOffsetPaginator/PageNumberPaginator and does not allow
sorting.

### Usage
```python
    from drf_tweaks.pagination import NoCountsLimitOffsetPagination
    from drf_tweaks.pagination import NoCountsPageNumberPagination
```

Use it as standard pagination - the only difference is that it does not return "count" in the dictionary. Page indicated
by "next" may be empty. Next page url is present if the current page size is as requested - if it contains less items
then requested, it means we're on the last page.

### NoCountsLimitOffsetPagination

A limit/offset based pagination, without performing counts. For example:
* http://api.example.org/accounts/?limit=100 - will return first 100 items
* http://api.example.org/accounts/?offset=400&limit=100 - will returns 100 items starting from 401th
* http://api.example.org/accounts/?offset=-50&limit=100 - will return first 50 items

HTML is not handled (no get_html_context).

Pros:
* no counts
* easier to use than cursor pagination (especially if you need sorting)
* works with angular ui-scroll (which requires negative offsets)

Cons:
* skip is a relatively slow operation, so this paginator is not as fast as cursor paginator when you use large offsets

### NoCountsPageNumberPagination

A standard page number pagination, without performing counts.

HTML is not handled (no get_html_context).

Pros:
* no counts
* easier to use than cursor pagination (especially if you need sorting)

Cons:
* skip is a relatively slow operation, so this paginator is not as fast as cursor paginator when you use large page
numbers

# Versioning

### Rationale
DRF provides a nice [versioning mechanism][drf-versioning], however there are two things that could be more automated,
and this is the point of this extension:
* Handling deprecation & obsoletion: when you don't have control over upgrading client app, it is best to set the
deprecation/obsoletion mechanism at the very beginning of your project - something that will start reminding a user that
he is using old app and he should update it, or in case of obsolition - information, that this app is outdated and it
must be upgraded in order to use it. This extension adds warning to header if the API version client is using is
deprecated and responds with 410: Gone error when the API version is obsolete.
* Choosing serializer. In DRF you have to overwrite get_serializer_class to provide different serializers for different
versions. This extension allows you to define just dictionary with it: versioning_serializer_classess. You may still
override get_serializer_class however if you choose to.

### Configuration
In order to make deprecation warning work, you need to add DeprecationMiddleware to MIDDLEWARE or MIDDLEWARE_CLASSESS
(depends on django version you're using):
```python
    # django >= 1.10
    MIDDLEWARE (
        ...
        "drf_tweaks.versioning.DeprecationMiddleware"
    )

    # django < 1.10
    MIDDLEWARE_CLASSES (
        ...
        "drf_tweaks.versioning.DeprecationMiddleware"
    )
```

It is highly recommended to add DEFAULT_VERSION along with DEFAUlt_VERSIONINg_CLASS to DRF settings:
```python
    REST_FRAMEWORK = {
        ...
        "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.AcceptHeaderVersioning",
        "DEFAULT_VERSION": "1",
    }
```
By default the DEFAULT_VERSION is None, which will in effect work as "latest" - it is safer to make passing newer
version explicitly.

### ApiVersionMixin
Use this as first in inheritance chain when creating own API classes, so for example:

```python
class MyApi(ApiVersionMixin, GenericApiView):
    ...
```

Returns serializer depending on versioning_serializer_classess and version:

```python
versioning_serializer_classess = {
    1: "x",
    2: "x",
}
```

You can set custom deprecated/obsolete versions on the class-level
```python
CUSTOM_DEPRECATED_VERSION = X
CUSTOM_OBSOLETE_VERSION = Y
```

It can be also configured on the settings level as a fixed version
```python
API_DEPRECATED_VERSION = X
API_OBSOLETE_VERSION = Y
```

or as an offset - for example:
```python
API_VERSION_DEPRECATION_OFFSET = 6
API_VERSION_OBSOLETE_OFFSET = 10
```

Offset is calculated using the highest version number, only if versioning_serializer_classess is defined:
```python
deprecated = max(self.versioning_serializer_classess.keys() - API_VERSION_DEPRECATION_OFFSET)
obsolete = max(self.versioning_serializer_classess.keys() - API_VERSION_OBSOLETE_OFFSET)
```

If neither is set, deprecation/obsolete will not work. Only the first applicable setting is taken into account
(in the order as presented above).

# Autodocumentation

### Rationale
[Django Rest Swagger][drs] is a awsome tool that generates swagger documentation out of your DRF API. There is however
one deficiency - it does not offer any hooks that would allow you to automaticaly generate some additional documentation.
For example, if you want pagination parameters to be visible in the docs, you'd have to set it explicitly:
```python
    class SomeAPi(ListAPIView):
        def get(...):
            """ page_number -- optional, page number """
```
You may also want to generate some part of description based on some fields in API and make it change automatically
each time you update them. Django Rest Swagger does not offer any hooks for that, and that is why this extension was
created.

Since there are no hooks available to add custom documentation, this extension is made in a form of class decorator,
that creates facade for each API method (get/post/patch/put - defined on the Autodoc class level) and creates a
docstring for them based on original docstring (if present) & applicable Autodoc classess.

### Usage & Configuration
```python
    @autodoc("List or create an account")
    class SomeApi(ApiVersionMixin, ListCreateAPIView):
        ...

    # you can skip certain classes:
    @autodoc("Base docstring", skip_classess=[PaginationAutodoc])

    # or add certain classess:
    @autodoc("Base docstring", add_classess=[CustomAutodoc])

    # you can also override autodoc classess - this one cannot be used with skip_classess or add_classess:
    @autodoc("Base docstring", classess=[PaginationAutodoc])
```


### Available Classess

Classess are applied in the same order they are defined.

#### BaseInfo

This one is adding basic info (the one passed to the decorator itself), as well as custom text or yaml if defined,
as in following examples:
```python
    @autodoc("some caption")
    class SomeApi(RetrieveUpdateAPIView):

        @classmethod
        def get_custom_get_doc(cls):
            return "custom get doc"

        @classmethod
        def get_custom_patch_doc_yaml(cls):
            return "some yaml"

```

#### Pagination

This one is adding parameters to "get" method in swagger in following format:
```
    page_number -- optional, page number
    page_size -- optional, page size
```
It adds all "*_query_param" from pagination class, as long as they have name defined, so for standard
PageNumberPagination, that has page_size_query_param defined as None it will not be enclodes.

If default pagination class is defined, and you don't want it to be added, you can simply:
```python
    class SomeClassWithoutPagination(RetrieveAPIView):
        pagination_class = None
```

#### Versioning

Autodoc for versioning - applied only when ApiVersionMixin is present and the decorated class is using
rest_framework.versioning.AcceptHeaderVersioning and has versioning_serializer_classess defined. It adds all available
versions to a swagger, so you can make a call from it using different API versions.

### Adding custom classess

Custom class should inherit from AutodocBase:
```python
    class CustomAutodoc(AutodocBase):
        applies_to = ("get", "post", "put", "patch", "delete")

        @classmethod
        def _generate_yaml(cls, documented_cls, method_name):
            return ""  # your implementation goes here

        @classmethod
        def _generate_text(cls, documented_cls, base_doc, method_name):
            return ""  # your implementation goes here
```

[drf]: http://www.django-rest-framework.org
[drf-versioning]: http://www.django-rest-framework.org/api-guide/versioning/
[drs]: https://github.com/marcgibbons/django-rest-swagger
[coverage-status-image]: https://img.shields.io/codecov/c/github/ArabellaTech/drf_tweaks/master.svg
[codecov]: http://codecov.io/github/ArabellaTech/drf_tweaks?branch=master
[build-status-image]: https://secure.travis-ci.org/ArabellaTech/drf_tweaks.svg?branch=master
[travis]: http://travis-ci.org/ArabellaTech/drf_tweaks?branch=master
[requires-io]: https://requires.io/github/ArabellaTech/drf_tweaks/requirements.svg?branch=master
