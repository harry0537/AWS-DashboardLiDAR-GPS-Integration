from flask import Flask, jsonify
from flask_cors import CORS
import boto3

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests

# DynamoDB Setup - Update endpoint_url if using DynamoDB Local
dynamodb = boto3.resource('dynamodb', region_name='us-west-2', endpoint_url='http://localhost:8000')
table = dynamodb.Table('UGVTelemetry')

@app.route('/api/telemetry')
def get_telemetry():
    response = table.scan()
    data = response.get('Items', [])
    return jsonify(data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
