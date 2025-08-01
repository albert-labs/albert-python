# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.2.0] - 2025-07-25

### Changed

- Default limit for all search() functions set to 1000 items per page

### Fixed

- Removed page_size parameter from all get_all() and search() functions for consistency

## [1.1.3] - 2025-07-23

### Added

- New activity tracking functionality ([#244] by @ventura-rivera)

- Initial release of Analytical Reports (analyticalreports) module ([#250] by @lkubie)

### Fixed

- Allow DataTemplate creation with inline parameters ([#248] by @prasad-albert)

## [1.0.1] - 2025-07-21

### Fixed

- Corrected base URL extraction for Client Credentials auth.

## [1.0.0] - 2025-07-21

### Added

- Unified AuthManager system:
  - SSO via `AlbertSSOClient` and `Albert.from_sso(...)`
  - Client Credentials via `AlbertClientCredentials` and `Albert.from_client_credentials(...)`
  - Static Token via `Albert.from_token(...)` or `ALBERT_TOKEN` environment variable
- `max_items` and `page_size` parameters added to all `get_all()` and `search()` methods for consistent, iterator-friendly pagination
- Support for `resource.hydrate()` to upgrade partial search results into fully hydrated resources
- Introduced `get_or_create(...)` method for safe idempotent creation

### Changed

- Deprecated `client_credentials` and `token` parameters in `Albert(...)`, replaced by `auth_manager`
- `create()` methods no longer perform existence checks and now raise an error if the entity already exists
- Deprecated all `list()` methods in favor of:
  - `get_all()` for detailed (hydrated) resources
  - `search()` for partial (unhydrated) resources
- Renamed `BatchDataCollection.get()` → `get_by_id()`
- Renamed `NotesCollection.list()` → `get_by_parent_id()`
- Renamed `tags.get_by_tag()` → `get_by_name()`
- Renamed all `collection.collection_exists()` → `collection.exists()`
- Renamed `InventoryInformation` model to:
  - `TaskInventoryInformation`
  - `PropertyDataInventoryInformation`
- Renamed `templates` module to `custom_templates`
