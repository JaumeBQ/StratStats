import streamlit as st



def main():
    st.set_page_config(
    page_title="StratStats",
    page_icon="💰",
    )
    import ui_style as theme
    theme.apply_theme()
    st.title('Welcome to StratStats')
    st.markdown('A simple backtesting tool for your trading strategies, options and stocks portfolio.')
    #st.sidebar.title('Options')
    #st.sidebar.header('Welcome Page')

    




if __name__ == '__main__':
    main()
    