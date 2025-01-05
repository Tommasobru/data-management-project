import pandas as pd 

def cleaning_player_data_year(file):
    # leggi il file 
    df = pd.read_csv(file)

    def convert_string(string):
        # removes symbols "€" and replace "," with "."
        clean_string = string.replace("€", "").strip().replace(",", ".")
    
        # check if string contains mln or mila and remove them 
        if "mln" in clean_string:
            # remove "mln" and convert the value to millions
            return float(clean_string.replace("mln", "").strip()) * 1000000
        elif "mila" in clean_string:
            # remove "mila" and convert the value to thousans
            return float(clean_string.replace("mila", "").strip()) * 1000
        elif "-" in clean_string:
            return 0
        else:
            return float(clean_string)

    
    for index, row in df.iterrows():
        name = row['Name'].strip().split()
        role = row["Role"].strip().split()

        if len(name) + 1 == len(role):
            role_clean = " ".join(role[-1:])
            df.at[index,"Role"] = role_clean
        elif len(name) + 2 == len(role):
            role_clean = " ".join(role[-2:])
            df.at[index,"Role"] = role_clean
        else:
            role_clean = " ".join(role[-3:])
            df.at[index,"Role"] = role_clean
            
    #  apply the function to the whole column
    df['Market Value'] = df["Market Value"].apply(convert_string)


    return df


file_player_data = 'dataset/player_data.csv'

df_player_data = cleaning_player_data_year(file_player_data)

df_player_data.to_csv('dataset/clean-player-data.csv')

