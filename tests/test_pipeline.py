import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from db import database
import main
from agent import nodes
from utils.normalize import normalize_action_items, normalize_sentiment


class NormalizeTests(unittest.TestCase):
    def test_normalize_action_items_handles_double_encoded_payload(self):
        value = '"[{\\"task\\": \\"Ship release\\", \\"owner\\": \\"Ava\\", \\"deadline\\": \\"Friday\\", \\"priority\\": \\"high\\"}]"'
        items = normalize_action_items(value)
        self.assertEqual(items[0]['task'], 'Ship release')
        self.assertEqual(items[0]['priority'], 'High')

    def test_normalize_sentiment_handles_double_encoded_payload(self):
        value = '"{\\"overall_tone\\": \\"Neutral\\", \\"risk_flags\\": [\\"Delay\\"], \\"energy_level\\": \\"Medium\\", \\"recommendation\\": \\"Follow up\\"}"'
        sentiment = normalize_sentiment(value)
        self.assertEqual(sentiment['overall_tone'], 'Neutral')
        self.assertEqual(sentiment['risk_flags'], ['Delay'])


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)

    @patch('main.index_meeting')
    @patch('main.save_meeting', return_value=42)
    @patch('main.meeting_app.invoke')
    def test_analyze_normalizes_payload_before_returning(self, invoke_mock, save_mock, index_mock):
        invoke_mock.return_value = {
            'transcript': 'Speaker A: launch update',
            'summary': 'Summary text',
            'action_items': '"[{\\"task\\": \\"Ship release\\", \\"owner\\": \\"Ava\\", \\"deadline\\": \\"Friday\\", \\"priority\\": \\"high\\"}]"',
            'sentiment': '"{\\"overall_tone\\": \\"Positive\\", \\"risk_flags\\": [], \\"energy_level\\": \\"High\\", \\"recommendation\\": \\"Keep momentum\\"}"',
            'report': 'Report text',
        }

        response = self.client.post('/analyze?push_notion=false', json={'audio_url': 'https://example.com/audio.mp3'})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIsInstance(body['action_items'], list)
        self.assertEqual(body['action_items'][0]['priority'], 'High')
        self.assertIsInstance(body['sentiment'], dict)
        self.assertEqual(body['sentiment']['overall_tone'], 'Positive')
        saved_payload = save_mock.call_args.args[0]
        self.assertIsInstance(saved_payload['action_items'], list)
        self.assertIsInstance(saved_payload['sentiment'], dict)

    @patch('main.index_meeting', side_effect=RuntimeError('chroma conflict'))
    @patch('main.save_meeting', return_value=99)
    @patch('main.meeting_app.invoke')
    def test_analyze_survives_rag_indexing_failure(self, invoke_mock, save_mock, index_mock):
        invoke_mock.return_value = {
            'transcript': 'Speaker A: launch update',
            'summary': 'Summary text',
            'action_items': [{'task': 'Ship release', 'owner': 'Ava', 'deadline': 'Friday', 'priority': 'High'}],
            'sentiment': {'overall_tone': 'Positive', 'risk_flags': [], 'energy_level': 'High', 'recommendation': 'Keep momentum'},
            'report': 'Report text',
        }

        response = self.client.post('/analyze?push_notion=false', json={'audio_url': 'https://example.com/audio.mp3'})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['meeting_id'], 99)
        self.assertEqual(body['summary'], 'Summary text')

class NodeTests(unittest.TestCase):
    @patch('agent.nodes.aai.Transcriber')
    def test_transcribe_audio_falls_back_to_text_when_utterances_missing(self, transcriber_cls):
        transcript_obj = SimpleNamespace(status='completed', utterances=None, text='Fallback transcript')
        transcriber = MagicMock()
        transcriber.transcribe.return_value = transcript_obj
        transcriber_cls.return_value = transcriber

        result = nodes.transcribe_audio({'audio_url': 'https://example.com/audio.mp3'})
        self.assertEqual(result['transcript'], 'Fallback transcript')

    @patch('agent.nodes.NotionClient')
    def test_push_to_notion_handles_malformed_items_without_crashing(self, notion_client_cls):
        notion = MagicMock()
        notion.databases.retrieve.return_value = {
            'properties': {
                'Task': {'type': 'title'},
                'Owner': {'type': 'rich_text'},
                'Deadline': {'type': 'rich_text'},
                'Priority': {'type': 'select'},
                'Meeting Date': {'type': 'date'},
                'Audio URL': {'type': 'rich_text'},
            }
        }
        notion_client_cls.return_value = notion

        with patch.dict('os.environ', {'NOTION_TOKEN': 'token', 'NOTION_DB_ID': 'db'}, clear=False):
            result = nodes.push_to_notion({
                'push_notion': True,
                'audio_url': 'https://example.com/audio.mp3',
                'action_items': ['just a string item'],
            })

        self.assertEqual(result, {})
        notion.pages.create.assert_called_once()


class DatabaseTests(unittest.TestCase):
    def test_get_all_meetings_normalizes_legacy_rows(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_db = os.path.join(tmpdir, 'meetings.db')
            with patch.object(database, 'DB_PATH', temp_db):
                database.init_db()
                conn = database.get_connection()
                conn.execute(
                    '''INSERT INTO meetings
                       (audio_url, transcript, summary, action_items, sentiment, report, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (
                        'https://example.com/audio.mp3',
                        'Transcript text',
                        'Summary text',
                        '"[{\\"task\\": \\"Task\\", \\"owner\\": \\"Ava\\", \\"deadline\\": \\"Friday\\", \\"priority\\": \\"high\\"}]"',
                        '"{\\"overall_tone\\": \\"Positive\\", \\"risk_flags\\": [], \\"energy_level\\": \\"High\\", \\"recommendation\\": \\"\\"}"',
                        'Report text',
                        '2026-04-19T00:00:00',
                    ),
                )
                conn.commit()
                conn.close()

                rows = database.get_all_meetings()

        self.assertEqual(rows[0]['action_items'][0]['priority'], 'High')
        self.assertEqual(rows[0]['sentiment']['overall_tone'], 'Positive')


if __name__ == '__main__':
    unittest.main()
