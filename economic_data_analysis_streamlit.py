# https://wbdata.readthedocs.io/en/stable/

import streamlit as st
import pandas as pd
import wbdata as wb
import matplotlib.pyplot as plt

# get datasources and countries from https://data.worldbank.org/
# and build instance of application method is cached and processed
# only at start of the application


@st.cache_data
def start():
    application = EconomicDataAnalysis(wb.get_source(), wb.get_country())
    return application

# fetch selected indicator values for countries


@st.cache_data
def fetch_world_bank_data(indicators, countries):
    # load data into session state for further processing
    st.session_state.df_wb_indicators_countries = wb.get_dataframe(
        indicators, country=countries, convert_date=False)

# fetch indicators for selected source


@st.cache_data
def fetch_indicators_of_source(source):
    return wb.get_indicator(source=source)


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

        # initialize variables representing selected parameter
        self.selected_source_name = None
        self.selected_indicator = None
        self.selected_country_names = []
        self.selected_indicator_names = []

        # initialize checkbox representation for output
        self.show_line_chart = False
        self.show_bar_chart = False
        self.show_pie_chart = False
        self.show_dataframe = False

    def output(self):
        if not (self.show_line_chart or self.show_bar_chart or self.show_pie_chart or self.show_dataframe):
            return

        # title
        st.header(self.selected_indicator['name'])
        st.subheader(self.selected_indicator['id'])

        # explanation of indicator
        st.caption(self.selected_indicator['sourceNote'])

        # line chart for history with full time series
        if self.show_line_chart:
            st.line_chart(data=self.df_indicator_per_country)

        # display dataframe for indicator
        if self.show_dataframe:
            st.dataframe(self.df_indicator_per_country)

        # bar chart with last and first time series for comparison
        if self.show_bar_chart or self.show_pie_chart:
            first_year, last_year = self.get_begin_end()

        # because of missing data first year or last year could not be determined
        if not 'first_year' in locals() or not 'last_year' in locals():
            return

        if self.show_bar_chart:
            try:
                self.plot_bar_charts(last_year, first_year)
            except Exception as err:
                st.write('Bar charts could not be generated')
                st.write(err)

        # pie chart with first and last time series
        if self.show_pie_chart:
            if len(self.selected_country_names) <= 1:
                st.write('Only one country selected, pie chart not supported')

            if len(self.selected_country_names) > 1 and not self.df_indicator_per_country.empty:
                self.plot_pie_charts(last_year, first_year)

    def plot_bar_charts(self, bar_chart_data_last_year, bar_chart_data_first_year):
        st.bar_chart(data=bar_chart_data_last_year)
        st.bar_chart(data=bar_chart_data_first_year)

    def plot_pie_charts(self, last_year, first_year):
        labels = []
        sizes_last_year = []
        sizes_first_year = []

        self.get_labels_and_sizes(last_year, first_year, labels, sizes_last_year, sizes_first_year)

        self.plot_pie_for_year(last_year, labels, sizes_last_year)

        self.plot_pie_for_year(first_year, labels, sizes_first_year)

    def get_labels_and_sizes(self, last_year, first_year, labels, sizes_last_year, sizes_first_year):
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
      

    def plot_pie_for_year(self, last_year, labels, sizes_last_year):
        piechart, axis_of_piechart = plt.subplots()

        axis_of_piechart.pie(sizes_last_year, labels=labels, autopct='%1.1f%%',
                             shadow=False)
        
        axis_of_piechart.axis('equal')

        st.header(last_year.name)
        st.pyplot(piechart)

    def get_begin_end(self):
        # if 1 country is selected indicator_per_country is a pandas.Series
        # if many counties are selected indicator per country is a pandas.DataFrame
        indicator_per_country = self.df_indicator_per_country.dropna(axis=0)
        if indicator_per_country.empty:
            st.write('Not enough datapoints for charts of first or last year of time series for indicator ',
                     self.selected_indicator['name'], '.')
            st.write(
                'Try the line chart or display the dataframe for the indicator and exclude the countries with missing data and try angain.')
            return None, None
        else:
            try:
                first_year = indicator_per_country.iloc(0)[-1]
                last_year = indicator_per_country.iloc(0)[0]
            except:
                st.write('Error iloc at handling with dataframe: ',
                         indicator_per_country)
                return None, None

            if len(self.selected_country_names) == 1:
                selected_country_name = self.selected_country_names[0]

                indicator_for_one_country = indicator_per_country[[
                    self.selected_country_names[0]]]
                
                first_year_value = indicator_for_one_country[-1]
                
                first_year_dict = {
                    self.selected_country_names[0]: first_year_value}
                
                first_year_date = indicator_for_one_country.index[-1][1]

                first_year = pd.Series(data=first_year_dict, index=[selected_country_name], name=first_year_date)

                last_year_value = indicator_per_country[[
                    self.selected_country_names[0]]][0]
                
                last_year_dict = {
                    self.selected_country_names[0]: last_year_value}
                
                last_year_date = indicator_for_one_country.index[0][1]

                last_year = pd.Series(data=last_year_dict, index=[selected_country_name], name=last_year_date)
            return first_year, last_year

    def run(self):

        # initialize session state
        self.initialize_session_state()

        st.title('Economic Indicators')

        st.sidebar.header('Selection')

        if st.session_state.df_wb_indicators_countries.empty:
            self.display_app_information()

        self.selected_source_name = st.sidebar.selectbox(
            'Source', self.source_names)

        if self.selected_source_name:
            self.create_mulitiselect_indicator_country()

        self.create_checkboxes()

        # not enough defined to fetch data?
        nothing_to_process = not self.selected_country_names or \
            not self.selected_indicator_names or \
            not (self.show_line_chart or self.show_pie_chart or self.show_bar_chart or self.show_dataframe)

        if nothing_to_process:
            return

        fetch_to_execute = self.selected_country_names and self.selected_indicator_names and \
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
            # for api call and append to session state
            st.session_state.fetched_indicators = []
            for indicator in self.selected_indicators:
                indicators[indicator['id']] = indicator['name']
                st.session_state.fetched_indicators.append(indicator['name'])

            # build list of selected countries
            # for api call and append to session state
            st.session_state.fetched_countries = []
            for country in self.selected_countries:
                countries.append(country['id'])
                st.session_state.fetched_countries.append(country['name'])

            # grab indicators above for countries above and load into data frame
            try:
                fetch_world_bank_data(indicators, countries)
            except Exception as err:
                # reset session state
                self.initialize_session_state()
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

    def create_mulitiselect_indicator_country(self):
        self.indicators = fetch_indicators_of_source(
            [element for element in self.sources if element['name'] == self.selected_source_name][0]['id'])
        # build list of indicator names
        self.indicator_names = []
        for indicator in self.indicators:
            self.indicator_names.append(indicator['name'])

        self.selected_indicator_names = st.sidebar.multiselect(
            'Indicator', self.indicator_names)

        self.selected_country_names = st.sidebar.multiselect(
            'Country', self.country_names)

    def create_checkboxes(self):
        st.sidebar.header('Output')
        self.show_line_chart = st.sidebar.checkbox(label='Line Chart')
        self.show_bar_chart = st.sidebar.checkbox(label='Bar Chart')
        self.show_pie_chart = st.sidebar.checkbox(label='Pie Chart')
        self.show_dataframe = st.sidebar.checkbox(label='Dataframe')

    def plot_indicator(self):
        for country_name in self.selected_country_names:
            try:
                self.df_indicator_per_country[country_name] = st.session_state.df_wb_indicators_countries.loc[country_name]
            except:
                st.write('No data for ', country_name, ' fetched')

        self.output()

    def plot_indicators(self):
        for indicator_name in self.selected_indicator_names:
            try:
                df_indicator = st.session_state.df_wb_indicators_countries[indicator_name]
            except:
                st.write('No data for indicator ', indicator_name)
                continue

            self.get_indicator_for_countries(df_indicator, indicator_name)

            self.output()

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


application = start()
application.run()
