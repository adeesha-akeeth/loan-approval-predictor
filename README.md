# Bank Loan Approval Predictor

## Live Demo

[http://loan-approval-app.s3-website.ap-south-1.amazonaws.com](http://loan-approval-app.s3-website.ap-south-1.amazonaws.com)

## Overview

A fully deployed machine learning web application predicting bank loan approval likelihood based on applicant details.

The application accepts Sri Lankan Rupee (LKR) values directly and returns an instant prediction with a probability score and key factors influencing the prediction.

For detailed deployment architecture and records, see [docs/architecture.md](docs/architecture.md).

## Architecture

```text
S3 Static Website -> API Gateway -> Lambda (ECR Container) -> S3 Models
```

### Why Docker Container Instead of ZIP Layer

The initial deployment used ZIP-based Lambda layers, but the combined size of pandas, scikit-learn, NumPy, and SciPy (~400 MB unzipped) exceeded AWS Lambda's 250 MB deployment package limit.

Attempting to reduce the package size by stripping unnecessary files broke internal library structures, resulting in runtime syntax errors.

**Solution:** The deployment was migrated to a containerized AWS Lambda using Amazon ECR. Lambda container images support up to 10 GB, allowing complete library installations without modification. The container was built and deployed using AWS CloudShell at no additional cost.

---

## ML Model

Three machine learning models were evaluated using GridSearchCV with 5-fold cross-validation.

| Model | Accuracy | Precision | Recall | F1 Score | AUC |
|---|---|---|---|---|---|
| Logistic Regression | 81.30% | 84.44% | 89.41% | 86.86% | 0.8207 |
| Decision Tree | 81.30% | 86.05% | 87.06% | 86.55% | 0.8215 |
| **Random Forest** | **85.37%** | **85.26%** | **95.29%** | **90.00%** | **0.8412** |

**Selected Model:** Random Forest (Highest F1 Score and AUC)

### Key Model Insights

- Shallow trees (`max_depth=3`) with `bootstrap=False` reduced overfitting on the 614-row dataset.
- High recall (95.29%) minimizes the chance of rejecting applicants likely to be approved.
- All models were tuned using GridSearchCV before comparison.

### Input Scaling

The model was trained on an Indian loan dataset containing lower monetary values. Therefore, LKR inputs are divided by a normalization factor of **15** before inference. This scaling is handled transparently in the frontend.

---

## AWS Services

| Service | Purpose | Cost |
|---|---|---|
| Amazon ECR | Docker container registry | Free |
| AWS Lambda | Serverless inference (container) | Free |
| Amazon API Gateway | Public HTTPS endpoint | Free |
| Amazon S3 | Model storage & static website hosting | Free |
| AWS CloudShell | Container build & deployment | Free |
| Amazon CloudWatch | Logging & monitoring | Free |

**Estimated Monthly Cost:** **$0.00**

---

## Repository Structure

```text
loan-approval-predictor/
├── docs/
│   └── architecture.md
├── frontend/
│   ├── app.js
│   ├── index.html
│   └── style.css
├── lambda/
│   ├── Dockerfile
│   └── lambda_function.py
├── model-training/
│   └── loan_approval_model.ipynb
├── .gitignore
└── README.md
```

---

## Challenges and Solutions

| Challenge | Solution |
|---|---|
| Lambda ZIP package exceeded 250 MB | Migrated to Docker container using Amazon ECR |
| Stripping libraries caused runtime errors | Used complete library installations inside the container |
| No local Docker environment | Built and deployed using AWS CloudShell |
| Browser CORS errors | Configured CORS in both API Gateway and Lambda |
| Model trained on INR values | Applied frontend normalization for LKR inputs |
| Incorrect LKR values in key factors | Passed original LKR values alongside scaled values |

---

## Author

**Adeesha**

Undergraduate, **BSc Honours in Information Technology Specializing Data Science**  
Sri Lanka Institute of Information Technology (SLIIT)
