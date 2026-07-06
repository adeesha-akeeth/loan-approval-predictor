const API_URL = 'https://djcjjroim3.execute-api.ap-south-1.amazonaws.com/prod/predict';

// Normalization factor
// Dividing by 15 brings LKR inputs into model-compatible range
const SCALE_FACTOR = 15;

async function predict() {
    const btn        = document.getElementById('predict-btn');
    const resultCard = document.getElementById('result-card');
    const errorCard  = document.getElementById('error-card');

    resultCard.classList.add('hidden');
    errorCard.classList.add('hidden');

    // Get raw LKR values
    const incomeLKR   = parseFloat(
        document.getElementById('applicant_income').value
    );
    const coIncomeLKR = parseFloat(
        document.getElementById('coapplicant_income').value
    ) || 0;
    const loanLKR     = parseFloat(
        document.getElementById('loan_amount').value
    );

    // Validate
    if (!incomeLKR || incomeLKR <= 0) {
        showError('Please enter a valid monthly income');
        return;
    }
    if (!loanLKR || loanLKR <= 0) {
        showError('Please enter a valid loan amount');
        return;
    }

    // Scale values to model compatible range
    // Income: divide by SCALE_FACTOR
    // Loan: divide by SCALE_FACTOR then by 1000 (model expects loan in thousands)
    const incomeScaled   = incomeLKR   / SCALE_FACTOR;
    const coIncomeScaled = coIncomeLKR / SCALE_FACTOR;
    const loanScaled     = (loanLKR / SCALE_FACTOR) / 1000;

    const data = {
        gender:
            parseInt(document.getElementById('gender').value),
        married:
            parseInt(document.getElementById('married').value),
        dependents:
            parseInt(document.getElementById('dependents').value),
        education:
            parseInt(document.getElementById('education').value),
        self_employed:
            parseInt(document.getElementById('self_employed').value),
        applicant_income:   incomeScaled,
        coapplicant_income: coIncomeScaled,
        loan_amount:        loanScaled,
        loan_term:
            parseInt(document.getElementById('loan_term').value),
        credit_history:
            parseFloat(document.getElementById('credit_history').value),
        property_area:
            parseInt(document.getElementById('property_area').value),

        // Send original LKR values for display in key factors
        income_lkr:    incomeLKR,
        co_income_lkr: coIncomeLKR,
        loan_lkr:      loanLKR
    };

    btn.disabled    = true;
    btn.textContent = 'Analyzing...';

    try {
        const response = await fetch(API_URL, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify(data)
        });

        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }

        const result = await response.json();
        displayResult(result);

    } catch (error) {
        if (error.message.includes('Failed to fetch')) {
            showError(
                'Cannot connect to prediction service. ' +
                'Please check your connection and try again.'
            );
        } else {
            showError(error.message);
        }
    } finally {
        btn.disabled    = false;
        btn.textContent = 'Check My Loan Approval';
    }
}

function displayResult(result) {
    const resultCard  = document.getElementById('result-card');
    const resultIcon  = document.getElementById('result-icon');
    const resultText  = document.getElementById('result-text');
    const probBar     = document.getElementById('probability-bar');
    const probText    = document.getElementById('probability-text');
    const factorsList = document.getElementById('factors-list');

    const isApproved = result.prediction === 'APPROVED';
    const prob       = result.approval_probability;

    resultIcon.textContent = isApproved ? 'APPROVED' : 'REJECTED';
    resultText.textContent = isApproved
        ? 'Likely Approved'
        : 'Likely Rejected';
    resultText.className   = 'result-text ' +
        (isApproved ? 'approved' : 'rejected');

    probBar.style.width  = `${prob}%`;
    probBar.className    = 'prob-bar ' + (
        prob >= 70 ? 'high'   :
        prob >= 40 ? 'medium' : 'low'
    );
    probText.textContent = `${prob}% approval probability`;

    factorsList.innerHTML = '';
    const factors = result.key_factors || [];
    if (factors.length > 0) {
        factors.forEach(factor => {
            const li       = document.createElement('li');
            li.textContent = factor;
            factorsList.appendChild(li);
        });
    } else {
        const li       = document.createElement('li');
        li.textContent = 'No detailed factors available';
        factorsList.appendChild(li);
    }

    resultCard.classList.remove('hidden');
    resultCard.scrollIntoView({ behavior: 'smooth' });
}

function showError(message) {
    const errorCard = document.getElementById('error-card');
    document.getElementById('error-text').textContent = message;
    errorCard.classList.remove('hidden');
    errorCard.scrollIntoView({ behavior: 'smooth' });
}