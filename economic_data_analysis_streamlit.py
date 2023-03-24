# https://wbdata.readthedocs.io/en/stable/

import streamlit as st
import pandas as pd
import wbdata as wb
import matplotlib.pyplot as plt


@st.cache_data
def fetch_world_bank_data(indicators, countries):
    # grab indicators above for countries above and load into data frame in session state
    # reset session state
    st.session_state.df_wb_indicators_countries = pd.DataFrame()
    st.session_state.df_wb_indicators_countries = wb.get_dataframe(
        indicators, country=countries, convert_date=False)


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
        self.show_dataframe = False

    def plotting(self):
        if not self.line_chart and not self.bar_chart and not self.pie_chart and not self.show_dataframe:
            return

        # title
        st.header(self.selected_indicator['name'])
        st.subheader(self.selected_indicator['id'])

        # line chart for history with full time series
        if self.line_chart == True:
            st.line_chart(data=self.df_indicator_per_country)

        # bar chart with last time series
        df_indicator_per_country = self.df_indicator_per_country.dropna(axis=0)
        if df_indicator_per_country.empty:
            bar_chart_data_last_year = self.df_indicator_per_country
        else:
            last_year = df_indicator_per_country.iloc(0)[0]
            first_year = df_indicator_per_country.iloc(0)[-1]
            bar_chart_data_last_year = last_year
            bar_chart_data_first_year = first_year
        if self.bar_chart == True:
            st.bar_chart(data=bar_chart_data_last_year)
            st.bar_chart(data=bar_chart_data_first_year)

        # pie chart with last time series
        if len(self.selected_country_names) > 1 and self.pie_chart == True and not df_indicator_per_country.empty:
            # Pie chart, where the slices will be ordered and plotted counter-clockwise:

            labels = []
            sizes_last_year = []
            sizes_first_year = []
            for country_name in self.selected_country_names:
                try:
                    if last_year[country_name] > 0 and first_year[country_name] > 0:
                        sizes_last_year.append(last_year[country_name])
                        sizes_first_year.append(first_year[country_name])
                        labels.append(country_name)
                    else:
                        st.write('Negative value for country ', country_name,
                                 ' could not be displayed in piechart')
                except:
                    st.write('Country ', country_name,
                             ' is not in last or first year')
                    continue

            piechart, axis_of_piechart = plt.subplots()

            axis_of_piechart.pie(sizes_last_year, labels=labels, autopct='%1.1f%%',
                                 shadow=False)
            # Equal aspect ratio ensures that pie is drawn as a circle.
            axis_of_piechart.axis('equal')

            st.header(last_year.name)
            st.pyplot(piechart)

            piechart, axis_of_piechart = plt.subplots()

            axis_of_piechart.pie(sizes_first_year, labels=labels, autopct='%1.1f%%',
                                 shadow=False)
            # Equal aspect ratio ensures that pie is drawn as a circle.
            axis_of_piechart.axis('equal')
            st.header(first_year.name)
            st.pyplot(piechart)

        if self.show_dataframe:
            st.dataframe(st.session_state.df_wb_indicators_countries)

        # explanation of indicator
        st.caption(self.selected_indicator['sourceNote'])

    def run(self):

        # initialize session state
        self.initialize_session_state()

        st.title('Economic Indicators')

        if st.session_state.df_wb_indicators_countries.empty:
            self.display_app_information()

        self.selected_source_name = st.sidebar.selectbox(
            'Sources', self.source_names)

        if self.selected_source_name:
            self.indicators = wb.get_indicator(
                source=[element for element in self.sources if element['name'] == self.selected_source_name][0]['id'])

            # build list of indicator names
            self.indicator_names = []
            for indicator in self.indicators:
                self.indicator_names.append(indicator['name'])

            self.selected_indicator_names = st.sidebar.multiselect(
                'Indicators', self.indicator_names)

        self.selected_country_names = st.sidebar.multiselect(
            'Country', self.country_names)

        self.create_checkboxes()

        # not enough defined to fetch data?
        nothing_to_process = not self.selected_country_names or \
                  not self.selected_indicator_names or \
                  not (self.line_chart or self.pie_chart or self.bar_chart or self.show_dataframe)
        
        if nothing_to_process:
            return
        

        fetch_to_execute =  self.selected_country_names and self.selected_indicator_names and \
               (not all(item in st.session_state.fetched_indicators for item in self.selected_indicator_names) or
                not all(item in st.session_state.fetched_countries for item in self.selected_country_names))

        # only process if selected data differs from displayed data
        if fetch_to_execute:

            self.selected_indicators = [
                element for element in self.indicators if element['name'] in self.selected_indicator_names]
            self.selected_countries = [
                element for element in self.countries if element['name'] in self.selected_country_names]
            # prepare parameter for api call
            indicators = {}
            countries = []

            # build dictionary of selected indicators
            st.session_state.fetched_indicators = []
            for indicator in self.selected_indicators:
                indicators[indicator['id']] = indicator['name']
                st.session_state.fetched_indicators.append(indicator['name'])

            # build list of selected countries
            st.session_state.fetched_countries = []
            for country in self.selected_countries:
                countries.append(country['id'])
                st.session_state.fetched_countries.append(country['name'])

            # grab indicators above for countries above and load into data frame
            try:
                fetch_world_bank_data(indicators, countries)
            except Exception as err:
                # reset session state
                st.session_state.fetched_countries = []
                st.session_state.fetched_indicators = []
                st.session_state.df_wb_indicators_countries = pd.DataFrame()
                st.header('Error fetching data at worldbank for:')
                st.write(countries)
                st.write(err)
                return

        # build dataframe df_indicator_per_country
        # for selected indicators and countries and plot it
        # only 1 indicator selected?
        if len(self.selected_indicator_names) == 1:
            self.selected_indicator = [
                element for element in self.indicators if element['name'] in self.selected_indicator_names][0]

            # ad column for each selected country
            # in dataframe df_indicator_per_country
            self.plot_indicator()

        else:
            df_indicator = pd.DataFrame()
            # plot each indicator for all selected countries
            self.plot_indicators()

        st.session_state.displayed_indicator_names = self.selected_indicator_names
        st.session_state.displayed_country_names = self.selected_country_names

    def create_checkboxes(self):
        self.line_chart = st.sidebar.checkbox(label='Line Chart')
        self.bar_chart = st.sidebar.checkbox(label='Bar Chart')
        self.pie_chart = st.sidebar.checkbox(label='Pie Chart')
        self.show_dataframe = st.sidebar.checkbox(label='Display Data')

    def plot_indicator(self):
        for country_name in self.selected_country_names:
            try:
                self.df_indicator_per_country[country_name] = st.session_state.df_wb_indicators_countries.loc[country_name]
            except:
                st.write('No data for ', country_name, ' fetched')

        self.plotting()

    def plot_indicators(self):
        for indicator_name in self.selected_indicator_names:
            try:
                df_indicator = st.session_state.df_wb_indicators_countries[indicator_name]
            except:
                st.write('No data for indicator ', indicator_name)
                continue

            self.get_indicator_for_countries(df_indicator, indicator_name)

            self.plotting()

    def get_indicator_for_countries(self, df_indicator, indicator_name):
        self.selected_indicator = [
            element for element in self.indicators if element['name'] == indicator_name][0]
        if len(self.selected_country_names) == 1:
            self.df_indicator_per_country = df_indicator
        else:
            self.append_indicator_for_countries(df_indicator, indicator_name)

    def append_indicator_for_countries(self, df_indicator, indicator_name):
        for country_name in self.selected_country_names:
            try:
                self.df_indicator_per_country[country_name] = df_indicator.loc[country_name]
            except:
                st.write('No data for ',
                         indicator_name, country_name)

    def display_app_information(self):
        st.write('1. Select source')
        st.write('2. Select indicators')
        st.write('3. Select countries')
        st.write('4. Select diagram types')
        st.write('5. Analyze data')

        st.write('Source: ', 'https://data.worldbank.org/')
        st.write('Interface: ', 'https://pypi.org/project/wbdata/')
        st.write('Processing: ', 'https://pandas.pydata.org/')
        st.write('Plotting: ', 'https://matplotlib.org/')
        st.write('App: ', 'https://docs.streamlit.io/')
        st.write('Repository: ',
                 'https://github.com/gitwalter/economic_data_analysis.git')

    def initialize_session_state(self):
        if 'displayed_country_names' not in st.session_state:
            st.session_state['displayed_country_names'] = []

        if 'displayed_indicator_names' not in st.session_state:
            st.session_state['displayed_indicator_names'] = []

        if 'fetched_countries' not in st.session_state:
            st.session_state['fetched_countries'] = []

        if 'fetched_indicators' not in st.session_state:
            st.session_state['fetched_indicators'] = []

        if 'df_wb_indicators_countries' not in st.session_state:
            st.session_state['df_wb_indicators_countries'] = pd.DataFrame()


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
