import pandas as pd

df = pd.read_csv('content.csv')
with open('sample.html', 'w', encoding='utf-8') as f:
    f.write(df['content_html'].iloc[0][:2000])
