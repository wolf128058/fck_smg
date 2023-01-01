#!/usr/bin/python3
# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring, line-too-long

import email
import sys

import os
import hashlib

from urllib.parse import urlencode
from io import BytesIO
import re

from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import subprocess

from dotenv import load_dotenv

import lxml.html
from imap_tools import MailBox

import pycurl

from random_user_agent.user_agent import UserAgent
from random_user_agent.params import SoftwareType, SoftwareName


def gpg_wrap(binary_plainmail):
    plainmail = email.message_from_bytes(binary_plainmail)
    gpg_cmdline = [os.getenv('GPG_PATH')] + [] + ['--armor', '--encrypt'] + ['--recipient', os.getenv('GPG_RECIPIENT')]
    gpgProg = subprocess.Popen(gpg_cmdline, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               stdin=subprocess.PIPE)
    innerMsg = MIMEMultipart()
    outerMsg = MIMEMultipart(_subtype='encrypted', protocol="application/pgp-encrypted")

    for part in plainmail.walk():
        if part.get_content_maintype() == 'text':
            new_mime = MIMEText(part.get_payload(), part.get_content_subtype(), _charset=part.get_charset())
            new_mime.set_charset('UTF-8')
            new_mime.replace_header("Content-Transfer-Encoding", "quoted-printable")
            innerMsg.attach(new_mime)
        elif part.get_content_maintype() == 'application':
            new_mime = MIMEText(part.get_payload(), _charset=None)
            new_mime.set_type('application/' + part.get_content_subtype())
            new_mime.replace_header("Content-Transfer-Encoding", "base64")
            if part.get_filename():
                new_mime.replace_header("Content-Type",
                                        'application/' + part.get_content_subtype() + '; ' + 'name="' + part.get_filename() + '"')
                new_mime.add_header("Content-Disposition", "attachment; filename=\"" + part.get_filename() + "\"")

            new_mime.set_charset(None)
            innerMsg.attach(new_mime)

    gpgOut = gpgProg.communicate(innerMsg.as_bytes())
    if len(gpgOut[1]) > 0:
        sys.exit('GPG Error')

    encryptedMsgHeader = MIMEBase('application', 'pgp-encrypted')
    encryptedMsgHeader.set_payload('Version 1\n')
    outerMsg.attach(encryptedMsgHeader)

    encryptedMsg = MIMEBase('application', 'octet-stream', name="encrypted.asc")
    encryptedMsg.set_payload(gpgOut[0].decode('utf-8'))
    encryptedMsg.add_header('Content-Disposition', 'inline', filename='encrypted.asc')
    outerMsg.attach(encryptedMsg)

    outerMsg['From'] = plainmail['From']
    outerMsg['Subject'] = plainmail['Subject']
    outerMsg['To'] = plainmail['To']
    outerMsg['Date'] = plainmail['Date']
    outerMsg['Message-ID'] = plainmail['Message-ID']
    return outerMsg


def login(c):
    c.setopt(c.URL, 'https://' + os.getenv('SMG_HOST') + os.getenv('SMG_PAGE_LOGIN'))
    c.setopt(pycurl.TIMEOUT, 10)
    c.setopt(pycurl.FOLLOWLOCATION, 1)
    c.setopt(pycurl.COOKIEJAR, hashlib.sha256(os.getenv('SMG_PAGE_USER').encode('utf-8')).hexdigest() + '.cookie')

    software_types = SoftwareType.WEB_BROWSER.value
    software_names = [SoftwareName.CHROME.value, SoftwareName.FIREFOX.value, SoftwareName.EDGE.value]
    user_agent_rotator = UserAgent(software_types=software_types, software_names=software_names, limit=100)
    user_agent = user_agent_rotator.get_random_user_agent()
    print('This time i am an: ' + user_agent)
    c.setopt(pycurl.HTTPHEADER, ['User-Agent: ' + user_agent])
    buffer_a = BytesIO()
    c.setopt(c.WRITEDATA, buffer_a)
    c.perform()

    regex = b"id=\"j_id__v_0:javax\.faces\.ViewState:1\" value=\"([^\"]+)\""
    matches = re.findall(regex, buffer_a.getvalue())

    if len(matches) < 2:
        sys.exit('No viewstate-information found.')
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

        currentmail = buffer_a.getvalue()

        if os.getenv('GPG_RECIPIENT'):
            currentmail = gpg_wrap(currentmail).as_bytes()

        with MailBox(os.getenv('IMAP_HOST')).login(os.getenv('IMAP_USER'), os.getenv('IMAP_PWD'),
                                                   initial_folder=os.getenv('IMAP_DIR')) as mailbox:
            mailbox.append(currentmail, 'DRS', dt=None, flag_set=[])


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
