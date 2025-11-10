import json
import os
import boto3
from botocore.exceptions import ClientError

# --- Environment/Configuration Variables ---

# The AWS Region where your SES is verified (e.g., 'us-east-1')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1') 

# The email address you verified with SES to send FROM
SENDER_EMAIL = 'no-reply@yourdomain.com' 

# The email address that will receive the contact form submissions
RECIPIENT_EMAIL = 'your-inbox@yourdomain.com' 

# --- SES Client Setup ---
ses_client = boto3.client('ses', region_name=AWS_REGION)

def lambda_handler(event, context):
    """
    Handles the POST request from API Gateway, parses the form data, and sends 
    an email notification via Amazon SES.
    """
    try:
        # 1. Parse the request body (API Gateway sends the body as a JSON string in event['body'])
        if event.get('body') is None:
            print("No body found in the event.")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'No form data submitted.'})
            }
            
        form_data = json.loads(event['body'])
        
        # Extract the fields from the parsed JSON payload
        name = form_data.get('name', 'N/A')
        email = form_data.get('email', 'N/A')
        subject = form_data.get('subject', 'N/A')
        message = form_data.get('message', 'N/A')
        
        # 2. Build the email content
        
        # HTML Body for a richer email format
        HTML_BODY = f"""
        <html>
        <head></head>
        <body>
            <p>You have received a new contact form submission:</p>
            <ul>
                <li><strong>Name:</strong> {name}</li>
                <li><strong>Email:</strong> {email}</li>
            </ul>
            <p><strong>Subject:</strong> {subject}</p>
            <h3>Message:</h3>
            <p>{message.replace(os.linesep, '<br>')}</p>
        </body>
        </html>
        """
        
        # Text Body for clients that don't display HTML
        TEXT_BODY = f"""
        New Contact Form Submission:
        Name: {name}
        Email: {email}
        Subject: {subject}
        Message:
        {message}
        """

        # SES parameters
        response = ses_client.send_email(
            Destination={
                'ToAddresses': [RECIPIENT_EMAIL],
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': 'UTF-8',
                        'Data': HTML_BODY,
                    },
                    'Text': {
                        'Charset': 'UTF-8',
                        'Data': TEXT_BODY,
                    },
                },
                'Subject': {
                    'Charset': 'UTF-8',
                    'Data': f'New Contact: {subject}',
                },
            },
            Source=SENDER_EMAIL,
            # Optional: Set the user's email as the Reply-To address
            ReplyToAddresses=[email], 
        )

    except ClientError as e:
        print(f"SES Send Email Error: {e.response['Error']['Message']}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*', # Necessary for CORS
                'Content-Type': 'application/json'
            },
            'body': json.dumps({'error': 'Failed to send email. Check Lambda logs.'})
        }
        
    except Exception as e:
        print(f"General Lambda Error: {e}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*', # Necessary for CORS
                'Content-Type': 'application/json'
            },
            'body': json.dumps({'error': 'Internal server error.'})
        }

    # 3. Successful execution response (for API Gateway)
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*', # VERY IMPORTANT for CORS from S3
            'Content-Type': 'application/json'
        },
        'body': json.dumps({'message': 'Email sent successfully!', 'message_id': response['MessageId']})
    }