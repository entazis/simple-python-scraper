import csv
from requests import get
from requests.exceptions import RequestException
from contextlib import closing
from bs4 import BeautifulSoup


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
    print('Getting data from v3.torontomls.net..')
    address_info = get_address_info()
    # write csv
    print('done.\n')
