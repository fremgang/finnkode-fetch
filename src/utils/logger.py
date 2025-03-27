"""
Minimal logging utilities for the application.
"""
import logging
import sys
import os
from datetime import datetime

def setup_logger(name, log_file=None, level=logging.INFO):
    """
    Set up a logger with file and console handlers.
    
    Args:
        name (str): Logger name
        log_file (str, optional): Path to the log file
        level (int, optional): Logging level
        
    Returns:
        logging.Logger: Configured logger
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Create formatters
    simple_formatter = logging.Formatter('%(levelname)s - %(message)s')
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)
    
    return logger

def get_default_logger():
    """
    Get a default logger.
    
    Returns:
        logging.Logger: Configured default logger
    """
    return setup_logger("finnkode_fetcher")