import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import uuid
from openai import OpenAI
from datetime import datetime

# Page config
st.set_page_config(
    page_title="Morning, Pirnar",
    page_icon="📊",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .stApp {
        background-color: #121212;
        color: white;
    }
    .stat-card {
        background-color: #1e1e1e;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 20px;
    }
    .stat-card h2 {
        font-size: 3rem;
        margin-bottom: 10px;
    }
    .stat-card p {
        font-size: 1.2rem;
        margin: 0;
    }
    .summary-box {
        background-color: #1e1e1e;
        padding: 25px;
        border-radius: 10px;
        margin: 20px 0;
        font-size: 1.1rem;
        line-height: 1.6;
    }
    .summary-box ul {
        margin-top: 15px;
        list-style-type: none;
        padding-left: 0;
    }
    .summary-box li {
        margin: 12px 0;
        font-size: 1.1rem;
    }
    .issue-card {
        background-color: #2a2a2a;
        padding: 20px;
        border-radius: 10px;
        margin: 15px 0;
    }
    .issue-card h4 {
        font-size: 1.3rem;
        margin: 0 0 10px 0;
    }
    .issue-card p {
        font-size: 1.1rem;
        margin: 5px 0;
    }
    .chat-message {
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        color: #fff;
    }
    
    .chat-message.user {
        background-color: #2d2d2d;
    }
    
    .chat-message.assistant {
        background-color: #1e1e1e;
    }
    
    .pin-button {
        float: right;
        padding: 0.5rem;
        background: none;
        border: none;
        color: #ffd700;
        cursor: pointer;
    }
    
    .pinned-note {
        background-color: #ffd700;
        color: black;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        position: relative;
    }
    
    .delete-pin {
        position: absolute;
        top: 0.5rem;
        right: 0.5rem;
        background: none;
        border: none;
        color: #ff4444;
        cursor: pointer;
    }
    </style>
""", unsafe_allow_html=True)

# Daten einlesen
@st.cache_data
def load_data():
    return pd.read_csv('UX_data_update.csv')

df = load_data()

# Impact Score Kategorien
def get_severity(score):
    if score <= -3:
        return 'Kritisch'
    elif score <= -2:
        return 'Schwerwiegend' 
    else:
        return 'Moderat'

df['Severity'] = df['Impact Score'].apply(get_severity)

# Header
st.title("UX Analysis Dashboard")

# Chat Interface
st.markdown("---")
st.subheader("💬 Frag die KI zu den Daten")

# Initialize session state
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
    
if 'pinned_notes' not in st.session_state:
    st.session_state.pinned_notes = []

# Chat Layout
chat_col1, chat_col2 = st.columns([3, 1])

# OpenAI Setup
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def get_ai_response(user_input, df):
    # Convert DataFrame to a more readable format
    data_details = ""
    
    # General statistics
    data_details += f"""
    DATENÜBERSICHT:
    Gesamtanzahl Einträge: {len(df)}
    Spalten: {', '.join(df.columns.tolist())}
    
    DETAILLIERTE DATEN:
    {df.to_string()}
    
    ZUSAMMENFASSENDE STATISTIKEN:
    
    1. Platform Verteilung:
    {df['Platform'].value_counts().to_string()}
    
    2. Severity Verteilung:
    {df['Severity'].value_counts().to_string()}
    
    3. Topics:
    {df['Topic'].value_counts().to_string()}
    
    4. Impact Score Statistiken:
    - Min: {df['Impact Score'].min()}
    - Max: {df['Impact Score'].max()}
    - Durchschnitt: {df['Impact Score'].mean():.2f}
    - Median: {df['Impact Score'].median()}
    
    5. Judgement Verteilung:
    {df['Judgement'].value_counts().to_string()}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"""Du bist ein präziser Analyst für UX/UI Issues.
                Du hast Zugriff auf die komplette CSV-Datei und alle ihre Daten.
                
                Die CSV enthält folgende Spalten:
                - Code: Eindeutige ID des Issues
                - Title: Beschreibung des Problems
                - Platform: Desktop oder Mobile Web
                - Is Low Cost: Ob das Problem günstig zu beheben ist
                - Is Missed Opportunity: Ob es eine verpasste Chance darstellt
                - Judgement: Bewertung des Issues
                - Impact: Auswirkung des Problems
                - Impact Score: Numerische Bewertung (negativ = schlecht)
                - Notes: Zusätzliche Anmerkungen
                - Topic: Themenbereich des Problems
                - Review Tool Link: Link zum Review-Tool
                - Selected scenarios: Betroffene Szenarien
                - Severity: Schweregrad (Kritisch/Schwerwiegend/Moderat)
                
                Wichtige Regeln für deine Antworten:
                - Maximal 3 Stichpunkte
                - Jeder Stichpunkt maximal 1 Zeile
                - Nur konkrete Zahlen und Fakten aus den Daten
                - Keine Erklärungen oder Interpretationen
                - Antworte auf Deutsch
                - Verwende Aufzählungszeichen (•)
                
                {data_details}"""},
                {"role": "user", "content": user_input}
            ],
            temperature=0.3,
            max_tokens=150
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        return f"Fehler: {str(e)}"

with chat_col1:
    user_input = st.text_input("Stelle eine Frage zu den Daten:", key="user_input")
    
    # Clear Chat Button
    col1, col2 = st.columns([6, 1])
    with col1:
        if st.button("Fragen", key="ask_button"):
            if user_input:
                st.session_state.chat_history.append({"role": "user", "content": user_input})
                response = get_ai_response(user_input, df)
                st.session_state.chat_history.append({"role": "assistant", "content": response})
                st.rerun()
    with col2:
        if st.button("🗑️ Chat leeren"):
            st.session_state.chat_history = []
            st.rerun()

with chat_col2:
    st.markdown("📌 **Gepinnte Notizen**")
    for idx, note in enumerate(st.session_state.pinned_notes):
        col1, col2 = st.columns([5,1])
        with col1:
            st.info(note['content'])
        with col2:
            if st.button("❌", key=f"delete_pin_{idx}"):
                st.session_state.pinned_notes.pop(idx)
                st.rerun()

# Chat History
for idx, message in enumerate(st.session_state.chat_history):
    cols = st.columns([5, 1, 1])  # Mehr Platz für den Text, zwei schmale Spalten für Buttons
    
    with cols[0]:
        if message["role"] == "user":
            st.markdown(f"""
                <div class="chat-message user">
                    👤: {message["content"]}
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
                <div class="chat-message assistant">
                    🤖: {message["content"]}
                </div>
            """, unsafe_allow_html=True)
    
    with cols[1]:
        if message["role"] == "assistant":
            if st.button("📌", key=f"pin_{idx}"):
                st.session_state.pinned_notes.append({
                    "id": str(uuid.uuid4()),
                    "content": message["content"]
                })
                st.rerun()
    
    with cols[2]:
        if st.button("🗑️", key=f"delete_message_{idx}"):
            st.session_state.chat_history.pop(idx)
            st.rerun()

# Display generated graphs
if 'generated_graphs' in st.session_state and st.session_state.generated_graphs:
    st.subheader("📊 Generierte Graphen")
    for fig in st.session_state.generated_graphs:
        st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# Enhanced AI Analysis Section
st.subheader("Zusammenfassung der Daten")

# Calculate key metrics
total_issues = len(df)
violated_high = len(df[df['Judgement'] == 'Violated High'])
violated_low = len(df[df['Judgement'] == 'Violated Low'])
adhered_high = len(df[df['Judgement'] == 'Adhered High'])
adhered_low = len(df[df['Judgement'] == 'Adhered Low'])

# Platform analysis
platform_severity = df.groupby(['Platform', 'Severity']).size().unstack(fill_value=0)
worst_platform = df.groupby('Platform')['Impact Score'].mean().sort_values().index[0]

# Topic analysis
topic_impact = df.groupby('Topic')['Impact Score'].sum().abs().sort_values(ascending=False)
most_critical_topic = topic_impact.index[0]
topic_count = len(df[df['Topic'] == most_critical_topic])

# Create three columns for key metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("""
        <div class="stat-card">
            <h2 style="color: #f44336">{}</h2>
            <p>Violated High</p>
        </div>
    """.format(violated_high), unsafe_allow_html=True)

with col2:
    st.markdown("""
        <div class="stat-card">
            <h2 style="color: #ff9800">{}</h2>
            <p>Violated Low</p>
        </div>
    """.format(violated_low), unsafe_allow_html=True)

with col3:
    st.markdown("""
        <div class="stat-card">
            <h2 style="color: #4CAF50">{}</h2>
            <p>Adhered High</p>
        </div>
    """.format(adhered_high), unsafe_allow_html=True)

with col4:
    st.markdown("""
        <div class="stat-card">
            <h2 style="color: #2196F3">{}</h2>
            <p>Adhered Low</p>
        </div>
    """.format(adhered_low), unsafe_allow_html=True)

# Detailed Analysis Box
st.markdown("""
    <div class="summary-box">
        <h3 style="color: #4CAF50; font-size: 1.5rem;">Detaillierte Analyse</h3>
        <ul>
            <li>🎯 Insgesamt wurden {} UX/UI-Issues identifiziert</li>
            <li>⚠️ {:.1f}% aller Issues sind kritisch oder schwerwiegend</li>
            <li>📱 Die Platform "{}" zeigt die schwerwiegendsten Probleme</li>
            <li>🔍 Der Bereich "{}" ist am stärksten betroffen mit {} Issues</li>
            <li>📊 Der durchschnittliche Impact Score beträgt {:.2f}</li>
        </ul>
    </div>
""".format(
    total_issues,
    ((violated_high + violated_low + adhered_high + adhered_low) / total_issues) * 100,
    worst_platform,
    most_critical_topic,
    topic_count,
    df['Impact Score'].mean()
), unsafe_allow_html=True)

# Add Judgement Analysis Graphs
st.subheader("📊 Judgement Analyse nach Platform und Topic")

# Create two columns for the graphs
graph_col1, graph_col2 = st.columns(2)

with graph_col1:
    # Platform Analysis
    platform_judgement = df.groupby(['Platform', 'Judgement']).size().reset_index(name='count')
    # Filter out 'Not applicable' and set custom order
    platform_judgement = platform_judgement[platform_judgement['Judgement'] != 'Not applicable']
    judgement_order = ['Violated High', 'Violated Low', 'Adhered Low', 'Adhered High']
    platform_judgement['Judgement'] = pd.Categorical(
        platform_judgement['Judgement'], 
        categories=judgement_order, 
        ordered=True
    )
    
    fig_platform = px.bar(
        platform_judgement,
        x='Platform',
        y='count',
        color='Judgement',
        title='Judgement Verteilung nach Platform',
        color_discrete_map={
            'Violated High': '#f44336',
            'Violated Low': '#ff9800',
            'Adhered Low': '#2196F3',
            'Adhered High': '#4CAF50'
        },
        category_orders={'Judgement': judgement_order},
        barmode='group'
    )
    fig_platform.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='white'
    )
    st.plotly_chart(fig_platform, use_container_width=True)

with graph_col2:
    # Add topic selection
    all_topics = sorted(df['Topic'].unique().tolist())
    selected_topics = st.multiselect(
        'Wähle die Topics aus:',
        options=all_topics,
        default=df['Topic'].value_counts().nlargest(5).index.tolist(),
        key='topic_selector'
    )
    
    # Update topic analysis with selected topics
    topic_judgement = df.groupby(['Topic', 'Judgement']).size().reset_index(name='count')
    topic_judgement = topic_judgement[topic_judgement['Judgement'] != 'Not applicable']
    topic_judgement = topic_judgement[topic_judgement['Topic'].isin(selected_topics)]
    topic_judgement['Judgement'] = pd.Categorical(
        topic_judgement['Judgement'], 
        categories=judgement_order, 
        ordered=True
    )
    
    fig_topic = px.bar(
        topic_judgement,
        x='Topic',
        y='count',
        color='Judgement',
        title='Judgement Verteilung nach ausgewählten Topics',
        color_discrete_map={
            'Violated High': '#f44336',
            'Violated Low': '#ff9800',
            'Adhered Low': '#2196F3',
            'Adhered High': '#4CAF50'
        },
        category_orders={'Judgement': judgement_order},
        barmode='group'
    )
    fig_topic.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='white',
        xaxis_tickangle=-45
    )
    st.plotly_chart(fig_topic, use_container_width=True)
    
# Improved Data Analysis Section
st.subheader("📊 Datenanalyse")

# Detailed Data View
st.subheader("Detaillierte Datenansicht")
columns_to_display = ['Title', 'Platform', 'Topic', 'Severity', 'Judgement', 'Impact Score', 'Review Tool Link']
search = st.text_input('Suche in der Datentabelle')

# Filter out "Not Yet Rated" entries and apply search
if search:
    filtered_df = df[
        (df['Title'].str.contains(search, case=False) | df['Topic'].str.contains(search, case=False)) &
        (df['Judgement'] != 'Not Yet Rated')
    ]
else:
    filtered_df = df[df['Judgement'] != 'Not Yet Rated']

# Create a styled dataframe with clickable links
def make_clickable(link):
    if pd.isna(link):
        return ""
    return f'<a href="{link}" target="_blank">🔗</a>'

styled_df = filtered_df[columns_to_display].sort_values('Impact Score').style.apply(
    lambda x: ['background-color: #f44336' if val == 'Kritisch' else
              'background-color: #ff9800' if val == 'Schwerwiegend' else
              'background-color: #ffc107' if val == 'Moderat' else ''
              for val in x],
    subset=['Severity']
).apply(
    lambda x: ['background-color: #f44336' if val == 'Violated High' else
              'background-color: #ff9800' if val == 'Violated Low' else
              'background-color: #4CAF50' if val == 'Adhered High' else
              'background-color: #2196F3' if val == 'Adhered Low' else
              'background-color: #666666' if val == 'Not applicable' else ''
              for val in x],
    subset=['Judgement']
).format({'Review Tool Link': make_clickable})

st.write(
    styled_df.to_html(escape=False),
    unsafe_allow_html=True
) 