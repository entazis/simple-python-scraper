from requests import get
from requests.exceptions import RequestException
from contextlib import closing
from bs4 import BeautifulSoup
import pandas as pd
import io

import pickle
import os.path
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.http import MediaIoBaseDownload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Enable the Drive API and download credentials.json here: https://developers.google.com/drive/api/v3/quickstart/python

# If deleting output file on google drive, delete file-id.txt
# If modifying these scopes, delete the file token.pickle.
SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/spreadsheets.readonly']

# The ID and range of the spreadsheet containing urls to scrape from.
URL_SPREADSHEET_ID = '10aF-7QKoOA0EgHPeDFIWLvCr4iIOv51OVB4pI6t642s'
URL_RANGE_NAME = 'Sheet1!A:A'

# You can set the order of the columns here
# Also if a label does not listed here then the script adds it to the end of the csv
COLUMNS = [
    'Key:',
    'List:', 'For:', 'SPIS:', 'Last Status:', 'DOM:', 'Unit#:', 'Corp#:', 'Locker#:', 'Locker Lev Unit:',
    'Locker Unit#:', 'Level:', 'Rms:', 'Bedrooms:', 'Washrooms:', 'Dir/Cross St:', 'Prop Mgmt:', 'MLS#:',
    'Contract Date:', 'PIN#:', 'Possession Date:', 'Possession Remarks:', 'Kitchens:', 'Fam Rm:', 'Basement:',
    'Fireplace/Stv:', 'Heat:', 'Apx Age:', 'Apx Sqft:', 'Sqft Source:', 'Exposure:', 'Phys Hdp-Eqp:',
    'Spec Desig:', 'Lndry Acc:', 'Lndry Lev:', 'Pets Perm:', 'Locker:', 'Maintenance:', 'A/C:', 'Central Vac:',
    'UFFI:', 'Elev/Lift:', 'Retirement:', 'All Incl:', 'Water Incl:', 'Heat Incl:', 'Hydro Incl:',
    'Cable TV Incl:', 'CAC Incl:', 'Bldg Ins Incl:', 'Prkg Incl:', 'ComElem Inc:', 'Energy Cert:', 'Cert Level:',
    'GreenPIS:', 'Pvt Ent:', 'Furnished:', 'Balcony:', 'Exterior:', 'Gar/Gar Spcs:', 'Park/Drive:', 'Park Type:',
    'Park/Drv Spcs:', 'Tot Prk Spcs:', 'Park $/Mo:', 'Prk Lvl/Unit:', 'Bldg Amen:', 'Prop Feat:',
    'Client Remks:', 'Extras:', 'Listing Contracted With:', 'Acreage:', 'All Inclusive:', 'CAC Inc:', 'Cable Inc:',
    'Cable TV Util:', 'Com Elem Inc:', 'Contract:', 'Drive Prk Spcs:', 'Drive:', 'Farm/Agr:', 'Fronting On:', 'Gas:',
    'Heat Inc:', 'Hydro Inc:', 'Hydro Util:', 'Irreg:', 'Lease:', 'Lndy Lev:', 'Lot:', 'Lse Term:', 'POTL Mo Fee:',
    'POTL:', 'Park Cost/Mo:', 'Parking Inc:', 'Pay Freq:', 'Phone:', 'Pool:', 'Pvt Entrance:', 'Sewers:', 'Tot Pk Spcs:',
    'Water Inc:', 'Water Supply:', 'Water:', 'Waterfront:',
    'Image URL:', 'Data without label:', 'Status:'
]


def log_error(e):
    print(e)


def scrape_data_from_urls(urls):
    headers = {
        "Host": "v3.torontomls.net",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0"
    }

    # You can choose proxies from here: https://free-proxy-list.net/
    proxies = {
        'http': 'http://194.226.34.132:5555',
        'https': 'http://194.226.34.132:5555'
    }

    df = pd.DataFrame(columns=COLUMNS)

    for url in urls:
        try:
            print('Scraping URL: ', url)
            response = simple_get(url, headers, proxies)

            if response is not None:
                html = BeautifulSoup(response, 'html.parser')
                forms = html.select('div.formitem.legacyBorder')

                for form_index, form in enumerate(forms):
                    sr = pd.Series()
                    values_without_label = []

                    img = form.select('img.imageset')
                    sr.at['Image URL:'] = img[0]['src']

                    form_fields = form.select('span.formitem.formfield')

                    for idx, form_field in enumerate(form_fields):
                        if len(form_field.contents) > 1:
                            label = form_field.contents[0].text
                            value = form_field.contents[1].text
                            sr.at[label] = value
                        else:
                            value = form_field.text
                            values_without_label.append(value)
                    sr.at['Key:'] = '-'.join(values_without_label[0:14])
                    sr.at['Data without label:'] = ' - '.join(values_without_label)
                    sr.at['Status:'] = 'Available'
                    df = df.append(sr, ignore_index=True).fillna('-')

            else:
                raise Exception('Error retrieving contents at {}'.format(url))

        except Exception as e:
            log_error(e)

    df.to_csv('output.csv', index=False)
    return True


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


def get_urls_from_google_sheet():
    try:
        service = build('sheets', 'v4', credentials=get_creds())

        sheet = service.spreadsheets()
        result = sheet.values().get(
            spreadsheetId=URL_SPREADSHEET_ID,
            range=URL_RANGE_NAME).execute()
        values = result.get('values', [])
        spreadsheet_urls = []

        if not values:
            print('No urls found in the spreadsheet.')
        else:
            for row in values:
                spreadsheet_urls.append(row[0])

        return spreadsheet_urls

    except Exception as e:
        log_error(e)


def upload_csv_to_google_drive():
    try:
        service = build('drive', 'v3', credentials=get_creds())

        file_metadata = {'name': 'output.csv'}
        media = MediaFileUpload(
            'output.csv',
            mimetype='text/csv',
            resumable=True)

        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id').execute()

        print('Created file ID: %s' % file.get('id'))
        return file.get('id')

    except Exception as e:
        log_error(e)


def update_csv_on_google_drive(google_drive_file_id):
    try:
        service = build('drive', 'v3', credentials=get_creds())

        # Download the previous CSV from Google Drive
        request = service.files().get_media(fileId=google_drive_file_id)
        fh = io.FileIO('output-previous.csv', 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            print('Download %d%%.' % int(status.progress() * 100))

        # Update Status
        df = pd.read_csv('output.csv')
        df_former = pd.read_csv('output-previous.csv', index_col=False)
        expired = df_former[~df_former['Key:'].str.contains('|'.join(df['Key:']), na=False)]
        if not expired.empty:
            expired['Status:'] = "Not Available"
            df = df.append(expired)
            df.to_csv('output.csv', index=False)

        media_body = MediaFileUpload(
            'output.csv',
            mimetype='text/csv',
            resumable=True)

        updated_file = service.files().update(
            fileId=google_drive_file_id,
            media_body=media_body).execute()

        print('Updated file ID: %s' % updated_file.get('id'))

    except Exception as e:
        log_error(e)


def get_creds():
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
            return creds


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


if __name__ == '__main__':
    print('Google drive authorization..')
    authorize()

    print('Getting urls from Google sheet..')
    urls_from_sheet = get_urls_from_google_sheet()

    print('Getting data from v3.torontomls.net..')
    scrape_data_from_urls(urls_from_sheet)

    if os.path.exists('file-id.txt'):
        file_id_file = open("file-id.txt", "r")
        print('Updating file on Google drive..')
        update_csv_on_google_drive(file_id_file.read())
    else:
        print('Uploading file to Google drive..')
        file_id = upload_csv_to_google_drive()
        file_id_file = open("file-id.txt", "w")
        file_id_file.write(file_id)

    print('done.\n')
