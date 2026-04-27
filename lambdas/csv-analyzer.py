import json
import boto3
import urllib.parse
import uuid
from datetime import datetime
from io import StringIO

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

REPORTS_BUCKET = 'YOUR-REPORTS-BUCKET-NAME'
DYNAMO_TABLE_NAME = 'csv-analyses'

DYNAMO_TABLE = dynamodb.Table(DYNAMO_TABLE_NAME)


def lambda_handler(event, context):
    try:
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'])
        
        print(f"Processing file: s3://{bucket}/{key}")
        
        response = s3.get_object(Bucket=bucket, Key=key)
        csv_content = response['Body'].read().decode('utf-8')
        
        lines = csv_content.strip().split('\n')
        if len(lines) < 2:
            raise ValueError("CSV file is empty or contains only header")
        
        headers = [h.strip() for h in lines[0].split(',')]
        rows = [line.split(',') for line in lines[1:]]
        
        report = analyze_csv(headers, rows, key)
        
        report_key = f"reports/{key.replace('.csv', '.json')}"
        s3.put_object(
            Bucket=REPORTS_BUCKET,
            Key=report_key,
            Body=json.dumps(report, indent=2, default=str),
            ContentType='application/json'
        )
        
        print(f"Report saved: s3://{REPORTS_BUCKET}/{report_key}")
        
        analysis_id = str(uuid.uuid4())
        DYNAMO_TABLE.put_item(
            Item={
                'analysis_id': analysis_id,
                'filename': key,
                'uploaded_at': datetime.utcnow().isoformat(),
                'rows_count': report['summary']['total_rows'],
                'columns_count': report['summary']['total_columns'],
                'duplicates_count': report['data_quality']['duplicates_count'],
                'has_missing_values': any(v > 0 for v in report['data_quality']['missing_per_column'].values()),
                'report_s3_key': report_key,
                'report_bucket': REPORTS_BUCKET
            }
        )
        
        print(f"Metadata saved to DynamoDB with id: {analysis_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'status': 'success',
                'analysis_id': analysis_id,
                'input_file': key,
                'report_location': f"s3://{REPORTS_BUCKET}/{report_key}",
                'rows_analyzed': report['summary']['total_rows']
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def analyze_csv(headers, rows, filename):
    total_rows = len(rows)
    total_columns = len(headers)
    
    missing_per_column = {}
    for col_idx, header in enumerate(headers):
        missing_count = sum(
            1 for row in rows 
            if col_idx >= len(row) or row[col_idx].strip() == ''
        )
        missing_per_column[header] = missing_count
    
    rows_as_tuples = [tuple(row) for row in rows]
    unique_rows = set(rows_as_tuples)
    duplicates_count = total_rows - len(unique_rows)
    
    rows_with_missing = sum(
        1 for row in rows
        if any(col_idx >= len(row) or row[col_idx].strip() == '' 
               for col_idx in range(total_columns))
    )
    
    numeric_stats = {}
    categorical_stats = {}
    
    for col_idx, header in enumerate(headers):
        values = [row[col_idx].strip() for row in rows 
                  if col_idx < len(row) and row[col_idx].strip()]
        
        if not values:
            continue
        
        try:
            numeric_values = [float(v) for v in values]
            numeric_stats[header] = {
                'count': len(numeric_values),
                'mean': round(sum(numeric_values) / len(numeric_values), 2),
                'min': min(numeric_values),
                'max': max(numeric_values),
                'sum': round(sum(numeric_values), 2)
            }
        except ValueError:
            value_counts = {}
            for v in values:
                value_counts[v] = value_counts.get(v, 0) + 1
            
            most_common = max(value_counts.items(), key=lambda x: x[1])
            categorical_stats[header] = {
                'unique_values': len(value_counts),
                'most_common': most_common[0],
                'most_common_count': most_common[1]
            }
    
    return {
        'filename': filename,
        'summary': {
            'total_rows': total_rows,
            'total_columns': total_columns,
            'column_names': headers
        },
        'data_quality': {
            'missing_per_column': missing_per_column,
            'duplicates_count': duplicates_count,
            'rows_with_any_missing': rows_with_missing
        },
        'numeric_stats': numeric_stats,
        'categorical_stats': categorical_stats
    }
