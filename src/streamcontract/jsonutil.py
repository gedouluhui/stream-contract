"""JSON decoding helpers for unambiguous stream objects."""
import json


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key: ' + key)
        result[key] = value
    return result


def loads(text, **kwargs):
    """Decode JSON while rejecting duplicate keys in every nested object."""
    return json.loads(text, object_pairs_hook=unique_object, **kwargs)
