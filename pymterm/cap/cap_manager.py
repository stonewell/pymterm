import os
import imp
import sys
import unknown_cap
import logging

def get_cap_handler(name):
    logging.getLogger('cap_manager').debug("cap:%s", name)
    
    # Fast path: see if the module has already been imported.
    try:
        return sys.modules[name]
    except KeyError:
        pass

    # If any of the following calls raises an exception,
    # there's a problem we can't handle -- let the caller handle it.
    fp = None

    try:
        fp, pathname, description = imp.find_module(name, [os.path.dirname(__file__)])

        return imp.load_module(name, fp, pathname, description)
    except ImportError:
        return unknown_cap
    finally:
        # Since we may exit via an exception, close fp explicitly.
        if fp:
            fp.close()
