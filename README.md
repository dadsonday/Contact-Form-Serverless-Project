# Serverless Static Website with a Contact Form (S3 → API Gateway → Lambda → SES) — A Complete, Real-World Guide

Building a serverless contact form is one of the most common use cases for AWS — yet many tutorials gloss over the parts that actually break things in production: CORS, Lambda to API Gateway wiring, IAM permissions, and SES sandbox rules.

S3 static website → API Gateway → Lambda → SES email delivery
<img width="720" height="329" alt="image" src="https://github.com/user-attachments/assets/2e882e5d-4ea1-459a-bad4-75316e7ebe13" />

Architecture Overview
The goal is to provide a robust contact form without maintaining any traditional servers.

You host your static site (HTML/CSS/JS) on Amazon S3.
The contact form submits a POST /submit request to API Gateway.
API Gateway invokes an AWS Lambda function using Lambda proxy integration.
Lambda sends an email through Amazon Simple Email Service (SES).
Lambda returns a JSON response with the necessary CORS headers so the browser accepts the successful response.
This is simple, secure, and has zero servers to maintain.

Prerequisites
Before starting, ensure you have the following ready in your AWS account (using us-east-1 in this example):

AWS Permissions: Access to S3, API Gateway, Lambda, IAM, and SES.
SES Verification: The sender email is verified. If your SES account is still in the sandbox, the recipient email must also be verified.
Configure the S3 Static Website
Create the Bucket and Policy
Go to S3 → Create bucket.
Give it a unique name (e.g., contform-s3-website-us-east-1.amazonaws.com).

<img width="720" height="285" alt="image" src="https://github.com/user-attachments/assets/1a6aa8d1-51a4-4f25-a4f3-946ec0e434f5" />

Disable “Block all public access” (you need this for static hosting).
Apply a Bucket policy for public read access (replace the bucket name):

{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": ["s3:GetObject"],
      "Resource": ["arn:aws:s3:::my-contact-site-12345/*"]
    }
  ]
}

Enable Static Hosting
Go to the Bucket → Properties → Static website hosting → Enable.
Set Index document: index.html
Configure SES (Email Service)
This step ensures you’re authorized to send emails.

In SES → Verified identities, verify both the sender email (required) and the recipient email (if you are in the SES sandbox).
You will receive a verification email to the address you enter. Click the link to confirm.

<img width="410" height="648" alt="image" src="https://github.com/user-attachments/assets/08c59647-b072-4aca-bbfd-0382b17360fd" />
<img width="828" height="336" alt="image" src="https://github.com/user-attachments/assets/e77d0635-3719-41fe-9e13-489881902bee" />

Create the Lambda Function
This Python function will receive the contact for data and send the email via SES.

Create IAM Role
This role gives the Lambda function permission to interact with other AWS services, specifically SES and CloudWatch Logs.

IAM → Roles → Create role.
Trusted entity type: AWS service.
Use case: Select Lambda.
In Add permissions, search for ses and select AmazonSESFullAccess.
Note: For production, use a more restrictive policy, but AmazonSESFullAccess simplifies the initial setup.

<img width="720" height="318" alt="image" src="https://github.com/user-attachments/assets/27ffbc9a-f1f2-4c89-8a8b-b332a1425d19" />
<img width="640" height="287" alt="image" src="https://github.com/user-attachments/assets/edeb480c-b226-442d-81e3-740517ca8d55" />
<img width="720" height="320" alt="image" src="https://github.com/user-attachments/assets/d4bf910b-10df-446b-b70f-2a63efdcb2a2" />
<img width="720" height="310" alt="image" src="https://github.com/user-attachments/assets/4806906b-c0ab-4548-a8f5-2773461fba14" />


Create the Lambda Function
Lambda → Create function.
Name: ContactFormSender.
Runtime: Python 3.11 (or latest).
Execution role: Choose the IAM role you just created (lambda-ses-send-role).
Add these Environment variables to the Lambda’s configuration:


Key,Value,Description
SENDER_EMAIL,your verified SES sender,Email used as the source of the message.
RECIPIENT_EMAIL,the business owner's email,Email where the contact form submission will go.
SES_REGION,us-east-1,The AWS region where SES is configured.

<img width="640" height="300" alt="image" src="https://github.com/user-attachments/assets/becff340-41a4-4b78-9f4e-58ef3982fdd6" />
<img width="640" height="290" alt="image" src="https://github.com/user-attachments/assets/a44afde2-c42f-4b12-95b9-af76d5ae0af1" />
<img width="640" height="285" alt="image" src="https://github.com/user-attachments/assets/c7430dcd-612b-4d1c-9dc8-eb7dcef95188" />
<img width="720" height="336" alt="image" src="https://github.com/user-attachments/assets/1312569e-2cd2-4612-a45a-9b41afb1242a" />

Lambda Code (Python)
Replace the code in lambda_function.py with the following. Pay close attention to the CORS headers in the _response function, which are crucial for the frontend


import json
import boto3
import logging
import os
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

SES_REGION = os.environ.get("SES_REGION", "us-east-1")
SENDER = os.environ.get("SENDER_EMAIL")
RECIPIENT = os.environ.get("RECIPIENT_EMAIL")

ses = boto3.client('ses', region_name=SES_REGION)

def lambda_handler(event, context):
    logger.info("Event: %s", event)

    try:
        # API Gateway uses Lambda Proxy Integration, so the body is a string
        body = event.get("body")
        data = json.loads(body)
    except Exception:
        return _response(400, {"error": "Invalid JSON body"})

    name = (data.get("name") or "").strip()
    sender_email = (data.get("email") or "").strip()
    message = (data.get("message") or "").strip()

    if not name or not sender_email or not message:
        return _response(400, {"error": "name, email and message are required"})

    subject = f"Contact form submission from {name}"
    body_text = f"Name: {name}\nEmail: {sender_email}\n\nMessage:\n{message}"

    try:
        ses.send_email(
            Source=SENDER,
            Destination={'ToAddresses': [RECIPIENT]},
            Message={
                'Subject': {'Data': subject},
                'Body': {'Text': {'Data': body_text}}
            },
            ReplyToAddresses=[sender_email]
        )
    except ClientError:
        logger.exception("SES send failed")
        return _response(500, {"error": "Failed to send email"})

    return _response(200, {"message": "Email sent"})

def _response(status_code, body):
    # For browsers (CORS): include Access-Control-Allow-Origin header
    # Allow site origin. The specific origin is more secure than "*".
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "http://contform-s3-website-us-east-1.amazonaws.com",
            "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
            "Access-Control-Allow-Methods": "OPTIONS,POST"
        },
        "body": json.dumps(body)
    }

Replace the Access-Control-Allow-Origin value with your actual S3 static website endpoint.

<img width="720" height="322" alt="image" src="https://github.com/user-attachments/assets/1b231dc9-6005-45d1-bfb8-f1f93c99149d" />

    Create API Gateway (REST API)
While HTTP API is simpler, we’ll demonstrate a REST API setup for maximum control over CORS, as shown in your images.

Create the API
API Gateway → Create API → REST API.
Choose New API.
API name: lambses.

<img width="720" height="332" alt="image" src="https://github.com/user-attachments/assets/ee2ac8d6-a0fc-4360-9a4f-0b9fef00a115" />


Create Resource and Method
Select the root resource (/) and Create resource.
Resource Name: submit.
Select the new /submit resource and Create method → POST.
Integration type: Lambda Function.
Lambda Region: us-east-1.
Lambda Function: ContactFormSender.

<img width="720" height="336" alt="image" src="https://github.com/user-attachments/assets/61ac3869-712d-43cb-b6e2-e99cad30cff1" />

Enable CORS on the Resource
CORS is mandatory for the browser to allow the cross-domain request from S3 to API Gateway.

Select the /submit resource.
Click Actions → Enable CORS.
3. Configure the CORS settings: * Gateway responses: Check Default 4XX and Default 5XX. * Access-Control-Allow-Origin: Enter your S3 website domain exactly (e.g., http://contform-s3-website-us-east-1.amazonaws.com). * Note: In production, do not use *.

4. Click Save. This action automatically creates the necessary OPTIONS method for pre-flight requests.

<img width="640" height="298" alt="image" src="https://github.com/user-attachments/assets/6fdfe5d9-403a-40fc-9930-25db78507134" />
<img width="720" height="331" alt="image" src="https://github.com/user-attachments/assets/cfbb193e-334d-4c16-b7f4-025bb32148b2" />

Deploy the API
Click Actions → Deploy API.
Deployment stage: [New Stage]
Stage name: prod.
Copy the Invoke URL from the stage details — you will use this in your frontend JavaScript.

<img width="640" height="295" alt="image" src="https://github.com/user-attachments/assets/a224f99d-fcdf-457d-aa17-052f0628d709" />
<img width="640" height="299" alt="image" src="https://github.com/user-attachments/assets/4fe5f0e6-30ef-4425-84d0-671ca5983f3d" />

Frontend: HTML + CSS Form
Upload these files to your S3 bucket. Remember to replace YOUR_API_ID.execute-api.us-east-1.amazonaws.com/prod/submit with your actual Invoke URL.

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Serverless Contact Form</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="container">
        <h1>Send Us a Message</h1>
        
        <form id="contact-form">
            <label for="name">Name</label>
            <input type="text" id="name" name="name" required>

            <label for="email">Email</label>
            <input type="email" id="email" name="email" required>

            <label for="subject">Subject</label>
            <input type="text" id="subject" name="subject" required>

            <label for="message">Message</label>
            <textarea id="message" name="message" rows="5" required></textarea>

            <button type="submit" id="submit-button">Send Message</button>

            <p id="form-status" aria-live="polite"></p>
        </form>
    </div>

    <script>
        // *** IMPORTANT: REPLACE THIS PLACEHOLDER WITH YOUR DEPLOYED API GATEWAY INVOKE URL ***
        const API_ENDPOINT = 'https://****.execute-api.us-east-1.amazonaws.com/prod/submit';

        const form = document.getElementById('contact-form');
        const statusMessage = document.getElementById('form-status');
        const submitButton = document.getElementById('submit-button');

        form.addEventListener('submit', function(event) {
            // Prevent the default form submission (which would refresh the page)
            event.preventDefault(); 
            
            // Collect form data
            const formData = new FormData(form);
            const payload = {};
            formData.forEach((value, key) => {
                payload[key] = value;
            });

            // Show loading state
            statusMessage.textContent = 'Sending...';
            submitButton.disabled = true;

            fetch(API_ENDPOINT, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload) // Convert the data object to a JSON string
            })
            .then(response => {
                // Check for a successful response (status 200-299)
                if (response.ok) {
                    return response.json(); // Process the JSON response from Lambda/API Gateway
                }
                // Handle HTTP error responses
                throw new Error(`Submission failed: ${response.status} ${response.statusText}`);
            })
            .then(data => {
                // Success
                statusMessage.textContent = '✅ Message sent successfully! We will be in touch soon.';
                form.reset(); // Clear the form fields
            })
            .catch(error => {
                // Error handling
                console.error('Error submitting form:', error);
                statusMessage.textContent = `❌ An error occurred: ${error.message}. Please try again.`;
            })
            .finally(() => {
                // Re-enable the button after process completes
                submitButton.disabled = false;
            });
        });
    </script>
</body>
</html>

<img width="1100" height="514" alt="image" src="https://github.com/user-attachments/assets/1a0e2c24-e7a1-436e-a5e0-ad1e05cf43c2" />

⚠️ CORS — What Breaks Most People
If your browser returns a No 'Access-Control-Allow-Origin' header is present… error, your CORS configuration is wrong.

Checklist for Success
API Gateway must have the OPTIONS method configured (done automatically when you click Enable CORS).
Lambda must return the correct Access-Control-Allow-Origin header in its response. This is set in the Python code's _response function.
The Allowed origin in both API Gateway and Lambda must exactly match your S3 website domain (including the http:// or https://) and must not have a trailing slash.
Final Checklist Before Launch
SES sender + recipient verified.
Lambda IAM role includes ses:SendEmail and CloudWatch Logs permissions.
API Gateway CORS enabled on the /submit resource.
Lambda returns CORS headers in the response function.
S3 website origin matches the Access-Control-Allow-Origin value.
Fun Trouble — CORS messed me up like four hours straight… the joy that it eventually worked.

<img width="640" height="370" alt="image" src="https://github.com/user-attachments/assets/a021485e-676d-4133-8602-baeee48ef3e5" />
<img width="640" height="315" alt="image" src="https://github.com/user-attachments/assets/f8f99308-0bf7-4890-9ea4-9d9c42459199" />

Happy Troubleshooting.





