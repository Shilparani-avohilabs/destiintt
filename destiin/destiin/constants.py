# Base URLs
MAIN_API_BASE_URL = "16.112.56.253"
OPS_API_BASE_URL = "http://18.60.41.154"
TASKS_API_BASE_URL = "16.112.56.253"

# API Endpoints
EMAIL_API_URL = f"{MAIN_API_BASE_URL}/main/v1/email/send"
HITPAY_CREATE_PAYMENT_URL = f"{MAIN_API_BASE_URL}/payments/v1/hitpay/create-payment"
HITPAY_REFUND_URL = f"{MAIN_API_BASE_URL}/payments/v1/hitpay/refund"
PRICE_COMPARISON_API_URL = f"{OPS_API_BASE_URL}/ops/v1/priceComparison"
EMAIL_AUTH_TOKEN_URL = f"{MAIN_API_BASE_URL}/crm/cbt/v1/utils/generateEmailActionToken"

# Task-specific endpoints (uses different base URL)
TASKS_HITPAY_CREATE_PAYMENT_URL = f"{TASKS_API_BASE_URL}/payments/v1/hitpay/create-payment"
TASKS_EMAIL_API_URL = f"{TASKS_API_BASE_URL}/main/v1/email/send"
