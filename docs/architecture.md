# Loan Approval Predictor Architecture

> End-to-end architecture and deployment documentation.

## Overview

This project is a serverless machine learning web application hosted entirely on AWS. Users submit loan application details through a static website, which invokes an AWS Lambda function via API Gateway to perform inference using a trained Scikit-learn model.

---

## Architecture Decision Record (ADR)

### Decision

Deploy the Lambda function as a **Docker container** instead of using a ZIP package with Lambda Layers.

### Context

The project depends on:

- pandas
- numpy
- scipy
- scikit-learn

The combined uncompressed size was approximately **400 MB**, exceeding the AWS Lambda ZIP deployment limit of **250 MB**.

Attempts to reduce package size by stripping files caused runtime import and syntax errors.

### Outcome

A containerized Lambda stored in **Amazon ECR** was adopted.

**Benefits**

- Supports images up to **10 GB**
- No dependency trimming required
- Faster, repeatable deployments
- Production-ready packaging

---

## High-Level Architecture

```text
                 ┌──────────────────────┐
                 │     User Browser     │
                 └──────────┬───────────┘
                            │
                            ▼
                 Amazon S3 Static Website
          (HTML • CSS • JavaScript Frontend)
                            │
                  HTTPS POST (fetch API)
                            │
                            ▼
                  Amazon API Gateway (HTTP)
                            │
                            ▼
           AWS Lambda (Docker Container on ECR)
        Python 3.12 • Scikit-learn • Pandas
                            │
             Loads trained model from Amazon S3
                            │
                            ▼
                 Prediction + Probability
                            │
                            ▼
                 JSON Response to Browser
```

---

## Deployment Workflow

```text
Developer
    │
    ▼
AWS CloudShell
    │
docker build
    │
docker push
    │
Amazon ECR
    │
aws lambda update-function-code
    │
AWS Lambda
    │
API Gateway
    │
Amazon S3 Website
```

---

## Deployment Updates

```bash
aws lambda update-function-code \
  --function-name loan-approval-container \
  --image-uri 951869163850.dkr.ecr.ap-south-1.amazonaws.com/loan-approval:latest
```

---

## AWS Services

| Service | Purpose | Cost |
|---------|---------|------|
| Amazon S3 | Static website + ML model storage | Free Tier |
| AWS Lambda | Serverless inference | Free Tier |
| Amazon ECR | Docker image registry | Free Tier (500 MB) |
| Amazon API Gateway | Public HTTPS API | Free Tier |
| AWS CloudShell | Build environment | Free |
| AWS IAM | Access management | Free |
| Amazon CloudWatch | Logs & monitoring | Free Tier |

---

## Estimated Monthly Cost

| Resource | Estimated Cost |
|----------|---------------:|
| Entire deployment | **$0.00 (Free Tier)** |

---

## Future Improvements

- CI/CD using GitHub Actions
- Model versioning
- Automated Docker image tagging
- Infrastructure as Code (Terraform/AWS SAM)
- Monitoring dashboards with CloudWatch
- HTTPS custom domain
