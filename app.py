import http.server
import socketserver
import json
import urllib.parse
from datetime import datetime, timedelta
import calendar
import http.client

PORT = 8000
API_KEY = "dd99f1bf2bmsh0f5bd2c85562ac6p1e9de8jsn8692db5d6578"
API_HOST = "agoda-com.p.rapidapi.com"

def make_api_request(endpoint, params):
    conn = http.client.HTTPSConnection(API_HOST)
    headers = {
        'x-rapidapi-key': API_KEY,
        'x-rapidapi-host': API_HOST
    }
    query_string = urllib.parse.urlencode(params)
    conn.request("GET", f"/{endpoint}?{query_string}", headers=headers)
    res = conn.getresponse()
    data = res.read()
    return json.loads(data.decode("utf-8"))

def get_price_info(property):
    pricing = property.get('pricing', {})
    offers = pricing.get('offers', [])
    if offers:
        room_offers = offers[0].get('roomOffers', [])
        if room_offers:
            room = room_offers[0].get('room', {})
            pricing_list = room.get('pricing', [])
            if pricing_list:
                price = pricing_list[0].get('price', {})
                per_room_per_night = price.get('perRoomPerNight', {})
                inclusive = per_room_per_night.get('inclusive', {})
                return inclusive.get('display', 'N/A'), pricing_list[0].get('currency', 'USD')
    return 'N/A', 'USD'

def is_all_inclusive(property):
    content = property.get('content', {})
    room_benefits = content.get('features', {}).get('hotelFacilities', [])
    return any(benefit.get('id') == 55 for benefit in room_benefits)

def do_GET(self):
        if self.path == '/':
            self.path = '/index.html'
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

def generate_agoda_url(property, check_in, check_out, adults, rooms):
    base_url = "https://www.agoda.com/search"
    property_id = property.get('propertyId', '')
    property_name = property.get('content', {}).get('informationSummary', {}).get('localeName', '')
    
    params = {
        'selectedproperty': property_id,
        'checkIn': check_in,
        'los': str((datetime.strptime(check_out, '%Y-%m-%d') - datetime.strptime(check_in, '%Y-%m-%d')).days),
        'rooms': str(rooms),
        'adults': str(adults),
        'children': '0',
        'cid': '1844104',
        'locale': 'en-us',
        'ckuid': '940281a0-85d9-49d2-8fff-188f065d1d6a',
        'prid': '0',
        'currency': 'USD',
        'correlationId': '0fda1e21-b32d-465d-a9df-cd0b947389fb',
        'pageTypeId': '1',
        'realLanguageId': '1',
        'languageId': '1',
        'origin': 'US',
        'userId': '940281a0-85d9-49d2-8fff-188f065d1d6a',
        'whitelabelid': '1',
        'loginLvl': '0',
        'storefrontId': '3',
        'currencyId': '7',
        'currencyCode': 'USD',
        'htmlLanguage': 'en-us',
        'cultureInfoName': 'en-us',
        'trafficGroupId': '1',
        'trafficSubGroupId': '84',
        'aid': '130589',
        'useFullPageLogin': 'true',
        'cttp': '4',
        'isRealUser': 'true',
        'mode': 'production',
        'checkOut': check_out,
        'priceCur': 'USD',
        'textToSearch': property_name,
        'productType': '-1',
        'travellerType': '1',
        'familyMode': 'off'
    }
    
    query_string = urllib.parse.urlencode(params)
    return f"{base_url}?{query_string}"

class MyHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        print(f"Received POST request to {self.path}")  # Add this line
        if self.path == '/api/search':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            print(f"Received data: {data}")

            start_month = data['startMonth']
            end_month = data['endMonth']
            nights = int(data['nights'])
            accommodation_type = data['accommodationType']
            star_rating = data['starRating']
            all_inclusive = data['allInclusive']
            adults = int(data['adults'])
            rooms = int(data['rooms'])

            # Get Cancun destination ID
            auto_complete_params = {"query": "Cancun"}
            auto_complete_result = make_api_request("hotels/auto-complete", auto_complete_params)
            
            if not auto_complete_result.get('data'):
                self.send_error(400, "No results found for Cancun")
                return
            
            destination_id = auto_complete_result['data'][0]['id']

            # Generate all possible date combinations
            current_year = datetime.now().year
            start_date = datetime(current_year, int(start_month), 1)
            end_date = datetime(current_year, int(end_month), calendar.monthrange(current_year, int(end_month))[1])
            
            best_deal = None
            best_price = float('inf')

            while start_date <= end_date:
                check_in = start_date.strftime('%Y-%m-%d')
                check_out = (start_date + timedelta(days=nights)).strftime('%Y-%m-%d')
                
                if datetime.strptime(check_out, '%Y-%m-%d') > end_date:
                    break

                search_params = {
                    "id": destination_id,
                    "checkinDate": check_in,
                    "checkoutDate": check_out,
                    "starRating": star_rating,
                    "limit": 30
                }
                
                if accommodation_type == "hotel":
                    search_params["propertyType"] = "34"
                elif accommodation_type == "resort":
                    search_params["propertyType"] = "37"

                search_results = make_api_request("hotels/search-overnight", search_params)
                
                if search_results.get('data', {}).get('properties'):
                    for property in search_results['data']['properties']:
                        price, currency = get_price_info(property)
                        if price != 'N/A' and (not all_inclusive or is_all_inclusive(property)):
                            price = float(price) * nights
                            if price < best_price:
                                best_price = price
                                best_deal = {
    'propertyName': property.get('content', {}).get('informationSummary', {}).get('localeName', 'N/A'),
    'starRating': property.get('content', {}).get('informationSummary', {}).get('rating', 'N/A'),
    'reviewScore': property.get('content', {}).get('reviews', {}).get('cumulative', {}).get('score', 'N/A'),
    'reviewCount': property.get('content', {}).get('reviews', {}).get('cumulative', {}).get('reviewCount', 'N/A'),
    'price': price,
    'currency': currency,
    'checkIn': check_in,
    'checkOut': check_out,
    'nights': nights,  # Add this line
    'imageUrl': property.get('content', {}).get('images', {}).get('hotelImages', [{}])[0].get('urls', [{}])[0].get('value', ''),
    'isAllInclusive': is_all_inclusive(property),
    'agodaUrl': generate_agoda_url(property, check_in, check_out, adults, rooms)
}

                start_date += timedelta(days=1)

            if best_deal:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(best_deal).encode())
            else:
                self.send_error(404, "No suitable deals found")
        else:
            super().do_GET()

with socketserver.TCPServer(("", PORT), MyHandler) as httpd:
    print(f"Serving at port {PORT}")
    httpd.serve_forever()