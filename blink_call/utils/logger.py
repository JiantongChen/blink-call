import logging

LEVEL_MAPPING = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}


class StreamHandlerColorFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[94m",
        "INFO": "\033[92m",
        "WARNING": "\033[93m",
        "ERROR": "\033[91m",
        "CRITICAL": "\033[95m",
    }
    RESET = "\033[0m"

    def format(self, record):
        # Apply color to the final formatted message
        message = super().format(record)
        color = self.COLORS.get(record.levelname, self.RESET)
        return f"{color}{message}{self.RESET}"


class Logger:
    handlers = []  # class variable for shared handlers

    @classmethod
    def set_handlers(cls, log_path=None):
        cls.handlers = []

        # Define log info format
        log_format = "[%(asctime)s] [%(filename)s:%(lineno)d] %(name)s - %(levelname)s : %(message)s"
        datefmt = "%Y-%m-%d %H:%M:%S"

        # File handler
        if log_path is not None:
            fh = logging.FileHandler(log_path, encoding="utf-8")
            fh.setFormatter(logging.Formatter(fmt=log_format, datefmt=datefmt))
            cls.handlers.append(fh)

        # Stream handler with color
        ch = logging.StreamHandler()
        ch.setFormatter(StreamHandlerColorFormatter(fmt=log_format, datefmt=datefmt))
        cls.handlers.append(ch)

    def __new__(cls, name=__name__, level="info"):
        """Return a logger instance directly when creating Logger."""
        # Get or create logger
        logger = logging.getLogger(name)
        logger.setLevel(LEVEL_MAPPING.get(level.lower(), logging.DEBUG))
        logger.propagate = False  # Prevent logs from propagating to root

        # Attach shared handlers if not already attached
        logger.handlers = []
        for h in cls.handlers:
            logger.addHandler(h)

        return logger
