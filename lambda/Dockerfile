# Base image — Python 3.12 Lambda runtime
FROM public.ecr.aws/lambda/python:3.12

# Install required libraries
RUN pip install \
    pandas \
    scikit-learn \
    numpy \
    scipy \
    joblib \
    boto3 \
    --no-cache-dir

# Copy Lambda function code
COPY lambda_function.py ${LAMBDA_TASK_ROOT}

# Set the handler
CMD ["lambda_function.lambda_handler"]