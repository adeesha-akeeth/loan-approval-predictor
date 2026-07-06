# Architecture — Loan Approval Predictor

## Why Docker Container Instead of ZIP Layer

### The Problem
Initial deployment attempted ZIP-based Lambda layers
for pandas, scikit-learn, numpy and scipy.

Combined unzipped size: ~400MB
AWS Lambda ZIP limit:   250MB

Attempts to reduce size by stripping test files
broke internal library structure causing
runtime syntax errors.

### The Solution
Switched to containerized Lambda using Amazon ECR.
Container images support up to 10GB — no size constraints.
Complete unbroken library installations preserved.

### Deployment Flow
CloudShell
-> docker build (Dockerfile)
-> docker push (ECR repository)
-> Lambda updated (aws lambda update-function-code)
-> API Gateway (unchanged)
-> S3 Frontend (unchanged)

### Cost
ECR free tier: 500MB private storage/month
Our image:     ~350MB
Cost:          $0.00

### Future Updates
1. Edit lambda_function.py
2. Rebuild image in CloudShell
3. Push to ECR
4. Run: aws lambda update-function-code
   --function-name loan-approval-container
   --image-uri 951869163850.dkr.ecr.ap-south-1.amazonaws.com/loan-approval:latest

## Full Architecture Diagram

```markdown
```mermaid
graph TD
    User[User Browser] -->|1. Visits URL| S3[S3 Static Website <br> index.html + style.css + app.js]
    S3 -->|2. HTTP POST fetch call with LKR values| APIGW[API Gateway HTTP API <br> HTTPS public endpoint / CORS enabled]
    APIGW -->|3. Forwards request| Lambda[AWS Lambda <br> Container image from ECR]
    S3_Model[Amazon S3 Bucket] -->|4. Loads model files on cold start| Lambda
    Lambda -->|5. Computes Prediction| Result[Response back to browser <br> probability + decision + key factors]

    style User fill:#f9f,stroke:#333,stroke-width:2px
    style S3 fill:#bbf,stroke:#333,stroke-width:2px
    style APIGW fill:#bfb,stroke:#333,stroke-width:2px
    style Lambda fill:#fbb,stroke:#333,stroke-width:2px
    style S3_Model fill:#fdd,stroke:#333,stroke-width:2px

```
## AWS Services Used

| Service     | Purpose                        | Cost          |
|-------------|--------------------------------|---------------|
| ECR         | Docker image registry          | Free (500MB)  |
| Lambda      | Serverless ML inference        | Free tier     |
| API Gateway | Public HTTPS endpoint          | Free tier     |
| S3          | Model storage + static website | Free tier     |
| CloudShell  | Build and deploy environment   | Free          |
| IAM         | Role based access control      | Free          |
| CloudWatch  | Logging and monitoring         | Free tier     |

Total monthly cost: $0.00