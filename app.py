import pandas as pd
import requests
import json
import plotly.express as px
from dash import Dash, dcc, html, Input, Output

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

app = Dash(__name__)
app.layout = html.Div([
    html.H1("Sentiment Scores"),
    dcc.Graph(id="graph"),
    html.Div(id="latest-table"),
    dcc.Interval(id="interval", interval=5*60*1000, n_intervals=0)
])

@app.callback(
    Output("graph", "figure"),
    Output("latest-table", "children"),
    Input("interval", "n_intervals")
)
def update(n):
    df = load_data()
    df_long = df.reset_index().melt(id_vars="timestamp", var_name="ticker", value_name="score")
    fig = px.line(df_long, x="timestamp", y="score", facet_col="ticker", facet_col_wrap=3)
    fig.update_layout(showlegend=False)
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))

    latest = df.iloc[-1].dropna().sort_values(ascending=False)
    table = html.Table([
        html.Tr([html.Th("Ticker"), html.Th("Score")])
    ] + [html.Tr([html.Td(k), html.Td(f"{v:.3f}")]) for k, v in latest.items()])
    return fig, table

if __name__ == "__main__":
    app.run(debug=True)
