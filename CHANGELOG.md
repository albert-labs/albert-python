# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.23.0-beta4](https://github.com/albert-labs/albert-python/compare/v1.23.0-beta3...v1.23.0-beta4) (2026-03-25)


### Bug Fixes

* **release:** add last-release-sha to anchor next branch beta releases ([1894d4b](https://github.com/albert-labs/albert-python/commit/1894d4b000d6b9d66b82fffe22a09f2832fc5d8b))
* **release:** pass versioning-strategy as action input and apply skip-changelog at package level ([e79ab73](https://github.com/albert-labs/albert-python/commit/e79ab73ffcde725c922dfe9704321ab449171132))
* **release:** redirect beta changelog to CHANGELOG-beta.md and add next push trigger ([a7346b9](https://github.com/albert-labs/albert-python/commit/a7346b98e52558c36951bfcae7e7a054dc7596c9))
* **release:** remove invalid package-name input and fix env var interpolation in workflow ([57398cd](https://github.com/albert-labs/albert-python/commit/57398cdd74c6dc35e2d1d2a3a85147d5bed395ce))
* **something:** test commit ([a33c3e4](https://github.com/albert-labs/albert-python/commit/a33c3e49b473fdf86b7c670cb810378f90883261))
* **something:** test pre-release autobump version ([689d4d8](https://github.com/albert-labs/albert-python/commit/689d4d80271f683d7fc8fdeab7bfbad9809544a9))

## [1.22.0](https://github.com/albert-labs/albert-python/compare/v1.21.0...v1.22.0) (2026-03-20)


### Features

* **attachments:** add attachment update support ([#404](https://github.com/albert-labs/albert-python/issues/404)) ([e7c35c0](https://github.com/albert-labs/albert-python/commit/e7c35c0b0d6253e53c35e595560221e47d033631))
* **cas:** support updating CAS metadata ([#415](https://github.com/albert-labs/albert-python/issues/415)) ([389508f](https://github.com/albert-labs/albert-python/commit/389508fe1c2e649de3c682981823c879b13b6484))
* **chat:** add AsyncAlbert client with chat collections ([#414](https://github.com/albert-labs/albert-python/issues/414)) ([0153410](https://github.com/albert-labs/albert-python/commit/0153410135aaa8eba8b8ef6e5e0f4c0c977e746d))


### Miscellaneous Chores

* prepare beta ([a2886dd](https://github.com/albert-labs/albert-python/commit/a2886ddc8af0b09218d533d6475f8fe5d712876a))
* **task:** adding option for team assignment ([#419](https://github.com/albert-labs/albert-python/issues/419)) ([7882ef3](https://github.com/albert-labs/albert-python/commit/7882ef36fc5f78ce262dbf87f0f449ba86776896))
* **teams:** add TeamsCollection for managing teams and membership ([#418](https://github.com/albert-labs/albert-python/issues/418)) ([9dfe703](https://github.com/albert-labs/albert-python/commit/9dfe703d990b4ff1c837d9aff9e55d84d2df01ba))

## [1.21.0](https://github.com/albert-labs/albert-python/compare/v1.20.0...v1.21.0) (2026-03-11)


### Features

* **data-templates:** support owner updates ([#390](https://github.com/albert-labs/albert-python/issues/390)) ([8bfa94d](https://github.com/albert-labs/albert-python/commit/8bfa94dd7067ffa79795c290e7fc759b4291aa0e))
* support targets + smartdatasets ([#389](https://github.com/albert-labs/albert-python/issues/389)) ([1e488d0](https://github.com/albert-labs/albert-python/commit/1e488d00a9bdfcf83c40756f3765995e11f32e8a))


### Bug Fixes

* **notebooks:** support CustomTemplateId (CTP) as a valid parentId ([#411](https://github.com/albert-labs/albert-python/issues/411)) ([ec7b17b](https://github.com/albert-labs/albert-python/commit/ec7b17bfcba074db8b1837f9c3eb741530d1f7d3))
* **sheets:** fixing calculation for total cell in worksheet ([#413](https://github.com/albert-labs/albert-python/issues/413)) ([b2a2a2a](https://github.com/albert-labs/albert-python/commit/b2a2a2aa0c09d7c031291a72f440fc5a137dbcc5))
* **total-cell:** fixing total cell ([b2a2a2a](https://github.com/albert-labs/albert-python/commit/b2a2a2aa0c09d7c031291a72f440fc5a137dbcc5))


### Documentation

* **collections:** improve public method docstrings ([#392](https://github.com/albert-labs/albert-python/issues/392)) ([6888c9b](https://github.com/albert-labs/albert-python/commit/6888c9b0a694310fc3205f7247ed26852781bd17))

## [1.21.0-beta2](https://github.com/albert-labs/albert-python/compare/v1.20.0...v1.21.0-beta2) (2026-03-06)


### Features

* SDK support for Smart Datasets API ([#394](https://github.com/albert-labs/albert-python/issues/394)) ([d523667](https://github.com/albert-labs/albert-python/commit/d52366763e1030ea3a832a574908392cc99166a5))
* support targets api ([#374](https://github.com/albert-labs/albert-python/issues/374)) ([012b3e4](https://github.com/albert-labs/albert-python/commit/012b3e422c7b16adb0b44003aa512c6c548f0f52))


### Bug Fixes

* **smartdatasets:** added build_state field to smartdataset record ([#407](https://github.com/albert-labs/albert-python/issues/407)) ([ba804fe](https://github.com/albert-labs/albert-python/commit/ba804fee537296861f2995f7ea71957d37dd2bbf))
* **targets:** removed data template id from target parameter ([#384](https://github.com/albert-labs/albert-python/issues/384)) ([7a12d13](https://github.com/albert-labs/albert-python/commit/7a12d13ad0c6ea0c01d22a8cc26099f3be9bead4))


### Documentation

* **collections:** improve public method docstrings ([#392](https://github.com/albert-labs/albert-python/issues/392)) ([6888c9b](https://github.com/albert-labs/albert-python/commit/6888c9b0a694310fc3205f7247ed26852781bd17))
* update beta features ([6d1dec9](https://github.com/albert-labs/albert-python/commit/6d1dec9839ec6f878224134519077a9427c47ea6))


### Miscellaneous Chores

* prepare beta ([c9a88da](https://github.com/albert-labs/albert-python/commit/c9a88da88131152ffaf2fd66976f2ecf6af72d5b))
* prepare beta ([#397](https://github.com/albert-labs/albert-python/issues/397)) ([7239cfb](https://github.com/albert-labs/albert-python/commit/7239cfb9b24a2ec120b2f84643240412704da563))
* prepare beta ([#400](https://github.com/albert-labs/albert-python/issues/400)) ([4f5a1ad](https://github.com/albert-labs/albert-python/commit/4f5a1ad7f0688cae4b86ed06e0b518ac64d22e09))
* prepare beta ([#403](https://github.com/albert-labs/albert-python/issues/403)) ([e7cf3c7](https://github.com/albert-labs/albert-python/commit/e7cf3c76918d663d18af3d7d22b8fb7492678ac9))
* prepare beta ([#408](https://github.com/albert-labs/albert-python/issues/408)) ([8c6fb27](https://github.com/albert-labs/albert-python/commit/8c6fb273d045708adfff13c6def61e75e20cdcc5))

## [1.20.0](https://github.com/albert-labs/albert-python/compare/v1.19.0...v1.20.0) (2026-03-04)


### Features

* add advanced search capabilities to datatemplates, parametergroups ([#383](https://github.com/albert-labs/albert-python/issues/383)) ([fc14149](https://github.com/albert-labs/albert-python/commit/fc14149a1da6dec67358422c6e062c9b19446564))


### Bug Fixes

* **cas_amount:** adding block for cas_caegory update ([#395](https://github.com/albert-labs/albert-python/issues/395)) ([9ab7fb3](https://github.com/albert-labs/albert-python/commit/9ab7fb3e13bf049c996cc9357261575925294f80))
* **parameters:** ensure get_or_create matches name exactly ([#380](https://github.com/albert-labs/albert-python/issues/380)) ([f741c8b](https://github.com/albert-labs/albert-python/commit/f741c8b7e1df6722db4e462300423c4374cf9f9c))

## [1.19.0](https://github.com/albert-labs/albert-python/compare/v1.18.0...v1.19.0) (2026-02-23)


### Features

* **lots:** add direct adjust and transfer actions ([#376](https://github.com/albert-labs/albert-python/issues/376)) ([23cc97d](https://github.com/albert-labs/albert-python/commit/23cc97d3793520541c2a64c9507fbba514cb4959))

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
