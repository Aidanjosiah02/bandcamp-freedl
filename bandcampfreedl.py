from bs4 import BeautifulSoup
import datetime
import json
from pathlib import Path
import random
import re
import requests
import time
from timeit import default_timer
import urllib.parse
from urllib.request import urlretrieve
from urllib.parse import urlparse
import string
import sys


WAITS = True
ROOT = Path("./")
METADATA_DIR = Path('./metadata')
BATCH = (ROOT / "batch.txt")
TEMPMAIL_API = 'https://www.1secmail.com/api/v1/'
tempmail_domainList = ['1secmail.com', '1secmail.net', '1secmail.org']
tempmail_domain = random.choice(tempmail_domainList)
download_pattern = r'http://bandcamp.com/download\?.+'
fsig_pattern = r'&fsig=([a-z0-9]{32})'
ts_pattern = r'&ts=([0-9]{10}\.[0-9])'
background_pattern = re.compile(r'background-image: url\((.*?)\);', re.MULTILINE | re.DOTALL)
imgurl_pattern = r'https://f4.bcbits.com/img/(.*\.[a-z]+)'
windows_forbidden = r'[<>:"/\\|?*]'
random_twelve = str(random.randrange(100000000000,999999999999))
mib = 1048576
gib = 1024*mib


# cover_images = input("Bandcamp album downloads include cover images; single tracks do not. Grab images for albums anyway? (y/n): ")
cover_images = "y"
track_images = "y"
if cover_images == "n":
    track_images = input("Grab cover art for all single-track releases (NOT albums)? (y/n): ")
all_format = input('Type your selected format for ALL music downloads. "mp3-v0", "mp3-320", "flac", "aac-hi", "vorbis", "alac", "wav", "aiff-lossless". To select PER ALBUM/TRACK and see their sizes, type "0": ')
if cover_images != "y" and cover_images != "n":
    print("enter either \"y\" or \"n\" next time. Exiting.")
    input("press any key...")
    exit()
preview_audio = input("For paid releases, download the 128kbps mp3s that are publicly available? (y/n): ")
# print("If the script fails unexpectedly, you can try continuing from the position at which it failed. Each URL checked says what position it is.")
# STARTPOS = int(input("Input start position. \"0\" or leave empty for whole list: "))
STARTPOS = 0


main_headers = {
    'accept-encoding': 'gzip, deflate, br',
    'accept-language': 'en-GB,en;q=0.9,en-US;q=0.8',
    'sec-ch-ua': '"Chromium";v="104", " Not A;Brand";v="99", "Microsoft Edge";v="104"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.102 Safari/537.36 Edg/104.0.1293.63'
}
navigate_headers = main_headers
navigate_headers.update({
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'cache-control': 'max-age=0',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1'
})

request_count = 0





class Get_path:

    def scan(self, path):
        items = [item for item in Path(path).iterdir()]
        return items

    def dirs(self, path):
        dirs = []
        for item in self.scan(path):
            if item.is_dir():
                dirs.append(item)
        return dirs

    def files(self, path, name = False):
        files = []
        for item in self.scan(path):
            if item.is_file():
                if name != True:
                    files.append(item)
                else:
                    files.append(item.name)
        return files


def write_file(session, download_url, path_w_filename, filename):
    request_count = 0
    dl = 0
    with open(path_w_filename, "wb") as f:
        print("Downloading %s" % filename)
        response = session.get(download_url, stream=True)
        request_count += 1
        total_length = int(response.headers.get('content-length'))
        length_mib = str(total_length/mib)
        print(length_mib + " MiB")
        if total_length is None: # no content length header
            trust = input("No content header. Unknown size. Do you trust this file to be a reasonable size? (y/n): ")
            if trust == "y":
                f.write(response.content)
        else:
            start = default_timer()
            for data in response.iter_content(chunk_size=mib):
                dl += len(data)
                f.write(data)
                done = int(32 * dl / total_length)
                sys.stdout.write(" %s MiB/s" % str((dl/mib)/(default_timer()-start))[:4])
                sys.stdout.write("\r[%s%s]" % ('=' * done, ' ' * (32-done)) )
                sys.stdout.flush()
    return request_count


def get_preview_audio(session, tralbum, artist_path, dirname):
    request_count = 0
    artist_path.mkdir(parents=True, exist_ok=True)
    album_title = tralbum["current"]["title"]
    album_artist = tralbum["artist"]
    for set in tralbum["trackinfo"]:
        download_url = set["file"]["mp3-128"]
        track_artist = album_artist
        set_artist = str(set["artist"])
        if set_artist != "None":
            track_artist = set_artist
        title = set["title"]
        filename = f"{dirname} - mp3-128.mp3"
        path_w_filename = artist_path / filename
        index = str(set["track_num"])
        if index != "None":
            filename = re.sub(windows_forbidden, '_', f"{track_artist} - {album_title} - {index.zfill(2)} {title}.mp3")
            path = artist_path / f"{dirname} - mp3-128"
            path.mkdir(parents=True, exist_ok=True)
            path_w_filename = path / filename
        write_file(session, download_url, path_w_filename, filename)
    return request_count


def get_albums_from_page(url, soup):
    print("Downloading artist data", url, "...")

    default_artist_name = (soup.find("p", {"id": "band-name-location"}).find("span", {"class": "title"}).text)
    grid = soup.find("ol", {"id": "music-grid"})

    for result in grid.find_all("li", {"class": "music-grid-item"}):
        album_dict = {}
        a = result.find("a")
        album_dict["url"] = urllib.parse.urljoin(url, a["href"])
        album_title = list(a.find("p", {"class": "title"}).strings)
        album_dict["title"] = album_title[0].strip()
        if len(album_title) > 1:
            album_dict["artist_name"] = album_title[1].strip()
        else:
            album_dict["artist_name"] = default_artist_name

        album_dict["band_id"] = soup.find("ol", {"id": "music-grid"}).find("li")["data-band-id"]
        
        yield album_dict


def generateUserName():
    name = string.ascii_lowercase + string.digits
    username = ''.join(random.choice(name) for i in range(10))
    return username


def extract(tempmail):
    getUserName = re.search(r'login=(.*)&', tempmail).group(1)
    getDomain = re.search(r'domain=(.*)', tempmail).group(1)
    return [getUserName, getDomain]


def send_email(item_id, item_type, address, session, full_domain, url):
    headers = main_headers
    headers.update({
        'accept': '*/*',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': full_domain,
        'referer': url,
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'x-requested-with': 'XMLHttpRequest'
    })
    payload = {
        "encoding_name": "none",
        "item_id": item_id,
        "item_type": item_type,
        "address": address,
        "country": "US",
        "postcode": "0"
    }
    post_email = session.post((full_domain + "/email_download"), headers=headers, data=payload)
    print(post_email.text + " : " + address)


def get_response(session, url, headers):
    response = session.get(url, headers=headers)
    text = response.text
    soup = BeautifulSoup(text, "html.parser")
    return soup


def get_dict(json_script):
    dict = {}
    dict["url"] = json_script["@id"]
    dict["title"] = json_script["name"]
    album_release = ""
    try:
        album_release = json_script["albumRelease"][0]
    except:
        album_release = json_script["inAlbum"]["albumRelease"][0]
    try:
        dict["currency"] = album_release["offers"]["priceCurrency"]
    except:
        dict["currency"] = "USD"
    dict["item_id"] = str(album_release["additionalProperty"][0]["value"])
    dict["cover_img"] = json_script["image"]
    try:
        dict["icon_img"] = json_script["publisher"]["image"]
    except:
        dict["icon_img"] = None
    dict["artist_name"] = json_script["byArtist"]["name"]
    dict["publisher_name"] = json_script["publisher"]["name"]
    dict["publisher_id"] = str(json_script["publisher"]["additionalProperty"][0]["value"])
    dict["publisher_str"] = re.sub(windows_forbidden, '_', (dict["publisher_name"] + " - [" + dict["publisher_id"] + "]"))
    dict["date_published"] = str(datetime.datetime.strptime((json_script["datePublished"])[:-13], '%d %b %Y').strftime('%Y%m%d'))
    return(dict)


def get_images(soup, url, path):
    # image_headers = main_headers
    # image_headers.update({
    #     'accept': 'image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
    #     'referer': url,
    #     'sec-fetch-dest': 'image',
    #     'sec-fetch-mode': 'no-cors',
    #     'sec-fetch-site': 'cross-site'
    # })

    header_tf = False
    try:
        header_img = soup.find("div", {"id": "customHeaderWrapper"}).find("div", {"class": "desktop-header"})
        header_img_src = header_img.find("img")["src"]
        header_img_name = re.sub(windows_forbidden, '_', (re.findall(imgurl_pattern, header_img_src)[0]))
        header_tf = True
    except:
        print("no header image: " + url)
    background_tf = False
    try:
        background_img = soup.find("style", {"type": "text/css"})
        background_img_url = re.findall(background_pattern, str(background_img))[0]
        background_img_name = re.sub(windows_forbidden, '_', (re.findall(imgurl_pattern, background_img_url)[0]))
        background_tf = True
    except:
        print("no background image: " + url)
    icon_tf = False
    try:
        icon_img = soup.find("div", {"id": "bio-container"}).find("a", {"class": "popupImage"})
        icon_img_url = icon_img["href"]
        icon_img_name = re.sub(windows_forbidden, '_', (re.findall(imgurl_pattern, icon_img_url)[0]))
        icon_tf = True
    except:
        print("no icon image: " + url)

    request_count = 0
    if header_tf == True:
        header_path = (path / ("header_img-" + header_img_name))
        if not header_path.is_file():
            urlretrieve(header_img_src, header_path)
            request_count += 1
    if background_tf == True:
        background_path = (path / ("background_img-" + background_img_name))
        if not background_path.is_file():
            urlretrieve(background_img_url, background_path)
            request_count += 1
    if icon_tf == True:
        icon_path = (path / ("icon_img-" + icon_img_name))
        if not icon_path.is_file():
            urlretrieve(icon_img_url, icon_path)
            request_count += 1
    return request_count


def get_cookies(session):
    cookies = []
    for cookie in session.cookies:
        cookie_str = (cookie.name + "=" + cookie.value)
        cookies.append(cookie_str)
    formatted_cookies = "; ".join(map(str,cookies))
    print(formatted_cookies)
    return formatted_cookies

















urls = []
with open((BATCH), 'r') as batch:
    lines = batch.read().splitlines()
    for line in lines:
        urls.append(line)

results = []
results_length = len(results)
session = requests.Session()
for url in urls:
    parsed_url = urlparse(url)
    url_netloc = parsed_url[1]
    print(url_netloc)
    if f"{url_netloc}/album/" not in url and f"{url_netloc}/track/" not in url:
        response = session.get(url, headers=navigate_headers)
        request_count += 1
        soup = BeautifulSoup(response.text, "html.parser")
        if "cookies" not in main_headers:
            cookies = get_cookies(session)
            main_headers.update({'cookies': cookies})
        for album in get_albums_from_page(url, soup):
            results.append(album["url"])
    else:
        results.append(url)





checkpoint_n = (ROOT / "checkpoint.txt")
checkpoint = []
if checkpoint_n.exists():
    with open(checkpoint_n, 'r', encoding="utf-8") as checkpoint_r:
        checkpoint = checkpoint_r.read().splitlines()
archive_file = (ROOT / "archive.txt")
archive_list = []
if archive_file.exists():
    with open(archive_file, 'r', encoding="utf-8") as archive:
        archive_list = archive.read().splitlines()
preview_archive_file = (ROOT / "archive-mp3-128.txt")
preview_archive_list = []
if preview_archive_file.exists():
    with open(preview_archive_file, 'r', encoding="utf-8") as archive:
        preview_archive_list = archive.read().splitlines()

len_results = len(results)
# print(f"{len_results} tracks/albums to check. Request stats: max {(8*len_results)} + downloads, min {(len_results)}.")
if WAITS == True:
    print("This script will pause a minimum of 3 seconds per url.")
tempmail_session = requests.Session()
tempmail_new = ""
iterations = 0
total_download_size = 0
for url in results[STARTPOS:]:

    if request_count > 1000:
        print(f"Request count is greater than 1000: {request_count}.")
        print("[ctrl + c] exits. Progress is recorded in \"checkpoint.txt\".")
    if url in checkpoint:
        iterations += 1
        continue
    
    parsed_url = urlparse(url)
    url_netloc = parsed_url[1]
    url_scheme = parsed_url[0]
    full_domain = (f"{url_scheme}://{url_netloc}")
    if WAITS == True:
        time.sleep(random.uniform(3.0,6.0))
    print(f"\n Getting response for item {iterations}: {url}")
    soup = get_response(session, url, navigate_headers)
    
    
    request_count += 1
    if "cookies" not in main_headers:
        cookies = get_cookies(session)
        main_headers.update({'cookies': cookies})

    json_script = json.loads(re.findall(r'<script.*>\s+(?P<json>.+)\s+</script>' , str(soup.find('script', {'type': 'application/ld+json'})))[0])
    dict = get_dict(json_script)
    dpub = dict["date_published"]
    aname = dict["artist_name"]
    title = dict["title"]
    itemid = dict["item_id"]
    durl = dict["url"]
    currency = dict["currency"]

    data_js = soup.find('script', attrs={'data-tralbum': re.compile(r'require_email')})
    data_tralbum = json.loads(data_js['data-tralbum'])
    require_email = str(data_tralbum["current"]["require_email"])
    track_or_album = data_tralbum["current"]["type"]
    price = data_tralbum["current"]["minimum_price"]

    filename = re.sub(windows_forbidden, '_', f"{dpub} - {aname} - {title} - [{itemid}]")

    if itemid in archive_list:
        print(itemid + " already in \"archive.txt\". Skipping.")
        iterations += 1
        continue

    metadata_path = (METADATA_DIR / dict["publisher_str"])
    release_metadata_path = (metadata_path / "release")
    release_metadata_path.mkdir(parents=True, exist_ok=True)
    artist_path = (ROOT / "publishers" / dict["publisher_str"])
    artist_path.mkdir(parents=True, exist_ok=True)

    request_count += get_images(soup, url, metadata_path)

    cover_tf = False
    if cover_images == "y":
        cover_tf = True
    if track_or_album == "track" and track_images == "y":
        cover_tf = True


    if cover_tf == True:
        image_headers = main_headers
        # image_headers.update({
        #     'accept': 'image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
        #     'referer': url,
        #     'sec-fetch-dest': 'image',
        #     'sec-fetch-mode': 'no-cors',
        #     'sec-fetch-site': 'cross-site'
        # })
        cover_img = dict["cover_img"]
        cover_img_name = re.findall(imgurl_pattern, cover_img)[0]
        urlretrieve(cover_img, (release_metadata_path / (re.sub(windows_forbidden, '_', (filename + "-cover_img-" + cover_img_name)))))
        request_count += 1
    
    album_dict = [{"url": durl, "title": title, "artist_name": aname, "band_id": dict["publisher_id"]}]
    publisher_json = (metadata_path / (dict["publisher_str"] + ".json"))
    if publisher_json.exists():
        with open(publisher_json, 'r') as json_r:
            json_load = json.load(json_r)
            album_dict.extend(json_load)
    album_dict_dedupe = [i for n, i in enumerate(album_dict) if i not in album_dict[n + 1:]]
    with open(publisher_json, 'w') as json_a:
        json.dump(album_dict_dedupe, json_a, indent=4)

    with open(release_metadata_path / (re.sub(windows_forbidden, '_', (filename + "-ld.json"))), 'w') as json_w:
        json.dump(json_script, json_w, indent=4)
    with open(release_metadata_path / (re.sub(windows_forbidden, '_', (filename + "-tralbum.json"))), 'w') as json_w:
        json.dump(data_tralbum, json_w, indent=4)






    if price > 0.0:
        txt_filename = (re.sub(windows_forbidden, '_', (dict["publisher_name"] + " - [" + dict["publisher_id"] + "]-paid_releases.csv")))
        txt_path = (ROOT / txt_filename)
        print(f"{aname} - {title}")
        print(f"Price: {str(price)}{currency}.")

        if preview_audio == "y":
            if itemid in preview_archive_list:
                print(itemid + " already in \"archive-mp3-128.txt\". Skipping.")
                iterations += 1
                continue
            else:
                print(f"Writing info to {txt_filename}. Downloading mp3-128.")
                request_count += get_preview_audio(session, data_tralbum, artist_path, filename)
                with open(preview_archive_file, 'a') as archive_a:
                    archive_a.write(itemid + "\n")
                artist_archive = (artist_path / "archive-mp3-128.txt")
                with open(artist_archive, 'a') as archive_a:
                    archive_a.write(itemid + "\n")
        else:
            print(f"Writing info to {txt_filename}. Skipping.")
        text_list = []
        if txt_path.exists():
            with open(txt_path, 'r', encoding="utf-8") as text:
                text_list = text.read().splitlines()
        txt_string = f"\"{durl}\",\"{price}\",\"{currency}\",\"{dpub} - {aname} - {title} - [{itemid}]\""
        if txt_string not in text_list:
            with open(txt_path, 'a', encoding="utf-8") as txt_file:
                txt_file.write(txt_string + "\n")

        iterations += 1
        with open("checkpoint.txt", 'a') as checkpoint_a:
            checkpoint_a.write(url + "\n")
        continue



    link_origin = 'same-origin'
    download_page = ""
    if require_email == "" or require_email == "None":
        download_page = data_tralbum["freeDownloadPage"]
        link_origin = 'same-origin'
    elif require_email == "1":
        if tempmail_new == "":
            tempmail_new = f"{TEMPMAIL_API}?login={generateUserName()}&domain={tempmail_domain}"
        tempmail = f"{extract(tempmail_new)[0]}@{extract(tempmail_new)[1]}"
        if WAITS == True:
            print("Waiting 6-10 seconds pretending to enter email and postal information.")
            time.sleep(random.uniform(6.0,10.0))
        send_email(itemid, track_or_album, tempmail, tempmail_session, full_domain, url)
        request_count += 1
        while download_page == "":
            print("Waiting 4 seconds for email.")
            time.sleep(4.0)
            tempmail_messages_str = f'{TEMPMAIL_API}?action=getMessages&login={extract(tempmail_new)[0]}&domain={extract(tempmail_new)[1]}'
            tempmail_messages = tempmail_session.get(tempmail_messages_str).json()
            tempmail_message_ids = []
            for i in tempmail_messages:
                for k,v in i.items():
                    if k == 'id':
                        tempmail_id = v
                        tempmail_message_ids.append(tempmail_id)

            tempmail_read = f'{TEMPMAIL_API}?action=readMessage&login={extract(tempmail_new)[0]}&domain={extract(tempmail_new)[1]}&id={tempmail_message_ids[0]}'
            try:
                text = tempmail_session.get(tempmail_read).json()["textBody"]
                tempmail_found_url = re.findall(download_pattern, text)[0]
                if len(tempmail_found_url) > 32:
                    download_page = tempmail_found_url
            except:
                send_email(itemid, track_or_album, tempmail, tempmail_session, full_domain, url)
                request_count += 1
                print("No email found. Trying again.")
        link_source = 'cross-site'






    headers = main_headers
    headers.update({
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': link_origin,
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1'
    })
    if WAITS == True:
        print("Waiting 2-3.5 seconds pretending to find link.")
        time.sleep(random.uniform(2.0,3.5))
    soup = get_response(session, download_page, headers)
    request_count += 1
    data_js = soup.find('div', {'id': "pagedata"})
    data_blob = json.loads(data_js['data-blob'])
    download_formats = data_blob["download_formats"]
    digital_items = data_blob["digital_items"][0]
    extensions = {
        "mp3-v0": download_formats[0]["file_extension"],
        "mp3-320": download_formats[1]["file_extension"],
        "flac": download_formats[2]["file_extension"],
        "aac-hi": download_formats[3]["file_extension"],
        "vorbis": download_formats[4]["file_extension"],
        "alac": download_formats[5]["file_extension"],
        "wav": download_formats[6]["file_extension"],
        "aiff-lossless": download_formats[7]["file_extension"]
    }
    fmts = digital_items["downloads"]
    selected_format = ""
    if all_format == "0":
        selected_format = input('Type your selected format. "mp3-v0" %s, "mp3-320" %s, "flac" %s, "aac-hi" %s, "vorbis" %s, "alac" %s, "wav" %s, "aiff-lossless" %s: ' % (fmts["mp3-v0"]["size_mb"], fmts["mp3-320"]["size_mb"], fmts["flac"]["size_mb"], fmts["aac-hi"]["size_mb"], fmts["vorbis"]["size_mb"], fmts["alac"]["size_mb"], fmts["wav"]["size_mb"], fmts["aiff-lossless"]["size_mb"]))
    else:
        selected_format = all_format
    
    download_page_url = digital_items["downloads"][selected_format]["url"]
    
    extension = ""
    if track_or_album == "track":
        extension = extensions[selected_format]
    else:
        extension = ".zip"

    with open(release_metadata_path / (re.sub(windows_forbidden, '_', (filename + "-pagedata.json"))), 'w') as json_w:
        json.dump(data_blob, json_w, indent=4)


    parsed_url = urlparse(download_page)
    url_netloc = parsed_url[1]
    url_scheme = parsed_url[0]
    origin = (f"{url_scheme}://{url_netloc}")
    headers = main_headers
    headers.update({
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'origin': origin,
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site'
    })

    stat_url = download_page_url.replace("/download/", "/statdownload/")
    full_stat_url = f"{stat_url}&.rand={random_twelve}&.vrs=1"
    print(full_stat_url)
    domain_poppler_remove = full_stat_url.replace("https://popplers5.bandcamp.com", "")
    response = session.get(full_stat_url, headers=headers)
    
    request_count += 1
    download_response = json.loads(response.text)
    if require_email == "" or require_email == "None":
        download_url = download_response["retry_url"]
    if require_email == "1":
        download_url = download_response["download_url"]



    headers = main_headers
    headers.update({
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'cross-site',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1'
    })

    

    filename_music = (filename + " - " + selected_format + extension)
    if WAITS == True:
        print("Waiting 1-2 seconds pretending to click download button.")
        time.sleep(random.uniform(1.0,2.0))
    request_count += write_file(session, download_url, (artist_path / filename_music), filename_music)


    with open(archive_file, 'a') as archive_a:
        archive_a.write(itemid + "\n")
    artist_archive = (artist_path / "archive.txt")
    with open(artist_archive, 'a') as archive_a:
        archive_a.write(itemid + "\n")
    with open("checkpoint.txt", 'a') as checkpoint_a:
        checkpoint_a.write(url + "\n")

    iterations += 1
