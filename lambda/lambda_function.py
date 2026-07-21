import json
import os
import boto3
import pickle
import joblib
import numpy as np
import pandas as pd

s3 = boto3.client('s3')

BUCKET_NAME = os.environ.get('BUCKET_NAME', 'data-lake-226')
MODEL_PREFIX = os.environ.get('MODEL_PREFIX', 'models/loan-approval')
MODEL_PATH = '/tmp/loan_model.pkl'

model = None

def load_model():
    global model
    if model is None:
        try:
            s3.download_file(BUCKET_NAME, f"{MODEL_PREFIX}/loan_model.pkl", MODEL_PATH)
            try:
                model = joblib.load(MODEL_PATH)
            except Exception:
                with open(MODEL_PATH, 'rb') as f:
                    model = pickle.load(f)
        except Exception as e:
            raise e

def lambda_handler(event, context):
    load_model()
    
    if 'body' in event:
        try:
            data = json.loads(event['body'])
        except Exception:
            data = event
    else:
        data = event

    try:
        # Extract base values
        gender = float(data.get('gender', 1))
        married = float(data.get('married', 0))
        dependents = float(data.get('dependents', 0))
        education = float(data.get('education', 0))
        self_employed = float(data.get('self_employed', 0))
        applicant_income = float(data.get('applicant_income', 0))
        coapplicant_income = float(data.get('coapplicant_income', 0))
        loan_amount = float(data.get('loan_amount', 0))
        loan_term = float(data.get('loan_term', 360))
        credit_history = float(data.get('credit_history', 1.0))
        property_area = float(data.get('property_area', 2))
        
        # Display variables (frontend metrics)
        income_lkr = float(data.get('income_lkr', 0))
        co_income_lkr = float(data.get('co_income_lkr', 0))
        loan_lkr = float(data.get('loan_lkr', 0))
        
        # Calculate engineered features exactly as the model expects them
        total_income = applicant_income + coapplicant_income
        emi = (loan_amount * 1000) / loan_term if loan_term > 0 else 0
        balance_income = total_income - emi
        
        # Safe log transformations (handling zero values safely)
        loan_amount_log = np.log(loan_amount * 1000) if loan_amount > 0 else 0
        total_income_log = np.log(total_income) if total_income > 0 else 0
        
        # Construct dataframe with the exact feature names and order required
        feature_dict = {
            'Gender': gender,
            'Married': married,
            'Dependents': dependents,
            'Education': education,
            'Self_Employed': self_employed,
            'Loan_Amount_Term': loan_term,
            'Credit_History': credit_history,
            'Property_Area': property_area,
            'EMI': emi,
            'Balance_Income': balance_income,
            'LoanAmount_log': loan_amount_log,
            'Total_Income_log': total_income_log
        }
        
        df = pd.DataFrame([feature_dict])
        
        prediction_code = model.predict(df)[0]
        
        if hasattr(model, "predict_proba"):
            prob = model.predict_proba(df)[0][1]
            approval_probability = int(round(prob * 100))
        else:
            approval_probability = 80 if prediction_code == 1 else 20
            
        prediction_text = "APPROVED" if prediction_code == 1 else "REJECTED"
        
        key_factors = []
        if credit_history == 1.0:
            key_factors.append("Good credit history — strongest positive factor")
        else:
            key_factors.append("Poor credit history — significantly increases risk of rejection")
            
        monthly_installment = loan_lkr / loan_term if loan_term > 0 else 0
        total_income_lkr = income_lkr + co_income_lkr
        disposable_balance = total_income_lkr - monthly_installment
        
        if disposable_balance > (total_income_lkr * 0.4):
            key_factors.append(f"Healthy monthly surplus remaining: Rs. {int(round(disposable_balance)):,}")
        elif disposable_balance > 0:
            key_factors.append(f"Positive but tight monthly balance: Rs. {int(round(disposable_balance)):,}")
        else:
            key_factors.append(f"Negative projected monthly balance: Rs. {int(round(disposable_balance)):,}")
            
        if total_income_lkr < 40000:
            key_factors.append(f"Lower overall income tier: Rs. {int(round(total_income_lkr)):,}/month may limit scaling")
            
        key_factors.append(f"Loan repayment calculated at: Rs. {int(round(monthly_installment)):,}/month over {int(loan_term)} months")
        
        response_body = {
            "prediction": prediction_text,
            "approval_probability": approval_probability,
            "key_factors": key_factors
        }
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps(response_body)
        }
        
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({"error": f"Model execution failed: {str(e)}"})
        }
