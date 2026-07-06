import json
import boto3
import numpy as np
import os
import io
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Global variables
# Loaded once on cold start
# Reused on warm invocations — key performance optimization
model         = None
feature_names = None
model_metadata = None

s3_client = boto3.client('s3')
BUCKET    = os.environ.get('BUCKET_NAME', 'your-bucket-name')
PREFIX    = os.environ.get('MODEL_PREFIX', 'models/loan-approval')

def load_models():
    """
    Load model artifacts from S3
    Only runs on Lambda cold start
    Subsequent warm invocations reuse
    the already-loaded model in memory
    """
    global model, feature_names, model_metadata
    import joblib

    logger.info("Cold start — loading models from S3...")

    # Load metadata first
    meta_obj = s3_client.get_object(
        Bucket=BUCKET,
        Key=f'{PREFIX}/model_metadata.json'
    )
    model_metadata = json.loads(meta_obj['Body'].read())
    logger.info(f"Model type: {model_metadata['model_type']}")
    logger.info(f"Uses scaler: {model_metadata['uses_scaler']}")

    # Load model
    model_obj = s3_client.get_object(
        Bucket=BUCKET,
        Key=f'{PREFIX}/loan_model.pkl'
    )
    model = joblib.load(io.BytesIO(model_obj['Body'].read()))

    # Load feature names
    features_obj = s3_client.get_object(
        Bucket=BUCKET,
        Key=f'{PREFIX}/feature_names.pkl'
    )
    feature_names = joblib.load(
        io.BytesIO(features_obj['Body'].read())
    )

    logger.info(f"Models loaded! Features: {feature_names}")

def build_response(status_code, body):
    """
    Build HTTP response with CORS headers
    CORS allows browser JavaScript to call this API
    Without these headers browser blocks the request
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin':  '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        },
        'body': json.dumps(body)
    }

def preprocess_input(data):
    """
    Apply EXACT same feature engineering as training
    Order and transformations must match perfectly
    """
    import pandas as pd

    try:
        gender        = int(data.get('gender', 1))
        married       = int(data.get('married', 1))
        dependents    = int(data.get('dependents', 0))
        education     = int(data.get('education', 0))
        self_employed = int(data.get('self_employed', 0))
        applicant_income   = float(data.get('applicant_income', 0))
        coapplicant_income = float(data.get('coapplicant_income', 0))
        loan_amount        = float(data.get('loan_amount', 0))
        loan_term          = float(data.get('loan_term', 360))
        credit_history     = float(data.get('credit_history', 1))
        property_area      = int(data.get('property_area', 1))

    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid input: {str(e)}")

    # Validate inputs
    if loan_amount <= 0:
        raise ValueError("Loan amount must be greater than 0")
    if applicant_income < 0:
        raise ValueError("Income cannot be negative")
    if loan_term <= 0:
        raise ValueError("Loan term must be greater than 0")

    # Feature engineering — must match training exactly
    total_income   = applicant_income + coapplicant_income
    emi            = loan_amount / loan_term
    balance_income = total_income - (emi * 1000)
    loan_amount_log   = np.log(loan_amount + 1)
    total_income_log  = np.log(total_income + 1)

    features = {
        'Gender':           gender,
        'Married':          married,
        'Dependents':       dependents,
        'Education':        education,
        'Self_Employed':    self_employed,
        'Loan_Amount_Term': loan_term,
        'Credit_History':   credit_history,
        'Property_Area':    property_area,
        'EMI':              emi,
        'Balance_Income':   balance_income,
        'LoanAmount_log':   loan_amount_log,
        'Total_Income_log': total_income_log
    }

    import pandas as pd
    df = pd.DataFrame([features])[feature_names]
    return df

def get_key_factors(input_df, probability, data):
    """
    Generate human readable explanation
    using original LKR values for display
    """
    factors = []

    credit  = input_df['Credit_History'].values[0]
    balance = input_df['Balance_Income'].values[0]
    emi     = input_df['EMI'].values[0]

    # Get original LKR values sent from frontend
    # These are exact values user entered
    income_lkr    = data.get('income_lkr', 0)
    co_income_lkr = data.get('co_income_lkr', 0)
    loan_lkr      = data.get('loan_lkr', 0)
    total_lkr     = income_lkr + co_income_lkr

    # Calculate balance in LKR using original values
    # EMI monthly payment estimate in LKR
    loan_term      = input_df['Loan_Amount_Term'].values[0]
    emi_lkr        = loan_lkr / loan_term
    balance_lkr    = total_lkr - emi_lkr

    logger.info(
        f"LKR values — income: {total_lkr}, "
        f"emi: {emi_lkr:.0f}, balance: {balance_lkr:.0f}"
    )

    # Credit history
    if credit == 1:
        factors.append(
            "Good credit history — strongest positive factor"
        )
    else:
        factors.append(
            "Poor credit history — strongest negative factor"
        )

    # Balance income in LKR
    if balance_lkr > 20000:
        factors.append(
            f"Strong monthly balance after loan repayment: "
            f"Rs. {balance_lkr:,.0f}"
        )
    elif balance_lkr > 0:
        factors.append(
            f"Positive but tight monthly balance: "
            f"Rs. {balance_lkr:,.0f}"
        )
    else:
        factors.append(
            f"Monthly repayment exceeds income — loan may be too large: "
            f"Rs. {abs(balance_lkr):,.0f} shortfall"
        )

    # Total income in LKR
    if total_lkr > 50000:
        factors.append(
            f"Strong total household income: "
            f"Rs. {total_lkr:,.0f} per month"
        )
    elif total_lkr > 25000:
        factors.append(
            f"Moderate household income: "
            f"Rs. {total_lkr:,.0f} per month"
        )
    else:
        factors.append(
            f"Lower income may affect repayment capacity: "
            f"Rs. {total_lkr:,.0f} per month"
        )

    # EMI assessment
    if emi_lkr < total_lkr * 0.3:
        factors.append(
            f"Loan repayment is within recommended range "
            f"(Rs. {emi_lkr:,.0f}/month)"
        )
    elif emi_lkr < total_lkr * 0.5:
        factors.append(
            f"Loan repayment is manageable "
            f"(Rs. {emi_lkr:,.0f}/month)"
        )
    else:
        factors.append(
            f"High monthly repayment relative to income "
            f"(Rs. {emi_lkr:,.0f}/month)"
        )

    return factors


def lambda_handler(event, context):
    """
    Main entry point for every Lambda invocation
    Called by API Gateway for each HTTP request
    """
    logger.info(f"Event: {json.dumps(event)}")

    # Handle CORS preflight request
    # Browser sends OPTIONS before actual POST
    # to check if cross-origin request is allowed
    http_method = (
        event.get('httpMethod') or
        event.get('requestContext', {})
             .get('http', {})
             .get('method', '')
    )
    if http_method == 'OPTIONS':
        return build_response(200, {'message': 'OK'})

    # Load model on cold start
    if model is None:
        load_models()

    try:
        # Parse request body
        body = event.get('body', '{}')
        if isinstance(body, str):
            data = json.loads(body)
        else:
            data = body or {}

        logger.info(f"Input: {data}")

        # Preprocess
        input_df = preprocess_input(data)

        # RF does not need scaler
        # But check metadata for future flexibility
        if model_metadata.get('uses_scaler', False):
            logger.warning(
                "Model requires scaler but scaler not loaded"
            )

        # Predict
        probability = float(
            model.predict_proba(input_df)[0][1]
        )
        decision    = 'APPROVED' if probability >= 0.5 else 'REJECTED'
        confidence  = max(probability, 1 - probability)
        key_factors = get_key_factors(input_df, probability, data)

        result = {
            'prediction':           decision,
            'approval_probability': round(probability * 100, 1),
            'confidence':           round(confidence * 100, 1),
            'key_factors':          key_factors,
            'model':                model_metadata['model_type'],
            'auc_score':            model_metadata.get('auc_score'),
            'disclaimer': (
                'This is a demonstration model only. '
                'Not for actual financial decisions.'
            )
        }

        logger.info(f"Result: {result}")
        return build_response(200, result)

    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return build_response(400, {'error': str(e)})

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return build_response(500, {
            'error': 'Internal server error. Please try again.'
        })
