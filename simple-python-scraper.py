import csv
from requests import get
from requests.exceptions import RequestException
from contextlib import closing
from bs4 import BeautifulSoup

import pickle
import os.path
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.pickle.
SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/spreadsheets.readonly']

# The ID and range of the spreadsheet containing urls to scrape from.
URL_SPREADSHEET_ID = '10aF-7QKoOA0EgHPeDFIWLvCr4iIOv51OVB4pI6t642s'
URL_RANGE_NAME = 'Sheet1!A:A'


def authorize():
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


def get_urls_from_google_sheet():
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    service = build('sheets', 'v4', credentials=creds)

    # Call the Sheets API
    sheet = service.spreadsheets()
    result = sheet.values().get(
        spreadsheetId=URL_SPREADSHEET_ID,
        range=URL_RANGE_NAME).execute()
    values = result.get('values', [])

    if not values:
        print('No urls found in the spreadsheet.')
    else:
        print('Urls:')
        for row in values:
            # Print columns A
            print('url: %s' % (row[0]))
        return values


def upload_to_google_drive():
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    service = build('drive', 'v3', credentials=creds)

    # Call the Drive v3 API
    file_metadata = {'name': 'output.csv'}
    media = MediaFileUpload(
        'output.csv',
        mimetype='text/csv',
        resumable=True)
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id').execute()

    print('File ID: %s' % file.get('id'))


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


def get_address_info(urls):
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

    rows = []
    columns = []

    for url in urls:
        try:
            response = simple_get(url, headers, proxies)

            if response is not None:
                html = BeautifulSoup(response, 'html.parser')
                forms = html.select('div.formitem.legacyBorder')

                for form in forms:
                    img = form.select('img.imageset')
                    image_url = img[0]['src']

                    form_fields = form.select('span.formitem.formfield')
                    form_object = {}

                    for idx, form_field in enumerate(form_fields):
                        label = 'text-' + str(idx) + ':'
                        if len(form_field.contents) > 1:
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
            else:
                raise Exception('Error retrieving contents at {}'.format(url))

        except Exception as e:
            log_error(e)

    with open('output.csv', 'w') as output_file:
        dict_writer = csv.writer(output_file)
        dict_writer.writerow(columns)
        dict_writer.writerows(rows)

    return True


if __name__ == '__main__':
    print('Google drive authorization..')
    authorize()

    print('Getting urls from Google sheet..')
    urls = get_urls_from_google_sheet()

    print('Getting data from v3.torontomls.net..')
    get_address_info(urls)

    print('Uploading file to Google drive..')
    upload_to_google_drive()

    print('done.\n')
