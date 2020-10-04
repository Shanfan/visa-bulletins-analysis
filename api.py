#!/usr/bin/python3

import urllib.request
import lxml.html
import pandas
import dateutil
import flask
from flask import request, jsonify

def get_url(fiscal_year):

    BASEURL = 'https://travel.state.gov'
    VISABULLETTINS = BASEURL + '/content/travel/en/legal/visa-law0/visa-bulletin.html'

    vb_index = urllib.request.urlopen(VISABULLETTINS).read()
    tree = lxml.html.fromstring(vb_index)

    bulletins = list()

    for link in tree.iterlinks():
        # example of a link: "/content/travel/en/legal/visa-law0/visa-bulletin/2020/visa-bulletin-for-may-2020.html"
        if '/visa-bulletin/' in link[2]:
            # select only Visa Bulletin from a few latest fiscal years
            # Note: US Govt FYs starts on October, and they are part of the URL components
            if int(link[2].split('/')[7]) >= fiscal_year:
                bulletins.append(BASEURL + link[2])
    bulletins.pop(0)
    return bulletins

def get_date(table, category, country):
    # Category only takes 2 or 3, corresponding to eb2 or eb3
    date = table[country][category]
    if date == 'C':
        return current_month
    else:
        return dateutil.parser.parse(date)

def get_bulletins(country, fiscal_year):
    # Country only takes 2 or 4, corresponding to China or India
    bulletins = list()

    for bulletin in get_url(fiscal_year):
        # the month the bulletin refers to
        current_month = dateutil.parser.parse('1 ' + bulletin.split('/')[-1].replace('visa-bulletin-for-', '').replace('.html', ''))
        data = pandas.read_html(bulletin)
        counter = 0

        for table in data:
            # there are multiple tables, we care about the two "Employment-based" table
            if 'employment' in table[0][0].lower() and counter==0:
                eb3_action_date = get_date(table,3, country)
                eb2_action_date = get_date(table,2, country)
                counter += 1
                continue
            if 'employment' in table[0][0].lower() and counter==1:
                eb3_filing_date = get_date(table,3, country)
                eb2_filing_date = get_date(table,2, country)
                break

        bulletins.append({
            current_month.strftime('%Y-%m'): {
                'eb2': {
                    'filing_date': eb2_filing_date.strftime('%Y-%m-%d'),
                    'action_date': eb2_action_date.strftime('%Y-%m-%d')
                },
                'eb3': {
                    'filing_date': eb3_filing_date.strftime('%Y-%m-%d'),
                    'action_date': eb3_action_date.strftime('%Y-%m-%d')
                }
            }
        })
    return bulletins

app = flask.Flask(__name__)
app.config["DEBUG"] = True

@app.route('/',methods=['GET'])
def home():
    return "<h1>Hello!</h1>"

@app.route('/api/bulletins/all',methods=['GET'])
def bulletins():
    return jsonify(get_bulletins(4, 2021)+get_bulletins(2, 2021)) #placeholder for now

@app.route('/api/bulletins',methods=['GET'])
def api_query():
    queries = request.args
    if queries:
        fy = int(queries.get('fy'))
        if 'country' in queries:
            country = queries.get('country')
            if country == 'india':
                return jsonify(get_bulletins(4, fy))
            if country == 'china':
                return jsonify(get_bulletins(2, fy))
            else:
                return "Error: country can only be either 'china' or 'india." 
        else:
            return jsonify({            
                'china': get_bulletins(2, fy),
                'india': get_bulletins(4, fy)
            })
    else:
        return "Error: No fiscal year provided."
app.run()