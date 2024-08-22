if __name__ == '__main__':
    from FordConnect.models import Client
    import time
    client = Client.from_file('fordpass.dat')
    client.check_authentication()
    client.vehicles[0].refresh_location()
    time.sleep(1)
    client.vehicles[0].fetch_details()
    print(client.vehicles[0].location.to_google_maps_link())
    client.save('fordpass.dat')