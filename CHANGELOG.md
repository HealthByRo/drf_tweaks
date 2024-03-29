# Change Log
All notable changes to this project will be documented in this file.

## [0.9.7] - 2021-09-29
### Changed
- Fix issue with django.core.exceptions.FieldError: Invalid field name(s) given in select_related: error.

## [0.9.6] - 2021-03-04
### Changed
- Run tests on Python 3.9.
- Explicitly test with Django 3.0 and 3.1.

## [0.9.5] - 2020-08-19
### Changed
- Dependencies (swagger >2)
- Small cleanup in tox

## [0.9.4] - 2020-03-31
### Added
- Added support for `select_for_update(of=...)` to lock limiter

### Removed
- support for Django <2.0

## [0.9.3] - 2019-04-15
### Fixed
- Use `wraps` to correctly wrap copied methods

## [0.9.2] - 2019-04-15
### Fixed
- A bug in the lock limiter: it'd crash when with_col_aliases was passed to SQLCompiler.as_sql()

## [0.9.1] - 2019-01-11
### Added
- Ability to force prefetch related instead of select related

## [0.9.0] - 2019-01-03
### Added
- BulkEditAPIMixin

## [0.8.1] - 2018-11-30
### Added
- TestQueryCounter.freeze decorator that disables the counter for the duration of a block
### Removed
- claims of support for Python <3.6 in setup.py

## [0.8.0] - 2018-11-17
### Added
- DatabaseAccessLintingAPIClient: detects attempts to `select_for_update` more than one table, includes the functionality of `DatabaseAccessLintingAPIClient`
### Removed
- support for Python <3.6

## [0.7.1] - 2018-04-16
### Added
- option to exclude fields from autofilter

## [0.7.0] - 2018-02-15
### Added
- support for Django 2.0
### Removed
- support for Django <1.11

## [0.6.3] - 2017-06-30
### Fixed
- swagger update reverted

## [0.6.2] - 2017-06-30
### Added
- possibility to not count some queries base on patterns

## [0.6.1] - 2017-06-30
### Added
- possibility to print queries on TooManySQLQueriesException

## [0.6.0] - 2017-06-21
### Added
- read_only_fields in Meta in Serializer now affects also explicitly defined fields in the serializer

## [0.5.2] - 2017-06-19
### Fixed
- typo

## [0.5.1] - 2017-06-19
### Changed
- auto-optimization is now a mixin, not a decorator

## [0.5.0] - 2017-06-15
### Added
- auto-optimization of APIs

### Fixed
- context passing to subserializers using many=True

### Changed
- query counting in tests refactored

## [0.4.1] - 2017-06-12
### Added
- pass_context method for filtering fields for Serializers used in SerializerMethodField

## [0.4.0] - 2017-06-08
### Added
- QueryCountingApiTestCase

## [0.3.2] - 2017-06-05
### Fixed
- Serializer may not have meta

## [0.3.1] - 2017-06-05
### Added
- On demand fields.
- Nested fields filtering.

## [0.3.0] - 2017-06-02
### Added
- Context passing to subserializers. This may be a breaking change in some cases.

## [0.2.11] - 2017-05-24
### Added
- Added unique fields to autofilter

## [0.2.10] - 2017-05-16
### Added
- Updated swagger docs with limiting fields

## [0.2.9] - 2017-05-11
### Fixed
- fixed allow_null when forcing required field

## [0.2.8] - 2017-04-11
### Fixed
- fixed extending existing filter class

## [0.2.7] - 2017-03-14
### Added
- __istartswith filter for strings in autofilter

## [0.2.6] - 2017-02-20
### Added
- changelog

### Changed
- documentation migrated from md to rst

