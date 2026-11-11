# Late Delivery Claims Process

Owner: Customer Service

## Steps
1. Confirm the order and its promised delivery time in the reporting database.
2. Confirm delivery status with the carrier scan in the ERP.
3. Calculate days late and the credit using the SLA policy (or legacy terms if flagged).
4. Open a credit ticket in the ERP with the order ID, days late, credit percentage and amount.
5. A team lead approves tickets above $1,000.

## Required Ticket Fields
order_id, customer_id, days_late, credit_percent, credit_amount_usd, reason.

## Turnaround
Credit tickets must be opened within 2 business days of the customer request.
