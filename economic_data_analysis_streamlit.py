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

        # build list of source names
        self.sources = pd.DataFrame(sources)
        self.source_names = self.sources['name'].tolist()

        # create dataframe of countries
        self.countries = self.build_country_dataframe(countries)

        # build list of country names
        self.country_names = []
        self.country_names = self.countries['name'].tolist()

        # get distinct regions
        self.regions = self.countries.region.unique().tolist()

        # get distinct income levels
        self.income_levels = self.countries.incomeLevel.unique().tolist()

        # initialize dataframe for indicators
        self.indicators = pd.DataFrame()

        # initialize dataframe for charts
        self.indicator_per_country = pd.DataFrame()

        # initialize variables representing selected parameter
        self.initialize_selection_parameter()

        # initialize checkbox representation for output
        self.initialize_output_control()

    def run(self):

        # initialize session state
        self.initialize_session_state()

        st.sidebar.header('Selection')

        self.selected_source_name = st.sidebar.selectbox(
            'Source', self.source_names)

        if self.selected_source_name:
            self.create_mulitiselects()

        # display app information if no data loaded
        if st.session_state.df_wb_indicators_countries.empty:
            self.display_app_information()
        # display title if data has been loaded
        else:
            self.set_title()

        self.create_checkboxes()

        self.get_selected_country_names()

        # not enough defined to fetch data?
        no_output_requested = not (self.selected_country_names or self.selected_regions or self.selected_income_levels) or \
            not self.selected_indicator_names or \
            not (self.show_line_chart or self.show_pie_chart or self.show_bar_chart or self.show_dataframe)

        # display indicator and country list
        # if no output is requested
        if no_output_requested:
            self.display_indicators_countries()
            return

        new_data_requested = self.selected_country_names and self.selected_indicator_names and \
            (not all(item in st.session_state.loaded_indicators for item in self.selected_indicator_names) or
             not all(item in st.session_state.loaded_countries for item in self.selected_country_names))

        # only process if selected data differs from displayed data
        if new_data_requested:
            # load indicators for countries
            try:
                indicators, countries = self.get_parameter_for_api_call()
                load_world_bank_data(indicators, countries)
                self.set_title()
            except:
                # reset session state
                self.initialize_session_state()
                self.reset_session_state()
                string_of_countries = ''
                for country_name in self.selected_country_names:
                    string_of_countries = string_of_countries + ' ' + country_name
                error_message = 'Error during dataload from worldbank for:' + string_of_countries
                st.error(error_message, icon="🔥")
                
                return

        if len(self.selected_indicator_names) == 1:
            # plot one indicator
            self.plot_indicator()

        else:
            # plot each indicator for all selected countries
            self.plot_indicators()

    def display_indicators_countries(self):
        if st.checkbox('Show Indicator List'):
            st.header('Indicator List')
            df_indicator_display = pd.DataFrame(self.indicators)
            df_indicator_display = df_indicator_display[[
                'id', 'name', 'sourceNote']]
            st.dataframe(df_indicator_display)

        if st.checkbox('Show Country List'):
            st.header('Country List')
            st.dataframe(self.countries)

    def get_selected_country_names(self):
        # countries are selected by names, regions or income levels
        if not (self.selected_country_names or self.selected_regions or self.selected_income_levels):
            return

        # append countries of selected regions
        countries_of_regions = self.countries[self.countries['region'].isin(
            self.selected_regions)]['name'].tolist()
        if not self.selected_country_names:
            self.selected_country_names = countries_of_regions
        else:
            self.selected_country_names.extend(countries_of_regions)

        countries_of_incomeLevels = self.countries[self.countries['incomeLevel'].isin(
            self.selected_income_levels)]['name'].tolist()
        if not self.selected_country_names:
            self.selected_country_names = countries_of_incomeLevels
        else:
            self.selected_country_names.extend(countries_of_incomeLevels)

        self.selected_country_names = list(set(self.selected_country_names))

    def output(self):
        # header for indicator
        st.header(self.selected_indicator.iloc[0]['name'])
        st.subheader(self.selected_indicator.iloc[0]['id'])

        # explanation of indicator
        st.caption(self.selected_indicator.iloc[0]['sourceNote'])

        if self.indicator_per_country.empty:
            return

        # line chart for history with full time series
        if self.show_line_chart:
            st.line_chart(data=self.indicator_per_country)

        # bar chart with last and first time series for comparison
        if self.show_bar_chart or self.show_pie_chart:
            first_year, last_year = self.get_begin_end()

            show_bar_chart = self.show_bar_chart
            show_pie_chart = self.show_pie_chart

            # data not set?
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

                if len(self.selected_country_names) > 1 and not self.indicator_per_country.empty:
                    self.plot_pie_charts(last_year, first_year)

        # display dataframe for indicator
        if self.show_dataframe:
            st.dataframe(self.indicator_per_country)

    def plot_indicator(self):
        # set selected indicator from selected indicator name
        self.selected_indicator = self.indicators[self.indicators['name']
                                                  == self.selected_indicator_names[0]]

        # iterate over countries and read indicator
        # for country from session state
        for country_name in self.selected_country_names:
            try:
                self.indicator_per_country[country_name] = st.session_state.df_wb_indicators_countries.loc[country_name]
            except:
                warning_message = 'No data for ' + country_name
                st.warning(warning_message, icon="⚠️")

        self.output()

    def plot_indicators(self):
        # iterate over indicators
        # and read indicator data for all countries from session state
        for indicator_name in self.selected_indicator_names:
            try:
                indicator = st.session_state.df_wb_indicators_countries[indicator_name]
            except:
                warning_message = 'No data for indicator ' + indicator_name
                st.error(warning_message, icon="⚠️")
                continue

            self.get_indicator_for_countries(indicator, indicator_name)

            self.output()

    def initialize_output_control(self):
        self.show_line_chart = False
        self.show_bar_chart = False
        self.show_pie_chart = False
        self.show_dataframe = False

    def initialize_selection_parameter(self):
        self.selected_source_name = None
        self.selected_indicator = None
        self.selected_country_names = []
        self.selected_indicator_names = []
        self.selected_regions = []
        self.selected_income_levels = []

    def build_country_dataframe(self, countries):
        self.countries = pd.DataFrame(countries)
        
        # unpack dictionaries in columns region and incomeLevel
        regions_in_countries = self.countries['region'].apply(pd.Series)
        regions_in_countries = regions_in_countries.rename(
            columns={"id": "RegionID", "iso2code": "Regioniso2code", "value": "region"})

        self.countries = pd.concat([self.countries.drop(
            ['region'], axis=1), regions_in_countries["region"]], axis=1)
        self.countries = self.countries.drop(
            columns=['iso2Code', 'adminregion', 'lendingType'])

        income_levels_in_countries = self.countries['incomeLevel'].apply(
            pd.Series)
        income_levels_in_countries = income_levels_in_countries.rename(
            columns={"id": "incomeLevelID", "iso2code": "incomeLeveliso2code", "value": "incomeLevel"})

        return pd.concat([self.countries.drop(['incomeLevel'], axis=1), income_levels_in_countries["incomeLevel"]], axis=1)

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

                    warning_message = 'Negative value for country ' + country_name + \
                        ' could not be displayed in piechart'

                    st.warning(warning_message, icon="⚠️")
            except:
                warning_message = 'No data for first or last year for ' + country_name
                st.warning(warning_message, icon="⚠️")
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

        # try to get rid of rows containing missing values        
        indicator_per_country = self.indicator_per_country.dropna(axis=0)

        # hase every row has missing values
        if indicator_per_country.empty:
            # try to get rid of columns containing missing values
            indicator_per_country = self.indicator_per_country.dropna(axis=1)

        if indicator_per_country.empty:            
            error_message = 'Not enough data for charts of first or last year of time series for indicator ' + \
                            self.selected_indicator.iloc[0]['name'] + '.' + \
                            ' Try the line chart or display the dataframe for the indicator and exclude countries with bad data quality and try again.'
            st.error(error_message, icon="🔥")
            return pd.Series(dtype=float), pd.Series(dtype=float)
        
        else:
            # read first and last year
            try:
                first_year = indicator_per_country.iloc(0)[-1]
                last_year = indicator_per_country.iloc(0)[0]
            except:
                error_message = 'Error iloc at handling with dataframe: ' + indicator_per_country
                st.error(error_message, icon="🔥")
                return pd.Series(dtype=float), pd.Series(dtype=float)

            # get first and last year for single country
            if len(self.selected_country_names) == 1:

                selected_country_name = self.selected_country_names[0]
                if type(indicator_per_country) is pd.DataFrame:
                    first_year, last_year = self.get_begin_end_from_dataframe(
                        indicator_per_country, selected_country_name)

                else:
                    first_year, last_year = self.get_begin_end_from_series(
                        indicator_per_country, selected_country_name)

            return first_year, last_year

    def get_begin_end_from_dataframe(self, indicator_per_country, selected_country_name):
        try:
            indicator_for_one_country = indicator_per_country[[
                selected_country_name]]
        except:
            warning_message = 'No data for indicator' + self.selected_indicator.iloc[0]['name'] + \
                ' and country ' + selected_country_name
            st.warning(warning_message, icon="⚠️")
            return pd.Series(), pd.Series()

        return indicator_for_one_country.iloc[-1], indicator_for_one_country.iloc[0]

    def get_begin_end_from_series(self, indicator_per_country, selected_country_name):
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

    def set_title(self):
        title = 'Source: ' + self.selected_source_name
        st.title(title)

    def get_parameter_for_api_call(self):

        df_selected_indicators = self.indicators[(self.indicators['name']).isin(
            self.selected_indicator_names)][['id', 'name']]

        # build dictionary of selected indicators
        indicators = {}
        indicators = pd.Series(
            df_selected_indicators.name.values, index=df_selected_indicators.id).to_dict()

        # write session state
        st.session_state.loaded_indicators = df_selected_indicators['name'].to_list(
        )

        # build list of selected countries
        # for api call and append to session state
        countries = []
        countries = self.countries[(self.countries['name']).isin(
            self.selected_country_names)]['id'].to_list()

        # st.session_state.loaded_countries = []
        st.session_state.loaded_countries = self.countries[(
            self.countries['name']).isin(self.selected_country_names)]['name'].to_list()

        return indicators, countries

    def create_mulitiselects(self):
        self.indicators = load_indicators_of_source(
            self.sources[self.sources['name'] == self.selected_source_name]['id'].iloc[0])
        self.indicators = pd.DataFrame(self.indicators)
        # build list of indicator names
        indicator_names = self.indicators['name'].to_list()

        self.selected_indicator_names = st.sidebar.multiselect(
            'Indicator', indicator_names)

        self.selected_country_names = st.sidebar.multiselect(
            'Country', self.country_names)

        self.selected_regions = st.sidebar.multiselect(
            'Region', self.regions)

        self.selected_income_levels = st.sidebar.multiselect(
            'Income Level', self.income_levels)

    def create_checkboxes(self):
        st.sidebar.header('Output')
        self.show_line_chart = st.sidebar.checkbox(label='Line Chart')
        self.show_bar_chart = st.sidebar.checkbox(label='Bar Chart')
        self.show_pie_chart = st.sidebar.checkbox(label='Pie Chart')
        self.show_dataframe = st.sidebar.checkbox(label='Dataframe')

    def get_indicator_for_countries(self, indicator, indicator_name):
        # self.selected_indicator = [
        #     element for element in self.indicators if element['name'] == indicator_name][0]
        self.selected_indicator = self.indicators[self.indicators['name']
                                                  == indicator_name]
        if len(self.selected_country_names) == 1:
            try:
                self.indicator_per_country = indicator.loc[self.selected_country_names[0]]
            except:
                warning_message = 'No data for ' + \
                    self.selected_country_names[0]
                st.warning(warning_message, icon="⚠️")
                return
        else:
            self.append_indicator_for_countries(indicator, indicator_name)

    def append_indicator_for_countries(self, df_indicator, indicator_name):
        for country_name in self.selected_country_names:
            try:
                self.indicator_per_country[country_name] = df_indicator.loc[country_name]
            except:
                warning_message = 'No data for indicator ' + indicator_name + \
                    ' and country ' + country_name
                st.warning(warning_message, icon="⚠️")

    def display_app_information(self):
        st.header('How to use')
        st.write('1. Select source')
        st.write('2. Select indicators')
        st.write('3. Select countries by name, region or income level')
        st.write('4. Select output')
        st.write('5. Analyze data')
        st.write('Data load starts after selection of output types. To avoid data load after each parameter change deactivate checkboxes for output during selection of indicators,countries, regions or income levels.')

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
