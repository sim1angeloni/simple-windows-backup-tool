import subprocess
import os
import json
import sys
import logging
import argparse
import time


SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__))
LOGGER_NAME = "backuplog"
LOGGER_FILE = "backup.log"
CONFIGURATION_FILE = "backup.json"
HOME_DIRECTORY_MARKER = "%HOME%"
log = logging.getLogger(LOGGER_NAME)


class Utilities:
    @staticmethod
    def get_env(envvar:str):
        """
        Get the value of an environment variable.

        Args:
            envvar (str): The name of the environment variable.

        Returns:
            str: The value of the environment variable.

        Raises:
            KeyError: If the environment variable does not exist.
        """

        var = os.environ.get(envvar, None)
        if not var:
            raise KeyError(f"The {envvar} environment variable does not exist")
        
        return var
        

    @staticmethod
    def convert_to_directory_path(path):
        """
        Convert a given directory to a non-absolute. Replaces the drive letter with the equivalent directory name (e.g., C: becomes C).

        Args:
            path (str): The path to be converted.

        Returns:
            str: The directory path.

        Notes:
            - If the input path is not absolute, it logs an error and returns None.
        """

        if os.path.isabs(path):
            return path.replace(":", "")
        else:
            log.error(f"Input path {path} is not an absolute path")
            return None


class Backup:
    def __init__(self) -> None:
        """
        Initialize the Backup object and configure logging & backup settings.
        """

        self._configure_logging(console_log=True, file_log=True)

        self.username = Utilities.get_env("USERNAME")       
        log.info(f"Username: {self.username}")

        self.computername = Utilities.get_env("COMPUTERNAME")
        log.info(f"Computer name: {self.computername}")

        self._configure_backup_script_from_file()
        log.setLevel(logging.DEBUG if self.debug else logging.INFO)
        log.info(f"Script configuration: debug={self.debug}, dryrun={self.dryrun}")

        self.backup_directory_full = os.path.join(self.backup_directory, self.username, self.computername)
        log.info(f"Backup root: {self.backup_directory}")
        log.info(f"Backup directory: {self.backup_directory_full}")


    def _configure_backup_script_from_file(self) -> None:
        """
        Read configuration settings from a JSON file and set class attributes.
        """

        config_file_path = os.path.join(SCRIPT_PATH, CONFIGURATION_FILE)
        log.info(f"Reading configuration file {config_file_path}...")
        with open(config_file_path, 'r') as config_file:
            config = json.load(config_file)

        home_directory = config.get("home_directory", None)
        if home_directory:
            home_directory = os.path.normpath(home_directory)
            
        self.source_directories = config.get("source_directories", [])
        self.source_directories = [os.path.normpath(path.replace(HOME_DIRECTORY_MARKER, os.path.join(home_directory, self.username))) for path in self.source_directories]
        log.info(f"Found {len(self.source_directories)} directories to backup")

        self.source_files = config.get("source_files", [])
        self.source_files = [os.path.normpath(path.replace(HOME_DIRECTORY_MARKER, os.path.join(home_directory, self.username))) for path in self.source_files]
        log.info(f"Found {len(self.source_files)} files to backup")

        self.backup_directory = config.get("backup_directory", None)
        if self.backup_directory is None:
            raise ValueError("Backup directory not found in the configuration file")

        self.backup_directory = os.path.normpath(self.backup_directory)
        self.debug = config.get("debug", False)
        self.dryrun = config.get("dryrun", True)
        self.notification = config.get("notification", False)
         

    def _backup_object(self, source_dir:str, destination_dir:str, filename = None) -> bool:
        """
        Perform a backup of a source directory (or file) to a destination directory (or file).

        Args:
            source_dir (str): The source directory path.
            destination_dir (str): The destination directory path.
            filename (str, optional): The filename to copy (if copying a file). Defaults to None (copying a directory).

        Notes:
            - Uses robocopy to perform the incremental backup.
            - MS documentation on robocopy: https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/robocopy
        """

        source_object = os.path.join(source_dir, filename) if filename else source_dir
        log.info(f"Starting backup of {source_object} in {destination_dir}...")

        robocopy_command = [
            "robocopy",
            source_dir,
            destination_dir,
        ]

        if filename:
            robocopy_command.append(filename)
        else:
            robocopy_command.append("/MIR") # Mirror the source directory to the destination

        robocopy_command.append("/Z")       # Copies files in restartable mode. In restartable mode, should a file copy be interrupted, robocopy can pick up where it left off rather than recopying the entire file.
        robocopy_command.append("/NP")      # Specifies that the progress of the copying operation (the number of files or directories copied so far) won't be displayed.
        robocopy_command.append("/NC")      # Specifies that file classes are not to be logged.
        robocopy_command.append("/NDL")     # Specifies that directory names are not to be logged.
        robocopy_command.append("/NJH")     # Specifies that there's no job header.
        robocopy_command.append("/W:10")    # Specifies the wait time between retries, in seconds. Reduced from the default 30 to 10.
        robocopy_command.append("/R:2")     # Specifies the number of retries on failed copies. By default it would retry 1mil times, which makes sense if the backup is on the network but doesn't for local drives.
        robocopy_command.append("/XJ")      # Excludes junction points, which are normally included by default.

        if self.dryrun:
            robocopy_command.append("/L")   # Specifies that files are to be listed only (and not copied, deleted, or time stamped).

        CREATE_NO_WINDOW = 0x08000000
        process = subprocess.Popen(robocopy_command, stdout=subprocess.PIPE, universal_newlines=True, creationflags=CREATE_NO_WINDOW)
        for line in iter(process.stdout.readline, ""):
            log.debug(line.strip())
        process.stdout.close()

        process.wait()
        if process.returncode >= 8:
            log.error(f"Backup of {source_object} failed")
            return False
        
        log.info(f"Backup of {source_object} completed successfully")
        return True


    def backup(self):
        """
        Perform the backup of source directories and files to the destination directory.

        Returns:
            bool: True if the backup completed successfully, False otherwise.
        """

        total_directories = len(self.source_directories)
        successfull_directories = 0 
        for source_dir in self.source_directories:
            source_path = Utilities.convert_to_directory_path(source_dir)
            if not source_path:
                continue

            destination_dir = os.path.join(self.backup_directory_full, source_path)
            if self._backup_object(source_dir, destination_dir):
                successfull_directories += 1
            
        total_files = len(self.source_files)
        successfull_files = 0
        for source_file in self.source_files:
            source_dir, filename = os.path.split(source_file)
            source_path = Utilities.convert_to_directory_path(source_dir)
            if not source_path:
                continue

            destination_dir = os.path.join(self.backup_directory_full, source_path)
            if self._backup_object(source_dir, destination_dir, filename):
                successfull_files += 1
        
        if successfull_directories != len(self.source_directories) or successfull_files != len(self.source_files):
            message = f"Errors during the backup procedure. {successfull_directories}/{total_directories} successfull directories. {successfull_files}/{total_files} successfull files"
            log.error(message)
            self._notify(message)
            return False
        
        message = "Backup of all directories and files completed successfully"
        log.info(message)
        self._notify(message)
        return True
    

    def _notify(self, message):
        if self.notification:
            from baloontip import WindowsBalloonTip
            w=WindowsBalloonTip(message, "Backup", os.path.join(SCRIPT_PATH, "backup.ico"), duration=5)


    def _configure_logging(self, console_log:bool, file_log:bool):
        """
        Configure logging for the script.

        Args:
            console_log (bool): Enable console logging.
            file_log (bool): Enable file logging.
        """

        log = logging.getLogger(LOGGER_NAME)
        log.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] - %(message)s')

        if console_log:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            log.addHandler(console_handler)

        if file_log:
            file_handler = logging.FileHandler(os.path.join(SCRIPT_PATH, LOGGER_FILE), mode='w')
            file_handler.setFormatter(formatter)
            log.addHandler(file_handler)


if __name__ == "__main__":  
    try:
        bck = Backup()
        sys.exit(0 if bck.backup() else 1)
    except Exception as e:
        log.error(f"exception: {e}")
        sys.exit(1)
