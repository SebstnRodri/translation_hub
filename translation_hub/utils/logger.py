import logging
import sys


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
	"""
	Configures and returns a logger.
	"""
	# Create a logger
	logger = logging.getLogger(name)
	logger.setLevel(level)

	# Create a handler and set its level
	handler = logging.StreamHandler(sys.stdout)
	handler.setLevel(level)

	# Create a formatter and add it to the handler
	formatter = logging.Formatter(
		"%(asctime)s - %(name)s - %(levelname)s - %(message)s",
		datefmt="%Y-%m-%d %H:%M:%S",
	)
	handler.setFormatter(formatter)

	# Add the handler to the logger
	if not logger.handlers:
		logger.addHandler(handler)

	return logger
