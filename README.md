# drf_extensions

**Set of extensions for Django Rest Framework**

This project is intended to contain a set of improvements/addons for DRF.

**This is work in progress**

# Current extensions
 - pagination without counts

TODO: add here each extensions after adding it
TODO: autodoc
TODO: versioning
TODO: Extended Serializer
- single pass
- custom errors
- pool
- fields controlled by param

---

# Pagination

Rationale: Calling "count" each time a queryset gets paginated is inefficient - especialy for large datasets. Moreover,
in most cases it is unnecessary to have counts (for example for endless scrolls). The fastest pagination in such case is
CursorPaginator, however it is not as easy to use as LimitOffsetPaginator/PageNumberPaginator and does not allow sorting.

* pagination.NoCountsLimitOffsetPagination *
A limit/offset based pagination, without performing counts. For example:

http://api.example.org/accounts/?limit=100 - will return first 100 items
http://api.example.org/accounts/?offset=400&limit=100 - will returns 100 items starting from 401th
http://api.example.org/accounts/?offset=-50&limit=100 - will return first 50 items

HTML is not handled (no get_html_context).

Pros:
    - no counts
    - easier to use than cursor pagination (especially if you need sorting)
    - works with angular ui-scroll (which requires negative offsets)

Cons:
    - skip is a relatively slow operation, so this paginator is not as fast as cursor paginator when you use
      large offsets

* pagination.NoCountsPageNumberPagination *
A standard page number pagination, without performing counts.

HTML is not handled (no get_html_context).

Pros:
    - no counts
    - easier to use than cursor pagination (especially if you need sorting)

Cons:
    - skip is a relatively slow operation, so this paginator is not as fast as cursor paginator when you use
      large page numbers
