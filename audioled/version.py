import pkg_resources
import logging

logger = logging.getLogger(__name__)
_test_version = None
def get_version():
    try:
        v = pkg_resources.get_distribution('molecole').version
        split = v.split('.')
        if len(split) > 3:
            v = "{}.{}.{}{}".format(split[0], split[1], split[2], "a" + "".join(split[3:]))
        return v
    except Exception as e:
        logger.error("Error getting version")
        logger.error(e)
        if _test_version is not None:
            return _test_version
        return "Undefined"