import logging
import os
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

# Define enum information
@dataclass
class LogTypeInfo:
    directory_name: str
    logger_format: str
    max_count: int

# Define log type enum & populate with types
class LogType(Enum):
    DEFAULT = LogTypeInfo(directory_name="",
                          logger_format=logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
                          max_count=10)
    APPLICATION = LogTypeInfo(directory_name="application",
                              logger_format=logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
                              max_count=30)
    DEBUG = LogTypeInfo(directory_name="debug",
                        logger_format=logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
                        max_count=5)

    @property
    def directory_name(self):
        return self.value.directory_name
    
    @property
    def logger_format(self):
        return self.value.logger_format
    
    @property
    def max_count(self):
        return self.value.max_count

def setup_logging():   
    # Get directories and file paths sorted 
    application_dir = os.path.join(os.path.dirname(__file__), "..", "..", "logs", LogType.APPLICATION.directory_name)
    debug_dir = os.path.join(os.path.dirname(__file__), "..", "..", "logs", LogType.DEBUG.directory_name)
    os.makedirs(application_dir, exist_ok=True)
    os.makedirs(debug_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    application_logfile = os.path.join(application_dir, f"{timestamp}_application.log")
    debug_logfile = os.path.join(debug_dir, f"{timestamp}_debug.log")

    application_logger = logging.basicConfig(filename=application_logfile, level=logging.INFO)
    debug_logger = logging.basicConfig(filename=debug_logfile, level=logging.DEBUG)

    # Create handlers
    # Standard log file - INFO and above
    file_handler = logging.FileHandler(application_logger)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(LogType.APPLICATION.logger_format)

    # Debug log file - DEBUG and above
    debug_file_handler = logging.FileHandler(debug_logger)
    debug_file_handler.setLevel(logging.DEBUG)
    debug_file_handler.setFormatter(LogType.DEBUG.logger_format)

    # Console output - INFO and above
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(LogType.DEFAULT.logger_format)

    # Configure root logger
    logging.basicConfig(
        level=logging.DEBUG,  # Set to DEBUG to capture all levels
        handlers=[file_handler, debug_file_handler, console_handler]
    )

    # Create module logger
    logger = logging.getLogger(__name__)

    # Cleanup the logs
    cleanup_logs(app_logs = [f for f in os.listdir(application_dir) if f.endswith('application.log')],
                 log_dir = application_dir,
                 log_type = LogType.APPLICATION)
    cleanup_logs(app_logs = [f for f in os.listdir(debug_dir) if f.endswith('debug.log')],
                 log_dir = debug_dir,
                 log_type = LogType.DEBUG)

    return logger

def cleanup_logs(log_list: list[str], log_dir: str, log_type: LogType = None):            
        # Sort by timestamp (oldest first)
        sorted_logs = sorted(log_list, key=lambda filename: filename.split("_")[0])
        
        # Remove oldest logs until we have max_count or fewer
        logs_to_remove = sorted_logs[:-log_type.max_count]
        
        for log_file in logs_to_remove:
            file_path = os.path.join(log_dir, log_file)
            try:
                os.remove(file_path)
                print(f"Removed old log: {log_file}")
            except Exception as e:
                print(f"Error removing log {log_file}: {e}")
