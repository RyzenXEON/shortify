import json
import boto3
import random
import string
import os

TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME')
REDIRECT_HTML_KEY = 'redirect.html' # The name of the HTML file in S3

if not TABLE_NAME:
    raise EnvironmentError("DYNAMODB_TABLE_NAME environment variable not set.")
if not S3_BUCKET_NAME:
    raise EnvironmentError("S3_BUCKET_NAME environment variable not set.")

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME)
s3_client = boto3.client('s3') # Create S3 client

# Function to generate a random short code
def generate_short_code(length=6):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for i in range(length))

# Function to get S3 redirect HTML template
def get_redirect_html_template():
    try:
        response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=REDIRECT_HTML_KEY)
        return response['Body'].read().decode('utf-8')
    except Exception as e:
        print(f"Error fetching S3 template {REDIRECT_HTML_KEY} from {S3_BUCKET_NAME}: {e}")
        return None # Or return a basic error HTML string


def lambda_handler(event, context):
    print(f"Received event: {json.dumps(event)}")

    # --- CORRECTED METHOD AND PATH EXTRACTION ---
    # For Lambda Function URLs (v2.0) and HTTP API Proxy Integrations (v2.0)
    http_method = event.get('requestContext', {}).get('http', {}).get('method')
    # Use rawPath for the full requested path including query parameters (if any)
    # If you only need the path without query params, you could use event.get('requestContext', {}).get('http', {}).get('path')
    path = event.get('rawPath')

    # path_parameters is correct for HTTP API path parameters like /{short_code}
    path_parameters = event.get('pathParameters', {})
    # --- END CORRECTION ---


    if http_method == 'POST' and path == '/shorten':
        # Handle shortening request (This block should now be reachable for POST /shorten)
        try:
            body = json.loads(event.get('body', '{}'))
            long_url = body.get('long_url')

            if not long_url:
                return {
                    'statusCode': 400,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({'error': 'Missing long_url in request body'})
                }

            # Generate a unique short code (add collision handling in production)
            short_code = generate_short_code()
            # Simple collision avoidance (retry if code exists) - improve this!
            # Use a transaction or conditional write for true uniqueness guarantee
            while table.get_item(Key={'short_code': short_code}).get('Item'):
                short_code = generate_short_code()


            # Store mapping in DynamoDB
            table.put_item(
                Item={
                    'short_code': short_code,
                    'long_url': long_url
                }
            )

            # Construct the short URL (replace with your domain)
            # This assumes you are using the custom domain 'thexeon.tech'
            # If using the invoke URL directly, construct accordingly.
            # You could potentially derive the host from event['headers']['host']
            short_url = f"https://thexeon.tech/{short_code}" # REPLACE WITH YOUR DOMAIN OR LOGIC TO GET HOST


            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*' # Required for browser extension API call
                },
                'body': json.dumps({'short_url': short_url})
            }

        except json.JSONDecodeError:
             return {
                 'statusCode': 400,
                 'headers': {'Content-Type': 'application/json'},
                 'body': json.dumps({'error': 'Invalid JSON body'})
             }
        except Exception as e:
            print(f"Error during shorten: {e}")
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Internal server error during shorten'})
            }


    # --- GET Redirect Logic (Mostly Correct for HTTP API once method is extracted) ---
    # This relies on API Gateway HTTP API having a route like GET /{short_code}
    # and passing {short_code} as a path parameter.
    elif http_method == 'GET':
        # Get short code from path parameters provided by API Gateway
        short_code = path_parameters.get('short_code')
        print(f"Attempting to retrieve short code: {short_code}") # Log the code being looked up

        # Handle request to the root path (e.g., https://thexeon.tech/)
        # In HTTP API, the root path might trigger the Lambda with an empty pathParameters
        if not short_code:
            # You could serve a simple landing page HTML here instead of this message
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'text/html'},
                'body': '<h1>TheXeon URL Shortener</h1><p>Append a short code to the URL to redirect.</p><p>Use the browser extension to create short codes.</p>'
            }


        try:
            # Retrieve long URL from DynamoDB
            response = table.get_item(
                Key={'short_code': short_code}
            )
            item = response.get('Item')

            if item and 'long_url' in item:
                long_url = item['long_url']

                # Fetch the redirect HTML template from S3
                redirect_html_template = get_redirect_html_template()

                if redirect_html_template:
                     # Replace the placeholder with the actual long URL
                     # This is a client-side redirect using the HTML page
                     redirect_html = redirect_html_template.replace('{{LONG_URL}}', long_url)
                     # Return the HTML page with a 200 OK status
                     return {
                         'statusCode': 200, # Return 200 instead of 302 for client-side redirect
                         'headers': {
                             'Content-Type': 'text/html'
                             # No Location header needed for client-side redirect
                         },
                         'body': redirect_html
                     }
                else:
                     # Handle case where S3 template couldn't be fetched
                     return {
                         'statusCode': 500,
                         'headers': {'Content-Type': 'text/html'},
                         'body': '<h1>Error</h1><p>Could not load redirect template.</p>'
                     }

            else:
                # Short code not found
                # Optionally load a 404 HTML page from S3 here too
                return {
                    'statusCode': 404, # Not Found
                    'headers': {'Content-Type': 'text/html'},
                    'body': '<h1>Not Found</h1><p>The short code you requested was not found.</p>'
                }

        except Exception as e:
            print(f"Error during redirect lookup or S3 fetch: {e}")
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'text/html'},
                'body': '<h1>Error</h1><p>An internal error occurred during redirect.</p>'
            }
    # --- END GET Redirect Logic ---


    else:
        # Handle unsupported methods or paths that weren't caught by specific routes
        # For HTTP API, this might be caught by the API Gateway routes themselves,
        # returning a default 404/405 before reaching the Lambda.
        # But good to have as a fallback if a misconfigured request hits the lambda.
        return {
            'statusCode': 405, # Method Not Allowed
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Method Not Allowed or path not configured'})
        }