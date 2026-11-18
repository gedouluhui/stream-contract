"""Deliberately narrow Chat Completions TEXT profile, not full API compliance."""
import json
from .sse import parse_sse
from .numbers import parse_float, parse_integer


def _reject_constant(_):
    raise ValueError('non-finite JSON')


def collect_chat(chunks) -> dict:
    choices, usage = {}, None
    done = False

    def result(status, diagnostic=None):
        return {'status': status, 'choices': [choices[i].copy() for i in sorted(choices)],
                'usage': usage, 'diagnostic': diagnostic}

    try:
        events = parse_sse(chunks)
    except (TypeError, ValueError):
        return result('profile_error', 'transport_input_or_budget')
    for event in events:
        if done:
            return result('profile_error', 'data_after_done')
        if event['event'] != 'message':
            return result('unsupported', 'named_sse_event')
        if event['data'] == '[DONE]':
            done = True
            continue
        try:
            obj = json.loads(event['data'], parse_constant=_reject_constant,
                             parse_float=parse_float, parse_int=parse_integer)
        except (ValueError, RecursionError):
            return result('profile_error', 'invalid_json')
        if type(obj) is not dict or obj.get('object') != 'chat.completion.chunk' or type(obj.get('choices')) is not list:
            return result('profile_error', 'invalid_chunk_shape')
        value = obj.get('usage')
        if value is not None:
            if type(value) is not dict:
                return result('profile_error', 'invalid_usage')
            usage = value
        indexes = set()
        for item in obj['choices']:
            if type(item) is not dict:
                return result('profile_error', 'invalid_choice')
            index = item.get('index')
            if type(index) is not int or index < 0 or index in indexes:
                return result('profile_error', 'invalid_choice_index')
            indexes.add(index)
            delta, finish = item.get('delta'), item.get('finish_reason')
            if type(delta) is not dict or (finish is not None and type(finish) is not str):
                return result('profile_error', 'invalid_delta_or_finish')
            if finish == '':
                return result('profile_error', 'empty_finish_reason')
            if finish is not None and finish not in ('stop', 'length', 'content_filter'):
                return result('unsupported', 'unsupported_finish_reason')
            if set(delta) - {'role', 'content'}:
                return result('unsupported', 'non_text_delta')
            if delta.get('role') not in (None, 'assistant'):
                return result('profile_error', 'invalid_role')
            content = delta.get('content')
            if content is not None and type(content) is not str:
                return result('profile_error', 'invalid_content')
            item_out = choices.setdefault(index, {'index': index, 'text': '', 'finish_reason': None})
            if item_out['finish_reason'] is not None and (content or finish is not None):
                return result('profile_error', 'choice_after_finish')
            item_out['text'] += content or ''
            if finish is not None:
                item_out['finish_reason'] = finish
    if not done:
        return result('incomplete', 'missing_done')
    if not choices:
        return result('profile_error', 'no_choices')
    if any(item['finish_reason'] is None for item in choices.values()):
        return result('incomplete', 'missing_finish')
    return result('complete')
