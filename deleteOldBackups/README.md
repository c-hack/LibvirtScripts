# Delete old backups Script
Deletes old backups but keeps some as defined in the config.

## Config
This config is a json dict with the following keys:
| Key | Description |
| --- | ----------- |
| `backupConfig` | The path to the backup config as described in the [backup Readme](../backup/README.md). This is used to get the domains and paths to the backups. |
| `ignorePattern` | The python regex to compare all files to. If a file matches this, it is ignored. See https://docs.python.org/3.6/library/re.html |
| `keepAllFor` | The time in seconds to never delete any backup |
| `keepDailyFor` | The number of days to keep daily backups for |
| `keepWeeklyFor` | The number of weeks to keep weekly backups for |
| `keepMonthlyFor` | The number of months to keep monthly backups for |

Example:

    {
      "backupConfig": "/path/to/backupConfig",
      "ignorePattern": ".*\\.keep$",
      "keepAllFor": 3600,
      "keepDailyFor": 10,
      "keepWeeklyFor": 3,
      "keepMonthlyFor": 9
    }