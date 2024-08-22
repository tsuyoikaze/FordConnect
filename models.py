import requests 
import sys 
import time 
import pickle
from .utils import generate_header, get, post, delete, raise_http_exception, FordConnectError
from .config import *


class Location:
    def __init__(self, lon: float, lat: float, timestamp: str = None):
        """Create a location object to display where the vehicle is.

        Args:
            lon (float): Longitude in float. Can be negative.
            lat (float): Latitude in float. Can be negative.
            timestamp (str, optional): Timestamp string of the update time. Defaults to None.
        """
        self.lon = lon
        self.lat = lat
        self.timestamp = timestamp
    
    def __repr__(self) -> str:
        if self.timestamp is None:
            return f'<{self.__repr__()}; no timestamp>'
        else:
            return f'<{self.__repr__()} at {self.timestamp}>'
    
    def __str__(self) -> str:
        return f'({self.lat},{self.lon})'

    def to_google_maps_link(self) -> str:
        """Generate URL link to Google Maps.

        Returns:
            str: URL link to Google Maps (only works on desktop browser).
        """
        return f'http://maps.google.com/maps?t=m&q=loc:{self.lat}+{self.lon}'
    
    def to_lat_lon_pair(self) -> str:
        """Generate latitude and longitude pair string representation.

        Returns:
            str: Lat/Lon pair useful for app usage. 
        """
        return f'{self.lat},{self.lon}'


class Vehicle:

    __BASENAME = 'https://api.mps.ford.com/api/fordconnect'

    __V1_BASENAME = __BASENAME + '/v1/vehicles/{}'
    __V3_BASENAME = __BASENAME + '/v3/vehicles/{}'

    DETAIL_URL = __V3_BASENAME

    REFRESH_STATUS_URL = __V1_BASENAME + '/status'
    CHECK_STATUS_URL = __V1_BASENAME + '/statusrefresh/{}'

    LOCK_URL = __V1_BASENAME + '/lock'
    CHECK_LOCK_URL = LOCK_URL + '/{}'
    UNLOCK_URL = __V1_BASENAME + '/unlock'
    CHECK_UNLOCK_URL = UNLOCK_URL + '/{}'
    START_ENG_URL = __V1_BASENAME + '/startEngine'
    CHECK_START_ENG_URL = START_ENG_URL + '/{}'
    STOP_ENG_URL = __V1_BASENAME + '/stopEngine'
    CHECK_STOP_ENG_URL = STOP_ENG_URL + '/{}'
    START_CRG_URL = __V1_BASENAME + '/startCharge'
    CHECK_START_CRG_URL = START_CRG_URL + '/{}'
    STOP_CRG_URL = __V1_BASENAME + '/stopCharge'
    CHECK_STOP_CRG_URL = STOP_CRG_URL + '/{}'
    CRG_SCHEDULE_URL = __V3_BASENAME + '/chargeSchedules'
    DEP_TIME_URL = __V3_BASENAME + '/departureTimes'
    SIGNAL_URL = __V1_BASENAME + '/signal'
    CHECK_SIGNAL_URL = SIGNAL_URL + '/{}'

    IMG_URL = __V1_BASENAME + '/images'

    REFRESH_LOCATION_URL = __V1_BASENAME + '/location'
    CHECK_LOCATION_URL = REFRESH_LOCATION_URL + '/{}'
    RETRIVE_LOCATION_URL = __V3_BASENAME + '/location'

    def __init__(self, client: object, vehicle_id: str):
        """Create an empty vehicle object.

        Args:
            client (object): The client this vehicle belongs to.
            vehicle_id (str): Vehicle ID. 
        """
        self.client = client
        self.id = vehicle_id 
        self.make = None 
        self.model_name = None 
        self.model_year = None 
        self.color = None 
        self.nickname = None 

        self.last_updated = None 
        self.fuel = None 
        self.mileage = None 
        self.location = None 
        self.is_engine_start = None 
        self.door_status = None
        self.is_locked = None

        self.raw_json = None
        self.is_detailed = False
    

    def populate(self, obj: dict) -> None:
        """Populate general vehicle information given the JSON object.

        Args:
            obj (dict): JSON object returned from either `fetch_vehicles` or `populate_details`.
        """
        self.id = obj['vehicleId']
        self.make = 'Ford' if obj['make'] == 'F' else 'Lincoln'
        self.model_name = obj['modelName']
        self.model_year = int(obj['modelYear'])
        self.color = obj['color']
        self.nickname = obj['nickName']
        self.is_ev = False

        if self.raw_json is None:
            self.raw_json = obj 
        elif self.is_detailed:
            for key in obj:
                self.raw_json[key] = obj[key]
        
    
    def populate_details(self, obj: dict) -> None:
        """Populate detailed vehicle information given the JSON object. 

        Args:
            obj (dict): JSON object returned from `populate_details`.
        """
        self.last_updated = obj['lastUpdated']
        self.is_ev = 'EV' in obj['engineType']
        if obj['engineType'] != 'BEV':
            self.fuel = obj['vehicleDetails']['fuelLevel']['value']
        else:
            self.fuel = obj['vehicleDetails']['batteryChargeLevel']['value']
        self.odometer = obj['vehicleDetails']['mileage']
        self.location = Location(lon = obj['vehicleLocation']['longitude'], lat = obj['vehicleLocation']['latitude'], timestamp = obj['vehicleLocation']['timeStamp'])
        self.is_engine_start = obj['vehicleStatus']['ignitionStatus']['value'] != "OFF"
        self.door_status = obj['vehicleStatus']['doorStatus']
        self.is_locked = obj['vehicleStatus']['lockStatus']['value'] == 'LOCKED'
        
        self.raw_json = obj 
        self.is_detailed = True


    def __submit_job(self, url: str) -> str:
        headers = generate_header(include_application_id = True, additional_args = {
            'Content-Type': 'application/json',
            'Authorization': f'{self.client.token_type} {self.client.access_token}'
        })

        response = post(self.client, url, headers = headers)
        if response['status'] == 'SUCCESS':
            return response['commandId']
        else:
            raise_http_exception(406, 'Vehicle request command failed.')


    def __check_job(self, url: str) -> str:
        headers = generate_header(include_application_id = True, additional_args = {
            'Authorization': f'{self.client.token_type} {self.client.access_token}'
        })

        response = get(self.client, url, headers = headers)
        if response['status'] == 'SUCCESS':
            return response['commandStatus']
        else:
            raise_http_exception(406, 'Vehicle request command failed.')
    
    def __delete_job(self, url: str) -> str:
        headers = generate_header(include_application_id = True, additional_args = {
            'Authorization': f'{self.client.token_type} {self.client.access_token}'
        })

        response = delete(self.client, url, headers = headers)
        if response['status'] == 'SUCCESS':
            return response['commandStatus']
        else:
            raise_http_exception(406, 'Vehicle request command failed.')

    def __perform_job(self, request_fn: callable, check_fn: callable) -> str:
        command_id = request_fn()
        num_retries = 0
        while num_retries < HTTP_MAX_RETRIES:
            command_status = check_fn(command_id)
            if command_status in ['COMPLETED', 'EMPTY']:
                self.update_from_server()
                return command_id
            elif command_status in ['TIMEOUT', 'FAILED', 'COMMUNICATIONFAILED', 'MODEMINDEEPSLEEPMODE', 'FIRMWAREUPGRADEINPROGRESS', 'FAILEDDUETOINVEHICLESETTINGS']:
                raise_http_exception(406, 'Vehicle command failed to execute.')
            else:
                num_retries += 1
                time.sleep(HTTP_RETRY_INTERVAL)
        raise_http_exception(408, 'Vehicle request timed out.')

    def update_from_server(self) -> None:
        """Fetch vehicle details from Ford server (not activating vehicle modem).

        Raises:
            FordConnectError: Specific connection error if it occurres. Note that it will attempt the max number of retries before the timeout is triggered. 
        """
        url = Vehicle.DETAIL_URL.format(self.id)
        headers = generate_header(include_application_id = True, additional_args = {
            'Authorization': f'{self.client.token_type} {self.client.access_token}'
        })
        response = get(self.client, url, headers = headers)
        self.populate_details(response['vehicle'])
    
    
    def request_update_from_vehicle(self) -> str: 
        """Request information to be refreshed and updated from the vehicle (modem required).

        Raises:
            FordConnectError: Specific connection error if it occurres. Note that it will attempt the max number of retries before the timeout is triggered. 

        Returns:
            str: The command ID, if the command is successfully sent. 
        """
        url = Vehicle.REFRESH_STATUS_URL.format(self.id)
        return self.__submit_job(url)


    def check_update_from_vehicle(self, command_id: str) -> str:
        """Check status of the request update from the vehicle.

        Args:
            command_id (str): Command ID from `request_update_from_vehicle`.

        Raises:
            FordConnectError: Specific connection error if it occurres. Note that it will attempt the max number of retries before the timeout is triggered. 

        Returns:
            str: Command running status. 
        """
        url = Vehicle.CHECK_STATUS_URL.format(self.id, command_id)
        return self.__check_job(url)
    
    def update_from_vehicle(self) -> None:
        self.__perform_job(self.request_update_from_vehicle, self.check_update_from_vehicle)

    def request_lock(self) -> str:
        """Request vehicle to lock. 

        Returns:
            str: Command ID, if the command is sent successfully. 
        """
        url = Vehicle.LOCK_URL.format(self.id)
        return self.__submit_job(url)

    def check_lock(self, command_id: str) -> str:
        """Check lock request status. 

        Args:
            command_id (str): The command ID from `request_lock`. 

        Returns:
            str: Command running status. 
        """
        url = Vehicle.CHECK_LOCK_URL.format(self.id, command_id)
        return self.__check_job(url)

    def lock(self) -> None:
        self.__perform_job(self.request_lock, self.check_lock)

    def request_unlock(self) -> str:
        url = Vehicle.UNLOCK_URL.format(self.id)
        return self.__submit_job(url)

    def check_unlock(self, command_id: str) -> str:
        url = Vehicle.CHECK_UNLOCK_URL.format(self.id, command_id)
        return self.__check_job(url)

    def unlock(self) -> None:
        self.__perform_job(self.request_unlock, self.check_unlock)

    def request_start_engine(self) -> str:
        url = Vehicle.START_ENG_URL.format(self.id)
        return self.__submit_job(url)

    def check_start_engine(self, command_id: str) -> str:
        url = Vehicle.CHECK_START_ENG_URL.format(self.id, command_id)
        return self.__check_job(url)

    def start_engine(self) -> None:
        self.__perform_job(self.request_start_engine, self.check_start_engine)

    def request_stop_engine(self) -> str:
        url = Vehicle.STOP_ENG_URL.format(self.id)
        return self.__submit_job(url)
    
    def check_stop_engine(self, command_id: str) -> str:
        url = Vehicle.CHECK_STOP_ENG_URL.format(self.id, command_id)
        return self.__check_job(url)

    def stop_engine(self) -> None:
        self.__perform_job(self.request_stop_engine, self.check_stop_engine)

    def request_start_charge(self) -> str:
        if self.is_ev == False:
            raise_http_exception(405, 'Using EV-only function on non-EV vehicle.')
        url = Vehicle.START_CRG_URL.format(self.id)
        return self.__submit_job(url)

    def check_start_charge(self, command_id: str) -> str:
        if self.is_ev == False:
            raise_http_exception(405, 'Using EV-only function on non-EV vehicle.')
        url = Vehicle.CHECK_START_CRG_URL.format(self.id, command_id)
        return self.__check_job(url)

    def start_charge(self) -> None:
        self.__perform_job(self.request_start_charge, self.check_start_charge)

    def request_stop_charge(self) -> str:
        if self.is_ev == False:
            raise_http_exception(405, 'Using EV-only function on non-EV vehicle.')
        url = Vehicle.STOP_CRG_URL.format(self.id)
        return self.__submit_job(url) 

    def check_stop_charge(self, command_id: str) -> str:
        if self.is_ev == False:
            raise_http_exception(405, 'Using EV-only function on non-EV vehicle.')
        url = Vehicle.CHECK_STOP_CRG_URL.format(self.id, command_id)
        return self.__check_job(url)

    def stop_charge(self) -> None:
        self.__perform_job(self.request_stop_charge, self.check_stop_charge)

    def request_refresh_location(self) -> str:
        url = Vehicle.REFRESH_LOCATION_URL.format(self.id)
        return self.__submit_job(url) 
    
    def check_refresh_location(self, command_id: str) -> str:
        url = Vehicle.CHECK_LOCATION_URL.format(self.id, command_id)
        return self.__check_job(url)
    
    def refresh_location(self) -> None:
        self.__perform_job(self.request_refresh_location, self.check_refresh_location)

    def request_signal(self) -> str:
        url = Vehicle.SIGNAL_URL.format(self.id)
        return self.__submit_job(url) 
    
    def check_signal(self, command_id: str) -> str:
        url = Vehicle.CHECK_SIGNAL_URL.format(self.id, command_id)
        return self.__check_job(url)

    def send_signal(self) -> str:
        return self.__perform_job(self.request_signal, self.check_signal)

    def cancel_signal(self, command_id: str) -> str:
        url = Vehicle.CHECK_SIGNAL_URL.format(self.id, command_id)
        return self.__delete_job(url)

    def __repr__(self) -> str:
        res = f'{self.model_year} {self.make} {self.model_name}: {self.nickname}\n'
        if self.is_detailed == False:
            try:
                self.update_from_server()
            except FordConnectError:
                return res
        engine_type = 'EV' if self.is_ev else 'Non-EV'
        res += f'  Engine Type: {engine_type}, Engine Start: {self.is_engine_start}\n'
        res += f'  Odometer: {self.odometer}, Fuel Level: {self.fuel}\n'
        res += f'  Locked: {self.is_locked}, Location: {self.location}'
        return res
        

    def __str__(self) -> str:
        res = f'[{self.model_year} {self.make} {self.model_name}: {self.nickname} (fuel: {self.fuel}%, location: {self.location})]'
        return res

class Client:

    CALLBACK_URL = f'https://fordconnect.cv.ford.com/common/login/?make=F&application_id=AFDC085B-377A-4351-B23E-5E1D35FB3700&client_id={CLIENT_ID}&response_type=code&state=123&redirect_uri=https%3A%2F%2Flocalhost%3A3000&scope=access'
    REDIR_URL = 'https://localhost:3000'

    TOKEN_URL = 'https://dah2vb2cprod.b2clogin.com/914d88b1-3523-4bf6-9be4-1b96b4f6f919/oauth2/v2.0/token?p=B2C_1A_signup_signin_common'

    LIST_VEHICLES_URL = 'https://api.mps.ford.com/api/fordconnect/v3/vehicles'

    def __init__(self):
        self.access_token = None
        self.refresh_token = None 
        self.id_token = None 
        self.token_expiration = None 
        self.refresh_token_expiration = None 
        self.token_type = None 
        self.session = requests.Session()

        self.vehicles = []
    
    def populate_authentication_info(self, response: dict) -> None:
        self.access_token = response['access_token']
        self.refresh_token = response['refresh_token']
        self.id_token = response['id_token']
        self.token_expiration = response['expires_on']
        self.refresh_token_expiration = response['not_before'] + response['refresh_token_expires_in']
        self.token_type = response['token_type']

    def authenticate(self, code: str | None = None) -> None:
        if code is None:
            print('No code provided. Using Standard Input instead. Please open the link below: ')
            print(Client.CALLBACK_URL)
            code = input('Please paste the URL here: ')
            code = code.split('code=')[1]

        url = Client.TOKEN_URL
        headers = generate_header()
        data = {
            'grant_type': 'authorization_code', 
            'client_id': CLIENT_ID, 
            'client_secret': CLIENT_SECRET, 
            'code': code, 
            'redirect_uri': Client.REDIR_URL
        }

        response = post(self, url, headers = headers, data = data, bypass_auth_check = True)
        self.populate_authentication_info(response)

    def refresh_access_token(self) -> None:
        url = Client.TOKEN_URL
        headers = generate_header()
        data = {
            'grant_type': 'refresh_token', 
            'refresh_token': self.refresh_token, 
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET
        }

        response = post(self, url, headers = headers, data = data, bypass_auth_check = True)
        self.populate_authentication_info(response)

    def check_authentication(self) -> None:
        curr_time = time.time()
        if curr_time >= self.refresh_token_expiration:
            self.authenticate()
        elif curr_time >= self.token_expiration:
            self.refresh_access_token()

    def fetch_vehicles(self) -> None:
        url = Client.LIST_VEHICLES_URL
        headers = generate_header(include_application_id = True, additional_args = {
            'Authorization': f'{self.token_type} {self.access_token}'
        })
        response = get(self, url, headers = headers)
        self.vehicles = []
        for vehicle in response['vehicles']:
            vehicle_obj = Vehicle(self, vehicle['vehicleId'])
            vehicle_obj.populate(vehicle)
            vehicle_obj.update_from_server()
            self.vehicles.append(vehicle_obj)
            

    def save(self, fpath: str) -> None:
        with open(fpath, 'wb') as f:
            pickle.dump(self, f)

    def __str__(self) -> str:
        return f'<Client with {len(self.vehicles)} vehicles>'

    def __repr__(self) -> str:
        res = f'<Client with {len(self.vehicles)} vehicles>'
        for v in self.vehicles:
            res += f'\n  {v.__str__()}'
        return res

    @classmethod
    def from_file(cls, fpath: str) -> None:
        with open(fpath, 'rb') as f:
            obj = pickle.load(f)
            return obj
    
        