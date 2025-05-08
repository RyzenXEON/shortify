import json
import boto3
import random
import string
import os

# Get the DynamoDB table name from environment variables
# You will set this later in Lambda configuration
TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')
if not TABLE_NAME:
     raise EnvironmentError("DYNAMODB_TABLE_NAME environment variable not set.")

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME)

# Function to generate a random short code
def generate_short_code(length=6):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for i in range(length))

def lambda_handler(event, context):
    print(f"Received event: {json.dumps(event)}")

    http_method = event.get('requestContext', {}).get('http', {}).get('method')
    path = event.get('rawPath')

    if http_method == 'POST' and path == '/shorten':
        # Handle shortening request
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
            # You'll need to know the protocol (https) and host (your domain)
            # Getting the host from event.headers might work, but hardcoding is simpler initially
            short_url = f"https://thexeon.tech/{short_code}"


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
                'body': json.dumps({'error': 'Internal server error'})
            }

    elif http_method == 'GET' and path.startswith('/'):
        # Handle redirect request
        # Extract short code from path (e.g., /abcde -> abcde)
        short_code = path.lstrip('/')

        if not short_code:
             # Handle request to the root path (optional: serve a landing page)
             return {
                 'statusCode': 200,
                 'headers': {'Content-Type': 'text/html'},
                 'body': '<h1>URL Shortener Root</h1><p>Append a short code to redirect.</p>'
             }


        try:
            # Retrieve long URL from DynamoDB
            response = table.get_item(
                Key={'short_code': short_code}
            )
            item = response.get('Item')

            if item and 'long_url' in item:
                long_url = item['long_url']
                # Perform redirect
                return {
                    'statusCode': 302, # Found
                    'headers': {
                        'Location': long_url
                    }
                }
            else:
                # Short code not found
                return {
                    'statusCode': 404, # Not Found
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({'error': 'Short code not found'})
                }

        except Exception as e:
            print(f"Error during redirect: {e}")
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Internal server error'})
            }

    else:
        # Handle unsupported methods or paths
        return {
            'statusCode': 405, # Method Not Allowed
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Method Not Allowed'})
        }