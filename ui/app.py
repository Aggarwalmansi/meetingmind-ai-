import streamlit as st
import requests, json

# ■■ Page configuration
st.set_page_config(
    page_title='MeetingMind AI',
    page_icon='■',
    layout='wide',
)

BACKEND_URL = 'https://meetingmind-ai-hkfc.onrender.com'

page = st.sidebar.radio('Navigate', ['Analyze Meeting', 'Meeting History'])

if page == 'Meeting History':
    st.title('Meeting History')
    search_q = st.text_input('Search meetings', placeholder='keyword...')
    
    if search_q:
        resp = requests.get(f'{BACKEND_URL}/history/search?query={search_q}')
    else:
        resp = requests.get(f'{BACKEND_URL}/history')
    
    if resp.status_code == 200:
        meetings = resp.json()
        st.caption(f'{len(meetings)} meeting(s) found')
        
        for m in meetings:
            with st.expander(f"{m['created_at'][:16]} — {m['audio_url'][:60]}"):
                st.write(m['summary'])
                items = json.loads(m['action_items'] or '[]')
                for item in items:
                    st.markdown(f"- **{item['task']}** — {item['owner']}")
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
                    resp = requests.post(
                        f'{BACKEND_URL}/analyze?push_notion={str(push_notion).lower()}',
                        json={'audio_url': audio_url},
                        timeout=300,
                    )
                    data = resp.json()
                    meeting_id = data.get('meeting_id')

                except Exception as e:
                    st.error(f'Could not reach backend: {e}')
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
                pdf_resp = requests.get(
                    f'{BACKEND_URL}/report/{meeting_id}',
                    timeout=60,
                )

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