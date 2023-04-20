# --- Creates/reads emails from inbox ---

import imaplib
import email
from email.header import decode_header
import webbrowser
import os
from google.cloud import datastore
from flask import Flask, request, render_template, redirect, send_from_directory
import re
import datetime

# Import Google Translate API
from google.cloud import translate_v2 as translate

# Initialize global variable
translate_client = translate.Client()


# account credentials

username = "alexmonilla.jobsearch@gmail.com"

password = "zrjlijlypnajmfap"

def clean(text):

    # clean text for creating a folder

    return "".join(c if c.isalnum() else "_" for c in text)


# create an IMAP4 class with SSL 

imap = imaplib.IMAP4_SSL("imap.gmail.com")

# authenticate

imap.login(username, password)

imap.select("INBOX")

status, messages = imap.search(None, '(UNSEEN)') # Fetch unseen emails

# number of top emails to fetch

N = 3

# total number of emails

# messages = int(messages[0])


for i in messages[0].split():

    # fetch the email message by ID

    res, msg = imap.fetch(i, "(RFC822)")

    for response in msg:

        if isinstance(response, tuple):

            # parse a bytes email into a message object

            msg = email.message_from_bytes(response[1])

            # decode the email subject

            subject, encoding = decode_header(msg["Subject"])[0]

            if isinstance(subject, bytes):

                # if it's a bytes, decode to str

                subject = subject.decode(encoding)

            # decode email sender

            From, encoding = decode_header(msg.get("From"))[0]

            if isinstance(From, bytes):

                From = From.decode(encoding)

            print("Subject:", subject)

            print("From:", From)

            # if the email message is multipart

            if msg.is_multipart():

                # iterate over email parts

                for part in msg.walk():

                    # extract content type of email

                    content_type = part.get_content_type()

                    content_disposition = str(part.get("Content-Disposition"))

                    try:

                        # get the email body

                        body = part.get_payload(decode=True).decode()

                    except:

                        pass

                    if content_type == "text/plain" and "attachment" not in content_disposition:

                        # print text/plain emails and skip attachments

                        print(body)

            else:

                # extract content type of email

                content_type = msg.get_content_type()

                # get the email body

                body = msg.get_payload(decode=True).decode()

                if content_type == "text/plain":

                    # print only text email parts

                    print(body)

            print("="*100)

# close the connection and logout

    body = re.sub('<[^<]+?>', '', body)

    Retrieval_date = datetime.datetime.now()

    client = datastore.Client()
    email_info_kind = 'Email-Info'

    Receive_date, encoding = decode_header(msg.get("Date"))[0]

    addr_pattern = re.compile("<(.+)>")
    Email = addr_pattern.findall(From)
    
    complete_key = client.key(email_info_kind)
    customer = datastore.Entity(key=complete_key)
    customer.update({
        'Body': translate_client.translate(body, target_language='en')['translatedText'],
        'Receive_Date': Receive_date,
        'Response_Date': '',
        'Retrieval_Date': Retrieval_date,
        'Sender_Email': Email[0],
        'Response_Flag': False,
        "Subject": translate_client.translate(subject, target_language='en')['translatedText'], 
    })
    client.put(customer)

imap.close()
imap.logout()