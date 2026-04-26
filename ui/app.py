import streamlit as st
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ■■ Page configuration
st.set_page_config(
    page_title='MeetingMind AI',
    page_icon='■',
    layout='wide',
)

BACKEND_URL = 'https://meetingmind-ai-hkfc.onrender.com'

session = requests.Session()
retry = Retry(
    total=3,
    connect=3,
    read=3,
    backoff_factor=1.5,
    status_forcelist=[502, 503, 504],
    allowed_methods=['GET'],
    raise_on_status=False,
)
adapter = HTTPAdapter(max_retries=retry)
session.mount('http://', adapter)
session.mount('https://', adapter)


def api_request(method: str, path: str, **kwargs) -> requests.Response:
    headers = kwargs.pop('headers', {})
    headers.setdefault('Accept', 'application/json')
    return session.request(method, f'{BACKEND_URL}{path}', headers=headers, **kwargs)


def parse_api_error(resp: requests.Response) -> str:
    content_type = resp.headers.get('content-type', '').lower()
    if 'text/html' in content_type:
        if resp.status_code == 502:
            return 'The frontend could reach the server, but the upstream gateway returned 502 while waiting for the analysis response. This usually means the long-running request needs a retry.'
        return f'The server returned an HTML error page (HTTP {resp.status_code}) instead of JSON.'

    try:
        payload = resp.json()
    except ValueError:
        return resp.text or f'HTTP {resp.status_code}'

    if isinstance(payload, dict):
        detail = payload.get('detail')
        if isinstance(detail, str) and detail.strip():
            return detail
        if resp.status_code == 429:
            return 'The analysis provider rate-limited this request. The frontend now sends only one analyze request per click, but you may still need to wait briefly and retry.'
    return str(payload)

page = st.sidebar.radio('Navigate', ['Analyze Meeting', 'Meeting History'])

if page == 'Meeting History':
    st.title('Meeting History')
    search_q = st.text_input('Search meetings', placeholder='keyword...')
    
    try:
        if search_q:
            resp = api_request('GET', '/history/search', params={'query': search_q}, timeout=(10, 60))
        else:
            resp = api_request('GET', '/history', timeout=(10, 60))
    except requests.RequestException as e:
        st.error(f'Could not load history: {e}')
        st.stop()
    
    if resp.status_code == 200:
        meetings = resp.json()
        st.caption(f'{len(meetings)} meeting(s) found')
        
        for m in meetings:
            with st.expander(f"{m['created_at'][:16]} — {m['audio_url'][:60]}"):
                st.write(m['summary'])
                items = m.get('action_items') or []
                for item in items:
                    if isinstance(item, dict):
                        st.markdown(f"- **{item.get('task', 'Untitled task')}** — {item.get('owner', 'Unassigned')}")
    else:
        st.error(f'Could not load history. Backend returned: {resp.status_code}')
        with st.expander('Debug Info'):
            st.write(resp.text)

else:
    # ■■ Header
    st.title('MeetingMind AI')
    st.caption('Upload a meeting audio URL and get an instant AI-powered report.')
    st.divider()

    # ■■ Input
    audio_url = st.text_input(
        'Audio file URL',
        placeholder='Paste a public MP3, WAV, or M4A URL...',
    )
    push_notion = st.checkbox('Push action items to Notion', value=True)

    if st.button('Analyze Meeting', type='primary'):
        if not audio_url.strip():
            st.warning('Please enter an audio URL.')
        else:
            with st.spinner('Agents are working... this takes 30-90 seconds.'):
                try:
                    resp = api_request(
                        'POST',
                        '/analyze',
                        params={'push_notion': str(push_notion).lower()},
                        json={'audio_url': audio_url},
                        timeout=(15, 600),
                    )
                    if resp.status_code != 200:
                        st.error(f'Analysis failed: {parse_api_error(resp)}')
                        st.stop()

                    data = resp.json()
                    meeting_id = data.get('meeting_id')

                except Exception as e:
                    st.error(f'Could not reach backend: {e}')
                    st.stop()

            if not meeting_id:
                st.error('Analysis did not return a meeting ID, so the report cannot be fetched.')
                st.stop()

            st.success('Analysis complete!')

            # Layout: three columns
            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                st.subheader('Executive Summary')
                st.write(data.get('summary', 'No summary.'))

            with col2:
                st.subheader('Sentiment')
                s = data.get('sentiment', {})
                tone = s.get('overall_tone', 'N/A')
                color = {
                    'Positive': 'green',
                    'Tense': 'red',
                    'Mixed': 'orange',
                    'Neutral': 'gray'
                }.get(tone, 'gray')

                st.markdown(f'**Tone:** :{color}[{tone}]')
                st.markdown(f'**Energy:** {s.get("energy_level","N/A")}')

                flags = s.get('risk_flags', [])
                if flags:
                    st.warning('Risk flags: ' + ', '.join(flags))

                st.info(s.get('recommendation', ''))

            with col3:
                st.subheader('Full Transcript')
                with st.expander('View transcript'):
                    st.text(data.get('transcript', 'No transcript.'))

            # ✅ Action Items (outside columns)
            st.divider()
            st.subheader('Action Items')

            items = data.get('action_items', [])
            if items:
                for item in items:
                    badge = {
                        'High': '■',
                        'Medium': '■',
                        'Low': '■'
                    }.get(item.get('priority',''), '■')

                    st.markdown(
                        f'{badge} **{item["task"]}** | '
                        f'Owner: `{item["owner"]}` | '
                        f'Due: {item["deadline"]}'
                    )
            else:
                st.write('No action items found.')

            # ✅ Full Report
            st.divider()
            st.subheader('Full AI Report')
            st.markdown(data.get('report', ''))

            # ✅ PDF Download (correct placement)
            st.divider()
            st.subheader('Download Report')

            if meeting_id:
                try:
                    pdf_resp = api_request('GET', f'/report/{meeting_id}', timeout=(10, 120))
                except requests.RequestException as e:
                    st.error(f'Could not fetch PDF report: {e}')
                    st.stop()

                if pdf_resp.status_code == 200:
                    st.download_button(
                        label='Download PDF Report',
                        data=pdf_resp.content,
                        file_name=f'meeting_{meeting_id}_report.pdf',
                        mime='application/pdf',
                    )
                else:
                    st.error('Could not generate PDF.')
            else:
                st.warning('No meeting ID found. Please analyze first.')
