#!/usr/bin/python3
# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring, line-too-long

import os
import hashlib

from urllib.parse import urlencode
from io import BytesIO
import re

from dotenv import load_dotenv

import lxml.html
import imap_tools
from imap_tools import MailBox

import pycurl


def login(c):
    c.setopt(c.URL, 'https://' + os.getenv('SMG_HOST') + os.getenv('SMG_PAGE_LOGIN'))
    c.setopt(pycurl.TIMEOUT, 10)
    c.setopt(pycurl.FOLLOWLOCATION, 1)
    c.setopt(pycurl.COOKIEJAR, hashlib.sha256(os.getenv('SMG_PAGE_USER').encode('utf-8')).hexdigest() + '.cookie')
    buffer_a = BytesIO()
    c.setopt(c.WRITEDATA, buffer_a)
    c.perform()

    regex = b"id=\"j_id__v_0:javax\.faces\.ViewState:1\" value=\"([^\"]+)\""
    matches = re.findall(regex, buffer_a.getvalue())

    if len(matches) < 2:
        exit('No viewstate-information found.')
    post_data = {'userName': os.getenv('SMG_PAGE_USER'), 'password': os.getenv('SMG_PAGE_PWD'),
                 'captchaWasNecessary': 'false', 'captcha_hidden': '', 'kickMailMessageCacheKey': '',
                 'org.apache.myfaces.trinidad.faces.FORM': 'loginForm',
                 'javax.faces.ViewState': matches[0].decode('utf-8'), 'source': 'submitButton'}
    postfields = urlencode(post_data)
    c.setopt(c.POSTFIELDS, postfields)
    buffer_b = BytesIO()
    c.setopt(c.WRITEDATA, buffer_b)
    c.perform()

    return buffer_b.getvalue().decode('utf-8')


def move_eml(c):
    listpage = lxml.html.fromstring(login(c))
    message_table = listpage.findall(".//tbody[@id='messagesList:tbody_element']")[0]
    message_links = message_table.findall(".//a")

    for message_link in message_links:
        id = re.findall(b'id=([0-9a-f]+)', message_link.attrib['href'].encode('utf-8'))[0].decode('utf-8')
        url = 'https://' + os.getenv('SMG_HOST') + os.getenv('SMG_PAGE_DOWNLOAD') + '?id=' + id + '&type=eml'
        c.setopt(c.URL, url)
        buffer_a = BytesIO()
        c.setopt(c.WRITEDATA, buffer_a)
        c.perform()

        with MailBox(os.getenv('IMAP_HOST')).login(os.getenv('IMAP_USER'), os.getenv('IMAP_PWD'),
                                                   initial_folder=os.getenv('IMAP_DIR')) as mailbox:
            mailbox.append(buffer_a.getvalue(), 'DRS', dt=None, flag_set=[])


def main():
    load_dotenv()
    c = pycurl.Curl()
    move_eml(c)
    c.close()

    cookie_path = os.path.realpath(hashlib.sha256(os.getenv('SMG_PAGE_USER').encode('utf-8')).hexdigest() + '.cookie')

    if os.path.exists(cookie_path):
        os.remove(cookie_path)

    os.system('dedup/imapdedup.py -s ' + os.getenv('IMAP_HOST') + ' -p ' + os.getenv('IMAP_PORT') + ' -u ' + os.getenv(
        'IMAP_USER') + ' -x -w ' + os.getenv('IMAP_PWD') + ' ' + os.getenv('IMAP_DIR'))


if __name__ == "__main__":
    main()
