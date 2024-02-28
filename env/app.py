# import necessary modules
import time, datetime
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from flask import Flask, request, url_for, session, redirect, render_template

# initialize Flask app
app = Flask(__name__)

# set the name of the session cookie
app.config['SESSION_COOKIE_NAME'] = 'Spotify'

# set a random secret key to sign the cookie
app.secret_key = 'YOUR_SECRET_KEY'

# set the key for the token info in the session dictionary
TOKEN_INFO = ''


# route to handle logging in
@app.route('/')
def login():
    # create a SpotifyOAuth instance and get the authorization URL
    auth_url = create_spotify_oauth().get_authorize_url()
    # redirect the user to the authorization URL
    return redirect(auth_url)


# route to handle the redirect URI after authorization
@app.route('/redirect')
def redirect_page():
    # clear the session
    session.clear()
    # get the authorization code from the request parameters
    code = request.args.get('code')
    # exchange the authorization code for an access token and refresh token
    token_info = create_spotify_oauth().get_access_token(code)
    # save the token info in the session
    session[TOKEN_INFO] = token_info
    # redirect the user to the save_discover_weekly route
    return redirect('/home')


@app.route('/home', methods=['GET', 'POST'])
def home():

    if request.method == "POST":
        return redirect('/playlistselection')

    return render_template('home.html')



@app.route('/playlistselection', methods=['GET', 'POST'])
def playlist_selector():
    try:
        token_info = get_token()
    except:
        print('User not logged in')
        return redirect("/")

    spotify = spotipy.Spotify(auth=token_info['access_token']) #make home page before this
    user_id = spotify.current_user()["id"]
    session["user"] = user_id

    playlist_data = get_all_playlists(sp=spotify)

    if request.method == 'POST':
        playlist_option = request.form.get('playlistOption')
        offset = 0
        playlist_id = playlist_data[playlist_option]

        if playlist_id == "Liked Songs":

            playlist_info = spotify.current_user_saved_tracks(offset=offset)
            total_songs = playlist_info["total"]

            track_ids = [song["track"]["id"] for song in playlist_info["items"]]

                        
            while len(track_ids) < total_songs:
                offset += 20
                playlist_info = spotify.current_user_saved_tracks(offset=offset)
                remaining = [song["track"]["id"] for song in playlist_info["items"]]
                track_ids = track_ids + remaining


        else:

            playlist_info = spotify.playlist_items(playlist_id=playlist_id, offset=offset, additional_types=('track',))
            total_songs = playlist_info["total"]

            track_ids = [song["track"]["id"] for song in playlist_info["items"]]

                        
            while len(track_ids) < total_songs:
                offset += 100
                playlist_info = spotify.playlist_items(playlist_id=playlist_id, offset=offset, additional_types=('track',))
                remaining = [song["track"]["id"] for song in playlist_info["items"]]
                track_ids = track_ids + remaining
            
        session["playlist"] = track_ids
        return redirect('/features')
    

    #save info in separate parts in session: for example session['playlist'] session['playlist2'] etc? maybe that would solve issue

    
    #have animation between pages as if you're going downward (like vandyhacks application)

    return render_template('playlist_selection.html', playlist_data=playlist_data)


@app.route('/features',  methods=['GET', 'POST'])
def features():
     
     if request.method == 'POST':
            
            features = request.form.getlist('option') #add error message if nothing is selected
            if not features:
                return render_template('features.html')
            features.append('result')
            session['features'] = features
            next = features.pop(0)
            return redirect(f'/{next.lower()}')
     
     return render_template('features.html')


@app.route('/genre', methods=['GET', 'POST'])
def genre():

    start = time.time()

    token_info = get_token()
    spotify = spotipy.Spotify(auth=token_info['access_token'])

    playlist = session['playlist']

    playlist_genres = {'indie': [], 'pop': [], 'rock': [], 'hip hop': []} #maybe add an input where they just can say 'indie' or 'hip hop'

    for id in playlist:

        song = spotify.track(track_id=id)

        artist_id = song['artists'][0]['id']

        artist_genres = spotify.artist(artist_id=artist_id)['genres']

        for gnr in artist_genres: #redo all of this

            checkers = {'indie': True, 'rock': True, 'pop': True, 'hip hop': True}

            if 'indie' in gnr and checkers['indie']:
                playlist_genres['indie'].append(id)
                checkers['rock'],checkers['hip hop'],checkers['pop'] = False, False, False

            if 'rock' in gnr and checkers['rock']:
                playlist_genres['rock'].append(id)
                checkers['rock'],checkers['hip hop'],checkers['pop'] = False, False, False

            if 'pop' in gnr and checkers['pop']:
                playlist_genres['pop'].append(id)
                checkers['rock'],checkers['hip hop'],checkers['pop'] = False, False, False

            if 'hip hop' in gnr and checkers['hip hop']:
                playlist_genres['hip hop'].append(id)
                checkers['rock'],checkers['hip hop'],checkers['pop'] = False, False, False

            if gnr in playlist_genres.keys():
                playlist_genres[gnr].append(id)
            else:
                playlist_genres[gnr] = [id]

    #add a start over button that takes you to playlist page and cleans the session
    
    if request.method == 'POST':

            chosen_genres = request.form.getlist('genre')
            final_playlist = []
            for genre in chosen_genres:
                final_playlist += playlist_genres[genre] #has duplicates, fix that

            session['playlist'] = final_playlist

            features = session['features']
            next = features.pop(0)
            return redirect(f'/{next.lower()}')

    end = time.time()

    print(end - start)

    return render_template('genre.html', playlist_genres=playlist_genres)


@app.route('/length', methods=['GET', 'POST'])
def length():

    token_info = get_token()
    spotify = spotipy.Spotify(auth=token_info['access_token'])

    #maybe every page should have a search button where they can check on a certain song (like how long it is, what genre it is etc to
    # get a sense of it all) have them submit a song id, or a spotify.search ??

    if request.method == 'POST':
            
        filtered_playlist = session['playlist']
        new_playlist = []

        more_less = request.form.get('moreless')
        length = int(request.form.get('length'))

        for track in filtered_playlist:
            song = spotify.track(track_id=track)

            duration = float(song['duration_ms']/1000/60)
            if more_less == 'longer than' and length <= duration:
                new_playlist.append(song['id'])
            if more_less == 'shorter than' and length >= duration:
                new_playlist.append(song['id'])

        session['playlist'] = new_playlist

        features = session['features']
        next = features.pop(0)
        return redirect(f'/{next.lower()}') #figure this out
    

    #possible parameters: danceability, tempo, 
    #loudness, instrumentalness, liveness (can return just live or non-live ones)

    #should also explain the different audio features and maybe provide examples of famous songs

    return render_template('length.html')


"""@app.route('/popularity', methods=['GET', 'POST'])  #the popularity metric isn't the best
def popularity():

    token_info = get_token()
    spotify = spotipy.Spotify(auth=token_info['access_token'])

    if request.method == 'POST' and "skip" in request.form:
        return redirect('/era')

    if request.method == 'POST':
        filtered_playlist = session['playlist']
        new_playlist = []

        pop = request.form.get('popularity')

        print(spotify.track(track_id='https://open.spotify.com/track/0avhBw11JbU6miRBqKANwH?si=4445377fc4ab4804'))

        for track in filtered_playlist:
            song = spotify.track(track_id=track)

            if pop == 'Popular' and 60 <= int(song['popularity']):
                new_playlist.append(song['id'])

            elif pop == 'Known' and 25 <= int(song['popularity']) < 60:
                new_playlist.append(song['id'])

            elif pop == 'Underground' and 10 <= int(song['popularity']) < 25:
                new_playlist.append(song['id'])

            elif pop == 'So quirky and different' and int(song['popularity']) < 10:
                new_playlist.append(song['id'])

        session['playlist'] = new_playlist
        return redirect('/era')


    return render_template('popularity.html')"""


@app.route('/era', methods=['GET', 'POST'])
def era():

    token_info = get_token()
    spotify = spotipy.Spotify(auth=token_info['access_token'])

    if request.method == 'POST':
        filtered_playlist = session['playlist']
        new_playlist = []

        start = int(request.form.get('from'))
        end = request.form.get('until')

        if end.lower() == 'now':
            end = int(datetime.datetime.now().year)
        else:
            end = int(end)

        for track in filtered_playlist:
            song = spotify.track(track_id=track)

            if start <= int(song['album']['release_date'][:4]) <= end:
                new_playlist.append(song['id'])

        session['playlist'] = new_playlist
        features = session['features']
        next = features.pop(0)
        return redirect(f'/{next.lower()}') #figure this out


    return render_template('era.html')



@app.route('/energy', methods=['GET', 'POST'])
def energy():

    token_info = get_token()
    spotify = spotipy.Spotify(auth=token_info['access_token'])

    filtered_playlist = session['playlist']
    new_playlist = []

    #if request.headers.get("Referer"): #figure out what happens when back button is pressed

    if request.method == 'POST':

        energy = request.form.get('energy')

        for track in filtered_playlist:
            song_energy = spotify.audio_features(tracks=track)[0]['energy']

            if energy == "Energetic" and song_energy >= 0.5:
                new_playlist.append(track)
            if energy == "Chill" and song_energy < 0.5:
                new_playlist.append(track)

        session['playlist'] = new_playlist

        features = session['features']
        next = features.pop(0)
        return redirect(f'/{next.lower()}') #figure this out
    
    return render_template('energy.html')


@app.route('/mood', methods=['GET', 'POST']) 
def mood():

    token_info = get_token()
    spotify = spotipy.Spotify(auth=token_info['access_token'])

    if request.method == 'POST':
            
        filtered_playlist = session['playlist']
        new_playlist = []

        mood = request.form.get('mood')

        for track in filtered_playlist:
            song_mood = spotify.audio_features(tracks=track)[0]['valence']

            if mood == "Happy" and song_mood >= 0.4:
                new_playlist.append(track)
            if mood == "Sad" and song_mood < 0.4:
                new_playlist.append(track)

        session['playlist'] = new_playlist

        features = session['features']
        next = features.pop(0)
        return redirect(f'/{next.lower()}')
    
    return render_template('mood.html')


#end of specific route

#the similar songs route?
@app.route('/similarsongs', methods=['GET', 'POST'])
def similarsongs():

    session['similar songs'] = ''

    if request.method == 'POST':
        similarsongs = request.form.get('similar songs')
        session['similar songs'] = similarsongs
        return redirect('/energy')


    return render_template('decade.html')


@app.route('/result', methods = ['GET', 'POST'])
def result():
    token_info = get_token()
    spotify = spotipy.Spotify(auth=token_info['access_token'])

    final_playlist = session['playlist']

    if request.method == "POST":

        if "restart" in request.form:
            session['playlist'] = []
            return redirect('/playlistselection')
        
        elif "done" in request.form:
            new_playlist_id = spotify.user_playlist_create(user=session['user'], name="Your Sorted Playlist")["id"]
            spotify.playlist_add_items(playlist_id=new_playlist_id, items=final_playlist)
            return redirect('/endpage')

    songs = []
    for song in final_playlist:
        song_info = spotify.track(track_id=song)
        song_name = song_info['name']
        artist_name = ''

        for artist in song_info['artists'][:-1]:
            artist_name += artist['name'] + ', '
        
        artist_name += song_info['artists'][-1]['name']

        songs.append(song_name + " - " + artist_name)


    return render_template('result.html', songs=songs)


@app.route('/endpage', methods=['GET', 'POST'])
def endpage():

    if request.method == 'POST':
        return redirect('/playlistselection')


    return render_template('endpage.html')


@app.route('/contact', methods=['GET', 'POST'])
def contact():

    return render_template('contact.html')


# function to get the token info from the session
def get_token():
    token_info = session.get(TOKEN_INFO, None)
    if not token_info:
        # if the token info is not found, redirect the user to the login route
        redirect(url_for('login', _external=False))

    # check if the token is expired and refresh it if necessary
    now = int(time.time())

    is_expired = token_info['expires_at'] - now < 60
    if is_expired:
        spotify_oauth = create_spotify_oauth()
        token_info = spotify_oauth.refresh_access_token(token_info['refresh_token'])

    return token_info


def create_spotify_oauth():
    return SpotifyOAuth(
        client_id='eedc6ce5c8d742bfa6849f3b3821289d',
        client_secret='d0a21e681f3d455bbf6103d1975bb8fa',
        redirect_uri=url_for('redirect_page', _external=True),
        scope="user-read-currently-playing,user-library-read,user-modify-playback-state, \
            user-read-recently-played,user-read-playback-state,playlist-modify-public, playlist-modify-private, playlist-read-collaborative"
    )


def genre_list():
    with open('genres.txt', 'r') as file:
        read = file.read()
        genres = read.split("\n")
        return genres


def get_all_playlists(sp):

    playlist = sp.current_user_playlists(offset=0)
    
    playlist_data = {"Liked Songs": "Liked Songs"}
    
    for item in playlist["items"]:
        playlist_data[item["name"]] = item["id"]
    
    ofst = 50
    remaining = sp.current_user_playlists(limit=50, offset=ofst)

    while len(remaining["items"]) > 0:
        for item in remaining["items"]:
            playlist_data[item["name"]] = item["id"]

        ofst += 50
        remaining = sp.current_user_playlists(limit=50, offset=ofst)
    
    return playlist_data



