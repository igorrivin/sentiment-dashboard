import pandas as pd
import requests
import json
import plotly.express as px
from dash import Dash, dcc, html, Input, Output
import dash, flask, os
from datetime import datetime, timedelta

from supabase import create_client

SUPABASE_URL= os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
def load_data():
    url = "https://raw.githubusercontent.com/igorrivin/sentiment-dashboard/main/sentiment_scores.jsonl"
    r = requests.get(url)
    lines = r.text.strip().splitlines()
    data = [json.loads(line) for line in lines]
    flat = [{"timestamp": d["timestamp"], **d["scores"]} for d in data]
    df = pd.DataFrame(flat)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df.set_index("timestamp", inplace=True)
    return df

def load_data_df(interval=7):
    begindate = (datetime.now() - timedelta(days=interval)).isoformat()
    response = (supabase.table('sentiment_scores') 
        .select('*') 
        .gte('timestamp', begindate) 
        .execute()
    )
    data = response.data
    # Convert to DataFrame and flatten the jsonb column
    rows = []
    for row in data:
        flat_row = {'timestamp': pd.to_datetime(row['timestamp'])}
        flat_row.update(row['scores'])  # Assumes 'stocks' is the jsonb column
        rows.append(flat_row)

    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df.set_index('timestamp', inplace=True)
    return df.sort_index()

def score_to_color(score):
    score = max(-1, min(1, score))  # clamp
    red = int(255 * (1 - max(score, 0)))
    green = int(255 * (1 + min(score, 0)))
    return f"background-color: rgb({red},{green},150); color: white; border-bottom: 1px solid #444;"

app = Dash(__name__)

app.layout = html.Div(
    children=[
        html.H1("Sentiment Scores"),
        dcc.Graph(id="graph"),
        html.Div(id="latest-table"),
        dcc.Interval(id="interval", interval=5*60*1000, n_intervals=0)
    ],
    style={
        "backgroundColor": "#1e1e2f",
        "padding": "20px",
        "color": "white",
        "fontFamily": "Arial, sans-serif"
    }
)

@app.callback(
    Output("graph", "figure"),
    Output("latest-table", "children"),
    Input("interval", "n_intervals")
)
def update(n):
    df = load_data_df()
    df_long = df.reset_index().melt(id_vars="timestamp", var_name="ticker", value_name="score")
    fig = px.line(df_long, x="timestamp", y="score", facet_col="ticker", facet_col_wrap=3)
    fig.update_layout(showlegend=False)
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))

    latest_time = df.index[-1].strftime("%Y-%m-%d %H:%M:%S UTC")
    latest = df.iloc[-1].dropna().sort_values(ascending=False)

    table = html.Div([
        html.H3(f"Latest Scores (as of {latest_time})"),
        html.Table([
            html.Tr([
                html.Th("Ticker", style={"textAlign": "left", "borderBottom": "2px solid white"}),
                html.Th("Score", style={"textAlign": "right", "borderBottom": "2px solid white"})
            ])
        ] + [
            html.Tr([
                html.Td(k, style={"textAlign": "left", "padding": "6px", "borderBottom": "1px solid #444"}),
                html.Td(f"{v:.3f}", style={"textAlign": "right", "padding": "6px", **{
                    "style": score_to_color(v)
                }})
            ]) for k, v in latest.items()
        ])
    ])

    # 🔍 Log access to Supabase
    try:
        
        supabase.table("visit_logs").insert({
            "timestamp": latest_time,
            "event": "dashboard_refresh"
        }).execute()
    except Exception as e:
        print("Supabase logging failed:", e)


    return fig, table

server = app.server

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8050)
