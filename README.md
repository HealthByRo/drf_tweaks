# DRF Extensions

**Set of extensions for [Django Rest Framework][drf]**

This project is intended to contain a set of improvements/addons for DRF.

**This is work in progress**

# Current extensions
* [Pagination without counts](#pagination)
* [Versioning extension](#versioning)

TODO: add here each extensions after adding it

TODO: autodoc

TODO: Extended Serializer: single pass, custom errors, pool, fields controlled by param

---

# Pagination

### Rationale

Calling "count" each time a queryset gets paginated is inefficient - especialy for large datasets. Moreover, in most
cases it is unnecessary to have counts (for example for endless scrolls). The fastest pagination in such case is
CursorPaginator, however it is not as easy to use as LimitOffsetPaginator/PageNumberPaginator and does not allow
sorting.

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
        "drf_extensions.versioning.DeprecationMiddleware"
    )

    # django < 1.10
    MIDDLEWARE_CLASSES (
        ...
        "drf_extensions.versioning.DeprecationMiddleware"
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

[drf]: http://www.django-rest-framework.org
[drf-versioning]: http://www.django-rest-framework.org/api-guide/versioning/
