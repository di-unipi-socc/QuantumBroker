import os
import json
import inspect
import datetime
import threading

from enum import Enum



class LogLevel(Enum):
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4
    NONE = 5

LOG_LEVEL= LogLevel.INFO
LOG_FILE = None


def log(level: LogLevel, message: str, caller: int = None):
    message = str(message)
    
    pre = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {level.name} - "
    if caller is not None:
        caller_filename = os.path.basename(inspect.stack()[caller].filename)
        caller_function = inspect.stack()[caller].function
        caller_lineno = inspect.stack()[caller].lineno
    else:
        caller_filename = os.path.basename(inspect.stack()[1].filename)
        caller_function = inspect.stack()[1].function
        caller_lineno = inspect.stack()[1].lineno
        
    post = f" [{caller_filename}: {caller_function} - {caller_lineno}]"
    
    message = pre + message + post
    
    if level.value >= LOG_LEVEL.value:
        print(message, flush=True)
        if LOG_FILE is not None:
            LOG_FILE.write(message+"\n")
            LOG_FILE.flush()
        
def set_log_level(level: LogLevel | str | int):
    global LOG_LEVEL
    if type(level) != LogLevel:
        if type(level) == int:
            level = LogLevel(level)
        elif type(level) == str:
            level = LogLevel[level.upper()]
    LOG_LEVEL = level

def set_no_log():
    global LOG_LEVEL
    LOG_LEVEL = LogLevel.NONE
    
def set_log_all():
    global LOG_LEVEL
    LOG_LEVEL = LogLevel.DEBUG

def set_log_file(path: str):
    global LOG_FILE
    LOG_FILE = open(path, "a+")
    
def close_log_file():
    global LOG_FILE
    LOG_FILE.close()
    LOG_FILE = None
    
def get_log_level() -> LogLevel:
    return LOG_LEVEL

def get_log_file() -> open:
    return LOG_FILE

def get_log_file_path() -> str:
    return LOG_FILE.name if LOG_FILE is not None else None

def log_debug(message: str):
    log(LogLevel.DEBUG, message, caller=2)
    
def log_info(message: str):
    log(LogLevel.INFO, message, caller=2)
    
def log_warning(message: str):
    log(LogLevel.WARNING, message, caller=2)
    
def log_error(message: str):
    log(LogLevel.ERROR, message, caller=2)
    
def log_critical(message: str):
    log(LogLevel.CRITICAL, message, caller=2)
    
PERF_FILE_PATH = None
CURRENT_SLOT = None

DEFAULT_SLOT = "perfomance"

PERF_FILE_LOCK = threading.Lock()
CURRENT_SLOT_LOCK = threading.Lock()

class PerfEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set) or isinstance(obj, frozenset):
            return list(obj)
        return json.JSONEncoder.default(self, obj)

def set_perf_file(path: str):
    PERF_FILE_LOCK.acquire()
    global PERF_FILE_PATH
    PERF_FILE_PATH = path
    try:
        with open(path, "r") as file:
            pass
    except FileNotFoundError:
        with open(path, "w+") as file:
            json.dump({}, file)
            file.flush()
    PERF_FILE_LOCK.release()
    
def get_perf_file() -> str:
    PERF_FILE_LOCK.acquire()
    path = PERF_FILE_PATH
    PERF_FILE_LOCK.release()
    return path

def set_perf_slot(slot: str):
    CURRENT_SLOT_LOCK.acquire()
    global CURRENT_SLOT
    CURRENT_SLOT = slot
    CURRENT_SLOT_LOCK.release()
    
def get_perf_slot() -> str:
    CURRENT_SLOT_LOCK.acquire()
    slot = CURRENT_SLOT
    CURRENT_SLOT_LOCK.release()
    return slot

def perf_store(topic: str, key: str, value: any, slot: str = DEFAULT_SLOT):
    PERF_FILE_LOCK.acquire()
    path = PERF_FILE_PATH
    
    if path is None:
        PERF_FILE_LOCK.release()
        return
    
    with open(path, "r") as file:
        data = json.load(file)
        
    if slot not in data:
        data[slot] = {"timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        
    if topic not in data[slot]:
        data[slot][topic] = {}
        
    if key not in data[slot][topic]:
        data[slot][topic][key] = []
        
    data[slot][topic][key].append((value, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        
    with open(path, "w") as file:
        json.dump(data, file, cls=PerfEncoder)
        file.flush()
        
    PERF_FILE_LOCK.release()
    