# Historical configuration templates

Each file is the `CONFIG_BLOCK` a released version shipped, extracted from its tag. They exist so
`test_config_loading.py` can replay every configuration this tool ever generated through the current parser,
which is what catches a renamed or removed setting that would reject an upgrading user's file.

| File | Released in |
| --- | --- |
| `1.6.conf` | v1.6 |
| `1.6.1.conf` | v1.6.1, v1.7, v1.8 |
| `1.9.conf` | v1.9, v1.9.1 |
| `1.9.2.conf` | v1.9.2, v1.9.3 |

Versions before v1.6 had no configuration file. Their settings lived in the source between the
`CONFIGURATION SECTION` markers, so there is nothing to replay for them.

Never edit these files. A released template is a historical fact. When a setting is renamed, add the old name
to `RETIRED_CONFIG_SETTINGS` instead.
