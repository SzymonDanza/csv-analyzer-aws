# CSV Analyzer Cloud

> Serverless web application on AWS that automatically analyzes CSV files and generates JSON reports with descriptive statistics and data quality insights.

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![AWS](https://img.shields.io/badge/AWS-Lambda%20%7C%20S3%20%7C%20API%20Gateway%20%7C%20DynamoDB-FF9900?logo=amazon-aws&logoColor=white)](https://aws.amazon.com/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## Overview

CSV Analyzer Cloud is a fully serverless application that automates the **exploratory data analysis (EDA)** phase that data engineers and analysts typically perform manually. Upload a CSV file through a web interface and receive an automated analysis including:

- **Structure overview** — rows, columns, types
- **Numeric statistics** — count, mean, min, max, sum
- **Categorical analysis** — unique values, most common, frequency
- **Data quality** — missing values per column, duplicate rows, completeness

## Architecture

```
USER (browser)
    │
    │ uploads CSV via web form
    ▼
[S3 — static website hosting] ─→ serves index.html
    │
    │ POST /upload (fetch API)
    ▼
[API Gateway — HTTP API]
    │
    │ invokes
    ▼
[Lambda: csv-uploader] ─→ saves file to S3 uploads bucket
                              │
                              │ S3 ObjectCreated event
                              ▼
                       [Lambda: csv-analyzer]
                          │            │
                          ▼            ▼
                    [S3 reports]  [DynamoDB metadata]
                          │
    GET /report/{filename}
                          │
[Lambda: csv-report-getter] ──┘
    │
    ▼
Frontend renders report
```

See [`architecture.md`](architecture.md) for detailed architecture documentation.

## Tech Stack

### AWS Services (region: `eu-central-1`)
- **Amazon S3** — three buckets (uploads, reports, static website hosting)
- **AWS Lambda** — three functions in Python 3.12
- **Amazon API Gateway** — HTTP API with REST endpoints
- **Amazon DynamoDB** — NoSQL metadata store
- **AWS IAM** — least-privilege roles for each Lambda
- **Amazon CloudWatch** — logs and monitoring

### Frontend
- HTML5, CSS3, vanilla JavaScript (Fetch API)
- Hosted as a static website on S3

## Repository Structure

```
csv-analyzer-aws/
├── lambdas/
│   ├── csv-analyzer.py          # core analyzer (S3 trigger)
│   ├── csv-uploader.py          # API upload handler
│   └── csv-report-getter.py     # API report fetcher
├── iam-policies/
│   ├── csv-analyzer-policy.json
│   ├── csv-uploader-policy.json
│   ├── csv-report-getter-policy.json
│   └── website-bucket-policy.json
├── frontend/
│   └── index.html               # web UI
├── examples/
│   ├── input/
│   │   ├── test-small.csv       # 6 rows for quick testing
│   │   └── employees.csv        # 10k rows for realistic demo
│   └── output/
│       └── test-small.json      # generated report example
├── architecture.md              # detailed architecture
├── DEPLOYMENT.md                # step-by-step deployment guide
└── README.md
```

## How It Works

1. **User uploads** a CSV file via the web frontend.
2. **JavaScript** sends a POST request to the API Gateway.
3. **API Gateway** routes the request to the `csv-uploader` Lambda.
4. **csv-uploader** validates file size (max 2 MB), generates a unique filename, and saves the file to the S3 uploads bucket.
5. **S3 ObjectCreated event** automatically triggers the `csv-analyzer` Lambda.
6. **csv-analyzer** downloads the file, parses CSV, computes statistics, and:
   - Saves a full JSON report to the S3 reports bucket
   - Saves metadata to DynamoDB
7. **Frontend** polls GET `/report/{filename}` to retrieve the report.
8. **csv-report-getter** Lambda fetches the JSON from S3 and returns it.
9. **Frontend** renders the report in a clean UI.

## Example Output

For a CSV with employee data, the analyzer generates:

```json
{
  "summary": {
    "total_rows": 208,
    "total_columns": 9,
    "column_names": ["employee_id", "full_name", "age", "department", ...]
  },
  "data_quality": {
    "duplicates_count": 8,
    "missing_per_column": {"age": 11, "salary_pln": 21, ...},
    "rows_with_any_missing": 110
  },
  "numeric_stats": {
    "age": {"count": 197, "mean": 42.3, "min": 22, "max": 62, "sum": 8333},
    "salary_pln": {"count": 187, "mean": 10547, "min": 4030, "max": 24820, ...}
  },
  "categorical_stats": {
    "department": {"unique_values": 10, "most_common": "IT", "most_common_count": 31},
    "city": {"unique_values": 10, "most_common": "Warszawa", "most_common_count": 33}
  }
}
```

See [`examples/output/test-small.json`](examples/output/test-small.json) for full example.

## Security

- **IAM least privilege** — each Lambda has only the permissions it needs (e.g., csv-analyzer can only read from uploads bucket and write to reports bucket)
- **CORS** configured explicitly on API Gateway
- **Request throttling** — 5 req/sec rate limit prevents abuse
- **File size limit** — 2 MB enforced at Lambda level
- **AWS Budget Alerts** — zero-spend budget alerts on any cost above $0.01
- **No public-write buckets** — only the website bucket has public read access; uploads and reports buckets are private

## Cost

The project runs entirely within **AWS Free Tier** for typical usage:

- Lambda: 1M invocations/month free (forever)
- API Gateway HTTP API: 1M requests/month free (first 12 months)
- S3: 5 GB storage + minimal requests free (first 12 months)
- DynamoDB: 25 GB storage on-demand free (forever)

**Expected monthly cost: $0.00**

## Deployment

See [`DEPLOYMENT.md`](DEPLOYMENT.md) for step-by-step deployment instructions.

## Limitations & Future Improvements

### Current Limitations
- **2 MB file size limit** — restricted by HTTP API hard limit (6 MB) and Lambda memory
- **CSV-only support** — no Excel, JSON, Parquet, or other formats
- **No authentication** — anyone with the API URL can use it (mitigated by throttling and budget alerts)

### Potential Improvements
- **Pre-signed URLs** for direct S3 uploads, bypassing the API Gateway 6 MB limit
- **API key or JWT authentication** for production usage
- **GenAI integration** — use OpenAI/Anthropic API to generate natural language summaries of datasets
- **Frontend enhancements** — interactive charts (Chart.js) for distribution visualization
- **Historical analyses view** — endpoint and UI for browsing past analyses from DynamoDB

## What I Learned

This was my first hands-on AWS project. Key takeaways:

- **Event-driven architecture** with S3 triggers + Lambda is powerful and elegant
- **IAM least privilege** is foundational — broad permissions are a security smell
- **HTTP API has hard limits** that shape architecture decisions (e.g., the 6 MB body limit motivated the file size validation)
- **Async by design** — separating upload acknowledgment from analysis improved UX (immediate response) and cost (Lambda runs only when needed)
- **CloudWatch is your debugging best friend** — every error message in this project was solved by reading logs first

## License

MIT — see [LICENSE](LICENSE) for details.

---

Built as a portfolio project to explore serverless architecture, event-driven design, and AWS cloud services.
