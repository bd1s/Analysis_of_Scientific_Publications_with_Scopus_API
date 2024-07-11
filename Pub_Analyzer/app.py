from flask import Flask, render_template, send_from_directory, jsonify
from data_analysis import retrieve_and_process_data, generate_analysis
from rdf_generation import generate_rdf_for_comp
import os

app = Flask(__name__)

topics = ['COMP', 'ENGI', 'MEDI', 'BIOC', 'CHEM', 'PHYS', 'MATH', 'ECON', 'SOCI', 'PSYC']

def perform_data_analysis():
    df = retrieve_and_process_data(topics)
    generate_analysis(df)
    print("Data retrieval, processing, and visualization completed.")

if not os.path.exists('static/plots/citations_distribution.png'):
    perform_data_analysis()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/plots/<path:path>')
def serve_plot(path):
    return send_from_directory('static/plots', path)

@app.route('/generate_rdf', methods=['POST'])
def generate_rdf():
    try:
        generate_rdf_for_comp() 
        return jsonify({'message': 'RDF Generation Completed'})
    except Exception as e:
        return jsonify({'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
