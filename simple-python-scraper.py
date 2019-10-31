import csv
from requests import get
from requests.exceptions import RequestException
from contextlib import closing
from bs4 import BeautifulSoup

import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly']


def authorize():
    """Shows basic usage of the Drive v3 API.
    Prints the names and ids of the first 10 files the user has access to.
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('drive', 'v3', credentials=creds)

    # Call the Drive v3 API
    results = service.files().list(
        pageSize=20, fields="nextPageToken, files(id, name)").execute()
    items = results.get('files', [])

    if not items:
        print('No files found.')
    else:
        print('Files:')
        for item in items:
            print(u'{0} ({1})'.format(item['name'], item['id']))


def simple_get(url, headers, proxies):
    try:
        with closing(get(url, headers=headers, proxies=proxies, stream=True)) as resp:
            if is_good_response(resp):
                return resp.content
            else:
                return None

    except RequestException as e:
        log_error('Error during requests to {0} : {1}'.format(url, str(e)))
        return None


def is_good_response(resp):
    content_type = resp.headers['Content-Type'].lower()
    return (resp.status_code == 200
            and content_type is not None
            and content_type.find('html') > -1)


def log_error(e):
    print(e)


def get_address_info():
    url = 'http://v3.torontomls.net/Live/Pages/Public/Link.aspx?Key=95089319b90c45e3b1cc10298ba6bab8&App=TREB'
    headers = {
        "Host": "v3.torontomls.net",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0"
    }
    proxies = {
        'http': 'http://194.226.34.132:5555',
        'https': 'http://194.226.34.132:5555'
    }
    response = simple_get(url, headers, proxies)

    if response is not None:
        html = BeautifulSoup(response, 'html.parser')
        forms = html.select('div.formitem.legacyBorder')
        rows = []
        columns = []

        for form in forms:
            img = form.select('img.imageset')
            image_url = img[0]['src']
            print(image_url)
            form_fields = form.select('span.formitem.formfield')
            form_object = {}
            for idx, form_field in enumerate(form_fields):
                label = 'text-' + str(idx) + ':'
                if (len(form_field.contents) > 1):
                    label = form_field.contents[0].text
                    value = form_field.contents[1].text
                else:
                    value = form_field.text

                form_object[label] = value
            print(form_object)

            keys = form_object.keys()
            row = form_object.values()
            columns = keys
            rows.append(row)

            with open('output.csv', 'w') as output_file:
                dict_writer = csv.writer(output_file)
                dict_writer.writerow(keys)
                dict_writer.writerow(row)

        with open('output-2.csv', 'w') as output_file:
            dict_writer = csv.writer(output_file)
            dict_writer.writerow(keys)
            dict_writer.writerows(rows)

        return forms

    raise Exception('Error retrieving contents at {}'.format(url))


if __name__ == '__main__':
    print('Google drive authorization..')
    authorize()
    # print('Getting data from v3.torontomls.net..')
    # address_info = get_address_info()
    print('done.\n')
