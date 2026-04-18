import streamlit as st
import requests, json
# ■■ Page configuration

st.set_page_config(
page_title='MeetingMind AI',
page_icon='■',
layout='wide',
)
# ■■ IMPORTANT: Change this URL in Phase 8 after backend is deployed ■■■■■■
BACKEND_URL = 'https://meetingmind-ai-hkfc.onrender.com'
# ■■ Header

st.title('■ MeetingMind AI')
st.caption('Upload a meeting audio URL and get an instant AI-powered report.')
st.divider()
# ■■ Input
audio_url = st.text_input(
'Audio file URL',
placeholder='Paste a public MP3, WAV, or M4A URL...',
)
if st.button('Analyze Meeting', type='primary'):
    if not audio_url.strip():
        st.warning('Please enter an audio URL.')
    else:
        with st.spinner('Agents are working... this takes 30-90 seconds.'):
            try:
                resp = requests.post(
                f'{BACKEND_URL}/analyze',
                json={'audio_url': audio_url},
                timeout=300,
    )
                data = resp.json()
            except Exception as e:
                st.error(f'Could not reach backend: {e}')
                st.stop()
            st.success('Analysis complete!')
#Layout: three columns 
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.subheader('Executive Summary')
        st.write(data.get('summary', 'No summary.'))
    with col2:
        st.subheader('Sentiment')
        s = data.get('sentiment', {})
        tone = s.get('overall_tone', 'N/A')
        color = {'Positive':'green','Tense':'red',
        'Mixed':'orange','Neutral':'gray'}.get(tone,'gray')
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
            st.divider()
            st.subheader('Action Items')
            items = data.get('action_items', [])
            if items:
                for item in items:
                    badge = {'High': '■', 'Medium': '■',
                    'Low': '■'}.get(item.get('priority',''), '■')
                    st.markdown(
                    f'{badge} **{item["task"]}** | '
                    f'Owner: `{item["owner"]}` | '
                    f'Due: {item["deadline"]}'
                    )
            else:
                st.write('No action items found.')
                st.divider()
                st.subheader('Full AI Report')
                st.markdown(data.get('report', ''))