import json
from flask import Flask, render_template, jsonify, request, send_file, Response, stream_with_context
from flask_cors import CORS
from flask_bootstrap import Bootstrap5
import os,dotenv,time,io,pypdf,datetime,requests
from gtts import gTTS
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from colorthief import ColorThief
from bs4 import BeautifulSoup
import spotipy
from spotipy.oauth2 import SpotifyOAuth
# import pandas
import plotly.express as px
import plotly.io as pio
from openai import OpenAI
from system_instruction import SYSTEM_INSTRUCTION

app = Flask(__name__)
# cors = CORS(app, origins="*")
CORS(app, origins="*")

dotenv.load_dotenv()

app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
Bootstrap5(app)

app.config['UPLOAD_FOLDER'] = 'uploads' # Define an upload folder (optional, but good practice)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True) # Create the folder if it doesn't exist

# Ensure a directory for static files where audio can be saved temporarily if needed
# Although for gTTS we'll use BytesIO to send directly
app.config['AUDIO_FOLDER'] = 'static/audio'
os.makedirs(app.config['AUDIO_FOLDER'], exist_ok=True)

@app.route('/')
def home():
    return jsonify({'message': "Welcome to the Blaine Silva's Python Portfolio Hub API"})


# --- Minimal JSON API to support the React frontend ---
@app.route('/api/projects')
def api_projects():
    projects_list = [
        {
            'id': 1,
            'title': 'To-do List',
            'description': "Keep your Tasks organized with this App where you can create Lists to categorize your to-dos.",
            'image': './images/todo-list.png',
            'color': '#2EC4B6',
            'category': 'Databases',
            'projectId': 'todo-list',
        },
        {
            'id': 2,
            'title': 'Year Tracker',
            'description': 'Create Trackers for your Activities like Mood and Exercises to keep track through the whole Year.',
            'image': './images/year-tracker.png',
            'color': '#FF6B6B',
            'category': 'Databases',
            'projectId': 'year-tracker',
        },
        {
            'id': 3,
            'title': 'Text to Speech Converter',
            'description': 'Convert Text to .mp3 Audio. You can type the text or extract text from PDF, then select language, voice and Convert!',
            'image': './images/tts-converter.png',
            'color': '#ffc61a',
            'category': 'External Libraries',
            'projectId': 'text-to-speech',
        },
        {
            'id': 4,
            'title': 'Timeless Playlist',
            'description': 'Choose a date and see what were the top 100 songs trending using BeautifulSoup and requests to extract data from websites.',
            'image': './images/timeless-playlist.png',
            'color': "#16AF49",
            'category': 'Automations',
            'projectId': 'timeless-playlist',
        },
        {
            'id': 5,
            'title': 'Data Visualization Dashboard',
            'description': 'Interactive dashboard built with Plotly to visualize complex datasets with charts and graphs.',
            'image': '/placeholder.svg',
            'color': '#87CEEB',
            'category': 'Data Science',
            'projectId': 'data-viz-dashboard',
        },
        {
            'id': 6,
            'title': 'Number Facts',
            'description': 'Get interesting facts about numbers including trivia, math, date, and year facts using the Numbers API.',
            'image': '/placeholder.svg',
            'color': '#FF6B6B',
            'category': 'APIs',
            'projectId': 'number-facts',
        },
        {
            'id': 7,
            'title': 'Palette Generator',
            'description': 'Generate color palettes from images using the ColorThief library to extract dominant colors.',
            'image': './images/palette-generator.png',
            'color': '#00b1b1',
            'category': 'External Libraries',
            'projectId': 'palette-generator',
        },
        {
            'id': 8,
            'title': 'CafeSeeker Website',
            'description': 'A web application that uses Google Maps API to fetch all cafes close to a given location.',
            'image': './images/cafe-seeker.png',
            'color': '#4A300E',
            'category': 'APIs',
            'projectId': 'cafe-seeker',
        },
        {
            'id': 9,
            'title': 'Internet Speed',
            'description': 'Check the speed of your Internet using Selenium, in a few minutes your results will be shown.',
            'image': './images/internet-speed.png',
            'color': '#DDA0DD',
            'category': 'Automations',
            'projectId': 'internet-speed',
        }
    ]
    return jsonify({'projects': projects_list})


@app.route('/api/projects/<project_id>')
def api_project_detail(project_id):
    projects_json = api_projects().get_json()
    projects_map = {p['projectId']: p for p in projects_json.get('projects', [])}
    project = projects_map.get(project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    return jsonify({'project': project})


@app.route('/api/chat', methods=['POST'])
def api_chat():
    data = request.get_json() or {}
    message = data.get('message', '')

    if not message:
        return jsonify({'reply': "I didn't receive a message."}), 400

    try:
        dotenv.load_dotenv()
        openai_api_key = os.getenv("OPENAI_API_KEY")
        
        if not openai_api_key:
            return jsonify({'error': 'OpenAI API key not configured'}), 500

        client = OpenAI(api_key=openai_api_key)

        # Use Chat Completions API (modern, non-deprecated)
        # Customize the system prompt to match your assistant's behavior
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # or "gpt-4" if you prefer; gpt-4o-mini is fast and cost-effective
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_INSTRUCTION
                },
                {
                    "role": "user",
                    "content": message
                }
            ],
            temperature=0.7,
            max_tokens=500
        )

        reply = response.choices[0].message.content if response.choices else "No response from assistant."
        return jsonify({'reply': reply})

    except Exception as e:
        print(f"Error in api_chat: {e}")
        return jsonify({'reply': f"Error communicating with AI: {str(e)}"}), 500

# ---------------------------------------------------- TEXT TO SPEECH ----------------------------------------------------

@app.route('/api/convert_to_speech', methods=['POST'])
def convert_to_speech():
    data = request.get_json()
    text = data.get('text')
    lang = data.get('language', 'en') # Default to English if not provided
    accent = data.get('accent', 'us')

    print(text, lang, accent)

    if not text:
        return jsonify({'error': 'No text provided'}), 400

    try:
        tts = gTTS(text=text, lang=lang, slow=False, tld=accent)
        # We'll use an in-memory byte stream instead of saving to a file
        audio_stream = io.BytesIO()
        tts.write_to_fp(audio_stream)
        audio_stream.seek(0) # Rewind the stream to the beginning
        # Return the audio file directly as a response
        return send_file(audio_stream, mimetype='audio/mpeg', as_attachment=False, download_name='speech.mp3')
        
    except Exception as e:
        print(f"Error during text-to-speech conversion: {e}")
        return jsonify({'error': f'Failed to convert text to speech: {str(e)}'}), 500

@app.route('/api/extract_pdf', methods=['POST'])
def extract_pdf():
    if 'pdf_file' not in request.files:
        return jsonify({'error': 'No PDF file provided'}), 400

    pdf_file = request.files['pdf_file']

    if pdf_file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if pdf_file and pdf_file.filename.endswith('.pdf'):
        try:
            # Create a temporary path to save the uploaded PDF
            # In a real application, you might want to use a more robust way to handle temporary files
            # or directly process the BytesIO object from pdf_file.stream
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], pdf_file.filename)
            pdf_file.save(filepath)

            text = ""
            with open(filepath, 'rb') as file:
                reader = pypdf.PdfReader(file)
                for page_num in range(len(reader.pages)):
                    page = reader.pages[page_num]
                    text += page.extract_text() + "\n" # Add a newline between pages

            os.remove(filepath) # Clean up the uploaded file

            return jsonify({'text': text})

        except pypdf.utils.PdfReadError:
            return jsonify({'error': 'Could not read PDF file. It might be encrypted or corrupted.'}), 400
        except Exception as e:
            return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500
    else:
        return jsonify({'error': 'Invalid file type. Please upload a PDF file.'}), 400


# ---------------------------------------------------- PALETTE GENERATOR ----------------------------------------------------
@app.route("/api/get-dominant-colors", methods=["POST"])
def get_dominant_colors():
    if 'image' not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    image_file = request.files['image']
    # sections = request.form.get('sections', default=10, type=int)

    try:
        # image = Image.open(image_file)
        color_thief = ColorThief(image_file)
        # colors = get_top_colors_by_region(image, num_sections=sections)
        colors_rgb = color_thief.get_palette(color_count=11,quality=5)
        colors = []
        for color_rgb in colors_rgb:
            r,g,b = color_rgb
            color_info = {
                'rgb': f'rgb({r}, {g}, {b})',
                'hex': '#{:02x}{:02x}{:02x}'.format(r, g, b)
            }
            colors.append(color_info)
        print(colors)
        return jsonify({"colors": colors})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------- NUMBER FACTS ----------------------------------------------------
BASE_URL = "http://numbersapi.com/"
@app.route("/api/number-facts/number",methods=['POST'])
def number():
    number = type = ""
    data = request.get_json()
    if request.method == "POST":
        number = data.get("number")
        type = data.get("type")
    if not number.isdigit():
        return jsonify({"error": "Invalid number"}), 400
    print(f"Received number: {number}, type: {type}")
    if type not in ['trivia', 'math', 'year']:
        return jsonify({"error": "Invalid type. Choose from 'trivia', 'math', or 'year'."}), 400
    try:
        response = requests.get(f"{BASE_URL}{number}/{type}")
        return jsonify({"fact": response.text}), 200
    except requests.RequestException as e:       
        response.raise_for_status()  # Raise an error for bad responses
        return jsonify({"error": str(e)}), 500
    
@app.route("/api/number-facts/date", methods=['POST'])
def date():
    data = request.get_json()
    month = data.get("month")
    day = data.get("day")
    print(f"Received month: {month}, day: {day}")
    if not (1 <= int(month) <= 12) or not (1 <= int(day) <= 31):
        return jsonify({"error": "Invalid date. Month must be between 1 and 12, and day must be between 1 and 31."}), 400
    try:
        response = requests.get(f"{BASE_URL}{month}/{day}/date")
        return jsonify({"fact": response.text}), 200
    except requests.RequestException as e:
        response.raise_for_status()
        return jsonify({"error": str(e)}), 500
    
@app.route("/api/number-facts/random", methods=['POST'])
def random():
    data = request.get_json()
    type = data.get("type")
    print(f"Received type: {type}")
    if type not in ['trivia', 'math', 'date', 'year']:
        return jsonify({"error": "Invalid type. Choose from 'trivia','date', 'math', or 'year'."}), 400
    try:
        response = requests.get(f"{BASE_URL}random/{type}")
        return jsonify({"fact": response.text}), 200
    except requests.RequestException as e:
        response.raise_for_status()
        return jsonify({"error": str(e)}), 500
    
# ------------------------------------- GOOGLE MAPS CAFE SEEKER -------------------------------------
@app.route('/api/googlemaps/cafes', methods=['POST'])
def get_cafes():
    data = request.get_json()
    location = data.get('location')
    dotenv.load_dotenv()
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    
    if not location:
        return jsonify({'error': 'No location provided'}), 400

    try:
        # Geocoding API to get latitude and longitude
        geocode_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={location}&key={api_key}"
        geocode_response = requests.get(geocode_url)
        geocode_data = geocode_response.json()
        # print(geocode_data)
        if geocode_data['status'] != 'OK':
            return jsonify({'error': 'Geocoding failed'}), 400

        lat_lng = geocode_data['results'][0]['geometry']['location']
        lat, lng = lat_lng['lat'], lat_lng['lng']
        search_radius_meters = 5000  # 5 km radius
        # print(lat,lng)
        # Places API to find cafes near the location
        NEARBY_SEARCH_URL = f"https://places.googleapis.com/v1/places:searchNearby"
        # Define the request body as a Python dictionary
        request_body = {
            "includedTypes": ["cafe"], # Searching for cafes
            "maxResultCount": 20,      # Limit to 10 results
            "locationRestriction": {
                "circle": {
                    "center": {
                        "latitude": lat,
                        "longitude": lng
                    },
                    "radius": search_radius_meters
                }
            }
        }

        # Define the headers for the request
        # X-Goog-Api-Key is for authentication
        # X-Goog-FieldMask is crucial to specify what data you want back
        # Content-Type tells the server we're sending JSON
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,places.rating,places.priceRange,places.regularOpeningHours,places.websiteUri,places.googleMapsUri,places.photos"
            # You can customize the field mask to get more or less data.
            # For example: "places.displayName,places.formattedAddress,places.location,places.types,places.websiteUri,places.internationalPhoneNumber"
            # Refer to the API documentation for available fields.
        }

        print("Making Nearby Search (New) request...")

        try:
            # Make the POST request
            response = requests.post(NEARBY_SEARCH_URL, headers=headers, data=json.dumps(request_body))

            # Check if the request was successful (status code 200)
            response.raise_for_status() # This will raise an HTTPError for bad responses (4xx or 5xx)

            # Parse the JSON response
            response_data = response.json()

            cafes = []
            # print(response_data['places'])
            # Process the results
            if response_data and 'places' in response_data:
                print(f"Found {len(response_data['places'])} cafes near ({lat}, {lng}):")
                for i, place in enumerate(response_data['places']):
                    id = i
                    display_name = place.get('displayName', {}).get('text', 'N/A')
                    formatted_address = place.get('formattedAddress', 'N/A')
                    # latitude = place.get('location', {}).get('latitude', 'N/A')
                    # longitude = place.get('location', {}).get('longitude', 'N/A')
                    rating = place.get('rating', 'N/A')
                    price_level = f"{place.get('priceRange', {}).get('startPrice', {}).get('units', 'N/A')}-{place.get('priceRange', {}).get('endPrice', {}).get('units', 'N/A')}" if 'priceRange' in place else 'N/A'
                    weekdayDescriptions = place.get('regularOpeningHours', {}).get('weekdayDescriptions', ['N/A'])
                    websiteUri = place.get('websiteUri', 'N/A')
                    googleMapsUri = place.get('googleMapsUri', 'N/A')
                    imgUrl = place['photos'][0]['name'] if 'photos' in place and place['photos'] else None


                    cafe = {
                        'id': id,
                        'display_name': display_name,
                        'formatted_address': formatted_address,
                        # 'latitude': latitude,
                        # 'longitude': longitude,
                        'rating': rating,
                        'price_level': price_level,
                        'weekdayDescriptions': weekdayDescriptions,
                        'websiteUri': websiteUri,
                        'googleMapsUri': googleMapsUri,
                        'imgUrl': imgUrl
                    }

                    cafes.append(cafe)

                    # print(f"\n--- Cafe {i+1} ---")
                    # print(f"Name: {display_name}")
                    # print(f"Address: {formatted_address}")
                    # # print(f"Location: Lat {latitude}, Lng {longitude}")
                    # print(f"Rating: {rating}")
                    # print(f"Price Level: {price_level}")
                    # print(weekdayDescriptions, websiteUri, googleMapsUri)
                    # print(imgUrl)
            else:
                print("No cafes found or unexpected response format.")
            return jsonify({'cafes': cafes})

        except requests.exceptions.HTTPError as err:
            print(f"HTTP error occurred: {err}")
            print(f"Response content: {response.text}")
        except requests.exceptions.ConnectionError as err:
            print(f"Connection error occurred: {err}")
        except requests.exceptions.Timeout as err:
            print(f"Timeout error occurred: {err}")
        except requests.exceptions.RequestException as err:
            print(f"An unexpected error occurred: {err}")
        except json.JSONDecodeError:
            print(f"Failed to decode JSON from response: {response.text}")

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/googlemaps/autocompletecity', methods=['POST'])
def autocomplete_city():
    data = request.get_json()
    input_text = data.get('input')
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")

    if not input_text:
        return jsonify({'error': 'No input provided'}), 400

    try:
        autocomplete_url = f"https://maps.googleapis.com/maps/api/place/autocomplete/json?input={input_text}&types=(cities)&key={api_key}"
        autocomplete_response = requests.get(autocomplete_url)
        autocomplete_data = autocomplete_response.json()
        # print(autocomplete_data)
        if autocomplete_data['status'] != 'OK':
            return jsonify({'error': 'Autocomplete API request failed'}), 400

        suggestions = []
        for prediction in autocomplete_data['predictions']:
            suggestions.append(prediction.get('description'))

        return jsonify({'suggestions': suggestions})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ----------------------------------------- TIMELESS PLAYLIST ----------------------------------------

@app.route('/api/get-top-songs-stream', methods=['GET'])
def get_top_songs_stream():
    """SSE endpoint that streams progress while fetching Billboard titles and looking them up on Spotify.
    Expects a `date` query parameter in YYYY-MM-DD format, e.g. /api/get-top-songs-stream?date=2025-12-10
    """
    date = request.args.get('date')
    if not date:
        return jsonify({'error': 'Missing "date" query parameter (YYYY-MM-DD).'}), 400

    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    username = os.getenv("USERNAME")

    def generate():
        try:
            # Notify client that fetching starts
            payload = {'phase': 'fetching_titles', 'message': 'Fetching the top 100 songs...'}
            yield f"data: {json.dumps(payload)}\n\n"

            url = f"https://www.billboard.com/charts/hot-100/{date}/"
            header = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) "
                            "Gecko/20100101 Firefox/131.0"
            }

            response = requests.get(url, headers=header)
            soup = BeautifulSoup(response.text, "html.parser")
            all_songs = soup.select(selector='li > ul:first-child > li:first-child > h3:first-child')
            titles = [song.getText().strip() for song in all_songs]

            # Inform client how many titles were found
            payload = {'phase': 'titles_fetched', 'count': len(titles), 'message': f'Fetched {len(titles)} titles'}
            yield f"data: {json.dumps(payload)}\n\n"

            # Initialize Spotify client (may prompt/cache token on first run)
            sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=client_id,
                                                          client_secret=client_secret,
                                                          redirect_uri="https://foo.com",
                                                          scope="playlist-modify-private",
                                                          show_dialog=True,
                                                          cache_path="token.txt",
                                                          username=username,
                                                          ))

            songs = []
            year = date.split("-")[0]
            found_count = 0
            n = 1
            for song in titles:
                try:
                    result = sp.search(q=f"track:{song} year:{year}", type="track")
                    item = result.get("tracks", {}).get("items", [])
                    if item:
                        artist = item[0]["album"]["artists"][0]["name"]
                        link = item[0]["external_urls"]["spotify"]
                        new_song = {'idcard': n, 'name': song, 'artist': artist, 'link': link}
                        songs.append(new_song)
                        found_count += 1
                        # Send incremental update for each found song
                        payload = {'phase': 'found_increment', 'count': found_count, 'message': f'Found {found_count} songs on Spotify'}
                        yield f"data: {json.dumps(payload)}\n\n"
                except Exception:
                    # Skip problematic items but continue streaming
                    pass
                n += 1

            # Final payload with all found songs
            payload = {'phase': 'done', 'songs': songs, 'message': 'Completed searching Spotify'}
            yield f"data: {json.dumps(payload)}\n\n"

        except Exception as e:
            payload = {'phase': 'error', 'message': str(e)}
            yield f"data: {json.dumps(payload)}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')


@app.route('/api/get-top-songs', methods=['POST'])
def get_top_songs():
    # Backwards-compatible fallback: return full JSON after processing (non-streaming)
    data = request.get_json() or {}
    date = data.get('date')
    if not date:
        return jsonify({'error': 'Missing date in request body'}), 400

    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    username = os.getenv("USERNAME")

    try:
        url = f"https://www.billboard.com/charts/hot-100/{date}/"
        header = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=header)
        soup = BeautifulSoup(response.text, "html.parser")
        all_songs = soup.select(selector='li > ul:first-child > li:first-child > h3:first-child')
        titles = [song.getText().strip() for song in all_songs]

        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=client_id,
                                                client_secret=client_secret,
                                                redirect_uri="https://foo.com",
                                                scope="playlist-modify-private",
                                                show_dialog=True,
                                                cache_path="token.txt",
                                                username=username,
                            ))
        songs = []
        year = date.split("-")[0]
        n = 1
        for song in titles:
            try:
                result = sp.search(q=f"track:{song} year:{year}", type="track")
                artist = result["tracks"]["items"][0]["album"]["artists"][0]["name"]
                link = result["tracks"]["items"][0]["external_urls"]["spotify"]
                new_song = {'idcard':n,'name':song,'artist':artist,'link':link}
                songs.append(new_song)
            except IndexError:
                pass
            n += 1
        return jsonify({ 'songs': songs })
    except Exception:
        return jsonify({ 'error': "Couldn't fetch the songs" })

# ---------------------------------------------- INTERNET SPEED -----------------------------------------
@app.route('/api/check-internet-speed', methods=['POST'])
def check_internet_speed():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_experimental_option("detach", True)
    driver = webdriver.Chrome(options=chrome_options)
    up = 0
    down = 0

    driver.get("https://www.speedtest.net/")

    try:
        # Wait for the cookie banner's "Accept" button to be clickable and click it
        # You might need to adjust the locator below based on the actual website's button ID/class
        accept_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
        )
        accept_button.click()
        print("Accepted cookies.")

    except TimeoutException:
        print("Cookie banner did not appear or accept button not found within the time limit.")

    # Now, attempt to click the original element
    start_test_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CLASS_NAME, "js-start-test"))
    )
    start_test_button.click()
    # time.sleep(15)
    # try:
    #     go = driver.find_element(By.CSS_SELECTOR, '.start-button a')
    # except:
    #     return jsonify({ 'error': 'Button not found' })
    # else:
    #     go.click()

    time.sleep(90)

    try:
        download = driver.find_element(By.CLASS_NAME, 'download-speed').text
        upload = driver.find_element(By.CLASS_NAME, 'upload-speed').text
    except:
        return jsonify({ 'error': 'Value(s) not found' })
    else:
        down = float(download)
        up = float(upload)
        return jsonify({ 'download': down, 'upload': up })
        # print("Download speed:", down)
        # print("Upload speed:", up)

if __name__ == '__main__':
    app.run(debug=True,port=5000)