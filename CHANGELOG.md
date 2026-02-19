# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.18.0](https://github.com/albert-labs/albert-python/compare/v1.17.0...v1.18.0) (2026-02-19)


### Features

* **inventory:** support formula override updates ([#370](https://github.com/albert-labs/albert-python/issues/370)) ([958fd3e](https://github.com/albert-labs/albert-python/commit/958fd3e85973330cad0e31f5fe4969a3f84da548))


### Bug Fixes

* **data-templates:** handle enum and calculation column updates ([#371](https://github.com/albert-labs/albert-python/issues/371)) ([4285a49](https://github.com/albert-labs/albert-python/commit/4285a498f129e12a3a8173675a9ba141880f1c3b))

## [1.17.0](https://github.com/albert-labs/albert-python/compare/v1.16.1...v1.17.0) (2026-02-12)


### Features

* **projects:** add metadata filter search ([#369](https://github.com/albert-labs/albert-python/issues/369)) ([8e3aa67](https://github.com/albert-labs/albert-python/commit/8e3aa67f44e7b3fa4183e73986c4f4e71b61ee3c))


### Bug Fixes

* **attachments:** preserve spaces in upload filenames ([#367](https://github.com/albert-labs/albert-python/issues/367)) ([96b71c8](https://github.com/albert-labs/albert-python/commit/96b71c8df8f60f089c8861767e34b018bc73adfa))

## [1.16.1](https://github.com/albert-labs/albert-python/compare/v1.16.0...v1.16.1) (2026-02-09)

### Bug Fixes

* **attachments:** upload with unique key ([#365](https://github.com/albert-labs/albert-python/issues/365)) ([1e562d7](https://github.com/albert-labs/albert-python/commit/1e562d72f36f02e979b054574628cb2f03d6aba3))
* fetch current user via API ([#355](https://github.com/albert-labs/albert-python/issues/355)) ([8e68c6d](https://github.com/albert-labs/albert-python/commit/8e68c6d28da3466c5119ed920075309551520c15))

## [1.15.0] - 2026-02-04

### Added

* Added `CustomTemplatesCollection.create` to support creating custom templates.
* Added `CustomTemplatesCollection.update_acl` to support updating custom template ACLs.
* Added `CustomTemplatesCollection.delete` to support deleting custom templates.

### Changed

* Standardized list-parameter normalization across collection filters so scalars and
  iterables are handled consistently.

### Fixed

* Resolved custom-template ACL handling and schema parsing issues.
* Defaulted missing custom-template workflow names to a sensible value.
* Fixed enum parameter resolution to use session-level enum definitions.

## [1.14.0] - 2025-01-29

### Added

* Added `ACLContainer` model for `{class, fgclist}` ACL payloads.
* Added `WorksheetCollection.duplicate_sheet` functionality.
* Added `WorksheetCollection.create_sheet_template` functionality.
* Added a deprecation warning for `NotebookCopyACL`; formal deprecation planned for 2.0 (use `ACLContainer`).

## [1.2.0] - 2025-07-25

### Changed

* Default limit for all search() functions set to 1000 items per page

### Fixed

* Removed page_size parameter from all get_all() and search() functions for consistency

## [1.1.3] - 2025-07-23

### Added

* New activity tracking functionality ([#244] by @ventura-rivera)

* Initial release of Analytical Reports (analyticalreports) module ([#250] by @lkubie)

### Fixed

* Allow DataTemplate creation with inline parameters ([#248] by @prasad-albert)

## [1.0.1] - 2025-07-21

### Fixed

* Corrected base URL extraction for Client Credentials auth.

## [1.0.0] - 2025-07-21

### Added

* Unified AuthManager system:
  * SSO via `AlbertSSOClient` and `Albert.from_sso(...)`
  * Client Credentials via `AlbertClientCredentials` and `Albert.from_client_credentials(...)`
  * Static Token via `Albert.from_token(...)` or `ALBERT_TOKEN` environment variable
* `max_items` and `page_size` parameters added to all `get_all()` and `search()` methods for consistent, iterator-friendly pagination
* Support for `resource.hydrate()` to upgrade partial search results into fully hydrated resources
* Introduced `get_or_create(...)` method for safe idempotent creation

### Changed

* Deprecated `client_credentials` and `token` parameters in `Albert(...)`, replaced by `auth_manager`
* `create()` methods no longer perform existence checks and now raise an error if the entity already exists
* Deprecated all `list()` methods in favor of:
  * `get_all()` for detailed (hydrated) resources
  * `search()` for partial (unhydrated) resources
* Renamed `BatchDataCollection.get()` → `get_by_id()`
* Renamed `NotesCollection.list()` → `get_by_parent_id()`
* Renamed `tags.get_by_tag()` → `get_by_name()`
* Renamed all `collection.collection_exists()` → `collection.exists()`
* Renamed `InventoryInformation` model to:
  * `TaskInventoryInformation`
  * `PropertyDataInventoryInformation`
* Renamed `templates` module to `custom_templates`
