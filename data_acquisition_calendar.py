import pandas as pd 

file = 'dataset/matches.csv'

matches = pd.read_csv(file)

calendar = matches[['season','giornata']].drop_duplicates()

calendar.to_csv('dataset/calendar.csv', index=False )

print(calendar)

