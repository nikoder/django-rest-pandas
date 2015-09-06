from rest_framework.test import APITestCase
from tests.testapp.models import ComplexTimeSeries
from rest_pandas.test import parse_csv
from wq.io import load_string
import unittest
try:
    from matplotlib.cbook import boxplot_stats
except ImportError:
    boxplot_stats = None


class ComplexTestCase(APITestCase):
    def setUp(self):
        data = (
            ('site1', 'height', 'ft', '2015-01-01', 'routine', 0.5, None),
            ('site1', 'height', 'ft', '2015-01-02', 'routine', 0.4, None),
            ('site1', 'height', 'ft', '2015-01-03', 'routine', 0.6, None),
            ('site1', 'height', 'ft', '2015-01-04', 'special', 0.2, None),
            ('site1', 'height', 'ft', '2015-01-05', 'routine', 0.1, None),

            ('site1', 'flow', 'cfs', '2015-01-01', 'special', 0.7, None),
            ('site1', 'flow', 'cfs', '2015-01-02', 'routine', 0.8, None),
            ('site1', 'flow', 'cfs', '2015-01-03', 'routine', 0.0, 'Q'),
            ('site1', 'flow', 'cfs', '2015-01-04', 'routine', 0.9, None),
            ('site1', 'flow', 'cfs', '2015-01-05', 'routine', 0.3, None),

            ('site2', 'flow', 'cfs', '2015-01-01', 'routine', 0.0, None),
            ('site2', 'flow', 'cfs', '2015-01-02', 'routine', 0.7, None),
            ('site2', 'flow', 'cfs', '2015-01-03', 'routine', 0.2, None),
            ('site2', 'flow', 'cfs', '2015-01-04', 'routine', 0.3, None),
            ('site2', 'flow', 'cfs', '2015-01-05', 'routine', 0.8, None),
        )
        for site, parameter, units, date, type, value, flag in data:
            ComplexTimeSeries.objects.create(
                site=site,
                parameter=parameter,
                units=units,
                date=date,
                type=type,
                value=value,
                flag=flag,
            )

    def test_complex_series(self):
        response = self.client.get("/complextimeseries.csv")
        self.assertEqual(
            """,,flag,value,value,value
            units,,cfs,cfs,cfs,ft
            parameter,,flow,flow,flow,height
            site,,site1,site1,site2,site1
            date,type,,,,
            2015-01-01,routine,,,0.0,0.5
            2015-01-01,special,,0.7,,
            2015-01-02,routine,,0.8,0.7,0.4
            2015-01-03,routine,Q,0.0,0.2,0.6
            2015-01-04,routine,,0.9,0.3,
            2015-01-04,special,,,,0.2
            2015-01-05,routine,,0.3,0.8,0.1
            """.replace(' ', ''),
            response.content.decode('utf-8'),
        )
        datasets = self.parse_unstacked_csv(response)
        self.assertEqual(len(datasets), 3)
        for dataset in datasets:
            self.assertEqual(len(dataset['data']), 5)

        s1flow = None
        s1height = None
        s2flow = None
        for dataset in datasets:
            if dataset['site'] == "site1":
                if dataset['parameter'] == "flow":
                    s1flow = dataset
                else:
                    s1height = dataset
            else:
                s2flow = dataset

        d0 = s1height['data'][0]
        self.assertEqual(d0['date'], '2015-01-01')
        self.assertEqual(d0['value'], 0.5)

        d1 = s1flow['data'][2]
        self.assertEqual(d1['date'], '2015-01-03')
        self.assertEqual(d1['value'], 0.0)
        self.assertEqual(d1['flag'], 'Q')

        d2 = s2flow['data'][4]
        self.assertEqual(d2['date'], '2015-01-05')
        self.assertEqual(d2['value'], 0.8)

    def test_complex_scatter(self):
        response = self.client.get("/complexscatter.csv")
        self.assertEqual(
            """,,flow-cfs-value,flow-cfs-value,height-ft-value
            site,,site1,site2,site1
            date,type,,,
            2015-01-02,routine,0.8,0.7,0.4
            2015-01-03,routine,0.0,0.2,0.6
            2015-01-05,routine,0.3,0.8,0.1
            """.replace(' ', ''),
            response.content.decode('utf-8')
        )
        datasets = self.parse_unstacked_csv(response)
        self.assertEqual([
            {'site': 'site1', 'data': [
                {'date': '2015-01-02', 'type': 'routine',
                 'flow-cfs-value': 0.8, 'height-ft-value': 0.4},
                {'date': '2015-01-03', 'type': 'routine',
                 'flow-cfs-value': 0.0, 'height-ft-value': 0.6},
                {'date': '2015-01-05', 'type': 'routine',
                 'flow-cfs-value': 0.3, 'height-ft-value': 0.1},
                ]},
            {'site': 'site2', 'data': [
                {'date': '2015-01-02', 'type': 'routine',
                 'flow-cfs-value': 0.7},
                {'date': '2015-01-03', 'type': 'routine',
                 'flow-cfs-value': 0.2},
                {'date': '2015-01-05', 'type': 'routine',
                 'flow-cfs-value': 0.8},
                ]},
        ], datasets)

    @unittest.skipUnless(boxplot_stats, "test requires matplotlib 1.4+")
    def test_complex_boxplot(self):
        # Default group=series-year
        response = self.client.get("/complexboxplot.csv")
        datasets = self.parse_unstacked_csv(response)

        self.assertEqual(len(datasets), 3)
        s1flow = None
        s1height = None
        s2flow = None
        for dataset in datasets:
            if dataset['site'] == "site1":
                if dataset['parameter'] == "flow":
                    s1flow = dataset
                else:
                    s1height = dataset
            else:
                s2flow = dataset

        self.assertEqual(len(s1height['data']), 1)
        self.assertEqual(s1height['units'], 'ft')
        stats = s1height['data'][0]
        self.assertEqual(stats['year'], '2015')
        self.assertEqual(stats['value-whislo'], 0.1)
        self.assertEqual(stats['value-mean'], 0.36)
        self.assertEqual(stats['value-whishi'], 0.6)

        self.assertEqual(s1flow['units'], 'cfs')
        stats = s1flow['data'][0]
        self.assertEqual(stats['year'], '2015')
        self.assertEqual(stats['value-whislo'], 0.0)
        self.assertEqual(round(stats['value-mean'], 8), 0.54)
        self.assertEqual(stats['value-whishi'], 0.9)

        self.assertEqual(s2flow['units'], 'cfs')
        stats = s2flow['data'][0]
        self.assertEqual(stats['year'], '2015')
        self.assertEqual(stats['value-whislo'], 0.0)
        self.assertEqual(stats['value-mean'], 0.4)
        self.assertEqual(stats['value-whishi'], 0.8)

    @unittest.skipUnless(boxplot_stats, "test requires matplotlib 1.4+")
    def test_complex_boxplot_series(self):
        response = self.client.get("/complexboxplot.csv?group=series")
        datasets = self.parse_unstacked_csv(response)
        s1flow = None
        s1height = None
        s2flow = None
        for dataset in datasets:
            if dataset['site'] == "site1":
                if dataset['parameter'] == "flow":
                    s1flow = dataset
                else:
                    s1height = dataset
            else:
                s2flow = dataset

        self.assertEqual(len(s1height['data']), 1)
        stats = s1height['data'][0]
        self.assertNotIn('year', stats)
        self.assertEqual(stats['value-whislo'], 0.1)
        self.assertEqual(stats['value-mean'], 0.36)
        self.assertEqual(stats['value-whishi'], 0.6)

        stats = s1flow['data'][0]
        self.assertNotIn('year', stats)
        self.assertEqual(stats['value-whislo'], 0.0)
        self.assertEqual(round(stats['value-mean'], 8), 0.54)
        self.assertEqual(stats['value-whishi'], 0.9)

        self.assertEqual(len(s1flow['data']), 1)
        stats = s2flow['data'][0]
        self.assertNotIn('year', stats)
        self.assertEqual(stats['value-whislo'], 0.0)
        self.assertEqual(stats['value-mean'], 0.4)
        self.assertEqual(stats['value-whishi'], 0.8)

    @unittest.skipUnless(boxplot_stats, "test requires matplotlib 1.4+")
    def test_complex_boxplot_month_group(self):
        response = self.client.get("/complexboxplot.csv?group=series-month")
        datasets = self.parse_unstacked_csv(response)
        s1flow = None
        s1height = None
        s2flow = None
        for dataset in datasets:
            if dataset['site'] == "site1":
                if dataset['parameter'] == "flow":
                    s1flow = dataset
                else:
                    s1height = dataset
            else:
                s2flow = dataset

        self.assertEqual(len(s1height['data']), 1)
        stats = s1height['data'][0]
        self.assertEqual(stats['month'], '1')
        self.assertEqual(stats['value-whislo'], 0.1)
        self.assertEqual(stats['value-mean'], 0.36)
        self.assertEqual(stats['value-whishi'], 0.6)

        stats = s1flow['data'][0]
        self.assertEqual(stats['month'], '1')
        self.assertEqual(stats['value-whislo'], 0.0)
        self.assertEqual(round(stats['value-mean'], 8), 0.54)
        self.assertEqual(stats['value-whishi'], 0.9)

        self.assertEqual(len(s1flow['data']), 1)
        stats = s2flow['data'][0]
        self.assertEqual(stats['month'], '1')
        self.assertEqual(stats['value-whislo'], 0.0)
        self.assertEqual(stats['value-mean'], 0.4)
        self.assertEqual(stats['value-whishi'], 0.8)

    @unittest.skipUnless(boxplot_stats, "test requires matplotlib 1.4+")
    def test_complex_boxplot_year(self):
        response = self.client.get("/complexboxplot.csv?group=year")
        datasets = self.parse_plain_csv(response)
        self.assertEqual(len(datasets), 1)
        stats = datasets[0]
        self.assertEqual(stats['year'], 2015)
        self.assertEqual(stats['value-whislo'], 0.0)
        self.assertEqual(round(stats['value-mean'], 5), 0.43333)
        self.assertEqual(stats['value-whishi'], 0.9)

    def parse_unstacked_csv(self, response):
        return parse_csv(response.content.decode('utf-8'))

    def parse_plain_csv(self, response):
        data = load_string(response.content.decode('utf-8')).data
        for row in data:
            for key in row:
                try:
                    row[key] = float(row[key])
                except ValueError:
                    pass
        return data
