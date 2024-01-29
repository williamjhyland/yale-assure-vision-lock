from yalexs.api import Api 
from yalexs.authenticator import Authenticator, AuthenticationState, ValidationResult

api = Api(timeout=20)
access_token_cache_file_path = './accesstoken.json' # Where you want to save the access token
authenticator = Authenticator(
    api, 
    "email", # Or Phone 
    "EMAIL@EMAIL.COM", # Your email here  
    "PASSWORD", # Your Yale Password Here
    access_token_cache_file=access_token_cache_file_path
    )
authentication = authenticator.authenticate()

# Attempt to authenticate from cache
authentication = authenticator.authenticate()

print(authentication.state)

if authentication.state == AuthenticationState.REQUIRES_VALIDATION:
    print("Validation required. Sending verification code...")
    authenticator.send_verification_code()
    verification_code = input("Enter verification code: ")  # Prompt user for verification code
    validation_result = authenticator.validate_verification_code(verification_code)
    print(validation_result)

    if validation_result == ValidationResult.VALIDATED:
        print("Validation successful. Re-authenticating...")
        authentication = authenticator.authenticate()  # Re-authenticate after validation
    else:
        print("Invalid verification code. Please try again.")
        # Handle invalid verification code scenario