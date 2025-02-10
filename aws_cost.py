import boto3
from datetime import datetime, timedelta

# Create a Cost Explorer client
ce_client = boto3.client('ce')

# Set the time range for the last 30 days
end_date = datetime.utcnow().date()
start_date = end_date - timedelta(days=30)

# Query Cost Explorer for API Gateway usage
response = ce_client.get_cost_and_usage(
    TimePeriod={
        'Start': start_date.isoformat(),
        'End': end_date.isoformat()
    },
    Granularity='DAILY',
    Metrics=['UsageQuantity'],
    GroupBy=[
        {'Type': 'DIMENSION', 'Key': 'SERVICE'},
        {'Type': 'DIMENSION', 'Key': 'USAGE_TYPE'}
    ],
    Filter={
        'Dimensions': {
            'Key': 'SERVICE',
            'Values': ['Amazon API Gateway']
        }
    }
)

# Process and display the results
print(f"API Gateway Usage from {start_date} to {end_date}:")
for result in response['ResultsByTime']:
    date = result['TimePeriod']['Start']
    for group in result['Groups']:
        service = group['Keys'][0]
        usage_type = group['Keys'][1]
        quantity = float(group['Metrics']['UsageQuantity']['Amount'])
        print(f"{date} - {service} - {usage_type}: {quantity:.2f}")

# Calculate total usage
total_usage = sum(
    float(group['Metrics']['UsageQuantity']['Amount'])
    for result in response['ResultsByTime']
    for group in result['Groups']
)

print(f"\nTotal API Gateway Usage: {total_usage:.2f}")

