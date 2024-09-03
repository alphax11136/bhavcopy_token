import pandas as pd
import streamlit as st

import warnings
warnings.filterwarnings("ignore")


############! Dynamic function !############

def main():
    '''
   
    '''
    st.title("Bhavcopy Tokens")

    #! Initialize session state variables at the beginning of the app

    # st.session_state.bhavopy_loaded = st.session_state.get('bhavopy_loaded', False)
    # st.session_state.oi_set = st.session_state.get('oi_set', False)
    # st.session_state.df_bhavcopy = st.session_state.get('df_bhavcopy', pd.DataFrame())
    # st.session_state.df_bhavcopy_updated = st.session_state.get('df_bhavcopy_updated', pd.DataFrame())

    #! Initialize the tokens variable
    tokens = None

    #! Form
    with st.form("form_token"):

        input_opt_bhavcopy = st.file_uploader("Choose a option bhavopy file", type="csv")
        input_fut_bhavcopy = st.file_uploader("Choose a future bhavopy file", type="csv")
        input_oi_value = st.number_input("OI Value", min_value=0, value=0, step=1, format="%d")

        btn_submit = st.form_submit_button("Submit")
    
        #! if btn clicked with a file name then load the data using (stocks_token function)
        if (btn_submit) and (input_opt_bhavcopy is not None) and (input_fut_bhavcopy is not None) and (input_oi_value is not None):
            tokens = stocks_token(input_opt_bhavcopy, input_fut_bhavcopy, input_oi_value)

    #! Show the download button outside the form after the form is submitted
    if tokens:
        st.download_button(label="Download Tokens", data=tokens, file_name="tickers.txt", mime="text/plain")


############! Static Function !############


def stocks_token(input_opt_bhavcopy,input_fut_bhavcopy,input_oi_value):
    '''

    '''

    #! Reading today's bhavcopy file
    df_fo_bhavcopy = pd.read_csv(input_opt_bhavcopy)
    df_fut_bhavcopy = pd.read_csv(input_fut_bhavcopy)

    #! Filter bhavcopy for stocks options only.
    df_optstk = df_fo_bhavcopy[df_fo_bhavcopy['CONTRACT_D'].str.startswith('OPTSTK')]
    df_futstk = df_fut_bhavcopy[df_fut_bhavcopy['CONTRACT_D'].str.startswith('FUTSTK')]

    #! Apply the function to the 'CONTRACT_D' column
    df_optstk[['symbol', 'expiry', 'position', 'strike']] = df_optstk['CONTRACT_D'].apply(extract_opt_details)
    df_futstk[['symbol', 'expiry']] = df_futstk['CONTRACT_D'].apply(extract_fut_details)

    #! Convert 'expiry' column to datetime format
    df_optstk['expiry'] = pd.to_datetime(df_optstk['expiry'], format='%d-%b-%Y').dt.date
    df_futstk['expiry'] = pd.to_datetime(df_futstk['expiry'], format='%d-%b-%Y').dt.date
    
    #! Filter the DataFrame to include only rows with the minimum expiry date
    df_optstk = df_optstk[df_optstk['expiry'] == df_optstk['expiry'].min()]
    df_futstk = df_futstk[df_futstk['expiry'] == df_futstk['expiry'].min()]

    #! Create a ticker column.
    df_optstk['ticker'] = 'NRML|' + df_optstk['symbol'] + df_optstk['expiry'].apply(lambda x: x.strftime('%y%b').upper()) + df_optstk['strike'] + df_optstk['position']
    df_futstk['ticker'] = 'NRML|' + df_futstk['symbol'] + df_futstk['expiry'].apply(lambda x: x.strftime('%y%b').upper()) + 'FUT'

    #! Convert strike to integer and drop all decimal strikes
    df_optstk['strike'] = df_optstk['strike'].apply(convert_to_int)
    df_optstk = df_optstk.dropna(subset=['strike'])
    df_optstk = df_optstk.reset_index(drop=True)

    #! Sort dataframe with symbol.
    df_optstk = df_optstk.sort_values(by='symbol')
    df_futstk = df_futstk.sort_values(by='symbol')

    #! Clear the tickers.txt file before starting
    with open('tickers.txt', 'w') as file:
        file.write('')

    df_optstk_stockwise = df_optstk.groupby('symbol')

    #! Open the file in append mode once
    with open('tickers.txt', 'a') as file:

        #! For options
        for symbol, stock_df in df_optstk_stockwise:
            
            #! Find equity price
            stock_eq_price = stock_df['UNDRLNG_ST'].unique()[0]
            #! For CE
            stock_df_ce = stock_df[(stock_df['position'] == 'CE') & (stock_df['strike'] < stock_eq_price)]
            stock_df_ce_token = stock_df_ce[stock_df_ce['OI_NO_CON'] > input_oi_value]
            #! For PE
            stock_df_pe = stock_df[(stock_df['position'] == 'PE') & (stock_df['strike'] > stock_eq_price)]
            stock_df_pe_token = stock_df_pe[stock_df_pe['OI_NO_CON'] > input_oi_value]

            #! Apply the function and flatten the list
            if not stock_df_ce_token.empty:
                tickers_ce = stock_df_ce_token.apply(add_pe_ticker, axis=1).explode()
                for ticker in tickers_ce:
                    file.write(f"{ticker}\n")
            
            if not stock_df_pe_token.empty:
                tickers_pe = stock_df_pe_token.apply(add_ce_ticker, axis=1).explode()
                for ticker in tickers_pe:
                    file.write(f"{ticker}\n")
            
            print(f"For {symbol}, tickers saved to tickers.txt")
        
        #! For futures
        for fut_ticker in df_futstk['ticker']:
            file.write(f"{fut_ticker}\n")
        
        
    #! Read the tickers.txt file content
    with open('tickers.txt', 'r') as file:
        tokens = file.read()
    
    return tokens


def find_correct_dash_index(s):
    dash_indices = [i for i, char in enumerate(s) if char == '-']
    
    for index in dash_indices:
        # Check if there are at least two digits before the dash
        if index >= 2 and s[index-2:index].isdigit():
            return index
    
    return None  # If no such dash is found


def extract_opt_details(contract_str):

    type = 'OPTSTK'
    contract_str = contract_str.split(type)[1]

    # first_dash_index = contract_str.find('-')
    first_dash_index = find_correct_dash_index(contract_str)
    
    symbol = contract_str[:first_dash_index-2]

    contract_str = contract_str.split(symbol)[1]

    first_dash_index = find_correct_dash_index(contract_str)

    if 'PE' in contract_str:
        # pos_index = contract_str.index('PE')
        position = 'PE'
    elif 'CE' in contract_str:
        # pos_index = contract_str.index('CE')
        position = 'CE'

    contract_str = contract_str.split(position)

    expiry = contract_str[0]
    strike = contract_str[1]

    return pd.Series([symbol, expiry, position, strike], index=['symbol', 'expiry', 'position', 'strike'])


def extract_fut_details(contract_str):
    
    type = 'FUTSTK'
    contract_str = contract_str.split(type)[1]

    first_dash_index = find_correct_dash_index(contract_str)
        
    symbol = contract_str[:first_dash_index-2]
    expiry = contract_str.split(symbol)[1]

    return pd.Series([symbol, expiry], index=['symbol', 'expiry'])


def add_ce_ticker(row):
    pe_ticker = row['ticker']
    ce_ticker = pe_ticker.replace('PE', 'CE')
    return [ce_ticker, pe_ticker]


def add_pe_ticker(row):
    ce_ticker = row['ticker']
    pe_ticker = ce_ticker.replace('CE', 'PE')
    return [ce_ticker, pe_ticker]


def convert_to_int(value):
    try:
        # Attempt to convert to integer
        return int(value)
    except (ValueError, TypeError):
        return None  # Return None for values that cannot be converted
    

#########! Main #########!
if __name__ == "__main__":
    st.set_page_config(layout="wide")
    main()


# streamlit run token_2.py