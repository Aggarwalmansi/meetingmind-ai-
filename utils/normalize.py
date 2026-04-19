import json
from typing import Any


def _unwrap_json_string(value: Any) -> Any:
    while isinstance(value, str):
        text = value.strip()
        if not text:
            return ''
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            return text
    return value


def _strip_code_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith('```') and cleaned.endswith('```'):
        lines = cleaned.splitlines()
        if len(lines) >= 3:
            cleaned = '\n'.join(lines[1:-1]).strip()
    return cleaned.removeprefix('json').strip() if cleaned.startswith('json') else cleaned


def normalize_action_items(value: Any) -> list[dict[str, str]]:
    value = _unwrap_json_string(value)
    if isinstance(value, str):
        value = _unwrap_json_string(_strip_code_fences(value))

    if isinstance(value, dict):
        if isinstance(value.get('action_items'), list):
            value = value['action_items']
        elif {'task', 'owner', 'deadline', 'priority'} & set(value.keys()):
            value = [value]
        else:
            value = []

    if not isinstance(value, list):
        return []

    normalized: list[dict[str, str]] = []
    for item in value:
        if isinstance(item, str):
            item = {'task': item, 'owner': 'Unassigned', 'deadline': 'Not specified', 'priority': 'Medium'}
        elif not isinstance(item, dict):
            continue

        normalized.append(
            {
                'task': str(item.get('task') or '').strip() or 'Untitled task',
                'owner': str(item.get('owner') or 'Unassigned').strip() or 'Unassigned',
                'deadline': str(item.get('deadline') or 'Not specified').strip() or 'Not specified',
                'priority': _normalize_priority(item.get('priority')),
            }
        )
    return normalized


def _normalize_priority(value: Any) -> str:
    text = str(value or 'Medium').strip().capitalize()
    return text if text in {'High', 'Medium', 'Low'} else 'Medium'


def normalize_sentiment(value: Any) -> dict[str, Any]:
    value = _unwrap_json_string(value)
    if isinstance(value, str):
        value = _unwrap_json_string(_strip_code_fences(value))
    if not isinstance(value, dict):
        value = {}

    risk_flags = value.get('risk_flags', [])
    if isinstance(risk_flags, str):
        risk_flags = [risk_flags] if risk_flags.strip() else []
    if not isinstance(risk_flags, list):
        risk_flags = []

    return {
        'overall_tone': str(value.get('overall_tone') or 'Unknown'),
        'risk_flags': [str(flag) for flag in risk_flags if str(flag).strip()],
        'energy_level': str(value.get('energy_level') or 'Unknown'),
        'recommendation': str(value.get('recommendation') or ''),
    }


def normalize_meeting_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    normalized['audio_url'] = str(normalized.get('audio_url') or '')
    normalized['transcript'] = str(normalized.get('transcript') or '')
    normalized['summary'] = str(normalized.get('summary') or '')
    normalized['report'] = str(normalized.get('report') or '')
    normalized['action_items'] = normalize_action_items(normalized.get('action_items'))
    normalized['sentiment'] = normalize_sentiment(normalized.get('sentiment'))
    return normalized
