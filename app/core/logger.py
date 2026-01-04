from datetime import datetime, timezone
import traceback
import logging
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler
import json
import threading

'''
# логирование в json с трассировкой
logger.exception(f"Ошибка")
logger.error(f"Ошибка", exc_info=True)
logger.critical(f"Ошибка", exc_info=True)
        '''
class JsonFormatter(logging.Formatter):
    """Json формат логов"""
    def init(self):
        # Передаем None чтобы избежать проблем с форматом
        super().init(fmt=None, datefmt=None)

    def format(self, record: logging.LogRecord) -> str:
        now_utc = datetime.now(timezone.utc)
        timestamp = now_utc.strftime('%Y-%m-%dT%H:%M:%SZ')

        log_record = {
            "timestamp": timestamp,
            "level": record.levelname,
            "module": record.name,
        }

        message = record.getMessage()
        # Проверяем, не JSON ли это
        try:
            data = json.loads(message)
            log_record.update(data)
        except Exception:
            log_record["message"] = message

            # trace_id
        if hasattr(record, "trace_id"):
            log_record["trace_id"] = record.trace_id

        # Добавляем информацию об ошибке если есть (для уровней логирования: ERROR, CRITICAL)
        if record.exc_info and record.levelno >= logging.ERROR:
            exc_type, exc_value, exc_tb = record.exc_info

            log_record["error"] = {"type": exc_type.__name__, "message": str(exc_value)}
            log_record["stacktrace"] = "".join(traceback.format_exception(exc_type, exc_value, exc_tb) )

        return json.dumps(log_record, ensure_ascii=False, default=str)

class SmartTimedRotatingFileHandler(TimedRotatingFileHandler):
    """Ротирует логи в формате app.YYYY-MM-DD.log"""
    def __init__(self, filename, when="midnight", interval=1, backupCount=30, encoding="utf-8"):
        base, ext = Path(filename).stem, Path(filename).suffix
        self.baseFilenameNoExt = str(Path(filename).parent / base)
        self.ext = ext
        super().__init__(filename, when=when, interval=interval, backupCount=backupCount, encoding=encoding)
        self.suffix = "%Y-%m-%d"

    def rotation_filename(self, default_name: str) -> str:
        base, ext = self.baseFilenameNoExt, self.ext
        date_str = default_name.split(".")[-1]  # "2025-12-02"
        return f"{base}.{date_str}{ext}"

class LoggerConfig:
    """Универсальный класс для настройки логирования"""
    _lock = threading.Lock()  # защита от гонок при многопоточном вызове
    def __init__(
        self,
        base_dir: str | Path | None = None,
        log_dir: str | Path | None = None,
        log_file: str = "app.log",
        log_level: str = "INFO",
        log_format: str = "%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        when: str = "midnight",
        interval: int = 1,
        backup_count: int = 30,
        encoding: str = "utf-8",
        console_output: bool = True,
        use_json: bool = False
    ):
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).resolve().parent
        self.log_dir = self._resolve_log_dir(log_dir)
        self.log_file = log_file
        self.log_level = log_level.upper()
        self.log_format = log_format
        self.when = when
        self.interval = interval
        self.backup_count = backup_count
        self.encoding = encoding
        self.console_output = console_output    # флаг для вывода в консоль
        self.use_json = use_json                # флаг для json логов
        self.app_logger_name = self.log_file.replace(".log", "")    # имя для файла с логами
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"Не удалось создать директорию для логов {self.log_dir}: {e}")
        self.logger = self.get_logger(self.app_logger_name)


    def _resolve_log_dir(self, log_dir: str | Path | None = None) -> Path:
        '''определям путь к директории для логов'''
        project_root = Path.cwd() # корень проекта
        if log_dir is None:
            return project_root / "logs"    # если не передан, то берет по умолчанию папку проекта/ + logs
        elif Path(log_dir).is_absolute():
            return Path(log_dir)            # если передан асолютный путь, то берет его
        else:
            return project_root / log_dir   # если передана папку, то берет корень проекта + папка

    def setup_logger(self) -> None:
        """Настройка логирования с защитой от повторной инициализации"""
        with self._lock:
            root = logging.getLogger()
            if root.handlers:
                return  # уже настроено

            log_path = self.log_dir / self.log_file
            # Выбираем форматтер
            formatter = JsonFormatter() if self.use_json else logging.Formatter(self.log_format)
            # Файловый обработчик с ротацией
            file_handler = SmartTimedRotatingFileHandler(
                filename=str(log_path),
                when=self.when,
                interval=self.interval,
                backupCount=self.backup_count,
                encoding=self.encoding
            )
            file_handler.setFormatter(formatter)
            handlers = [file_handler]
            if self.console_output:
                console_handler = logging.StreamHandler()
                console_handler.setFormatter(formatter)
                handlers.append(console_handler)
            for h in handlers:
                root.addHandler(h)
            root.setLevel(getattr(logging, self.log_level, logging.INFO))
            self.logger.info(repr(self))

    def get_logger(self, name: str | None = None) -> logging.Logger:
        """Именованный логгер (по умолчанию __name__)"""
        logger = logging.getLogger(name or __name__)
        #logger.propagate = False  # избегаем дублирования в root
        return logger

    def get_log_path(self) -> Path:
        'путь '
        return self.log_dir / self.log_file

    def __repr__(self) -> str:
        return (f"LoggerConfig(log_dir={self.log_dir}, log_file={self.log_file}, "
                f"level={self.log_level}, console={self.console_output}, use_json={self.use_json})")



