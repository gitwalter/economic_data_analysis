# https://wbdata.readthedocs.io/en/stable/

import streamlit as st
import pandas as pd
import wbdata as wb
import matplotlib.pyplot as plt


@st.cache_data
def fetch_world_bank_data(indicators, countries):
    #grab indicators above for countries above and load into data frame in session state           
    st.session_state.df_wb_indicators_countries = wb.get_dataframe(indicators, country=countries, convert_date=False)
    


class EconomicDataAnalysis:
   
    def __init__(self, sources, countries):      
        # get datasources and countries 
        # from https://data.worldbank.org/
        self.sources = sources
        self.countries = countries  
        
        
        # build list of country names
        self.country_names = []
        for country in self.countries:
            self.country_names.append(country['name'])
        
        # build list of source names
        self.source_names = []
        for source in self.sources:
            self.source_names.append(source['name'])


        # initialize dataframe for charts
        self.df_indicator_per_country = pd.DataFrame()

        # initialize selected indicator and selected
        # country names
        self.selected_source_name = None
        self.selected_indicator = None
        self.selected_country_names = []
        self.selected_indicator_names = []

        # initialize checkbox representation
        # for style of chart
        self.line_chart = False        
        self.bar_chart = False
        self.pie_chart = False
       

    def plotting(self):
        if not self.line_chart and not self.bar_chart and not self.pie_chart:
            return
        
        # title                        
        st.write(self.selected_indicator['id'])
        st.write(self.selected_indicator['name'])                

        # line chart for history with full time series
        if self.line_chart == True:            
            st.line_chart(data=self.df_indicator_per_country)
        
        # bar chart with last time series
        df_indicator_per_country = self.df_indicator_per_country.dropna(axis=0)
        last_year = df_indicator_per_country.iloc(0)[0]
        if df_indicator_per_country.empty:
           bar_chart_data = self.df_indicator_per_country
        else:
           bar_chart_data = last_year
        if self.bar_chart  == True:
            st.bar_chart(data=bar_chart_data)
        

        # pie chart with last time series
        if len(self.selected_country_names) > 1 and self.pie_chart == True:
            # Pie chart, where the slices will be ordered and plotted counter-clockwise:
            
            labels = self.selected_country_names
            sizes = []        
            for country_name in self.selected_country_names:
                sizes.append(last_year[country_name])                                        

            piechart, axis_of_piechart = plt.subplots()
      
            axis_of_piechart.pie(sizes, labels=labels, autopct='%1.1f%%',
                    shadow=False)
            axis_of_piechart.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.

            st.pyplot(piechart)

        # explanation of indicator
        st.write(self.selected_indicator['sourceNote'])
                   

    def run(self):

        # initialize session state
        if 'displayed_country_names' not in st.session_state:
            st.session_state['displayed_country_names'] = []

        if 'displayed_indicator_names' not in st.session_state:
            st.session_state['displayed_indicator_names'] = []

        if 'df_wb_indicators_countries' not in st.session_state:
            st.session_state['df_wb_indicators_countries'] = pd.DataFrame()


        st.title('Economic Indicators')
        self.selected_source_name = st.sidebar.selectbox('Sources', self.source_names)
        
        if self.selected_source_name:                        
            self.indicators = wb.get_indicator(source=[element for element in self.sources if element['name'] == self.selected_source_name][0]['id'])
            
           
           # build list of indicator names
            self.indicator_names = []
            for indicator in self.indicators:
                self.indicator_names.append(indicator['name'])

            self.selected_indicator_names = st.sidebar.multiselect('Indicators', self.indicator_names)

        
        self.selected_country_names = st.sidebar.multiselect('Country', self.country_names)

        self.line_chart = st.sidebar.checkbox(label='Line Chart')
        self.bar_chart = st.sidebar.checkbox(label='Bar Chart')
        self.pie_chart = st.sidebar.checkbox(label='Pie Chart')
        
        # not enough defined to fetch data?
        if not self.selected_country_names or \
           not self.selected_indicator_names or \
           not ( self.line_chart or self.pie_chart or self.bar_chart ):
           return

        # only process if selected data differs from displayed data
        if self.selected_country_names and self.selected_indicator_names and \
           ( not all(item in st.session_state.displayed_indicator_names for item in self.selected_indicator_names) or \
             not all(item in st.session_state.displayed_country_names for item in self.selected_country_names) ):
            
            self.selected_indicators = [element for element in self.indicators if element['name'] in self.selected_indicator_names]
            self.selected_countries = [element for element in self.countries if element['name'] in self.selected_country_names]
            # prepare parameter for api call
            indicators = {}
            countries = []

            # build dictionary of selected indicators
            for indicator in self.selected_indicators:
                indicators[indicator['id']] = indicator['name']

            # build list of selected countries
            for country in self.selected_countries:
                countries.append(country['id'])

            #grab indicators above for countries above and load into data frame
            try:        
                fetch_world_bank_data(indicators,countries)
            except Exception as err:
                st.write('error for', indicators, countries)
                st.write(err)
                return
            
        # build dataframe df_indicator_per_country
        # for selected indicators and countries and plot it
        # only 1 indicator selected?
        if len(self.selected_indicator_names) == 1:
            self.selected_indicator = [element for element in self.indicators if element['name'] in self.selected_indicator_names][0]
            # only 1 contry selected?
            if len(self.selected_country_names) == 1:
                    self.df_indicator_per_country = st.session_state.df_wb_indicators_countries
            else:
                # ad column for each selected country
                # in dataframe df_indicator_per_country
                for country_name in self.selected_country_names:
                    try:
                        self.df_indicator_per_country[country_name] = st.session_state.df_wb_indicators_countries.loc[country_name]
                    except:
                        st.write('No data for ', country_name, ' fetched')

            self.plotting()
            
        else:
            df_indicator = pd.DataFrame()
            # plot each indicator for all selected countries
            for indicator_name in self.selected_indicator_names:
                df_indicator = st.session_state.df_wb_indicators_countries[indicator_name]
                self.selected_indicator = [element for element in self.indicators if element['name'] == indicator_name ][0]
                if len(self.selected_country_names) == 1:
                    self.df_indicator_per_country = df_indicator
                else:
                    for country_name in self.selected_country_names:
                        self.df_indicator_per_country[country_name] = df_indicator.loc[country_name]

                self.plotting()   
    
        st.session_state.displayed_indicator_names = self.selected_indicator_names
        st.session_state.displayed_country_names = self.selected_country_names


# get datasources and countries 
# from https://data.worldbank.org/
# and build instance of application
# method is cached and processed
# only at start of the application
@st.cache_data
def start():  
    sources = wb.get_source()
    countries = wb.get_country()
    application = EconomicDataAnalysis(sources, countries)    
    return application

application = start()
application.run()


