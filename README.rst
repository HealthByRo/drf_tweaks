DRF Tweaks
========================
|travis|_ |pypi|_ |requiresio|_ |codecov|_

--------------

Set of tweaks for `Django Rest Framework <http://www.django-rest-framework.org/>`_


This project is intended to contain a set of improvements/addons for DRF that we've developed during using DRF.

Current tweaks
--------------
* `Extended Serializers`_
* `Auto filtering and ordering`_
* `Pagination without counts`_
* `Versioning extensions`_
* `Autodocumentation`_ - extension for `Django Rest Swagger <https://github.com/marcgibbons/django-rest-swagger>`_
* `Autooptimization`_
* `Counting SQL queries in tests`_


--------------

Extended Serializers
--------------------

There are a few improvements that the standard DRF Serializer could benefit from. Each improvement, how to use it
& rationale for it is described in the sections below.

One-step validation
~~~~~~~~~~~~~~~~~~~

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

.. code:: python

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


Making fields required
~~~~~~~~~~~~~~~~~~~~~~

Standard ModelSerializer is taking the "required" state from the corresponding Model field. To make not-required model
field required in serializer, you have to declare it explicitly on serializer, so if the field first_name is not
required in the model, you need to do:

.. code:: python

    class MySerializer(serializers.ModelSerializer):
        first_name = serializers.CharField(..., required=True)


This is quite annoying when you have to do it often, that's why our ModelSerializer allows you to override this by simple
specifying the list of fields you want to make required:

.. code:: python

    from drf_tweaks.serializers import ModelSerializer

    class MySerializer(ModelSerializer):
        required_fields = ["first_name"]


Custom errors
~~~~~~~~~~~~~

Our serializers provide a simple way to override blank & required error messages, by either specifying default error for
all fields or specifying error for specific field. To each error message "fieldname" is passed as format parameter.
Example:

.. code:: python

    from drf_tweaks.serializers import ModelSerializer

    class MySerializer(ModelSerializer):
        required_error = blank_error = "{fieldname} is required"
        custom_required_errors = custom_blank_errors = {
            "credit_card_number": "You make me a saaaad Panda."
        }


Passing context to subserializers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Rationale: In DRF context is not passed to sub-serializers. So for example, in the standard serializer, you will have "request" in the context for the main object (say, Message), but the context for a sub-serializer (say, sender's Account) context will be empty. To workaround this you could for example re-initialize sub-serializers on the serializer's init, or instead of using a sub-serializer use a SerializerMethodField and initialize a sub-serializer inside it, etc. The problem is described here: https://github.com/encode/django-rest-framework/issues/2471

Our serializers includes a mechanism to pass context to sub-serializers, workarounding the problem stated above.

If for any reason you are using SerializerMethodField with a Serializer inside, and you want to pass context, use pass_context method to filter the fields & include fields properly.

.. code:: python

    from drf_tweaks.serializers import pass_context

    class SomeSerializer(Serializer):
        some_field = serializers.SerializerMethodField()

        def get_some_field(self, obj):
            return OtherSerializer(obj, context=pass_context("some_field", self.context)).data


**WARNING: passing context may cause some unexpected behaviours, since sub-serializer will start receive the main context (and earlier they were not getting it).**


Control over serialized fields
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Our serializers provide control over serialized fields. It may be useful in following cases:
* You have quite heavy serializer (many fields, foreign keys, db calls, etc.), that you need in one place, but in the
other place you just need some basic data from it - say just name & id. You could provide separate serializer for such
case, or even separate endpoint, but it would be easier if the client can have control over which fields get serialized.
* You have some fields that should be serialized only for some state of the serialized object, and not for other.

Both things can be achieved with our serializer. By default they check if the "fields" were passed in the context or if
"fields" were passed as a GET parameter (in such case "request" must be present in the context), but you can define
custom behaviour by overriding the followin method in the Serializer:

.. code:: python

    def get_fields_for_serialization(self, fields):  # fields must be in ("fields", "include_fields")
        return {"name", "id"}

This works also with sub-serializers (using context-passing). Here is an example usage:

.. code::

    https://your.url?fields=some_field,other_field,nested_serializer__some_field,nested_serializer__other_field


Making fields available only on demand
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Rationale: it is a good practice to minimize the number of APIs, by making them as generic as possible. This however creates a performance problem when the amount of data being serialized grows by including sub-serializers (which can include sub-serializers themselves). Using control over serialized fields, as described above should be sufficient. However, in practice this mechanism will not be used as frequent as it should. That's why we've introduced another mechanism: on demand fields. Those are fields, specified in the serializer, that will be returned only if requested either by passing their name in "fields" (see the previous chapter) or in "include_fields" parameter.


.. code:: python

    class MySerializer(serializers.ModelSerializer):
        some_subserializer = OtherSerializer()

        class Meta:
            model = MyModel
            fields = ["some_property", "some_subserializer"]
            on_demand_fields = ["some_subserializer"]

.. code::

    https://your.url?include_fields=some_subserializer


Auto filtering and ordering
---------------------------

Rationale
~~~~~~~~~

There are nice OrderingFilter and DjangoFilterBackend backends in place, however sorting and filtering fields have to be declared explicitly, which is sometimes time consuming. That's why we've created a decorator that allows to sort & filter (with some extra lookup methods by default) by all the indexed fields present in model and in serializer class (as non write-only). Non-indexed fields may also be added to sorting & filtering, but it must be done explicitly - the idea is, that ordering or filtering by non-indexed field is not optimal from the DB perspective, so if the field is not included in sorting/filtering you should rather create index on it than declare it explicitly.

Decorator works with explicitly defined FilterBackends, as well as with explicitly defined ordering_fields, filter_fields or filter_class. In order to work, it requires ModelSerializer (obtainable either serializer_class or get_serializer_class), from which fields & model class are extracted.

Usage
~~~~~

.. code:: python

    @autofilter()
    class SomeAPI(...):
        serializer_class = SomeModelSerializer

    # it works well with autodoc:
    @autodoc()  # autodoc should be before autofilter, so it operates on the result from autofilter
    @autofilter()
    class SomeAPI(...):
        serializer_class = SomeModelSerializer

    # you can add some extra fields to sort or filter
    @autofilter(extra_filter=("non_indexed_field", ), extra_ordering=("non_indexed_field", ))
    class SomeAPI(...):
        serializer_class = SomeModelSerializer
        ordering_fields = ("other_non_indexed_field", )
        filter_fields = ("other_non_indexed_field", )

    # it works also when you have a custom filter_class set
    class SomeFilter(filters.FilterSet):
        class Meta:
            model = SomeModel
            fields = ("non_indexed_field", )

    @autofilter()
    class SomeAPI(...):
        serializer_class = SomeModelSerializer
        filter_class = SomeFilter


Pagination without counts
-------------------------

Rationale
~~~~~~~~~

Calling "count" each time a queryset gets paginated is inefficient - especialy for large datasets. Moreover, in most
cases it is unnecessary to have counts (for example for endless scrolls). The fastest pagination in such case is
CursorPaginator, however it is not as easy to use as LimitOffsetPaginator/PageNumberPaginator and does not allow
sorting.

Usage
~~~~~

.. code:: python

    from drf_tweaks.pagination import NoCountsLimitOffsetPagination
    from drf_tweaks.pagination import NoCountsPageNumberPagination


Use it as standard pagination - the only difference is that it does not return "count" in the dictionary. Page indicated
by "next" may be empty. Next page url is present if the current page size is as requested - if it contains less items
then requested, it means we're on the last page.

NoCountsLimitOffsetPagination
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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

NoCountsPageNumberPagination
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A standard page number pagination, without performing counts.

HTML is not handled (no get_html_context).

Pros:
* no counts
* easier to use than cursor pagination (especially if you need sorting)

Cons:
* skip is a relatively slow operation, so this paginator is not as fast as cursor paginator when you use large page
numbers

Versioning extensions
---------------------

Rationale
~~~~~~~~~

DRF provides a nice `versioning mechanism <http://www.django-rest-framework.org/api-guide/versioning/>`_, however there are two things that could be more automated,
and this is the point of this extension:

* Handling deprecation & obsoletion: when you don't have control over upgrading client app, it is best to set the deprecation/obsoletion mechanism at the very beginning of your project - something that will start reminding a user that he is using old app and he should update it, or in case of obsolition - information, that this app is outdated and it must be upgraded in order to use it. This extension adds warning to header if the API version client is using is deprecated and responds with 410: Gone error when the API version is obsolete.
* Choosing serializer. In DRF you have to overwrite get_serializer_class to provide different serializers for different versions. This extension allows you to define just dictionary with it: versioning_serializer_classess. You may still override get_serializer_class however if you choose to.

Configuration
~~~~~~~~~~~~~

In order to make deprecation warning work, you need to add DeprecationMiddleware to MIDDLEWARE or MIDDLEWARE_CLASSESS
(depends on django version you're using):

.. code:: python

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


It is highly recommended to add DEFAULT_VERSION along with DEFAUlt_VERSIONINg_CLASS to DRF settings:

.. code:: python

    REST_FRAMEWORK = {
        ...
        "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.AcceptHeaderVersioning",
        "DEFAULT_VERSION": "1",
    }


By default the DEFAULT_VERSION is None, which will in effect work as "latest" - it is safer to make passing newer
version explicitly.

ApiVersionMixin
~~~~~~~~~~~~~~~
Use this as first in inheritance chain when creating own API classes, so for example:

.. code:: python

    class MyApi(ApiVersionMixin, GenericApiView):
        ...


Returns serializer depending on versioning_serializer_classess and version:

.. code:: python

    versioning_serializer_classess = {
        1: "x",
        2: "x",
    }


You can set custom deprecated/obsolete versions on the class-level

.. code:: python

    CUSTOM_DEPRECATED_VERSION = X
    CUSTOM_OBSOLETE_VERSION = Y


It can be also configured on the settings level as a fixed version

.. code:: python

    API_DEPRECATED_VERSION = X
    API_OBSOLETE_VERSION = Y


or as an offset - for example:

.. code:: python

    API_VERSION_DEPRECATION_OFFSET = 6
    API_VERSION_OBSOLETE_OFFSET = 10


Offset is calculated using the highest version number, only if versioning_serializer_classess is defined:

.. code:: python

    deprecated = max(self.versioning_serializer_classess.keys() - API_VERSION_DEPRECATION_OFFSET)
    obsolete = max(self.versioning_serializer_classess.keys() - API_VERSION_OBSOLETE_OFFSET)


If neither is set, deprecation/obsolete will not work. Only the first applicable setting is taken into account
(in the order as presented above).

Autodocumentation
-----------------

Rationale
~~~~~~~~~

[Django Rest Swagger][drs] is a awsome tool that generates swagger documentation out of your DRF API. There is however
one deficiency - it does not offer any hooks that would allow you to automaticaly generate some additional documentation.
For example, if you want pagination parameters to be visible in the docs, you'd have to set it explicitly:

.. code:: python

    class SomeAPi(ListAPIView):
        def get(...):
            """ page_number -- optional, page number """


You may also want to generate some part of description based on some fields in API and make it change automatically
each time you update them. Django Rest Swagger does not offer any hooks for that, and that is why this extension was
created.

Since there are no hooks available to add custom documentation, this extension is made in a form of class decorator,
that creates facade for each API method (get/post/patch/put - defined on the Autodoc class level) and creates a
docstring for them based on original docstring (if present) & applicable Autodoc classess.

Usage & Configuration
~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    @autodoc("List or create an account")
    class SomeApi(ApiVersionMixin, ListCreateAPIView):
        ...

    # you can skip certain classes:
    @autodoc("Base docstring", skip_classess=[PaginationAutodoc])

    # or add certain classess:
    @autodoc("Base docstring", add_classess=[CustomAutodoc])

    # you can also override autodoc classess - this one cannot be used with skip_classess or add_classess:
    @autodoc("Base docstring", classess=[PaginationAutodoc])


Available Classess
~~~~~~~~~~~~~~~~~~

Classess are applied in the same order they are defined.

BaseInfo
********

This one is adding basic info (the one passed to the decorator itself), as well as custom text or yaml if defined,
as in following examples:

.. code:: python

    @autodoc("some caption")
    class SomeApi(RetrieveUpdateAPIView):

        @classmethod
        def get_custom_get_doc(cls):
            return "custom get doc"

        @classmethod
        def get_custom_patch_doc_yaml(cls):
            return "some yaml"


Pagination
**********

This one is adding parameters to "get" method in swagger in following format:

.. code:: python

    page_number -- optional, page number
    page_size -- optional, page size


It adds all "\*_query_param" from pagination class, as long as they have name defined, so for standard
PageNumberPagination, that has page_size_query_param defined as None it will not be enclodes.

If default pagination class is defined, and you don't want it to be added, you can simply:

.. code:: python

    class SomeClassWithoutPagination(RetrieveAPIView):
        pagination_class = None


OrderingAndFiltering
********************

This one is adding ordering & filtering information, based on OrderingFilter and DjangoFilterBackend for "get" method in swagger in following format:
.. code::

    Sorting:
        usage: ?ordering=FIELD_NAME,-OTHER_FIELD_NAME
        available fields: id, first_name, last_name, date_of_birth

    Filtering:
        id: exact, __gt, __gte, __lt, __lte, __in, __isnull
        date_of_birth: exact, __gt, __gte, __lt, __lte, __in
        first_name: exact, __gt, __gte, __lt, __lte, __in, __icontains, __istartswith
        last_name: exact, __gt, __gte, __lt, __lte, __in, __icontains, __istartswith


Versioning
**********

Autodoc for versioning - applied only when ApiVersionMixin is present and the decorated class is using
rest_framework.versioning.AcceptHeaderVersioning and has versioning_serializer_classess defined. It adds all available
versions to a swagger, so you can make a call from it using different API versions.

Permissions
***********

Autodoc for permissions - adds permission class name & it's docstring to the method description.


Adding custom classess
~~~~~~~~~~~~~~~~~~~~~~

Custom class should inherit from AutodocBase:

.. code:: python

    class CustomAutodoc(AutodocBase):
        applies_to = ("get", "post", "put", "patch", "delete")

        @classmethod
        def _generate_yaml(cls, documented_cls, method_name):
            return ""  # your implementation goes here

        @classmethod
        def _generate_text(cls, documented_cls, base_doc, method_name):
            return ""  # your implementation goes`here


Autooptimization
----------------

You can discover select related & prefetch related structure just by using @optimize decorator. It takes fields & include_fields parameters, so if the related object is not going to be serialized, it will not be queried.

The structure is discovered based on serializer that is retrieved by get_serializer_class() with context obtained by get_serializer_context().

.. code:: python

    from drf_tweaks.optimizator import optimize

    @optimize()
    class MyAPI(ListCreateAPIView):
        serializer_class = SerializerClassWithManyLevelsOfSubserializers


Counting SQL queries in tests
-----------------------------

Rationale
~~~~~~~~~
It is important to make sure your web application is efficient and can work well under high load. The ``drf_tweaks.test_utils.QueryCountingApiTestCase`` allows to have an eye on the SQL queries number. For each view it counts how many calls were executed, and if the number is high (configurable in settings), it shows suitable information (warning or exception).

Usage & Configuration
~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    from django.urls import reverse_lazy
    from drf_tweaks.test_utils import QueryCountingApiTestCase

    class TestFoo(QueryCountingApiTestCase):
        def test_bar():
            # In case there will be more SQL queries than configured in settings, an Exception or warning will be raised
            self.client.post(reverse_lazy("some-post-url"))
            # ...

To configure, set in your settings, for example:

``TEST_QUERY_NUMBER_SHOW_WARNING = 1  # default: 10``
``TEST_QUERY_NUMBER_RAISE_ERROR = 3  # default: 15``

To override those settings in tests, use the ``django.test.override_settings`` decorator
(check the `docs <https://docs.djangoproject.com/en/1.11/topics/testing/tools/#django.test.override_settings>`_).


.. |travis| image:: https://secure.travis-ci.org/ArabellaTech/drf_tweaks.svg?branch=master
.. _travis: http://travis-ci.org/ArabellaTech/drf_tweaks?branch=master

.. |pypi| image:: https://img.shields.io/pypi/v/drf_tweaks.svg
.. _pypi: https://pypi.python.org/pypi/drf_tweaks

.. |codecov| image:: https://img.shields.io/codecov/c/github/ArabellaTech/drf_tweaks/master.svg
.. _codecov: http://codecov.io/github/ArabellaTech/drf_tweaks?branch=master

.. |requiresio| image:: https://requires.io/github/ArabellaTech/drf_tweaks/requirements.svg?branch=master
.. _requiresio: https://github.com/ArabellaTech/drf_tweaks
