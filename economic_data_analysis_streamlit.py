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

# load selected indicator values for countries
@st.cache_data
def load_world_bank_data(indicators, countries):
    # load data into session state for further processing
    st.session_state.df_wb_indicators_countries = wb.get_dataframe(
        indicators, country=countries, convert_date=False)

# load indicators for selected source
@st.cache_data
def load_indicators_of_source(source):
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
        # header for indicator
        st.header(self.selected_indicator['name'])
        st.subheader(self.selected_indicator['id'])

        # explanation of indicator
        st.caption(self.selected_indicator['sourceNote'])

        if self.df_indicator_per_country.empty:
            return

        # line chart for history with full time series
        if self.show_line_chart:
            st.line_chart(data=self.df_indicator_per_country)

        # bar chart with last and first time series for comparison
        if self.show_bar_chart or self.show_pie_chart:
            first_year, last_year = self.get_begin_end()

            show_bar_chart = self.show_bar_chart
            show_pie_chart = self.show_pie_chart

            if not 'first_year' in locals():
                show_bar_chart = False
                show_pie_chart = False
            elif first_year.empty:
                show_bar_chart = False
                show_pie_chart = False

            if show_bar_chart:
                try:
                    self.plot_bar_charts(last_year, first_year)
                except Exception as err:
                    st.write('Bar charts could not be generated')
                    st.write(err)

            # pie chart with first and last time series
            if show_pie_chart:
                if len(self.selected_country_names) <= 1:
                    st.write('Only one country selected, pie chart not supported')

                if len(self.selected_country_names) > 1 and not self.df_indicator_per_country.empty:
                    self.plot_pie_charts(last_year, first_year)

        # display dataframe for indicator
        if self.show_dataframe:
            st.dataframe(self.df_indicator_per_country)

    def plot_bar_charts(self, bar_chart_data_last_year, bar_chart_data_first_year):
        st.bar_chart(data=bar_chart_data_last_year)
        st.bar_chart(data=bar_chart_data_first_year)

    def plot_pie_charts(self, last_year, first_year):
        labels = []
        sizes_last_year = []
        sizes_first_year = []

        self.get_pie_chart_labels_sizes(
            last_year, first_year, labels, sizes_last_year, sizes_first_year)

        self.plot_pie_chart_for_year(last_year, labels, sizes_last_year)

        self.plot_pie_chart_for_year(first_year, labels, sizes_first_year)

    def get_pie_chart_labels_sizes(self, last_year, first_year, labels, sizes_last_year, sizes_first_year):
        # iterate over selected countries
        # and append sizes and labels for first and last year
        # if values are above 0 since negative values
        # could not be displayed in a pie chart
        for country_name in self.selected_country_names:
            try:
                if last_year[country_name] > 0 and first_year[country_name] > 0:
                    sizes_last_year.append(last_year[country_name])
                    sizes_first_year.append(first_year[country_name])
                    labels.append(country_name)
                else:

                    error_message = 'Negative value for country ' + country_name + \
                                    ' could not be displayed in piechart'

                    st.error(error_message, icon="🤖")
            except:
                error_message = 'No data for first or last year for ' + country_name
                st.error(error_message, icon="🔥")
                continue

    def plot_pie_chart_for_year(self, last_year, labels, sizes_year):
        piechart, axis_of_piechart = plt.subplots()

        axis_of_piechart.pie(sizes_year, labels=labels, autopct='%1.1f%%',
                             shadow=False)

        axis_of_piechart.axis('equal')

        st.header(last_year.name)
        st.pyplot(piechart)

    def get_begin_end(self):
        # if 1 country is selected indicator_per_country is a pandas.Series
        # if many countries are selected indicator per country is a pandas.DataFrame
        indicator_per_country = self.df_indicator_per_country.dropna(axis=0)
        if indicator_per_country.empty:
            error_message = 'Not enough data for charts of first or last year of time series for indicator ' + \
                            self.selected_indicator['name'] + '.' + \
                            ' Try the line chart or display the dataframe for the indicator and exclude countries with bad data quality and try again.'

            st.error(error_message, icon="🔥")

            return pd.Series(), pd.Series()
        else:
            try:
                first_year = indicator_per_country.iloc(0)[-1]
                last_year = indicator_per_country.iloc(0)[0]
            except:
                error_message = 'Error iloc at handling with dataframe: ' + indicator_per_country
                st.error(error_message, icon="🔥")
                return pd.Series, pd.Series()

            if len(self.selected_country_names) == 1:
                selected_country_name = self.selected_country_names[0]

                if type(indicator_per_country) is pd.DataFrame:
                    try:
                        indicator_for_one_country = indicator_per_country[[
                            selected_country_name]]
                    except:
                        error_message = 'No data for indicator' + self.selected_indicator['name'] + \
                                        ' and country ' + selected_country_name
                        st.error(error_message, icon="🔥")
                        return None, None
                    first_year = indicator_for_one_country.iloc[-1]
                    last_year = indicator_for_one_country.iloc[0]

                else:
                    indicator_for_one_country = indicator_per_country
                    first_year_value = indicator_for_one_country[-1]
                    first_year_date = indicator_for_one_country.index[-1][1]
                    first_year_dict = {selected_country_name: first_year_value}
                    first_year = pd.Series(data=first_year_dict, index=[
                                           selected_country_name], name=first_year_date)

                    last_year_value = indicator_for_one_country[0]
                    last_year_date = indicator_for_one_country.index[0][1]
                    last_year_dict = {selected_country_name: last_year_value}
                    last_year = pd.Series(data=last_year_dict, index=[
                                          selected_country_name], name=last_year_date)

            return first_year, last_year

    def run(self):

        # initialize session state
        self.initialize_session_state()

        st.sidebar.header('Selection')

        self.selected_source_name = st.sidebar.selectbox(
            'Source', self.source_names)

        if self.selected_source_name:
            self.create_mulitiselect_indicator_country()
        
        if st.session_state.df_wb_indicators_countries.empty:
            self.display_app_information()
        else:
            self.set_title()

        self.create_checkboxes()

        # not enough defined to fetch data?
        nothing_to_process = not self.selected_country_names or \
            not self.selected_indicator_names or \
            not (self.show_line_chart or self.show_pie_chart or self.show_bar_chart or self.show_dataframe)

        if nothing_to_process:            
            st.header('Indicator list')            
            df_indicator_display = pd.DataFrame(self.indicators)
            df_indicator_display = df_indicator_display[['id', 'name', 'sourceNote']]
            st.dataframe(df_indicator_display)
                        
            st.header('Country list')
            df_country_display = pd.DataFrame(self.countries)
            st.dataframe(df_country_display)                        
            return

        load_to_execute = self.selected_country_names and self.selected_indicator_names and \
            (not all(item in st.session_state.loaded_indicators for item in self.selected_indicator_names) or
             not all(item in st.session_state.loaded_countries for item in self.selected_country_names))

        # only process if selected data differs from displayed data
        if load_to_execute:
            # grab indicators above for countries above and load into data frame
            try:
                indicators, countries = self.get_parameter_for_api_call()
                load_world_bank_data(indicators, countries)                
                self.set_title()
            except Exception as err:
                # reset session state
                self.initialize_session_state()
                self.reset_session_state()
                country_string = ''
                for country_name in self.selected_country_names:
                    country_string = country_string + ' ' + country_name
                error_message = 'Error during dataload from worldbank for:' + country_string
                st.error(error_message, icon="🔥")
                return

        if len(self.selected_indicator_names) == 1:
            # plot one indicator
            self.plot_indicator()
        else:
            # plot each indicator for all selected countries
            self.plot_indicators()

    def set_title(self):
        title = 'Source: ' + self.selected_source_name
        st.title(title)

    def get_parameter_for_api_call(self):
        self.selected_indicators = [
            element for element in self.indicators if element['name'] in self.selected_indicator_names]
        self.selected_countries = [
            element for element in self.countries if element['name'] in self.selected_country_names]

        # prepare parameter for api call
        indicators = {}
        countries = []

        # build dictionary of selected indicators
        # for api call and append to session state
        st.session_state.loaded_indicators = []
        for indicator in self.selected_indicators:
            indicators[indicator['id']] = indicator['name']
            st.session_state.loaded_indicators.append(indicator['name'])

        # build list of selected countries
        # for api call and append to session state
        st.session_state.loaded_countries = []
        for country in self.selected_countries:
            countries.append(country['id'])
            st.session_state.loaded_countries.append(country['name'])
        return indicators, countries

    def create_mulitiselect_indicator_country(self):
        self.indicators = load_indicators_of_source(
            [element for element in self.sources if element['name'] == self.selected_source_name][0]['id'])
        # build list of indicator names
        indicator_names = []
        for indicator in self.indicators:
            indicator_names.append(indicator['name'])

        self.selected_indicator_names = st.sidebar.multiselect(
            'Indicator', indicator_names)

        self.selected_country_names = st.sidebar.multiselect(
            'Country', self.country_names)

    def create_checkboxes(self):
        st.sidebar.header('Output')
        self.show_line_chart = st.sidebar.checkbox(label='Line Chart')
        self.show_bar_chart = st.sidebar.checkbox(label='Bar Chart')
        self.show_pie_chart = st.sidebar.checkbox(label='Pie Chart')
        self.show_dataframe = st.sidebar.checkbox(label='Dataframe')

    def plot_indicator(self):
        self.selected_indicator = [
            element for element in self.indicators if element['name'] in self.selected_indicator_names][0]
        for country_name in self.selected_country_names:
            try:
                self.df_indicator_per_country[country_name] = st.session_state.df_wb_indicators_countries.loc[country_name]
            except:
                error_message = 'No data for ' + country_name
                st.error(error_message, icon="🔥")

        self.output()

    def plot_indicators(self):
        for indicator_name in self.selected_indicator_names:
            try:
                indicator = st.session_state.df_wb_indicators_countries[indicator_name]
            except:
                error_message = 'No data for indicator ' + indicator_name
                st.error(error_message, icon="🔥")
                continue

            self.get_indicator_for_countries(indicator, indicator_name)

            self.output()

    def get_indicator_for_countries(self, indicator, indicator_name):
        self.selected_indicator = [
            element for element in self.indicators if element['name'] == indicator_name][0]
        if len(self.selected_country_names) == 1:
            try:
                self.df_indicator_per_country = indicator.loc[self.selected_country_names[0]]
            except:
                error_message = 'No data for ' + self.selected_country_names[0]
                st.error(error_message, icon="🔥")
                return
        else:
            self.append_indicator_for_countries(indicator, indicator_name)

    def append_indicator_for_countries(self, df_indicator, indicator_name):
        for country_name in self.selected_country_names:
            try:
                self.df_indicator_per_country[country_name] = df_indicator.loc[country_name]
            except:
                error_message = 'No data for indicator' + indicator_name + \
                    'and country ' + country_name
                st.error(error_message, icon="🔥")

    def display_app_information(self):
        st.header('How to use')
        st.write('1. Select source')
        st.write('2. Select indicators')
        st.write('3. Select countries')
        st.write('4. Select output')
        st.write('5. Analyze data')
        st.write('Data load starts after selection of output. To avoid data load after each parameter change deactivate output during selection of indicators or countries.')

        st.write('Source: ', 'https://data.worldbank.org/')
        st.write('Interface: ', 'https://pypi.org/project/wbdata/')
        st.write('Processing: ', 'https://pandas.pydata.org/')
        st.write('Plotting: ', 'https://matplotlib.org/')
        st.write('App: ', 'https://docs.streamlit.io/')
        st.write('Repository: ',
                 'https://github.com/gitwalter/economic_data_analysis.git')

    def initialize_session_state(self):
        if 'loaded_countries' not in st.session_state:
            st.session_state['loaded_countries'] = []

        if 'loaded_indicators' not in st.session_state:
            st.session_state['loaded_indicators'] = []

        if 'df_wb_indicators_countries' not in st.session_state:
            st.session_state['df_wb_indicators_countries'] = pd.DataFrame()

    def reset_session_state(self):
        st.session_state.loaded_indicators = []
        st.session_state.loaded_countries = []
        st.session_state.df_wb_indicators_countries = pd.DataFrame()
application = start()
application.run()
