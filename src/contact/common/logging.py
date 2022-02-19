import logging
import sys

_logger = logging.getLogger(__name__)

def setup_logging(loglevel):
    """Setup basic logging

    Args:
      loglevel (int): minimum loglevel for emitting messages
    """
    if loglevel == logging.DEBUG:
      logformat = "[%(asctime)s] %(levelname)s: %(name)s:%(message)s"
    else:
      logformat = "[%(asctime)s] (%(levelname)s) %(message)s"
    logging.basicConfig(
        level=loglevel, stream=sys.stdout, format=logformat, datefmt="%Y-%m-%d %H:%M:%S"
    )
