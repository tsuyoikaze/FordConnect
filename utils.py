import requests 
import time

from .config import *


class FordConnectError(ConnectionError):
    can_retry = False
    pass

class BadRequest(FordConnectError):
    can_retry = False
    pass

class Unauthorized(FordConnectError):
    can_retry = False
    pass

class Forbidden(FordConnectError):
    can_retry = False
    pass

class VehicleNotFound(FordConnectError):
    can_retry = False
    pass

class MethodNotAllowed(FordConnectError):
    can_retry = False
    pass

class UnsupportedMediaType(FordConnectError):
    can_retry = False
    pass

class FailureDependency(FordConnectError):
    can_retry = False
    pass

class TooManyRequests(FordConnectError):
    can_retry = True
    pass

class InternalServerError(FordConnectError):
    can_retry = True
    pass

class BadGateway(FordConnectError):
    can_retry = True
    pass

class CommandTimeOut(FordConnectError):
    can_retry = True
    pass

class CommandFailed(FordConnectError):
    can_retry = True
    pass


HTTP_EXCEPTION_DICT: dict[int, FordConnectError] = {
    400: BadRequest, 
    401: Unauthorized, 
    403: Forbidden, 
    404: VehicleNotFound, 
    405: MethodNotAllowed, 
    415: UnsupportedMediaType, 
    424: FailureDependency, 
    429: TooManyRequests, 
    500: InternalServerError, 
    502: BadGateway, 
    408: CommandTimeOut, 
    406: CommandFailed
}


def raise_http_exception(http_status_code: int, message: str) -> None:
    """Raise corresponding exception based on the status code. 

    Args:
        http_status_code (int): http status code. 
        message (str): Message to display. 

    Raises:
        FordConnectError: The corresponding python exception. 
    """
    raise HTTP_EXCEPTION_DICT[http_status_code](message)


def generate_header(include_application_id: bool = False, additional_args: dict[str, str] = None) -> dict[str, str]:
    """Generate corresponding HTTP headers. 

    Args:
        include_application_id (bool, optional): Whether to include application ID. Defaults to False.
        additional_args (dict[str, str], optional): Additional header fields to populate. Defaults to None.

    Returns:
        dict[str, str]: Generated http headers in the form of dictionary. 
    """
    res = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'PostmanRuntime/7.41.1',
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive'
    }
    if include_application_id:
        res['Application-Id'] = APPLICATION_ID
    if additional_args != None:
        for key in additional_args:
            res[key] = additional_args[key]
    return res 


def get(client: object, url: str, headers: dict[str, str] = None, bypass_auth_check: bool = False) -> dict:
    """Perform a HTTP GET request. 

    Args:
        client (Client): The client object to perform the operation. 
        url (str): The target URL. 
        headers (dict[str, str], optional): The request headers. Defaults to None.
        bypass_auth_check (bool, optional): Whether to bypass access token validity check. Defaults to False.

    Raises:
        FordConnectError: Specific connection error if it occurres. Note that it will attempt the max number of retries before the timeout is triggered. 

    Returns:
        dict: The JSON response from the server. 
    """
    if bypass_auth_check == False:
        client.check_authentication()
    
    num_retries = 0
    while num_retries < HTTP_MAX_RETRIES:
        response = client.session.get(url, headers = headers)
        if response.status_code < 400:
            return response.json()
        elif HTTP_EXCEPTION_DICT[response.status_code].can_retry == False:
            raise_http_exception(response.status_code, 'Error during GET request.')
        num_retries += 1
        time.sleep(HTTP_RETRY_INTERVAL)
    raise_http_exception(408, 'Timeout during GET request.')


def post(client: object, url: str, headers: dict[str, str] = None, data: dict = None, bypass_auth_check: bool = False) -> dict:
    """Perform a HTTP POST request. 

    Args:
        client (Client): The client object to perform the operation. 
        url (str): The target URL. 
        headers (dict[str, str], optional): The request headers. Defaults to None.
        data (dict, optional): The body data to be submitted. Defaults to None.
        bypass_auth_check (bool, optional): Whether to bypass access token validity check. Defaults to False.

    Raises:
        FordConnectError: Specific connection error if it occurres. Note that it will attempt the max number of retries before the timeout is triggered. 

    Returns:
        dict: The JSON response from the server. 
    """
    if bypass_auth_check == False:
        client.check_authentication()
    
    num_retries = 0
    while num_retries < HTTP_MAX_RETRIES:
        response = client.session.post(url, headers = headers, data = data)
        if response.status_code < 400:
            return response.json()
        elif HTTP_EXCEPTION_DICT[response.status_code].can_retry == False:
            raise_http_exception(response.status_code, 'Error during POST request.')
        num_retries += 1
        time.sleep(HTTP_RETRY_INTERVAL)
    raise_http_exception(408, 'Timeout during POST request.')

def delete(client: object, url: str, headers: dict[str, str] = None, bypass_auth_check: bool = False) -> dict:
    """Perform a HTTP DELETE request. 

    Args:
        client (Client): The client object to perform the operation. 
        url (str): The target URL. 
        headers (dict[str, str], optional): The request headers. Defaults to None.
        bypass_auth_check (bool, optional): Whether to bypass access token validity check. Defaults to False.

    Raises:
        FordConnectError: Specific connection error if it occurres. Note that it will attempt the max number of retries before the timeout is triggered. 

    Returns:
        dict: The JSON response from the server. 
    """
    if bypass_auth_check == False:
        client.check_authentication()
    
    num_retries = 0
    while num_retries < HTTP_MAX_RETRIES:
        response = client.session.delete(url, headers = headers)
        if response.status_code < 400:
            return response.json()
        elif HTTP_EXCEPTION_DICT[response.status_code].can_retry == False:
            raise_http_exception(response.status_code, 'Error during DELETE request.')
        num_retries += 1
        time.sleep(HTTP_RETRY_INTERVAL)
    raise_http_exception(408, 'Timeout during DELETE request.')