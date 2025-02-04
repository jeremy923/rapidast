import copy
import logging
from pprint import pformat


class RapidastConfigModel:
    def __init__(self, conf=None):
        if conf is None:
            conf = {}

        self.conf = conf

    def get(self, path, default=None):
        """Walks `path` in the config, and returns the corresponding value
        - If the path does not exist, returns `default`
        """

        path = path_to_list(path)
        walk = self.conf
        try:
            for e in path:
                walk = walk.get(e, default)
            return walk
        except KeyError:
            pass
        except AttributeError:
            pass
        # Failed to iterate until the end: the path does not exist
        logging.debug(
            f"Config path {path} was not found. Returning default '{default}'"
        )
        return default

    def exists(self, path):
        """Returns true if `path` exists in configuration
        Even if the value is None
        """
        path = path_to_list(path)
        tmp = self.conf
        try:
            for key in path:
                tmp = tmp[key]
            return True
        except KeyError:
            return False

    def set(self, path, value):
        """Set the value pointed by `path` to `value`
        - Create the path if necessary
        - Discard previous value
        - Override (with a warning) path if necessary (if something in the path was not a dict)
        """
        path = path_to_list(path)
        walk = self.conf

        # Walk the path, create subdictionary if needed
        for key in path[:-1]:
            tmp = walk.get(key)
            if not tmp:
                tmp = walk[key] = {}
            if not isinstance(tmp, dict):
                logging.warning(
                    f"RapidastConfigModel.set: overriding entry {key} in {path} from {type(tmp)} to dict"
                )
                walk[key] = {}

            walk = walk[key]
        walk[path[-1]] = value

    def merge(self, merge, preserve=False, root=None):
        """Recursively merge `merge` into the configuration.
        - if `preserve` is True, in case of value collision, keep previous
        - if `root`, then merge `merge` into `self.conf[root...]`
        """

        if not merge:
            return
        if not isinstance(merge, dict):
            raise TypeError(
                f"RapidastConfigModel.merge: merge must be a dict (was: {type(merge)})"
            )

        root = path_to_list(root)

        if root and not self.exists(root):
            self.set(root, {})

        # get to the root of the merging
        sub_conf = self.get(root)

        deep_dict_merge(sub_conf, merge, preserve)

    def __repr__(self):
        return pformat(vars(self), indent=4, width=1)


## BELOW: utility functions


def path_to_list(path):
    """Ensure that a path is a list
    - if it's a list, keep it as it is
    - if it's a string, split by '.'
    - Otherwise, just try to convert to list

    e.g.:
    - path_to_list('abc') => ['abc']
    - path_to_list('a.b.c') => ['a','b','c']
    - path_to_list(('a','b','c')) => ['a','b','c']
    """

    if isinstance(path, str):
        path = path.split(".")
    return list(path)


def deep_dict_merge(dest, merge, preserve=False):
    """Modifies and returns the 'dest' dict, after merging 'merge' into it

    Deep (recursively) merge the dict "merge" into "dest".
    Recursively means that if a key exist in both dicts, and they both point
    to a dict, the merge will recurse instead of overwriting.
    Think of it as a recursive `dest += merge`

    In case of key collision
    (a key exists in both dicts, but at most 1 is a dict):
    - if preserve is True: the value taken from `dest` is favored
    - if preserve is False: the value taken from `merge` is favored

    Notes/Warnings/Limitations:
    - `dest` is modified during the process
    - it can't be used to remove an entry, even with preserve=False
    - the copy is done using deepcopy() to prevent accidental cross-modification

    Example:
    deep_dict_merge({'key1':'val1', 'key2':'val2'}, {'key2':'newVal'}, False)
     - Will modify the first argument to {'key1':'val1', 'key2':'newVal'}
     - And return it

    Internal :
     - for each key of `merge`:
        - if no correspondance in `dest`: value is imported
        - if both are dicts: descend in both recursively
        - else: copy or preserve, according to `preserve`
    """

    if merge is None:
        return dest

    if not isinstance(dest, dict) or not isinstance(merge, dict):
        logging.warning(
            "[deep_dict_merge]: one of the argument was NOT a dictionary. "
            "The function was likely called incorrectly and may result in incorrect behavior"
        )

    for key, val in merge.items():
        if not dest.get(key):
            dest[key] = copy.deepcopy(val)
        elif isinstance(dest[key], dict) and isinstance(val, dict):
            deep_dict_merge(dest[key], val, preserve)
        elif not preserve:
            dest[key] = copy.deepcopy(val)
    return dest
