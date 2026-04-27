import json
import boto3
import base64
import uuid
from datetime import datetime

s3 = boto3.client('s3')

UPLOADS_BUCKET = 'BUCKET-NAME-PLACEHOLDER'
MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024


def lambda_handler(event, context):
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Content-Type': 'application/json'
    }
    
    request_context = event.get('requestContext', {})
    http_method = request_context.get('http', {}).get('method', '')
    
    if http_method == 'OPTIONS':
        return {'statusCode': 200, 'headers': headers, 'body': ''}
    
    try:
        body = event.get('body', '')
        is_base64 = event.get('isBase64Encoded', False)
        
        if not body:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Empty request body'})
            }
        
        if is_base64:
            csv_content = base64.b64decode(body).decode('utf-8')
        else:
            csv_content = body
        
        content_size_bytes = len(csv_content.encode('utf-8'))
        
        if content_size_bytes > MAX_FILE_SIZE_BYTES:
            return {
                'statusCode': 413,
                'headers': headers,
                'body': json.dumps({
                    'error': 'File too large',
                    'max_size_mb': round(MAX_FILE_SIZE_BYTES / (1024 * 1024), 2),
                    'received_size_mb': round(content_size_bytes / (1024 * 1024), 2),
                    'message': f'Maximum file size is {round(MAX_FILE_SIZE_BYTES / (1024 * 1024), 1)} MB. Please upload a smaller CSV.'
                })
            }
        
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        filename = f'upload_{timestamp}_{unique_id}.csv'
        
        s3.put_object(
            Bucket=UPLOADS_BUCKET,
            Key=filename,
            Body=csv_content,
            ContentType='text/csv'
        )
        
        print(f"File uploaded: s3://{UPLOADS_BUCKET}/{filename} ({content_size_bytes} bytes)")
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'status': 'success',
                'message': 'File uploaded successfully. Analysis will be available shortly.',
                'filename': filename,
                'size_bytes': content_size_bytes
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }
