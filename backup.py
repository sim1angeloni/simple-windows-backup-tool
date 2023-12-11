import subprocess
import os
import json
import sys
import logging
import shutil
from datetime import datetime


# Configuration
LOGGER_NAME = "backuplog"
LOGGER_FILE = "backup.log"
CONFIGURATION_FILE = "backup.json"
ROTATION_FILE = "rotation.json"
NOTIFICATION_ICON_FILE = "backup.ico"
HOME_DIRECTORY_MARKER = "%HOME%"


class RotationFile:
    def __init__(self, file_path:str) -> None:
        self.file_path = file_path
        self.date = 0
        self.backups_list = []


    def exists(self) -> bool:
        return os.path.exists(self.file_path)


    def save(self) -> None:
        data = {
            "date": self.date,
            "list": self.backups_list
        }

        with open(self.file_path, "w") as f:
            json.dump(data, f, ensure_ascii=True, indent=4)


    def load(self) -> None:
        with open(self.file_path, "r") as f:
            content = json.load(f)
            self.date = content["date"]
            self.backups_list = content["list"]


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
            return None


class Backup:
    def __init__(self, configuration_path:str, log_path:str, resources_path:str = "") -> None:
        """
        Initialize the Backup object and configure logging & backup settings.

        Args:
            configuration_path (str): The directory that contains the configuration file.
            log_path (str): The directory where the log file will be written.
            resources_path (str): The directory that contains the ico file.
        """

        self.configuration_path = configuration_path
        self.log_path = log_path
        self.resources_path = resources_path
        self.log = self._configure_logging(console_log=True, file_log=True)

        self.username = Utilities.get_env("USERNAME")       
        self.log.info(f"Username: {self.username}")

        self.computername = Utilities.get_env("COMPUTERNAME")
        self.log.info(f"Computer name: {self.computername}")

        self._configure_backup_script_from_file()
        self.log.setLevel(logging.DEBUG if self.debug else logging.INFO)
        self.log.info(f"Script configuration: debug={self.debug}, dryrun={self.dryrun}")

        self.backup_directory = os.path.normpath(os.path.join(self.backup_root, self.backup_name))
        self.backup_directory_full = os.path.join(self.backup_directory, self.username, self.computername)
        self.log.info(f"Backup root: {self.backup_directory}")
        self.log.info(f"Backup directory: {self.backup_directory_full}")


    def _configure_backup_script_from_file(self) -> None:
        """
        Read configuration settings from a JSON file and set class attributes.
        """

        config_file_path = os.path.join(self.configuration_path, CONFIGURATION_FILE)
        self.log.info(f"Reading configuration file {config_file_path}...")
        with open(config_file_path, 'r') as config_file:
            config = json.load(config_file)

        home_directory = config.get("home_directory", None)
        if home_directory:
            home_directory = os.path.normpath(home_directory)
            
        self.source_directories = config.get("source_directories", [])
        self.source_directories = [os.path.normpath(path.replace(HOME_DIRECTORY_MARKER, os.path.join(home_directory, self.username))) for path in self.source_directories]
        self.log.info(f"Found {len(self.source_directories)} directories to backup")

        self.exclude_directories = config.get("exclude_directories", [])
        self.exclude_directories = [os.path.normpath(path.replace(HOME_DIRECTORY_MARKER, os.path.join(home_directory, self.username))) for path in self.exclude_directories]
        self.log.info(f"Found {len(self.exclude_directories)} directories to exclude")

        self.exclude_files = config.get("exclude_files", [])
        self.exclude_files = [os.path.normpath(path.replace(HOME_DIRECTORY_MARKER, os.path.join(home_directory, self.username))) for path in self.exclude_files]
        self.log.info(f"Found {len(self.exclude_files)} files to exclude")

        self.source_files = config.get("source_files", [])
        self.source_files = [os.path.normpath(path.replace(HOME_DIRECTORY_MARKER, os.path.join(home_directory, self.username))) for path in self.source_files]
        self.log.info(f"Found {len(self.source_files)} files to backup")

        self.backup_root = config.get("backup_root", None)
        if self.backup_root is None:
            raise ValueError("Backup root directory not found in the configuration file")
        
        self.backup_name = config.get("backup_name", None)
        if self.backup_name is None:
            raise ValueError("Backup name not found in the configuration file")
        
        rotation = config.get("rotation", {})
        self.rotation_enabled = rotation.get("enabled", False)
        self.rotation_interval = rotation.get("interval", 30)
        self.rotation_interval = max(self.rotation_interval, 1)
        self.rotation_max_saved = rotation.get("max_saved", 5)
        self.rotation_max_saved = max(self.rotation_max_saved, 1)
        
        self.debug = config.get("debug", False)
        self.dryrun = config.get("dryrun", True)
        self.notification = config.get("notification", False)
         

    def _backup_object(self, source_dir:str, destination_dir:str, filename:str = None, exclude_directories:list = None, exclude_files:list = None) -> bool:
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
        self.log.info(f"Starting backup of {source_object} in {destination_dir}...")

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

        if not filename:
            if exclude_directories:
                robocopy_command.append("/XD")  # Excludes files that match the specified names or paths.
                robocopy_command.extend(exclude_directories)

            if exclude_files:
                robocopy_command.append("/XF")  # Excludes directories that match the specified names and paths.
                robocopy_command.extend(exclude_files)

        if self.dryrun:
            robocopy_command.append("/L")   # Specifies that files are to be listed only (and not copied, deleted, or time stamped).

        CREATE_NO_WINDOW = 0x08000000
        process = subprocess.Popen(robocopy_command, stdout=subprocess.PIPE, universal_newlines=True, creationflags=CREATE_NO_WINDOW)
        for line in iter(process.stdout.readline, ""):
            self.log.debug(line.strip())
        process.stdout.close()

        process.wait()
        if process.returncode >= 8:
            self.log.error(f"Backup of {source_object} failed")
            return False
        
        self.log.info(f"Backup of {source_object} completed successfully")
        return True


    def _rotate(self) -> None:
        if not self.rotation_enabled or self.dryrun:
            return
        
        now_time_epoch = int(datetime.utcnow().replace(second=0, microsecond=0).timestamp())

        self.rotation_file_path = os.path.join(self.backup_directory, ROTATION_FILE)
        rotation_file = RotationFile(self.rotation_file_path)
        if not rotation_file.exists():
            rotation_file.date = now_time_epoch
            rotation_file.save()
            return
        
        rotation_file.load()

        saved_time_epoch = rotation_file.date
        saved_datetime = datetime.utcfromtimestamp(saved_time_epoch)
        current_datetime = datetime.utcfromtimestamp(now_time_epoch)

        days_elapsed = (current_datetime - saved_datetime).days
        if days_elapsed < self.rotation_interval:
            rotation_file.date = now_time_epoch
            rotation_file.save()
            return
        
        backups = sorted(rotation_file.backups_list)
        try:
            while len(backups) >= self.rotation_max_saved:
                oldest_backup_name = backups.pop(0)
                oldest_backup_path = os.path.join(self.backup_root, oldest_backup_name)
                if os.path.exists(oldest_backup_path):
                    shutil.rmtree(oldest_backup_path, ignore_errors=True)
            
            newest_backup_name = f"{self.backup_name}_{now_time_epoch}"
            newest_backup_path = os.path.join(self.backup_directory, newest_backup_name)
            os.system(f'move /Y "{self.backup_directory}" "{newest_backup_path}"')
            backups.append(newest_backup_name)
        finally:
            rotation_file.date = now_time_epoch
            rotation_file.backups_list = backups
            rotation_file.save()


    def backup(self) -> bool:
        """
        Perform the backup of source directories and files to the destination directory.

        Returns:
            bool: True if the backup completed successfully, False otherwise.
        """

        self._rotate()

        total_directories = len(self.source_directories)
        successfull_directories = 0 
        for source_dir in self.source_directories:
            source_path = Utilities.convert_to_directory_path(source_dir)
            if not source_path:
                self.log.error(f"Input path {source_path} is not an absolute path")
                continue

            destination_dir = os.path.join(self.backup_directory_full, source_path)
            if self._backup_object(source_dir, destination_dir, 
                                   exclude_directories=[path for path in self.exclude_directories if path.startswith(source_dir)],
                                   exclude_files=[path for path in self.exclude_files if path.startswith(source_dir)]):
                successfull_directories += 1
            
        total_files = len(self.source_files)
        successfull_files = 0
        for source_file in self.source_files:
            source_dir, filename = os.path.split(source_file)
            source_path = Utilities.convert_to_directory_path(source_dir)
            if not source_path:
                self.log.error(f"Input path {source_path} is not an absolute path")
                continue

            destination_dir = os.path.join(self.backup_directory_full, source_path)
            if self._backup_object(source_dir, destination_dir, filename):
                successfull_files += 1
        
        if successfull_directories != len(self.source_directories) or successfull_files != len(self.source_files):
            message = f"Errors during the backup procedure. {successfull_directories}/{total_directories} successfull directories. {successfull_files}/{total_files} successfull files"
            self.log.error(message)
            self._notify(message)
            return False
        
        message = "Backup of all directories and files completed successfully"
        self.log.info(message)
        self._notify(message)
        return True
    

    def _notify(self, message):
        if self.notification:
            from notification import WindowsBalloonTip
            w=WindowsBalloonTip(message, "Backup", os.path.join(self.resources_path, NOTIFICATION_ICON_FILE), duration=5)


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
            file_handler = logging.FileHandler(os.path.join(self.log_path, LOGGER_FILE), mode='w')
            file_handler.setFormatter(formatter)
            log.addHandler(file_handler)

        return log


if __name__ == "__main__":  
    try:
        script_path = os.path.dirname(os.path.abspath(__file__))
        bck = Backup(script_path, script_path, script_path)
        sys.exit(0 if bck.backup() else 1)
    except Exception as e:
        print(f"exception: {e}")
        sys.exit(1)
