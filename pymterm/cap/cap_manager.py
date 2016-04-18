import os
import imp
import sys
import unknown_cap

def get_cap_handler(name):
    print "cap:", name
    
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
        import traceback
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stderr)
        return unknown_cap
    finally:
        # Since we may exit via an exception, close fp explicitly.
        if fp:
            fp.close()
