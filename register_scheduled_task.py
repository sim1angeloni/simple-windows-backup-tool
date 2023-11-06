import os
import subprocess
import venv
import xml.etree.ElementTree as ET

# Configuration
VENV_NAME = "venv"
SCHEDULED_TASK_NAME = "ScheduledBackup"
REQUIREMENTS_FILE = "requirements.txt"
BACKUP_FILE = "backup.py"
SCHEDULED_TASK_CONFIG = "scheduled_task_config.xml"
SCHEDULED_TASK_CONFIG_OUT = "scheduled_task_config_generated.xml"

if __name__ == "__main__":  
    script_path = os.path.dirname(os.path.abspath(__file__))
    venv_path = os.path.join(script_path, VENV_NAME)
    requirements_path = os.path.join(script_path, "requirements.txt")

    # Check if the virtual environment directory exists
    if not os.path.exists(venv_path):
        print("Virtual environment directory not found. Creating...")
        builder = venv.EnvBuilder(with_pip=True)
        builder.create(venv_path)
        pip_path = os.path.join(VENV_NAME, "Scripts", "pip.exe")
        subprocess.run([pip_path, "install", "-r", requirements_path], shell=True, check=True)

    # Read the XML file and fixes the action tag
    input_xml_file = os.path.join(script_path, SCHEDULED_TASK_CONFIG)
    output_xml_file = os.path.join(script_path, SCHEDULED_TASK_CONFIG_OUT)
    with open(input_xml_file, "r", encoding="utf-16-le") as f_in:
        xml_content = f_in.read()

        xml_content = xml_content.replace("%PYTHON%", os.path.join(venv_path, "Scripts", "pythonw.exe"))
        xml_content = xml_content.replace("%SCRIPT%", os.path.join(script_path, BACKUP_FILE))

        with open(output_xml_file, "w", encoding="utf-16-le") as f_out:
            f_out.write(xml_content)

    # Register a new Scheduled Task
    task_command = [
        'schtasks',
        '/Create',
        '/TN', SCHEDULED_TASK_NAME,
        '/XML', output_xml_file
    ]

    subprocess.run(task_command, check=True)
