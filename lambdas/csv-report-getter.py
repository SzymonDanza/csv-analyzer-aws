import json
import boto3

s3 = boto3.client('s3')

REPORTS_BUCKET = 'BUCKET-NAME-PLACEHOLDER'


def lambda_handler(event, context):
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Content-Type': 'application/json'
    }
    
    request_context = event.get('requestContext', {})
    http_method = request_context.get('http', {}).get('method', '')
    
    if http_method == 'OPTIONS':
        return {'statusCode': 200, 'headers': headers, 'body': ''}
    
    try:
        path_params = event.get('pathParameters', {}) or {}
        filename = path_params.get('filename')
        
        if not filename:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Missing filename in path'})
            }
        
        if filename.endswith('.csv'):
            report_key = f"reports/{filename.replace('.csv', '.json')}"
        elif filename.endswith('.json'):
            report_key = f"reports/{filename}"
        else:
            report_key = f"reports/{filename}.json"
        
        print(f"Fetching report: s3://{REPORTS_BUCKET}/{report_key}")
        
        try:
            response = s3.get_object(Bucket=REPORTS_BUCKET, Key=report_key)
            report_content = response['Body'].read().decode('utf-8')
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': report_content
            }
        except s3.exceptions.NoSuchKey:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({
                    'error': 'Report not found',
                    'message': f'No report exists for {filename}. The file may not have been analyzed yet, or filename is incorrect.',
                    'looked_for': f's3://{REPORTS_BUCKET}/{report_key}'
                })
            }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }
