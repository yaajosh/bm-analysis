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
    return pd.read_csv('ux_data.csv')

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
    # Prepare context from dataframe
    data_summary = f"""
    Daten:
    {df.to_string()}
    
    Verfügbare Spalten:
    {', '.join(df.columns.tolist())}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"""Du bist ein präziser Analyst für UX/UI Issues.
                Du kannst auch Graphen erstellen. Wenn der User nach einem Graphen fragt,
                antworte EXAKT in diesem Format:
                
                GRAPH:
                type: bar
                data: [Beschreibung der benötigten Daten]
                x: Platform
                y: value
                title: [Titel - Verwende diese Schlüsselwörter:
                       - "Kritisch" für kritische Issues
                       - "Violated" für Issues mit Impact Score <= -2]
                
                WICHTIG: 
                - Verwende IMMER 'value' als y-Wert für Anzahlen
                - Verwende IMMER 'Platform' als x-Wert
                - Sei präzise mit den Schlüsselwörtern im Titel
                
                Aktuelle Daten:
                - Anzahl Issues gesamt: {len(df)}
                - Anzahl kritische Issues: {len(df[df['Severity'] == 'Kritisch'])}
                - Anzahl violated Issues: {len(df[df['Impact Score'] <= -2])}
                
                Verfügbare Daten:
                {data_summary}"""},
                {"role": "user", "content": user_input}
            ],
            temperature=0.3,
            max_tokens=150
        )
        
        ai_response = response.choices[0].message.content
        
        # Check if response contains graph request
        if "GRAPH:" in ai_response:
            fig = create_and_display_graph(ai_response, df)
            if fig:
                if 'generated_graphs' not in st.session_state:
                    st.session_state.generated_graphs = []
                st.session_state.generated_graphs.append(fig)
                return "Graph wurde erstellt! 📊"
            return "Fehler bei der Graph-Erstellung. Bitte versuchen Sie es erneut."
        
        return ai_response
        
    except Exception as e:
        return f"Fehler: {str(e)}"

def create_and_display_graph(graph_spec, df):
    # Parse graph specification
    lines = graph_spec.split('\n')
    graph_config = {}
    for line in lines:
        if ':' in line:
            key, value = line.split(':', 1)
            graph_config[key.strip().lower()] = value.strip()
    
    # Filter data based on graph requirements
    plot_df = df.copy()
    
    # Filter for violated (high and low) if specified in title
    if "violated" in graph_config.get('title', '').lower():
        plot_df = plot_df[plot_df['Impact Score'] <= -2]  # Assuming Impact Score <= -2 means violated
    
    # Filter for critical issues if specified
    elif "kritisch" in graph_config.get('title', '').lower():
        plot_df = plot_df[plot_df['Severity'] == 'Kritisch']
    
    # Count values
    if graph_config.get('y') == 'value':
        # Group by x-axis column and count
        counts = plot_df.groupby(graph_config.get('x')).size().reset_index(name='value')
        plot_df = counts
        y_column = 'value'
    else:
        y_column = graph_config.get('y')
    
    # Create graph
    if graph_config.get('type') == 'bar':
        fig = px.bar(
            plot_df,
            x=graph_config.get('x'),
            y=y_column,
            title=graph_config.get('title'),
            color_discrete_sequence=['#d32f2f']
        )
        
        # Add value labels inside bars
        fig.update_traces(
            texttemplate='%{value}',
            textposition='inside',
            textfont=dict(color='white')
        )
    
        # Update layout
        fig.update_layout(
            height=400,
            showlegend=False,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            yaxis=dict(
                range=[0, max(plot_df[y_column]) * 1.1]  # Add 10% padding to y-axis
            )
        )
        
        return fig
    
    return None

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
st.subheader("🤖 KI-Analyse der Daten")

# Calculate key metrics
total_issues = len(df)
critical_issues = len(df[df['Severity'] == 'Kritisch'])
severe_issues = len(df[df['Severity'] == 'Schwerwiegend'])
moderate_issues = len(df[df['Severity'] == 'Moderat'])

# Platform analysis
platform_severity = df.groupby(['Platform', 'Severity']).size().unstack(fill_value=0)
worst_platform = df.groupby('Platform')['Impact Score'].mean().sort_values().index[0]

# Topic analysis
topic_impact = df.groupby('Topic')['Impact Score'].sum().abs().sort_values(ascending=False)
most_critical_topic = topic_impact.index[0]
topic_count = len(df[df['Topic'] == most_critical_topic])

# Create three columns for key metrics
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
        <div class="stat-card">
            <h2 style="color: #f44336">{}</h2>
            <p>Kritische Issues</p>
        </div>
    """.format(critical_issues), unsafe_allow_html=True)

with col2:
    st.markdown("""
        <div class="stat-card">
            <h2 style="color: #ff9800">{}</h2>
            <p>Schwerwiegende Issues</p>
        </div>
    """.format(severe_issues), unsafe_allow_html=True)

with col3:
    st.markdown("""
        <div class="stat-card">
            <h2 style="color: #ffc107">{}</h2>
            <p>Moderate Issues</p>
        </div>
    """.format(moderate_issues), unsafe_allow_html=True)

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
    ((critical_issues + severe_issues) / total_issues) * 100,
    worst_platform,
    most_critical_topic,
    topic_count,
    df['Impact Score'].mean()
), unsafe_allow_html=True)

# Improved Data Analysis Section
st.subheader("📊 Datenanalyse")

# Detailed Data View
st.subheader("Detaillierte Datenansicht")
columns_to_display = ['Title', 'Platform', 'Topic', 'Severity', 'Impact Score', 'Review Tool Link']
search = st.text_input('Suche in der Datentabelle')

# Prepare the DataFrame with styling
if search:
    filtered_df = df[df['Title'].str.contains(search, case=False) | 
                    df['Topic'].str.contains(search, case=False)]
else:
    filtered_df = df

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
    lambda x: ['color: white' if val in ['Kritisch', 'Schwerwiegend'] else
              'color: black' if val == 'Moderat' else ''
              for val in x],
    subset=['Severity']
).format({'Review Tool Link': make_clickable})

st.write(
    styled_df.to_html(escape=False),
    unsafe_allow_html=True
) 