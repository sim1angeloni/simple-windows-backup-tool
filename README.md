
# Simple Windows Backup Tool

## Description

A simple Python tool for performing incremental backups of directories and files for multiple users based on a configuration file.

## Table of Contents:

- [Simple Windows Backup Tool](#simple-windows-backup-tool)
  - [Description](#description)
  - [Table of Contents:](#table-of-contents)
  - [Reason](#reason)
  - [Features](#features)
  - [Requirements](#requirements)
  - [Installation](#installation)
  - [Usage](#usage)
  - [Configuration](#configuration)
  - [Scheduling the Backups](#scheduling-the-backups)
  - [Contributing](#contributing)
  - [License](#license)

## Reason

Frustrated with the limited backup options offered by Windows:
- Windows Backups (cloud-based and incomplete - cannot backup extra directories)
- File History (not easily configurable in Windows 11)
- Backup & Restore (just doing system's snapshots)

I decided to come up with my own simple solution for performing incremental backups of directories and files.

## Features

- Configurable through a JSON file.
- No installation required.
- Can run as a Scheduled Task.
- Optional notifications to the taskbar.
- Use `robocopy` ([Robust File Copy by Microsoft](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/robocopy)) under the hood.

## Requirements

- **python 3.x** (*tested with Python 3.11.6*)
- **pywin32** (*only if using notification*)

## Installation

 1. Download the latest stable [release](https://github.com/sim1angeloni/simple-windows-backup-tool/releases).

OR

 1.  Clone directly the repository:
    `git clone https://github.com/sim1angeloni/simple-windows-backup-tool.git` 

> This tool can be run from any location of your choice. You have the flexibility to save the files wherever you prefer.

## Usage

1. Configure the tool. See [Configuration](#configuration).

2. Set the `dryrun` mode to `false`.

3. To run the tool periodically as a Scheduled Task, see [Scheduling the Backups](#scheduling-the-backups).

OR 

3. To perform a manual run, use the following command:
`python -u \path\to\simple-windows-backup-tool\backup.py` 

## Configuration

Specify the backup configuration in a JSON file called `backup.json` that must exist in the same directory of the python script. Here is an example of a configuration file (provided with the repository/stable release):

    {
        "backup_directory": "D:\\backup",
        "home_directory": "C:\\Users",
        "source_directories": [
            "%HOME%\\Documents",
            "C:\\Path\\To\\Other\\Directory",
            "E:\\Path\\To\\Directory\\In\\Another\\Drive"
        ],
        "source_files": [
            "%HOME%\\.gitconfig"
        ],
        "debug": true,
        "dryrun": true,
        "notification": false
    }

- `backup_directory`: The root directory where backups will be stored.
The backups are divided by **user** and by **computer name** so the final directory will be `<backup_directory>\<username>\<computername>\`

- `source_directories`: An array of directories to be backed up.
You must specify the absolute paths to each directory. You can use `%HOME%` to avoid specifying the full path of the subdirectories inside the User's home directory. Using `%HOME%` will ensure that the script works for multiple users.

- `source_files`: An array of directories to be backed up. You can use `%HOME%` here too.
  
- `debug`: Set it to `true` to log the list of all files that will be interested by the backup. (default: true - *does not affect performances*)
  
- `dryrun`: Set it to `true` to simulate the backup without actually performing it. (default: true - *set it to false to activate the backup system*)
  
- `notification`: Set it to `true` to activate the notifications (default: false - you need to `pip install pywin32` to use this system)

## Scheduling the Backups

To automate your backups, you can set up the backup tool as a Scheduled Task on your system.

Execute the following script to create and register the scheduled task:
`python \path\to\simple-windows-backup-tool\register_scheduled_task.py`

This script configure the task and install it, specifically:
1. Create a Python virtual environment under the same `simple-windows-backup-tool` directory.
2. Configure the virtual environment with the necessary dependencies. See `requirements.txt`.
3. Configure the Scheduled Task reading & modifying the XML file `scheduled_task_config.xml` provided with the build.
4. Install the task `ScheduledBackup`.

After the task is installed you can configure it further:

1. Open your system's Task Scheduler and ensure that the task `ScheduledBackup` has been successfully created.
2. Right click on the task then click Properties to customize it.

By default the task is configured as following:
- Run only when the user is logged on.
- Run at 3 PM every day.
- Can run on demand.
- Stop the task if it runs longer than 1 hour.

Congratulations! You've now set up your Python backup script as a scheduled task, making regular backups a breeze. Your data will be protected without any manual intervention. 

If you have configured notifications, you will get a notification every time a backup is completed (either successfully or with errors).

## Contributing

Contributions are welcome! If you'd like to contribute to this project, please follow these steps:

1.  Fork the repository.
2.  Create a new branch for your feature or bug fix: `git checkout -b feature-name`.
3.  Make your changes and commit them.
4.  Push to your branch: `git push origin feature-name`.
5.  Create a pull request on GitHub.

You can [Report a bug](https://github.com/sim1angeloni/simple-windows-backup-tool/issues/new/choose) too.

## License

This project is licensed under the MIT - see the [LICENSE](https://github.com/sim1angeloni/simple-windows-backup-tool/blob/master/LICENSE) file for details.
