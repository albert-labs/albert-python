# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.33.0](https://github.com/albert-labs/albert-python/compare/albert-v1.32.1...albert-v1.33.0) (2026-07-07)


### Features

* **activities:** add search() method ([#547](https://github.com/albert-labs/albert-python/issues/547)) ([c6f8572](https://github.com/albert-labs/albert-python/commit/c6f85722d0ff3ce3a27e23810a44b489470b5a1e))
* **activities:** adding AlbertCollections to Albert methods ([64faf30](https://github.com/albert-labs/albert-python/commit/64faf30dd6525276e420f44761a3b84283b19fdf))
* **activities:** adding changelog and contributing symlinks ([1397f08](https://github.com/albert-labs/albert-python/commit/1397f08a6792524573975d37b0e72e0d03faa1c6))
* **activities:** adding test for activity list ([674e1c9](https://github.com/albert-labs/albert-python/commit/674e1c9b2155279c8dc9137a21522469b95eab92))
* **activities:** creating data models for Activities ([d543fd3](https://github.com/albert-labs/albert-python/commit/d543fd3ff64dea2349f74af5b8f40ac6be281c78))
* **activities:** exposing activity list endpoint ([b885cf9](https://github.com/albert-labs/albert-python/commit/b885cf95d02c6de6607561b7f4b04acbf1ab0f7a))
* **activities:** incorporating new page_size and max_items ([d606cb7](https://github.com/albert-labs/albert-python/commit/d606cb75fca1ea58688dc4c726a6d2b75d0a3b3b))
* **activities:** list-&gt;get_all ([e5817ce](https://github.com/albert-labs/albert-python/commit/e5817ced38552c642246cbc1383336e1c04b6bf1))
* **activities:** merge main into feature/activity ([da35f0d](https://github.com/albert-labs/albert-python/commit/da35f0d19e31d35b06f47c502075d4b6545bfbe3))
* **activities:** merge remote feature/activities into local feature/activities ([93b2450](https://github.com/albert-labs/albert-python/commit/93b24502afcc6587dad7a47d6a2ea1a187d1d586))
* **activities:** merge remote feature/activities into local feature/activities ([99edf78](https://github.com/albert-labs/albert-python/commit/99edf7837fc8c8a173b3717985502c1567141f1d))
* **activities:** minor comment update ([5c97617](https://github.com/albert-labs/albert-python/commit/5c97617b19ff8b401a75a46a71cbc61b2d7bdc21))
* **activities:** minor comment update ([21db8af](https://github.com/albert-labs/albert-python/commit/21db8afff7b1a92297f5b3ee56a1c07d249cdcb6))
* **activities:** minor comment update ([b29c515](https://github.com/albert-labs/albert-python/commit/b29c5152ed6ca9b778bb46aa965657b847e0da53))
* **activities:** minor fix for activity test ([dfdae44](https://github.com/albert-labs/albert-python/commit/dfdae44b6df230cc63aaab528c2893de50d4ca4f))
* **activities:** minor fix; missing decorator ([0542964](https://github.com/albert-labs/albert-python/commit/05429647f9517f4f8df7218b6920b6ef68b05d14))
* **activities:** minor import fix ([2903cbb](https://github.com/albert-labs/albert-python/commit/2903cbb5714a731f3f88e3f534d6fe1de5aa023d))
* **activities:** minor import fix in test ([e51eef8](https://github.com/albert-labs/albert-python/commit/e51eef80affcf861c5a2243f4b685a66c65d3c6d))
* **activities:** removing .value from order_by in case NoneType ([7feea7c](https://github.com/albert-labs/albert-python/commit/7feea7c6569d4eb7bc0f8182249ddc03f83bdc0e))
* **activities:** update src/albert/collections/activities.py ([8178261](https://github.com/albert-labs/albert-python/commit/8178261dd81dd1221e29f67c33591f3eaac75d4d))
* **activities:** update src/albert/collections/activities.py ([a18a2f6](https://github.com/albert-labs/albert-python/commit/a18a2f6b03e3d7394bba70468d8cb0e41931e1d8))
* **activities:** update tests/collections/test_activities.py ([066df77](https://github.com/albert-labs/albert-python/commit/066df774956801bbfc156538a26a7d889aa2b651))
* **activities:** update tests/collections/test_activities.py ([13053e2](https://github.com/albert-labs/albert-python/commit/13053e2a47533b7e06096dc6b204aebf5ae715ef))
* **activities:** version bump ([526c61e](https://github.com/albert-labs/albert-python/commit/526c61ec1a83901be2ccd0d7705a605eeb9156c6))
* **activity:** adding activity module to docs ([21d3475](https://github.com/albert-labs/albert-python/commit/21d34756a8255a87f656cb4536adb2ceab051f07))
* add advanced search capabilities to datatemplates, parametergroups ([#383](https://github.com/albert-labs/albert-python/issues/383)) ([fc14149](https://github.com/albert-labs/albert-python/commit/fc14149a1da6dec67358422c6e062c9b19446564))
* add customtemplate create and normalize list params across collections ([#332](https://github.com/albert-labs/albert-python/issues/332)) ([b313115](https://github.com/albert-labs/albert-python/commit/b313115fc71ec9367f09672d9f1539c0fbfb8333))
* add search for lots ([#335](https://github.com/albert-labs/albert-python/issues/335)) ([a8d5b2f](https://github.com/albert-labs/albert-python/commit/a8d5b2fe3b9aa785aeb46fb1aac436e7e609801b))
* add storage-classes, hazards collections, support sds upload ([#290](https://github.com/albert-labs/albert-python/issues/290)) ([df463d3](https://github.com/albert-labs/albert-python/commit/df463d33f07fd9905af042c56e7c78ffa15cfc99))
* add support for get_data ([#488](https://github.com/albert-labs/albert-python/issues/488)) ([f6e5ae8](https://github.com/albert-labs/albert-python/commit/f6e5ae8249cec8b0acbe52866ea22657bec56185))
* Added document search to projects collection ([#363](https://github.com/albert-labs/albert-python/issues/363)) ([53d648e](https://github.com/albert-labs/albert-python/commit/53d648ee4be7cea86d48a09773372419cb39849a))
* adds analytical report coverage ([694b405](https://github.com/albert-labs/albert-python/commit/694b405c873bf9422e1caf953d1d4f73ce4af620))
* AsyncAlbert client, chat collections, and smart datasets ([#482](https://github.com/albert-labs/albert-python/issues/482)) ([e0efaeb](https://github.com/albert-labs/albert-python/commit/e0efaeb3dd8138cfa0fe6deb4b0e0bbaccbee57c))
* **attachments:** add attachment update support ([#404](https://github.com/albert-labs/albert-python/issues/404)) ([e7c35c0](https://github.com/albert-labs/albert-python/commit/e7c35c0b0d6253e53c35e595560221e47d033631))
* **attachments:** add get_jurisdiction_codes and get_language_codes methods ([#524](https://github.com/albert-labs/albert-python/issues/524)) ([1f75c33](https://github.com/albert-labs/albert-python/commit/1f75c330904bcc74595c6581146ab1437d22d545))
* **cas:** cap get_by_number partial-match pagination to avoid OpenSearch 500 ([#505](https://github.com/albert-labs/albert-python/issues/505)) ([cc4f03c](https://github.com/albert-labs/albert-python/commit/cc4f03cc8956a35c6b520041979767e798dfcf3d))
* **cas:** support updating CAS metadata ([#415](https://github.com/albert-labs/albert-python/issues/415)) ([389508f](https://github.com/albert-labs/albert-python/commit/389508fe1c2e649de3c682981823c879b13b6484))
* **chats:** add pageContext to ChatMessage (AI-637) ([#556](https://github.com/albert-labs/albert-python/issues/556)) ([301a7d9](https://github.com/albert-labs/albert-python/commit/301a7d94b9022e1a03370f5f0453c5f18747ec44))
* **chats:** add TOOL_CALL and ERROR to ChatComponentType [SDK-50] ([#502](https://github.com/albert-labs/albert-python/issues/502)) ([5c21d50](https://github.com/albert-labs/albert-python/commit/5c21d50dac091c2a1788899eafb183f458bbe5da))
* **companies:** support merge companies ([#331](https://github.com/albert-labs/albert-python/issues/331)) ([85deeaa](https://github.com/albert-labs/albert-python/commit/85deeaabeee485edf54b27ae56e9c94a19dc8b1d))
* curve and image property data ([#342](https://github.com/albert-labs/albert-python/issues/342)) ([28495a1](https://github.com/albert-labs/albert-python/commit/28495a135d3a5cfcf17af773b1acaf1af0652aa5))
* **custom_fields:** allow customfields for CAS ([#258](https://github.com/albert-labs/albert-python/issues/258)) ([3a30251](https://github.com/albert-labs/albert-python/commit/3a3025168cb1009621b0cc4a5987f2bd8a2d45b7))
* **customfields:** date-and-datetime-type ([#577](https://github.com/albert-labs/albert-python/issues/577)) ([f3d2182](https://github.com/albert-labs/albert-python/commit/f3d21826b424ecf02b3f7fadf06151e525f154ba))
* **customfields:** support editable ([#296](https://github.com/albert-labs/albert-python/issues/296)) ([d24d906](https://github.com/albert-labs/albert-python/commit/d24d9063f6afad9b4ffcd3a26a3f7c67adb0b689))
* **data_columns:** add get_or_create method to DataColumnCollection ([#478](https://github.com/albert-labs/albert-python/issues/478)) ([d838de9](https://github.com/albert-labs/albert-python/commit/d838de932533ee866ceebab612f6a2f6927fd17d))
* **data-templates:** support owner updates ([#390](https://github.com/albert-labs/albert-python/issues/390)) ([8bfa94d](https://github.com/albert-labs/albert-python/commit/8bfa94dd7067ffa79795c290e7fc759b4291aa0e))
* **entitytypes:** extend entitytypes to add inventories ([#326](https://github.com/albert-labs/albert-python/issues/326)) ([f8950ca](https://github.com/albert-labs/albert-python/commit/f8950cafda6e4cb2fd88d0606c1a6aff94cae862))
* inventory function on cas ([#348](https://github.com/albert-labs/albert-python/issues/348)) ([2086637](https://github.com/albert-labs/albert-python/commit/20866377fcf3dda7c2bd198d9b9c2c419640023b))
* inventory search key from created at ([#318](https://github.com/albert-labs/albert-python/issues/318)) ([96f1542](https://github.com/albert-labs/albert-python/commit/96f1542ee8c6168c36b795d5c7e0cb18795629f0))
* **inventory:** support formula override updates ([#370](https://github.com/albert-labs/albert-python/issues/370)) ([958fd3e](https://github.com/albert-labs/albert-python/commit/958fd3e85973330cad0e31f5fe4969a3f84da548))
* **lots:** add direct adjust and transfer actions ([#376](https://github.com/albert-labs/albert-python/issues/376)) ([23cc97d](https://github.com/albert-labs/albert-python/commit/23cc97d3793520541c2a64c9507fbba514cb4959))
* **notebook:** ketcher block creation using SMILES ([#336](https://github.com/albert-labs/albert-python/issues/336)) ([3b54a29](https://github.com/albert-labs/albert-python/commit/3b54a29846d845dd3b5f89e7ff5da8743673baa5))
* **notebooks:** add append_blocks to safely add blocks ([#581](https://github.com/albert-labs/albert-python/issues/581)) ([87fddc0](https://github.com/albert-labs/albert-python/commit/87fddc0793e0d4da24af71a545f6eed4733728da))
* **parameter_groups:** add required field to ParameterValue with patch support ([#480](https://github.com/albert-labs/albert-python/issues/480)) ([5101fc4](https://github.com/albert-labs/albert-python/commit/5101fc4a92c22ddf6d3f62dc8c7de51ef5b6a4af)), closes [#479](https://github.com/albert-labs/albert-python/issues/479)
* **parameter_groups:** support User-type special parameter values ([#543](https://github.com/albert-labs/albert-python/issues/543)) ([f1e3b79](https://github.com/albert-labs/albert-python/commit/f1e3b79e1779cd4faf74fce98f11a96e4bdb2672))
* **projects:** add metadata filter search ([#369](https://github.com/albert-labs/albert-python/issues/369)) ([8e3aa67](https://github.com/albert-labs/albert-python/commit/8e3aa67f44e7b3fa4183e73986c4f4e71b61ee3c))
* **propertydata:** add optional return_scope for faster updates ([#319](https://github.com/albert-labs/albert-python/issues/319)) ([565968c](https://github.com/albert-labs/albert-python/commit/565968c2ec725b41532a2da8ba2b2249dc08b66f))
* **reports:** add report template and report retrieval capabilities ([babbe58](https://github.com/albert-labs/albert-python/commit/babbe584cbee8364c4f88b9d38d23b163e205d16))
* **reports:** added generalized report category caller and analytics report ([b1ff7fc](https://github.com/albert-labs/albert-python/commit/b1ff7fc875b1bc3cdd88f018c3738d9682c22222))
* **reports:** added generalized report category caller and analytics… ([884f376](https://github.com/albert-labs/albert-python/commit/884f376554bbfddf004bf8ce4cdb7b5265a41eb9))
* **session:** add configurable request timeout ([#572](https://github.com/albert-labs/albert-python/issues/572)) ([960f1de](https://github.com/albert-labs/albert-python/commit/960f1de714a852990548ee691f3886fa14fc9016))
* **sheets:** add is_column_right field to Sheet model ([75327db](https://github.com/albert-labs/albert-python/commit/75327dbcf95f8226c081efa23f102bd9503302fa))
* **sheets:** row grouping, new column/row types, and fixes from PR [#267](https://github.com/albert-labs/albert-python/issues/267) ([#528](https://github.com/albert-labs/albert-python/issues/528)) ([3fe9642](https://github.com/albert-labs/albert-python/commit/3fe9642034a4d53c00e10bc402a5a21adb0cfb00))
* **sheets:** support min/max in cells ([#266](https://github.com/albert-labs/albert-python/issues/266)) ([36ef01f](https://github.com/albert-labs/albert-python/commit/36ef01fea19c31e50b45e9a667e63d08e25209e0))
* **sheets:** support process design grid ([#322](https://github.com/albert-labs/albert-python/issues/322)) ([055cc75](https://github.com/albert-labs/albert-python/commit/055cc75db17e79a4f9053d598971f34325ea714c))
* **smart_dataset:** add pagination to get_all ([#555](https://github.com/albert-labs/albert-python/issues/555)) ([c46096e](https://github.com/albert-labs/albert-python/commit/c46096e7f39ad97c8d5f239f3f6ae24e42c73429))
* **smartdatasets:** adds optional parent-id to smartdatasets for inheriting project ACL policy ([#506](https://github.com/albert-labs/albert-python/issues/506)) ([29600d1](https://github.com/albert-labs/albert-python/commit/29600d1387a34b5bacbfbaed38c0c9f1377f45ca))
* standardize create, and add get_or_create ([6c7880b](https://github.com/albert-labs/albert-python/commit/6c7880bcfd9f677a72d460832d633f81ed101add))
* support parent id on targets ([#504](https://github.com/albert-labs/albert-python/issues/504)) ([fcc40a0](https://github.com/albert-labs/albert-python/commit/fcc40a084e1982a14c5cb3492db3c5b9871d1f5d))
* support smart projects ([#523](https://github.com/albert-labs/albert-python/issues/523)) ([5d42f9a](https://github.com/albert-labs/albert-python/commit/5d42f9a302553eab6f4236bd3f2a28104d8e5523))
* support targets + smartdatasets ([#389](https://github.com/albert-labs/albert-python/issues/389)) ([1e488d0](https://github.com/albert-labs/albert-python/commit/1e488d00a9bdfcf83c40756f3765995e11f32e8a))
* **targets:** widen TargetParameter.value to operator/value-pair with legacy coercion ([#539](https://github.com/albert-labs/albert-python/issues/539)) ([ae1a99d](https://github.com/albert-labs/albert-python/commit/ae1a99de628035bc227eb87893afb60c5eee4364))
* **task:** adding option for team assignment ([#419](https://github.com/albert-labs/albert-python/issues/419)) ([7882ef3](https://github.com/albert-labs/albert-python/commit/7882ef36fc5f78ce262dbf87f0f449ba86776896))
* **tasks:** allow a cancelled tasks ([#281](https://github.com/albert-labs/albert-python/issues/281)) ([bebf9f4](https://github.com/albert-labs/albert-python/commit/bebf9f437314bcdc138215037641cff427eb1085))
* **tasks:** support updating project via tasks.update() ([#529](https://github.com/albert-labs/albert-python/issues/529)) ([16f4feb](https://github.com/albert-labs/albert-python/commit/16f4feb9011f95b4db6d68e2529d8d7cc5a5c8e3))
* **teams:** add TeamsCollection for managing teams and membership ([#418](https://github.com/albert-labs/albert-python/issues/418)) ([9dfe703](https://github.com/albert-labs/albert-python/commit/9dfe703d990b4ff1c837d9aff9e55d84d2df01ba))
* **workflows:** support DT with linked parameters ([#268](https://github.com/albert-labs/albert-python/issues/268)) ([349f451](https://github.com/albert-labs/albert-python/commit/349f451fb8c82f196a4a702e92d91756eff341be))
* **worksheets:** support duplicating a sheet ([#245](https://github.com/albert-labs/albert-python/issues/245)) ([61f89aa](https://github.com/albert-labs/albert-python/commit/61f89aa6f7384eb200e5612e01586fc5410cddc5))
* **worksheet:** support locking formula/column ([#269](https://github.com/albert-labs/albert-python/issues/269)) ([8cfec01](https://github.com/albert-labs/albert-python/commit/8cfec0130e1703c38e957ccd08fd6e58ce1da5ed))


### Bug Fixes

* **acl:** add CASFullAccess in ACL ([#286](https://github.com/albert-labs/albert-python/issues/286)) ([ced30bb](https://github.com/albert-labs/albert-python/commit/ced30bbf8c03c4685e5b6c1a423c866379eff6b4))
* **acl:** add ProjectStrictViewer in ACL ([#285](https://github.com/albert-labs/albert-python/issues/285)) ([4a6914e](https://github.com/albert-labs/albert-python/commit/4a6914eee18307841b4e368090047d50bec30bf1))
* add attachments field to ChatMessage ([#588](https://github.com/albert-labs/albert-python/issues/588)) ([c06ba6e](https://github.com/albert-labs/albert-python/commit/c06ba6e12050e155dfb689ea703a9d3ffb1aff9f))
* add missing validate_call for ID normalization ([#343](https://github.com/albert-labs/albert-python/issues/343)) ([5e01f8d](https://github.com/albert-labs/albert-python/commit/5e01f8d65ead1204c6d631f483cb7aa5e34ec707))
* add optional session param to Albert ([43bd502](https://github.com/albert-labs/albert-python/commit/43bd502c437b10cb7ac4d79f71ddc9ca3bd8017d))
* add parent id to btinsight and btdataset ([#449](https://github.com/albert-labs/albert-python/issues/449)) ([0d17179](https://github.com/albert-labs/albert-python/commit/0d17179c3a940e95ce337bd3975ae44b509e161e))
* add symbols metadata to SDS ([#293](https://github.com/albert-labs/albert-python/issues/293)) ([ca61128](https://github.com/albert-labs/albert-python/commit/ca611282b7521a7d24363602b5edb15def981f44))
* add uv.lock ([448de9e](https://github.com/albert-labs/albert-python/commit/448de9e30951d5a27d875d157d281e8b5982b17d))
* add uv.lock and update docs ([119c2d3](https://github.com/albert-labs/albert-python/commit/119c2d3c5e97e85e9a0419061e2edf4e80ed5048))
* allow inv-id in Component ([#291](https://github.com/albert-labs/albert-python/issues/291)) ([4c49a95](https://github.com/albert-labs/albert-python/commit/4c49a957b27bd060df408e118ed43da11b700623))
* **attachments:** accept unknown category values gracefully ([#552](https://github.com/albert-labs/albert-python/issues/552)) ([96c701e](https://github.com/albert-labs/albert-python/commit/96c701e01cba3c1297b646a6bf276d33910e32d8))
* **attachments:** attachment override on upload ([#350](https://github.com/albert-labs/albert-python/issues/350)) ([acf008f](https://github.com/albert-labs/albert-python/commit/acf008ff532de2db7b7a01f512b623dd32b72149))
* **attachments:** preserve spaces in upload filenames ([#367](https://github.com/albert-labs/albert-python/issues/367)) ([96b71c8](https://github.com/albert-labs/albert-python/commit/96b71c8df8f60f089c8861767e34b018bc73adfa))
* **attachments:** upload with unique key ([#365](https://github.com/albert-labs/albert-python/issues/365)) ([1e562d7](https://github.com/albert-labs/albert-python/commit/1e562d72f36f02e979b054574628cb2f03d6aba3))
* **auth:** fix base url in client creds ([f21a3bc](https://github.com/albert-labs/albert-python/commit/f21a3bc9d40f1e2c9ec9ab09b80b22f99c6ed1c5))
* **auth:** fix base url in client creds ([fcc0352](https://github.com/albert-labs/albert-python/commit/fcc03525cc1154ae2dadd064ad02358a222cc6c6))
* **auth:** set token for tenant specified by user ([#260](https://github.com/albert-labs/albert-python/issues/260)) ([1a226c3](https://github.com/albert-labs/albert-python/commit/1a226c327e8edd721f040e842ae32771de406c97))
* **auth:** standardize albert base url ([#271](https://github.com/albert-labs/albert-python/issues/271)) ([f6d5475](https://github.com/albert-labs/albert-python/commit/f6d5475e100a2139006380e2250dc63648c1cb30))
* **base:** fixes metadata list patch ([#257](https://github.com/albert-labs/albert-python/issues/257)) ([8c0260e](https://github.com/albert-labs/albert-python/commit/8c0260eda7692674b1446471b6c966b03bfb552c))
* **base:** fixes patch operation on metadata when new val is None ([c7d3e6b](https://github.com/albert-labs/albert-python/commit/c7d3e6b609bb7d8c16ead9fdc17fe182a8660c61))
* **base:** fixes patch operation on metadata when new val is None ([9418369](https://github.com/albert-labs/albert-python/commit/94183693324cda44cfcceccfda48afe5a2a2e5c3))
* **cas_amount:** adding block for cas_caegory update ([#395](https://github.com/albert-labs/albert-python/issues/395)) ([9ab7fb3](https://github.com/albert-labs/albert-python/commit/9ab7fb3e13bf049c996cc9357261575925294f80))
* **cas:** add status, created, updated to CAS ([#264](https://github.com/albert-labs/albert-python/issues/264)) ([5aba29a](https://github.com/albert-labs/albert-python/commit/5aba29aaec4b25a7c94c8e7d3a3ddcd5106ca5b9))
* **cas:** fix pagination for unfiltered listing and filtered search paths ([#445](https://github.com/albert-labs/albert-python/issues/445)) ([73f5418](https://github.com/albert-labs/albert-python/commit/73f5418e03977113078b689c36f3434732aedee5))
* **cas:** get_all uses API filtering by opensearch ([#325](https://github.com/albert-labs/albert-python/issues/325)) ([85f1053](https://github.com/albert-labs/albert-python/commit/85f1053274e9771be4a0f86e73d4c0c626a5c5e1))
* **cell value type:** adding list to cell value types ([#300](https://github.com/albert-labs/albert-python/issues/300)) ([4f392d0](https://github.com/albert-labs/albert-python/commit/4f392d0aada07589faa5bac7d6d746222dbe43ca))
* **chats:** add attachments field to ChatMessage ([c06ba6e](https://github.com/albert-labs/albert-python/commit/c06ba6e12050e155dfb689ea703a9d3ffb1aff9f))
* **chats:** add DOCUMENT_CITATION component type AI-655 ([#538](https://github.com/albert-labs/albert-python/issues/538)) ([e761ce4](https://github.com/albert-labs/albert-python/commit/e761ce40c3a1d1b0b8ab9028351a0bee3e000a36))
* **ci:** harden and upgrade claude-code workflows ([#586](https://github.com/albert-labs/albert-python/issues/586)) ([4a70bd3](https://github.com/albert-labs/albert-python/commit/4a70bd388ecfcfd220b10165ab632f967f065a20))
* **ci:** route manifest-file per target branch in release-please workflow ([#594](https://github.com/albert-labs/albert-python/issues/594)) ([cc1778b](https://github.com/albert-labs/albert-python/commit/cc1778bf653c4b701bfc75a5dc5efb2f229587a5))
* **ci:** trigger claude review workflows only on PR state changes ([#597](https://github.com/albert-labs/albert-python/issues/597)) ([8abce3f](https://github.com/albert-labs/albert-python/commit/8abce3fe15b5719f4f5f7cecc6fcbb21e9c9491a))
* **companies:** fix flakes in company test ([9899c90](https://github.com/albert-labs/albert-python/commit/9899c9047c1b580bed09dd921c599b876364b233))
* **custom_fields:** align customEntityCategory patch ops with new API semantics ([#526](https://github.com/albert-labs/albert-python/issues/526)) ([9692d8b](https://github.com/albert-labs/albert-python/commit/9692d8bb117280054d7a15d7953743adc97dafa5))
* **custom_fields:** correct PATCH operation/oldValue handling for unset fields ([#557](https://github.com/albert-labs/albert-python/issues/557)) ([f4b5d76](https://github.com/albert-labs/albert-python/commit/f4b5d76faa26c105cc0156b0321f07914278c525))
* **custom_fields:** support defaults ([#280](https://github.com/albert-labs/albert-python/issues/280)) ([ea4484b](https://github.com/albert-labs/albert-python/commit/ea4484bab440c1aab41049d17791b3e04663437b))
* **data_templates:** create dt with parameters ([c8ac123](https://github.com/albert-labs/albert-python/commit/c8ac1234508fdc79c5d44c3a2c5b901b5cec96be))
* **data_templates:** workaround backend s3key bug in calculation update test ([#498](https://github.com/albert-labs/albert-python/issues/498)) ([669a1db](https://github.com/albert-labs/albert-python/commit/669a1dbe89025fe54a10d3b6cc610f7dd57ec4fc))
* **data-templates:** allow creation with no data columns ([8dc23f4](https://github.com/albert-labs/albert-python/commit/8dc23f4faf6ed019f2bd7f4ca89317c582000404))
* **data-templates:** allow creation with no data columns ([69bab08](https://github.com/albert-labs/albert-python/commit/69bab08e4c6dd763d440d63581fb63c2271fb7f2))
* **data-templates:** correct payload for datacolumn delete in update() ([#585](https://github.com/albert-labs/albert-python/issues/585)) ([a9cbe5d](https://github.com/albert-labs/albert-python/commit/a9cbe5d461ef12d6efdc29599386e1a9afaafcfe))
* **data-templates:** handle enum and calculation column updates ([#371](https://github.com/albert-labs/albert-python/issues/371)) ([4285a49](https://github.com/albert-labs/albert-python/commit/4285a498f129e12a3a8173675a9ba141880f1c3b))
* **datatemplate:** patch enums for existing parameters ([#288](https://github.com/albert-labs/albert-python/issues/288)) ([b5a5caf](https://github.com/albert-labs/albert-python/commit/b5a5caf9743ecbb47197eb1008b45e1aac81b209))
* **datatemplates:** fixes patching of parameters on DTs ([d1014a6](https://github.com/albert-labs/albert-python/commit/d1014a6358f7ac2a16ac736786a9b069448c0851))
* deploy docs ([773de7c](https://github.com/albert-labs/albert-python/commit/773de7c0a1d33ddf2be62074a770b3435ab740c7))
* docs ([5723173](https://github.com/albert-labs/albert-python/commit/57231735efe91a09d486ec1b1927ec641ebf9fed))
* **docs:** re-add CONTRIBUTING.md file ([7f2dba8](https://github.com/albert-labs/albert-python/commit/7f2dba8caced869acd6858c7dc1d961c01243c4e))
* **docs:** re-add CONTRIBUTING.md file ([58a9ff7](https://github.com/albert-labs/albert-python/commit/58a9ff7e8835f7c3f6a37fa3ba8f7a19223541b1))
* entity type null defaults ([#341](https://github.com/albert-labs/albert-python/issues/341)) ([8e4bacd](https://github.com/albert-labs/albert-python/commit/8e4bacd1dea0bea779710c4e24706e9424a137bc))
* **exceptions:** make AlbertHTTPError picklable for Ray/multiprocessing contexts ([#560](https://github.com/albert-labs/albert-python/issues/560)) ([22579d1](https://github.com/albert-labs/albert-python/commit/22579d1e66fef775fdc0f2c7f82b8d946fb98402))
* fetch current user via API ([#355](https://github.com/albert-labs/albert-python/issues/355)) ([8e68c6d](https://github.com/albert-labs/albert-python/commit/8e68c6d28da3466c5119ed920075309551520c15))
* get propertydata if exists ([#304](https://github.com/albert-labs/albert-python/issues/304)) ([ade6190](https://github.com/albert-labs/albert-python/commit/ade6190d6912d5cec3886d91471c945ad5ed9cc9))
* **HazardSymbol:** fixing hazard symbol status ([#519](https://github.com/albert-labs/albert-python/issues/519)) ([be64a05](https://github.com/albert-labs/albert-python/commit/be64a05e58cc104f43b749267528e4a8f7119eea))
* **identifiers:** ParameterGroupId ([#261](https://github.com/albert-labs/albert-python/issues/261)) ([5bf71a7](https://github.com/albert-labs/albert-python/commit/5bf71a7c667335283a2b738fc6322aa9419e0f28))
* **inventories:** perform delete before add ([#284](https://github.com/albert-labs/albert-python/issues/284)) ([59a6878](https://github.com/albert-labs/albert-python/commit/59a6878714b2eabfcbc5cfe95def416578df9c30))
* **inventory cas:** add cas amount target ([#294](https://github.com/albert-labs/albert-python/issues/294)) ([77ea2dd](https://github.com/albert-labs/albert-python/commit/77ea2dd925b3dc23cc380c42e133dfe9aa842482))
* **inventory:** add InventoryMergeModule enum for merge modules parameter ([#542](https://github.com/albert-labs/albert-python/issues/542)) ([91d990c](https://github.com/albert-labs/albert-python/commit/91d990caa6c4d09d2c01bb0786a7cbfe9c03060a))
* **inventory:** cast int values to str in InventorySpecValue validator ([#534](https://github.com/albert-labs/albert-python/issues/534)) ([dc0f0ad](https://github.com/albert-labs/albert-python/commit/dc0f0adb87777f77818fa60eeefc2be3cf72d242))
* **inventory:** expose inventory_on_hand on InventoryItem ([#536](https://github.com/albert-labs/albert-python/issues/536)) ([1a686cd](https://github.com/albert-labs/albert-python/commit/1a686cd5cd7d4371a1b3dfae71aae71ef4d9b078)), closes [#533](https://github.com/albert-labs/albert-python/issues/533)
* **inventory:** patch cas composition ([#305](https://github.com/albert-labs/albert-python/issues/305)) ([cf0d328](https://github.com/albert-labs/albert-python/commit/cf0d3286c95fdb61e61abc7ad119512284dede20))
* **inventory:** set get_all, search default sort_by to None ([d1de3e9](https://github.com/albert-labs/albert-python/commit/d1de3e95b5ae5857ba4b6f1516d1ff8d8889ba16))
* **inventory:** update CAS target/inventoryValue ([#273](https://github.com/albert-labs/albert-python/issues/273)) ([6282222](https://github.com/albert-labs/albert-python/commit/6282222b41f65acd84da10b379caa2c5de3b202e))
* **lists:** fixes pagination on lists collection ([5369b44](https://github.com/albert-labs/albert-python/commit/5369b4401441b7f6f12e24451ec1ab79bcb1186f))
* **lots:** handle create lot inventory-on-hand ([#333](https://github.com/albert-labs/albert-python/issues/333)) ([81c30a8](https://github.com/albert-labs/albert-python/commit/81c30a8057423b01c6a06e4c09cc1212dc5fa65e))
* **lots:** round inventoryOnHand to decimal places ([#330](https://github.com/albert-labs/albert-python/issues/330)) ([8723838](https://github.com/albert-labs/albert-python/commit/872383806cd532e7b0629315e898f3a56ab92ddb))
* **lots:** skip no-op patches in adjust() and transfer() ([#447](https://github.com/albert-labs/albert-python/issues/447)) ([09ea79c](https://github.com/albert-labs/albert-python/commit/09ea79ca27d442be83b66ea762ee4055fb521e1e))
* **lots:** support display ID format in ensure_lot_id ([#432](https://github.com/albert-labs/albert-python/issues/432)) ([a458ba4](https://github.com/albert-labs/albert-python/commit/a458ba4e9b62a62a4e02d5ad0f6bc27a7f3ecfa7))
* **lots:** support owner updates via update() ([#420](https://github.com/albert-labs/albert-python/issues/420)) ([50bbeb2](https://github.com/albert-labs/albert-python/commit/50bbeb2958c4d870a6408f2bb6f91944021f5655))
* **lots:** update inventory on hand correctly ([#282](https://github.com/albert-labs/albert-python/issues/282)) ([7af4d51](https://github.com/albert-labs/albert-python/commit/7af4d510c6b588a7e3841a38e5a6d923e4687da1))
* **lots:** update storage-location for lot ([#292](https://github.com/albert-labs/albert-python/issues/292)) ([eea4d33](https://github.com/albert-labs/albert-python/commit/eea4d33d4764802233d2815e80b56dea8dd99a9e))
* make ETT category optional ([#347](https://github.com/albert-labs/albert-python/issues/347)) ([5173e22](https://github.com/albert-labs/albert-python/commit/5173e22e7bf4f10f552ea6ed849c65b340276bec))
* merge conflicts ([544f30b](https://github.com/albert-labs/albert-python/commit/544f30bc97d5d407bb81e016fec07159419eecb7))
* **metadata:** metadata patch logic ([213c64d](https://github.com/albert-labs/albert-python/commit/213c64d3ea7f8995c535afdaea9bb240ca1beeae))
* **metadata:** replace list-valued metadata in a single update ([#558](https://github.com/albert-labs/albert-python/issues/558)) ([59dc385](https://github.com/albert-labs/albert-python/commit/59dc3850edea69cfaf90802a00c14e874af07a45))
* mkdocs config ([19c5b2f](https://github.com/albert-labs/albert-python/commit/19c5b2ff6eda92090d6baf64ef5ccf72ca981adb))
* notebook header content level ([#313](https://github.com/albert-labs/albert-python/issues/313)) ([64ef043](https://github.com/albert-labs/albert-python/commit/64ef043b4366d60e877f207ccdd329d34dea781d))
* **notebooks:** support CustomTemplateId (CTP) as a valid parentId ([#411](https://github.com/albert-labs/albert-python/issues/411)) ([ec7b17b](https://github.com/albert-labs/albert-python/commit/ec7b17bfcba074db8b1837f9c3eb741530d1f7d3))
* **notebooks:** update AttachesContent fields ([#315](https://github.com/albert-labs/albert-python/issues/315)) ([1844332](https://github.com/albert-labs/albert-python/commit/184433225ad3621c74288774cd7d212cc4213ae2))
* **pagination:** remove page_size from all collections ([#252](https://github.com/albert-labs/albert-python/issues/252)) ([fc50050](https://github.com/albert-labs/albert-python/commit/fc50050b79414c06fea952127d9af61b9f0db71a))
* **pagination:** stop pagination when same lastKey encountered ([#259](https://github.com/albert-labs/albert-python/issues/259)) ([17cca09](https://github.com/albert-labs/albert-python/commit/17cca09fe8a110da9c7bd636be752f031eeac8bf))
* **pagination:** support max_items and page_size in get_all, search ([5c5960e](https://github.com/albert-labs/albert-python/commit/5c5960e7a5639b489afb9fe521a628821ad57c2a))
* **parameter_groups:** assign enum IDs and fix search item model ([#485](https://github.com/albert-labs/albert-python/issues/485)) ([5d13cb9](https://github.com/albert-labs/albert-python/commit/5d13cb9efac31e847a4207c3a9b1f781131ceb54))
* **parameter-groups:** add missing timestamp DataType enum value ([#590](https://github.com/albert-labs/albert-python/issues/590)) ([e143327](https://github.com/albert-labs/albert-python/commit/e1433274ccabdeee3f152975ca394277dfb5ad5d))
* **parametergroups, tasks:** clear-then-update metadata list items ([07d0984](https://github.com/albert-labs/albert-python/commit/07d09847fb63e87017a2faea0abdb1431023c044))
* **parametergroups:** update validation datatype ([#303](https://github.com/albert-labs/albert-python/issues/303)) ([ad20280](https://github.com/albert-labs/albert-python/commit/ad20280ecde0731da03e944a0a3b74839be100a8))
* **parameters:** ensure get_or_create matches name exactly ([#380](https://github.com/albert-labs/albert-python/issues/380)) ([f741c8b](https://github.com/albert-labs/albert-python/commit/f741c8b7e1df6722db4e462300423c4374cf9f9c))
* params encoding centralized in Paginator ([1083b89](https://github.com/albert-labs/albert-python/commit/1083b8955954e04c2c535cd128de1aa1616f33a4))
* patch param on dt compare ([#262](https://github.com/albert-labs/albert-python/issues/262)) ([6d345e5](https://github.com/albert-labs/albert-python/commit/6d345e5e4df3245302ec65fc3024ef2d5af7f629))
* patch parametergroups metadata ([367e8eb](https://github.com/albert-labs/albert-python/commit/367e8eb1dc618c91310d32eba56fbba694ae8fb4))
* **patch:** leave unset fields untouched in update payloads ([#561](https://github.com/albert-labs/albert-python/issues/561)) ([0642e94](https://github.com/albert-labs/albert-python/commit/0642e94cd420f227a48be0f855918a11632cb714))
* perf improvements in formula addition ([#302](https://github.com/albert-labs/albert-python/issues/302)) ([126d50d](https://github.com/albert-labs/albert-python/commit/126d50d559bb51061dd29cd10cc06ca6908ef8f5))
* **property_data:** type storage_key and athena on PropertyData ([#570](https://github.com/albert-labs/albert-python/issues/570)) ([ede4a83](https://github.com/albert-labs/albert-python/commit/ede4a83b677f1d7cdc2698f27e1c3fc3f4dd11ca))
* **property-data:** accept numeric values in TaskPropertyCreate.value ([#564](https://github.com/albert-labs/albert-python/issues/564)) ([e23ce3e](https://github.com/albert-labs/albert-python/commit/e23ce3ee052c045dc1e6acf3f5239002ace5c179))
* **property-data:** make PTD search result trial optional ([#576](https://github.com/albert-labs/albert-python/issues/576)) ([aeffc1d](https://github.com/albert-labs/albert-python/commit/aeffc1d587362d479428ab9d7fcac17ea6660788))
* **property-data:** type PropertyDataResult.trial as Any ([#578](https://github.com/albert-labs/albert-python/issues/578)) ([34512bc](https://github.com/albert-labs/albert-python/commit/34512bc209c230e8c9909e440c6848d18e929b80))
* **propertydata:** column match regex ([#328](https://github.com/albert-labs/albert-python/issues/328)) ([2fbbe6e](https://github.com/albert-labs/albert-python/commit/2fbbe6e30b28639b517bbcb0083065db2a1ec019))
* **propertydata:** eval propertydata calculations ([#351](https://github.com/albert-labs/albert-python/issues/351)) ([cb3bc65](https://github.com/albert-labs/albert-python/commit/cb3bc65af5c8e441577f95d31f31fca923de865c))
* removed 'public' from the ProjectClass Enum as it isn't supported on platform anymore ([9617149](https://github.com/albert-labs/albert-python/commit/96171499d543019632d3fef31911cb763ec0a8ba))
* **resources:** tolerate None in Lot serializers and KetcherContent.data ([#563](https://github.com/albert-labs/albert-python/issues/563)) ([25ec5e7](https://github.com/albert-labs/albert-python/commit/25ec5e706bc5ce43ffb06b0b3784d08e57fba15c))
* revert lotId normalization, enforce custom-template id ([#283](https://github.com/albert-labs/albert-python/issues/283)) ([f197608](https://github.com/albert-labs/albert-python/commit/f197608644cf15f537cc8216972fb327fab755b3))
* **session:** handle None params in _encode_query_params ([#490](https://github.com/albert-labs/albert-python/issues/490)) ([2baea92](https://github.com/albert-labs/albert-python/commit/2baea9205177e15c1ea0c71c863e58b7412bf493))
* **sheets:** Add allowed cell type enums ([#334](https://github.com/albert-labs/albert-python/issues/334)) ([e8db233](https://github.com/albert-labs/albert-python/commit/e8db23386dc25e248a8848ed25be8d4b3adf14ce))
* **sheets:** add colSizeMode field to Sheet model ([#497](https://github.com/albert-labs/albert-python/issues/497)) ([b53604e](https://github.com/albert-labs/albert-python/commit/b53604e2c4e62b0eaf34f04ce2f1b26f3cb229e2))
* **sheets:** add flag to clear existing formulation ([#265](https://github.com/albert-labs/albert-python/issues/265)) ([b87303c](https://github.com/albert-labs/albert-python/commit/b87303c1bd026522c4f8c1fb41aa9bdfa4f93384))
* **sheets:** add is_column_right field to Sheet model ([#484](https://github.com/albert-labs/albert-python/issues/484)) ([75327db](https://github.com/albert-labs/albert-python/commit/75327dbcf95f8226c081efa23f102bd9503302fa))
* **sheets:** fix leftmost_pinned_column causing silent wksSequence drop ([#525](https://github.com/albert-labs/albert-python/issues/525)) ([55d3a32](https://github.com/albert-labs/albert-python/commit/55d3a32d878cf64c18b36e2586c54da28d40fcb0))
* **sheets:** fixing calculation for total cell in worksheet ([#413](https://github.com/albert-labs/albert-python/issues/413)) ([b2a2a2a](https://github.com/albert-labs/albert-python/commit/b2a2a2aa0c09d7c031291a72f440fc5a137dbcc5))
* **sheets:** refactor get_column + more ([#263](https://github.com/albert-labs/albert-python/issues/263)) ([c4941aa](https://github.com/albert-labs/albert-python/commit/c4941aaf5010fac30568caa85fef5b96a63b8641))
* **sheets:** scope recolor_column test to product design cells ([#500](https://github.com/albert-labs/albert-python/issues/500)) ([a37156b](https://github.com/albert-labs/albert-python/commit/a37156bcfcd9cd14ee59d9344110b9f2b6bbdbc9))
* **substance:** default catch_errors=True in get_by_id and relax count assertions ([#569](https://github.com/albert-labs/albert-python/issues/569)) ([6c22ba3](https://github.com/albert-labs/albert-python/commit/6c22ba38d12e4aac99dea3d9b24459ca6e6428f3))
* sync with main ([6de6c03](https://github.com/albert-labs/albert-python/commit/6de6c0341160256fd3014f849fd8277f34219b5d))
* **synthesis:** omit null smiles and default blockId on create ([#580](https://github.com/albert-labs/albert-python/issues/580)) ([0f63644](https://github.com/albert-labs/albert-python/commit/0f63644032d62c00fd122e0730888bb5c08c72b9))
* task search by dt and pg ([#301](https://github.com/albert-labs/albert-python/issues/301)) ([63f67b4](https://github.com/albert-labs/albert-python/commit/63f67b4d785ca48a99717d6dd900cb0a05d5ca45))
* **tasks:** add property blocks support to BatchTask ([#499](https://github.com/albert-labs/albert-python/issues/499)) ([e1b4fa0](https://github.com/albert-labs/albert-python/commit/e1b4fa0077e0d610b344c954956d40b2c426ed00))
* **tasks:** clear-then-update metadata list items ([59e1cd5](https://github.com/albert-labs/albert-python/commit/59e1cd5b89eeb2e4c561f9ac2e19f2fe161366f1))
* **tasks:** fix update-assigned bug when updating the assigned user ([#254](https://github.com/albert-labs/albert-python/issues/254)) ([e0ef3f5](https://github.com/albert-labs/albert-python/commit/e0ef3f5a4e0150bc2d25a45ac57784227677b8a1))
* **tasks:** search by projectId ([#310](https://github.com/albert-labs/albert-python/issues/310)) ([769998f](https://github.com/albert-labs/albert-python/commit/769998faf3825b00bbaacd90e81ee0a05b1f34cc))
* **tasks:** update tags ([#320](https://github.com/albert-labs/albert-python/issues/320)) ([238db69](https://github.com/albert-labs/albert-python/commit/238db6900c1183c95db1d06e30465b10b03288af))
* **total-cell:** fixing total cell ([b2a2a2a](https://github.com/albert-labs/albert-python/commit/b2a2a2aa0c09d7c031291a72f440fc5a137dbcc5))
* **units:** patch synonyms as item-level add/delete operations ([#559](https://github.com/albert-labs/albert-python/issues/559)) ([30e64c5](https://github.com/albert-labs/albert-python/commit/30e64c5412bdf39adde49ac5d570563513bf63b8))
* update customfields model ([#329](https://github.com/albert-labs/albert-python/issues/329)) ([c28d860](https://github.com/albert-labs/albert-python/commit/c28d86034b9de060a3340eff1d88a5d15d46ef05))
* update metadata does not remove pre-linked param ([#327](https://github.com/albert-labs/albert-python/issues/327)) ([b3a23ed](https://github.com/albert-labs/albert-python/commit/b3a23eda2197f35bfa1df3e63fd692d9d20e250d))
* update PropertyData model ([#312](https://github.com/albert-labs/albert-python/issues/312)) ([6bd6f69](https://github.com/albert-labs/albert-python/commit/6bd6f691a5ab18e0f7790c9abca2f7889f06c722))
* **users:** add witnesser field to User model ([#540](https://github.com/albert-labs/albert-python/issues/540)) ([0a95cda](https://github.com/albert-labs/albert-python/commit/0a95cda769a3ab2cb574b9cdbb42d38fa859642f))
* validate identifiers across collections ([#274](https://github.com/albert-labs/albert-python/issues/274)) ([6e768ce](https://github.com/albert-labs/albert-python/commit/6e768ceaa391a11dbbff28da4c8001b084b28f42))
* version bump ([1b8b461](https://github.com/albert-labs/albert-python/commit/1b8b461cd8d70d76f6b7ae2fd808dc9a60eed07b))
* **workflows:** allow Special parameters to have Intervals ([#508](https://github.com/albert-labs/albert-python/issues/508)) ([167b8d4](https://github.com/albert-labs/albert-python/commit/167b8d4dd54a02b5f3c114e7354c3a058202fe5f))
* **workflows:** back-fill prgPrmRowId when user supplies explicit setpoints ([#545](https://github.com/albert-labs/albert-python/issues/545)) ([7554481](https://github.com/albert-labs/albert-python/commit/75544815bcc98045474cf4b265c93609d3e121be))
* **workflows:** fixes issue when forming an interval with no unit ([#272](https://github.com/albert-labs/albert-python/issues/272)) ([8b560c7](https://github.com/albert-labs/albert-python/commit/8b560c7b2a0a6804eddcffd59eaf079f95286c15))
* **workflows:** handle duplicate detection and relax intervals validator ([#568](https://github.com/albert-labs/albert-python/issues/568)) ([93cba60](https://github.com/albert-labs/albert-python/commit/93cba607603f13b3d31979017120c179ab29fa96))


### Documentation

* add PR template and update contributing guide ([#277](https://github.com/albert-labs/albert-python/issues/277)) ([dda773c](https://github.com/albert-labs/albert-python/commit/dda773ce88e272640f93b84867ca4520a0e57706))
* **agents:** clarify conventional commit type usage ([7de25ba](https://github.com/albert-labs/albert-python/commit/7de25babcba56f8b646870a3dc3f02ea4a3583fb))
* **agents:** forbid manual version bumps; release-please owns versioning ([#551](https://github.com/albert-labs/albert-python/issues/551)) ([bfffd17](https://github.com/albert-labs/albert-python/commit/bfffd17591393d8ab7a9b9d4d0404f59b1aede04))
* **collections:** improve public method docstrings ([#392](https://github.com/albert-labs/albert-python/issues/392)) ([6888c9b](https://github.com/albert-labs/albert-python/commit/6888c9b0a694310fc3205f7247ed26852781bd17))
* drop duplicate changelog symlink ([#317](https://github.com/albert-labs/albert-python/issues/317)) ([62dad00](https://github.com/albert-labs/albert-python/commit/62dad0053799834fabc54329f8ad0d62ce0222b2))
* **enums:** document shared enums and add to SDK reference ([#496](https://github.com/albert-labs/albert-python/issues/496)) ([56b5452](https://github.com/albert-labs/albert-python/commit/56b5452b5fc60286ac4e077c8e94775c17756eb5)), closes [#489](https://github.com/albert-labs/albert-python/issues/489)
* **parameter_groups:** fix ParameterValue docstring accuracy ([#477](https://github.com/albert-labs/albert-python/issues/477)) ([5520198](https://github.com/albert-labs/albert-python/commit/552019893c28be5bf7b519a6dd2010c7b2a657b0))
* rename changelog, contributing ([1e4c608](https://github.com/albert-labs/albert-python/commit/1e4c608b862d54c9426dcb68a47be97ff9530fdc))
* rename changelog, contributing ([84c0bc2](https://github.com/albert-labs/albert-python/commit/84c0bc2b1f486b1b925151681e8283c76414e54c))
* rename changelog, contributing ([8fc12c5](https://github.com/albert-labs/albert-python/commit/8fc12c5b083ee95ab0763332f13517e8fc42ecbd))
* rename changelog, contributing ([5123369](https://github.com/albert-labs/albert-python/commit/51233697feca30ae716f027a9ffac75b793aee14))
* seperate resources from collections ([fa588f8](https://github.com/albert-labs/albert-python/commit/fa588f8b94a8eaa7e3737760b8e1de6cd9c3be4e))
* **tasks:** clarify task_id and albert_id search parameters ([#476](https://github.com/albert-labs/albert-python/issues/476)) ([df70231](https://github.com/albert-labs/albert-python/commit/df70231b4ff9ddc9b36326a2ff32a68773ac78a1))
* update branding assets and styles ([#353](https://github.com/albert-labs/albert-python/issues/353)) ([5c1c89d](https://github.com/albert-labs/albert-python/commit/5c1c89d85ba782a4f7153475aac580af64eb3896))
* update contributing guidelines ([d6b9244](https://github.com/albert-labs/albert-python/commit/d6b9244de8c64c4bae0d6a7e1283597fd5093d4b))
* update docs, readme, changelog, etc ([eeefa91](https://github.com/albert-labs/albert-python/commit/eeefa9182a350c08c8cdf9c7dd4cefd52b70cdfc))
* use mike for versioning ([40242c6](https://github.com/albert-labs/albert-python/commit/40242c63da04a5030038571bee4a97efa07ac2f7))

## [1.32.1](https://github.com/albert-labs/albert-python/compare/v1.32.0...v1.32.1) (2026-07-06)


### Bug Fixes

* **parameter-groups:** add missing timestamp DataType enum value ([#590](https://github.com/albert-labs/albert-python/issues/590)) ([e143327](https://github.com/albert-labs/albert-python/commit/e1433274ccabdeee3f152975ca394277dfb5ad5d))

## [1.32.0](https://github.com/albert-labs/albert-python/compare/v1.31.0...v1.32.0) (2026-07-03)


### Features

* **notebooks:** add append_blocks to safely add blocks ([#581](https://github.com/albert-labs/albert-python/issues/581)) ([87fddc0](https://github.com/albert-labs/albert-python/commit/87fddc0793e0d4da24af71a545f6eed4733728da))
* **session:** add configurable request timeout ([#572](https://github.com/albert-labs/albert-python/issues/572)) ([960f1de](https://github.com/albert-labs/albert-python/commit/960f1de714a852990548ee691f3886fa14fc9016))


### Bug Fixes

* **ci:** harden and upgrade claude-code workflows ([#586](https://github.com/albert-labs/albert-python/issues/586)) ([4a70bd3](https://github.com/albert-labs/albert-python/commit/4a70bd388ecfcfd220b10165ab632f967f065a20))
* **data-templates:** correct payload for datacolumn delete in update() ([#585](https://github.com/albert-labs/albert-python/issues/585)) ([a9cbe5d](https://github.com/albert-labs/albert-python/commit/a9cbe5d461ef12d6efdc29599386e1a9afaafcfe))
* **synthesis:** omit null smiles and default blockId on create ([#580](https://github.com/albert-labs/albert-python/issues/580)) ([0f63644](https://github.com/albert-labs/albert-python/commit/0f63644032d62c00fd122e0730888bb5c08c72b9))

## [1.31.0](https://github.com/albert-labs/albert-python/compare/v1.30.1...v1.31.0) (2026-07-01)


### Features

* **customfields:** date-and-datetime-type ([#577](https://github.com/albert-labs/albert-python/issues/577)) ([f3d2182](https://github.com/albert-labs/albert-python/commit/f3d21826b424ecf02b3f7fadf06151e525f154ba))


### Bug Fixes

* **property-data:** make PTD search result trial optional ([#576](https://github.com/albert-labs/albert-python/issues/576)) ([aeffc1d](https://github.com/albert-labs/albert-python/commit/aeffc1d587362d479428ab9d7fcac17ea6660788))
* **property-data:** type PropertyDataResult.trial as Any ([#578](https://github.com/albert-labs/albert-python/issues/578)) ([34512bc](https://github.com/albert-labs/albert-python/commit/34512bc209c230e8c9909e440c6848d18e929b80))
* **resources:** tolerate None in Lot serializers and KetcherContent.data ([#563](https://github.com/albert-labs/albert-python/issues/563)) ([25ec5e7](https://github.com/albert-labs/albert-python/commit/25ec5e706bc5ce43ffb06b0b3784d08e57fba15c))

## [1.30.1](https://github.com/albert-labs/albert-python/compare/v1.30.0...v1.30.1) (2026-06-29)


### Bug Fixes

* **patch:** leave unset fields untouched in update payloads ([#561](https://github.com/albert-labs/albert-python/issues/561)) ([0642e94](https://github.com/albert-labs/albert-python/commit/0642e94cd420f227a48be0f855918a11632cb714))
* **property_data:** type storage_key and athena on PropertyData ([#570](https://github.com/albert-labs/albert-python/issues/570)) ([ede4a83](https://github.com/albert-labs/albert-python/commit/ede4a83b677f1d7cdc2698f27e1c3fc3f4dd11ca))
* **property-data:** accept numeric values in TaskPropertyCreate.value ([#564](https://github.com/albert-labs/albert-python/issues/564)) ([e23ce3e](https://github.com/albert-labs/albert-python/commit/e23ce3ee052c045dc1e6acf3f5239002ace5c179))
* **substance:** default catch_errors=True in get_by_id and relax count assertions ([#569](https://github.com/albert-labs/albert-python/issues/569)) ([6c22ba3](https://github.com/albert-labs/albert-python/commit/6c22ba38d12e4aac99dea3d9b24459ca6e6428f3))
* **workflows:** handle duplicate detection and relax intervals validator ([#568](https://github.com/albert-labs/albert-python/issues/568)) ([93cba60](https://github.com/albert-labs/albert-python/commit/93cba607603f13b3d31979017120c179ab29fa96))

## [1.30.0](https://github.com/albert-labs/albert-python/compare/v1.29.1...v1.30.0) (2026-06-24)


### Features

* **chats:** add pageContext to ChatMessage (AI-637) ([#556](https://github.com/albert-labs/albert-python/issues/556)) ([301a7d9](https://github.com/albert-labs/albert-python/commit/301a7d94b9022e1a03370f5f0453c5f18747ec44))
* **smart_dataset:** add pagination to get_all ([#555](https://github.com/albert-labs/albert-python/issues/555)) ([c46096e](https://github.com/albert-labs/albert-python/commit/c46096e7f39ad97c8d5f239f3f6ae24e42c73429))


### Bug Fixes

* **custom_fields:** correct PATCH operation/oldValue handling for unset fields ([#557](https://github.com/albert-labs/albert-python/issues/557)) ([f4b5d76](https://github.com/albert-labs/albert-python/commit/f4b5d76faa26c105cc0156b0321f07914278c525))
* **exceptions:** make AlbertHTTPError picklable for Ray/multiprocessing contexts ([#560](https://github.com/albert-labs/albert-python/issues/560)) ([22579d1](https://github.com/albert-labs/albert-python/commit/22579d1e66fef775fdc0f2c7f82b8d946fb98402))
* **metadata:** replace list-valued metadata in a single update ([#558](https://github.com/albert-labs/albert-python/issues/558)) ([59dc385](https://github.com/albert-labs/albert-python/commit/59dc3850edea69cfaf90802a00c14e874af07a45))
* **units:** patch synonyms as item-level add/delete operations ([#559](https://github.com/albert-labs/albert-python/issues/559)) ([30e64c5](https://github.com/albert-labs/albert-python/commit/30e64c5412bdf39adde49ac5d570563513bf63b8))


### Documentation

* **agents:** forbid manual version bumps; release-please owns versioning ([#551](https://github.com/albert-labs/albert-python/issues/551)) ([bfffd17](https://github.com/albert-labs/albert-python/commit/bfffd17591393d8ab7a9b9d4d0404f59b1aede04))

## [1.29.1](https://github.com/albert-labs/albert-python/compare/v1.29.0...v1.29.1) (2026-06-17)


### Bug Fixes

* **attachments:** accept unknown category values gracefully ([#552](https://github.com/albert-labs/albert-python/issues/552)) ([96c701e](https://github.com/albert-labs/albert-python/commit/96c701e01cba3c1297b646a6bf276d33910e32d8))
* **chats:** add DOCUMENT_CITATION component type AI-655 ([#538](https://github.com/albert-labs/albert-python/issues/538)) ([e761ce4](https://github.com/albert-labs/albert-python/commit/e761ce40c3a1d1b0b8ab9028351a0bee3e000a36))
* **inventory:** add InventoryMergeModule enum for merge modules parameter ([#542](https://github.com/albert-labs/albert-python/issues/542)) ([91d990c](https://github.com/albert-labs/albert-python/commit/91d990caa6c4d09d2c01bb0786a7cbfe9c03060a))

## [1.29.0](https://github.com/albert-labs/albert-python/compare/v1.28.0...v1.29.0) (2026-06-12)


### Features

* **targets:** widen TargetParameter.value to operator/value-pair with legacy coercion ([#539](https://github.com/albert-labs/albert-python/issues/539)) ([ae1a99d](https://github.com/albert-labs/albert-python/commit/ae1a99de628035bc227eb87893afb60c5eee4364))

## [1.28.0](https://github.com/albert-labs/albert-python/compare/v1.27.0...v1.28.0) (2026-06-12)


### Features

* **activities:** add search() method ([#547](https://github.com/albert-labs/albert-python/issues/547)) ([c6f8572](https://github.com/albert-labs/albert-python/commit/c6f85722d0ff3ce3a27e23810a44b489470b5a1e))
* **parameter_groups:** support User-type special parameter values ([#543](https://github.com/albert-labs/albert-python/issues/543)) ([f1e3b79](https://github.com/albert-labs/albert-python/commit/f1e3b79e1779cd4faf74fce98f11a96e4bdb2672))
* **sheets:** row grouping, new column/row types, and fixes from PR [#267](https://github.com/albert-labs/albert-python/issues/267) ([#528](https://github.com/albert-labs/albert-python/issues/528)) ([3fe9642](https://github.com/albert-labs/albert-python/commit/3fe9642034a4d53c00e10bc402a5a21adb0cfb00))


### Bug Fixes

* **inventory:** cast int values to str in InventorySpecValue validator ([#534](https://github.com/albert-labs/albert-python/issues/534)) ([dc0f0ad](https://github.com/albert-labs/albert-python/commit/dc0f0adb87777f77818fa60eeefc2be3cf72d242))
* **inventory:** expose inventory_on_hand on InventoryItem ([#536](https://github.com/albert-labs/albert-python/issues/536)) ([1a686cd](https://github.com/albert-labs/albert-python/commit/1a686cd5cd7d4371a1b3dfae71aae71ef4d9b078)), closes [#533](https://github.com/albert-labs/albert-python/issues/533)
* **users:** add witnesser field to User model ([#540](https://github.com/albert-labs/albert-python/issues/540)) ([0a95cda](https://github.com/albert-labs/albert-python/commit/0a95cda769a3ab2cb574b9cdbb42d38fa859642f))
* **workflows:** back-fill prgPrmRowId when user supplies explicit setpoints ([#545](https://github.com/albert-labs/albert-python/issues/545)) ([7554481](https://github.com/albert-labs/albert-python/commit/75544815bcc98045474cf4b265c93609d3e121be))

## [1.27.0](https://github.com/albert-labs/albert-python/compare/v1.26.0...v1.27.0) (2026-06-08)


### Features

* **attachments:** add get_jurisdiction_codes and get_language_codes methods ([#524](https://github.com/albert-labs/albert-python/issues/524)) ([1f75c33](https://github.com/albert-labs/albert-python/commit/1f75c330904bcc74595c6581146ab1437d22d545))
* **tasks:** support updating project via tasks.update() ([#529](https://github.com/albert-labs/albert-python/issues/529)) ([16f4feb](https://github.com/albert-labs/albert-python/commit/16f4feb9011f95b4db6d68e2529d8d7cc5a5c8e3))


### Bug Fixes

* **custom_fields:** align customEntityCategory patch ops with new API semantics ([#526](https://github.com/albert-labs/albert-python/issues/526)) ([9692d8b](https://github.com/albert-labs/albert-python/commit/9692d8bb117280054d7a15d7953743adc97dafa5))
* **sheets:** fix leftmost_pinned_column causing silent wksSequence drop ([#525](https://github.com/albert-labs/albert-python/issues/525)) ([55d3a32](https://github.com/albert-labs/albert-python/commit/55d3a32d878cf64c18b36e2586c54da28d40fcb0))

## [1.26.0](https://github.com/albert-labs/albert-python/compare/v1.25.1...v1.26.0) (2026-06-05)


### Features

* support smart projects ([#523](https://github.com/albert-labs/albert-python/issues/523)) ([5d42f9a](https://github.com/albert-labs/albert-python/commit/5d42f9a302553eab6f4236bd3f2a28104d8e5523))


### Bug Fixes

* **HazardSymbol:** fixing hazard symbol status ([#519](https://github.com/albert-labs/albert-python/issues/519)) ([be64a05](https://github.com/albert-labs/albert-python/commit/be64a05e58cc104f43b749267528e4a8f7119eea))
* **sheets:** add colSizeMode field to Sheet model ([#497](https://github.com/albert-labs/albert-python/issues/497)) ([b53604e](https://github.com/albert-labs/albert-python/commit/b53604e2c4e62b0eaf34f04ce2f1b26f3cb229e2))

## [1.25.1](https://github.com/albert-labs/albert-python/compare/v1.25.0...v1.25.1) (2026-05-22)


### Bug Fixes

* **workflows:** allow Special parameters to have Intervals ([#508](https://github.com/albert-labs/albert-python/issues/508)) ([167b8d4](https://github.com/albert-labs/albert-python/commit/167b8d4dd54a02b5f3c114e7354c3a058202fe5f))

## [1.25.0](https://github.com/albert-labs/albert-python/compare/v1.24.0...v1.25.0) (2026-05-18)


### Features

* add support for get_data ([#488](https://github.com/albert-labs/albert-python/issues/488)) ([f6e5ae8](https://github.com/albert-labs/albert-python/commit/f6e5ae8249cec8b0acbe52866ea22657bec56185))
* **smartdatasets:** adds optional parent-id to smartdatasets for inheriting project ACL policy ([#506](https://github.com/albert-labs/albert-python/issues/506)) ([29600d1](https://github.com/albert-labs/albert-python/commit/29600d1387a34b5bacbfbaed38c0c9f1377f45ca))

## [1.24.0](https://github.com/albert-labs/albert-python/compare/v1.23.1...v1.24.0) (2026-05-18)


### Features

* **cas:** cap get_by_number partial-match pagination to avoid OpenSearch 500 ([#505](https://github.com/albert-labs/albert-python/issues/505)) ([cc4f03c](https://github.com/albert-labs/albert-python/commit/cc4f03cc8956a35c6b520041979767e798dfcf3d))
* **chats:** add TOOL_CALL and ERROR to ChatComponentType [SDK-50] ([#502](https://github.com/albert-labs/albert-python/issues/502)) ([5c21d50](https://github.com/albert-labs/albert-python/commit/5c21d50dac091c2a1788899eafb183f458bbe5da))
* **sheets:** add is_column_right field to Sheet model ([75327db](https://github.com/albert-labs/albert-python/commit/75327dbcf95f8226c081efa23f102bd9503302fa))
* support parent id on targets ([#504](https://github.com/albert-labs/albert-python/issues/504)) ([fcc40a0](https://github.com/albert-labs/albert-python/commit/fcc40a084e1982a14c5cb3492db3c5b9871d1f5d))


### Bug Fixes

* **data_templates:** workaround backend s3key bug in calculation update test ([#498](https://github.com/albert-labs/albert-python/issues/498)) ([669a1db](https://github.com/albert-labs/albert-python/commit/669a1dbe89025fe54a10d3b6cc610f7dd57ec4fc))
* **parameter_groups:** assign enum IDs and fix search item model ([#485](https://github.com/albert-labs/albert-python/issues/485)) ([5d13cb9](https://github.com/albert-labs/albert-python/commit/5d13cb9efac31e847a4207c3a9b1f781131ceb54))
* **sheets:** add is_column_right field to Sheet model ([#484](https://github.com/albert-labs/albert-python/issues/484)) ([75327db](https://github.com/albert-labs/albert-python/commit/75327dbcf95f8226c081efa23f102bd9503302fa))
* **sheets:** scope recolor_column test to product design cells ([#500](https://github.com/albert-labs/albert-python/issues/500)) ([a37156b](https://github.com/albert-labs/albert-python/commit/a37156bcfcd9cd14ee59d9344110b9f2b6bbdbc9))
* **tasks:** add property blocks support to BatchTask ([#499](https://github.com/albert-labs/albert-python/issues/499)) ([e1b4fa0](https://github.com/albert-labs/albert-python/commit/e1b4fa0077e0d610b344c954956d40b2c426ed00))


### Documentation

* **agents:** clarify conventional commit type usage ([7de25ba](https://github.com/albert-labs/albert-python/commit/7de25babcba56f8b646870a3dc3f02ea4a3583fb))
* **enums:** document shared enums and add to SDK reference ([#496](https://github.com/albert-labs/albert-python/issues/496)) ([56b5452](https://github.com/albert-labs/albert-python/commit/56b5452b5fc60286ac4e077c8e94775c17756eb5)), closes [#489](https://github.com/albert-labs/albert-python/issues/489)

## [1.23.1](https://github.com/albert-labs/albert-python/compare/v1.23.0...v1.23.1) (2026-05-12)


### Bug Fixes

* **session:** handle None params in _encode_query_params ([#490](https://github.com/albert-labs/albert-python/issues/490)) ([2baea92](https://github.com/albert-labs/albert-python/commit/2baea9205177e15c1ea0c71c863e58b7412bf493))

## [1.23.0](https://github.com/albert-labs/albert-python/compare/v1.22.1...v1.23.0) (2026-05-05)


### Features

* AsyncAlbert client, chat collections, and smart datasets ([#482](https://github.com/albert-labs/albert-python/issues/482)) ([e0efaeb](https://github.com/albert-labs/albert-python/commit/e0efaeb3dd8138cfa0fe6deb4b0e0bbaccbee57c))
* **data_columns:** add get_or_create method to DataColumnCollection ([#478](https://github.com/albert-labs/albert-python/issues/478)) ([d838de9](https://github.com/albert-labs/albert-python/commit/d838de932533ee866ceebab612f6a2f6927fd17d))
* **parameter_groups:** add required field to ParameterValue with patch support ([#480](https://github.com/albert-labs/albert-python/issues/480)) ([5101fc4](https://github.com/albert-labs/albert-python/commit/5101fc4a92c22ddf6d3f62dc8c7de51ef5b6a4af)), closes [#479](https://github.com/albert-labs/albert-python/issues/479)


### Bug Fixes

* **lots:** skip no-op patches in adjust() and transfer() ([#447](https://github.com/albert-labs/albert-python/issues/447)) ([09ea79c](https://github.com/albert-labs/albert-python/commit/09ea79ca27d442be83b66ea762ee4055fb521e1e))


### Documentation

* **parameter_groups:** fix ParameterValue docstring accuracy ([#477](https://github.com/albert-labs/albert-python/issues/477)) ([5520198](https://github.com/albert-labs/albert-python/commit/552019893c28be5bf7b519a6dd2010c7b2a657b0))
* **tasks:** clarify task_id and albert_id search parameters ([#476](https://github.com/albert-labs/albert-python/issues/476)) ([df70231](https://github.com/albert-labs/albert-python/commit/df70231b4ff9ddc9b36326a2ff32a68773ac78a1))

## [1.23.0-beta10](https://github.com/albert-labs/albert-python/compare/v1.23.0-beta9...v1.23.0-beta10) (2026-04-13)


### Bug Fixes

* **specs:** allowed float reference values ([#469](https://github.com/albert-labs/albert-python/issues/469)) ([0063dfb](https://github.com/albert-labs/albert-python/commit/0063dfb44ff3707bf8b4012b8c7e1c81d92dac11))

## [1.23.0-beta9](https://github.com/albert-labs/albert-python/compare/v1.23.0-beta8...v1.23.0-beta9) (2026-04-09)


### Features

* **chats:** add last_message_at field to ChatSession ([#467](https://github.com/albert-labs/albert-python/issues/467)) ([a25fa63](https://github.com/albert-labs/albert-python/commit/a25fa63f27cf4170de54de7d4a3d318b770ef7ce))

## [1.23.0-beta8](https://github.com/albert-labs/albert-python/compare/v1.22.1...v1.23.0-beta8) (2026-04-09)


### Features

* **chat:** add AsyncAlbert client with chat collections ([#414](https://github.com/albert-labs/albert-python/issues/414)) ([36017af](https://github.com/albert-labs/albert-python/commit/36017afeb29af2a9ff39158c64ecabae84925236))
* **chats:** add update, delete, flags, and session/folder enhancements ([#453](https://github.com/albert-labs/albert-python/issues/453)) ([8051289](https://github.com/albert-labs/albert-python/commit/8051289d55efd52fab7a0116b5ee94fe66f45475))


### Bug Fixes

* **chats:** allow clearing parentId by passing None to session update ([#465](https://github.com/albert-labs/albert-python/issues/465)) ([42d3943](https://github.com/albert-labs/albert-python/commit/42d39431967b89c11cf26f345aa6183edbcec1d0))
* **lots:** skip no-op patches in adjust() and transfer() ([#447](https://github.com/albert-labs/albert-python/issues/447)) ([09ea79c](https://github.com/albert-labs/albert-python/commit/09ea79ca27d442be83b66ea762ee4055fb521e1e))
* patch smartdatasets ([#422](https://github.com/albert-labs/albert-python/issues/422)) ([3741c17](https://github.com/albert-labs/albert-python/commit/3741c17268c493e5260c993af20ec1b0d469e1f0))
* **release:** configure pre-release behavior for next branch ([d90ff83](https://github.com/albert-labs/albert-python/commit/d90ff830eb45e137aa5be08508e9e7f71adad021))
* **smartdatasets:** add missing building state to smart datasets ([#442](https://github.com/albert-labs/albert-python/issues/442)) ([9620b11](https://github.com/albert-labs/albert-python/commit/9620b1184840dae995fc0580e8c2614be7f5bb9f))
* **smartdatasets:** allowed no-op patch ([#430](https://github.com/albert-labs/albert-python/issues/430)) ([db22f81](https://github.com/albert-labs/albert-python/commit/db22f8182c6baa4339c39117b8e3415fa656975d))
* **smartdatasets:** updated PATCH contract ([#426](https://github.com/albert-labs/albert-python/issues/426)) ([66e29e0](https://github.com/albert-labs/albert-python/commit/66e29e0488df813d30fcb7ab720e834f66b00ba9))


### Miscellaneous Chores

* prepare beta ([42a1580](https://github.com/albert-labs/albert-python/commit/42a15808e58e9d25380f4e1deda3acfb72c7c251))
* prepare beta ([0eaf60a](https://github.com/albert-labs/albert-python/commit/0eaf60a0b7f8f89a931026a576f9342aa20f69ad))
* prepare beta ([3f4bc0a](https://github.com/albert-labs/albert-python/commit/3f4bc0a8fb0eaadcf3c5b3bcbd0e17c0ea9d9d24))
* prepare beta ([#423](https://github.com/albert-labs/albert-python/issues/423)) ([41352b9](https://github.com/albert-labs/albert-python/commit/41352b9446aabd9a92dacc97e7c1bf98e5706cbf))
* prepare beta ([#455](https://github.com/albert-labs/albert-python/issues/455)) ([5658c1e](https://github.com/albert-labs/albert-python/commit/5658c1e119fd7bdddaa2980261d95c826eace554))

## [1.23.0-beta6](https://github.com/albert-labs/albert-python/compare/v1.23.0-beta5...v1.23.0-beta6) (2026-04-07)


### Features

* **chats:** add update, delete, flags, and session/folder enhancements ([#453](https://github.com/albert-labs/albert-python/issues/453)) ([ebde070](https://github.com/albert-labs/albert-python/commit/ebde0702763a7c3ef0a5c955a1a79243cc58b47d))

## [1.23.0-beta5](https://github.com/albert-labs/albert-python/compare/v1.22.1...v1.23.0-beta5) (2026-04-07)


### Features

* **chat:** add AsyncAlbert client with chat collections ([#414](https://github.com/albert-labs/albert-python/issues/414)) ([53d6400](https://github.com/albert-labs/albert-python/commit/53d6400f3059ee20473d242d4d6ccddb7ef02b94))


### Bug Fixes

* patch smartdatasets ([#422](https://github.com/albert-labs/albert-python/issues/422)) ([31d5be2](https://github.com/albert-labs/albert-python/commit/31d5be2ce04bb903f3be916dda52abc6cad19013))
* **release:** configure pre-release behavior for next branch ([5637cde](https://github.com/albert-labs/albert-python/commit/5637cde42be6d97faef958b4131b8b686df54025))
* **smartdatasets:** add missing building state to smart datasets ([#442](https://github.com/albert-labs/albert-python/issues/442)) ([fac7b85](https://github.com/albert-labs/albert-python/commit/fac7b8504236743d4bdab6864e97e262e77a35d1))
* **smartdatasets:** allowed no-op patch ([#430](https://github.com/albert-labs/albert-python/issues/430)) ([be2d70d](https://github.com/albert-labs/albert-python/commit/be2d70d58b78ae4d583d7023469827bd6fba4f9b))
* **smartdatasets:** updated PATCH contract ([#426](https://github.com/albert-labs/albert-python/issues/426)) ([f9bb9ab](https://github.com/albert-labs/albert-python/commit/f9bb9abe0ebcb14d2d85d26ee717d841b63b6686))


### Miscellaneous Chores

* prepare beta ([ca8edd3](https://github.com/albert-labs/albert-python/commit/ca8edd377fc0a1f413388baf989f03ae9eb6e944))
* prepare beta ([b84fdbe](https://github.com/albert-labs/albert-python/commit/b84fdbef650bbff5f321d9746e17458adc3966cc))
* prepare beta ([#423](https://github.com/albert-labs/albert-python/issues/423)) ([eac7437](https://github.com/albert-labs/albert-python/commit/eac7437987e9c35ff0bfe5998bd73c188a3fb2d7))
* prepare beta ([#455](https://github.com/albert-labs/albert-python/issues/455)) ([1e73bb1](https://github.com/albert-labs/albert-python/commit/1e73bb1827dcc41116350f8e8cd2078d6d2618c1))

## [1.22.1](https://github.com/albert-labs/albert-python/compare/v1.22.0...v1.22.1) (2026-04-07)


### Bug Fixes

* add parent id to btinsight and btdataset ([#449](https://github.com/albert-labs/albert-python/issues/449)) ([0d17179](https://github.com/albert-labs/albert-python/commit/0d17179c3a940e95ce337bd3975ae44b509e161e))
* **cas:** fix pagination for unfiltered listing and filtered search paths ([#445](https://github.com/albert-labs/albert-python/issues/445)) ([73f5418](https://github.com/albert-labs/albert-python/commit/73f5418e03977113078b689c36f3434732aedee5))
* **lots:** support display ID format in ensure_lot_id ([#432](https://github.com/albert-labs/albert-python/issues/432)) ([a458ba4](https://github.com/albert-labs/albert-python/commit/a458ba4e9b62a62a4e02d5ad0f6bc27a7f3ecfa7))
* **lots:** support owner updates via update() ([#420](https://github.com/albert-labs/albert-python/issues/420)) ([50bbeb2](https://github.com/albert-labs/albert-python/commit/50bbeb2958c4d870a6408f2bb6f91944021f5655))

## [1.22.0](https://github.com/albert-labs/albert-python/compare/v1.21.0...v1.22.0) (2026-03-20)


### Features

* **attachments:** add attachment update support ([#404](https://github.com/albert-labs/albert-python/issues/404)) ([e7c35c0](https://github.com/albert-labs/albert-python/commit/e7c35c0b0d6253e53c35e595560221e47d033631))
* **cas:** support updating CAS metadata ([#415](https://github.com/albert-labs/albert-python/issues/415)) ([389508f](https://github.com/albert-labs/albert-python/commit/389508fe1c2e649de3c682981823c879b13b6484))
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
