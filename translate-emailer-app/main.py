import os
from config import *
import datetime

# Import Sendgrid info
import sendgrid
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

# Required Flask Libraries
from flask import Flask, request, render_template, redirect, send_from_directory

# Import Google Datastore API
from google.cloud import datastore

# Import Google Translate API
from google.cloud import translate_v2 as translate

# Initialize global variable
translate_client = translate.Client()
client = datastore.Client()
kind = 'Custinfo'
Email_kind = 'Email-Info'

# Start Flask app
app = Flask(__name__)

# Static directory for css
@app.route('/static/<path:path>')
def send_js(path):
    return send_from_directory('static', path)

# Home Page (will show all the customers in the datastore)
@app.route('/', methods=['GET'])
def index():
    query1 = client.query(kind=kind)
    query1.add_filter("Class", "=", "z81")
    query2 = client.query(kind=kind)
    query2.add_filter("Class", "=", "z82")
    class1 = list(query1.fetch())
    class2 = list(query2.fetch())
    return render_template('index.html', class1=class1, class2=class2)

# Create
@app.route('/create', methods=['POST', 'GET'])
def create():
    if request.method == 'POST':
        data = request.form.to_dict(flat=True)

        # Put customer record
        complete_key = client.key(kind, data['Last'])
        customer = datastore.Entity(key=complete_key)
        customer.update({
            'Class': data['Class'],
            'First': data['First'],
            'Last': data['Last'],
            'email': data['email'],
            "lang": data['lang'],
        })
        client.put(customer)

        # Redirect to customer page
        return redirect("/read/" + data['Last'])

    else:
        # GET - Render customer creation form
        return render_template('create.html')


# Read
@app.route('/read/<name>', methods=['GET'])
def read(name):
    key = client.key(kind, name)
    customer = client.get(key)
    return render_template('customer.html', first=customer['First'], last=customer['Last'], email=customer['email'],
                           lang=customer['lang'], Class=customer['Class'])


# Update
@app.route('/update/<name>', methods=['GET', 'POST'])
def update(name):
    if request.method == 'POST':
        data = request.form.to_dict(flat=True)

        key = client.key(kind, name)
        customer = client.get(key)

        customer['Class'] = data['Class']
        customer['email'] = data['email']
        customer['lang'] = data['lang']
        client.put(customer)

        # Redirect to customer page
        return redirect("/read/" + name)

    else:
        # Get customer data
        key = client.key(kind, name)
        customer = client.get(key)

        # Renders update page with existing data
        return render_template('update.html', first=customer['First'], email=customer['email'], lang=customer['lang'],
                               last=customer['Last'], Class=customer['Class'])

# Delete
@app.route('/delete/<name>', methods=['GET'])
def delete(name):
    # Delete Customer Record
    key = client.key(kind, name)
    client.delete(key)

    # Redirect to index page
    return redirect('/')


#Compose Message - GET
@app.route('/compose', methods=['GET'])
def compose():
    return render_template('compose.html')

#Compose Message - POST
@app.route('/compose-message', methods=['POST'])
def compose_message():
    data = request.form.to_dict(flat=True)
    sendEmail(data)
    return redirect('/')

def sendEmail(data):
    sg = sendgrid.SendGridAPIClient(SENDGRID_KEY)
    from_email = Email(SENDGRID_EMAIL, DISPLAY_NAME)
    subject_input = data['subject']
    message_input = data['message']
    Class = data['Class']

    query1 = client.query(kind=kind)
    query1.add_filter("Class", "=", "z81")
    query2 = client.query(kind=kind)
    query2.add_filter("Class", "=", "z82")
    if Class == 'z81':
        results = list(query1.fetch())
    elif Class == 'z82':
        results = list(query2.fetch())
    else:
        results = list()

# //Could use a dictionary for these if statements
    for contact in results: 
        contact_lang = contact['lang']
        message_lang = "English"
        if contact_lang == 'en':
            message_lang = 'English'
        elif contact_lang == 'de':
            message_lang = "German"
        elif contact_lang == 'fr':
            message_lang = "French"
        elif contact_lang == 'es':
            message_lang = "Spanish"
        elif contact_lang == 'it':
            message_lang = "Italian"
        elif contact_lang == 'hi':
            message_lang = "Hindi"
        default_message = f"Your assigned language is: {message_lang}"
        header = HEADER
        footer = FOOTER

        subject = f"{subject_input}, {message_lang}"

        # Translate subject and message of email
        subject = translate_client.translate(subject, target_language=contact_lang)['translatedText']

        default_message = translate_client.translate(default_message, target_language=contact_lang)['translatedText']
        header = translate_client.translate(header, target_language=contact_lang)['translatedText']
        footer = translate_client.translate(footer, target_language=contact_lang)['translatedText']
        message_input = translate_client.translate(message_input, target_language=contact_lang)['translatedText']

        message = f"{default_message}\n" \
                  f"{header}\n" \
                  f"{message_input}" \
                  f"\n\n{footer}"

        to_email = contact['email']
        content = Content("text/plain", message)

        mail = Mail(from_email, to_email, subject, content)
        mail.reply_to = REPLY_EMAIL
        mail_json = mail.get()

        # Send an HTTP POST request to /mail/send
        response = sg.client.mail.send.post(request_body=mail_json)

        # For debugging
        print(response.status_code) 

@app.route('/unresponded', methods=['GET'])
def unresponded():
    retrieve = client.query(kind=Email_kind)
    retrieve.add_filter("Response_Flag", "=", False)    
    emails = list(retrieve.fetch())
    return render_template('unresponded.html', emails=emails)

@app.route('/email_read/<Receive_Date>', methods=['GET'])
def email_read(Receive_Date):
    retrieve = client.query(kind=Email_kind)
    retrieve.add_filter("Receive_Date", "=", Receive_Date)    
    emails = list(retrieve.fetch())

    return render_template('email_content.html', emails=emails)

#Compose Message - POST
@app.route('/reply', methods=['POST'])
def helper():
    data = request.form.to_dict(flat=True)
    reply_em(data)
    return redirect('/')

def reply_em(data):

    Receive_Date = data['Receive_Date']
    email_retrieve = client.query(kind=Email_kind)
    email_retrieve.add_filter("Receive_Date", "=", Receive_Date)    
    datastore_entity = list(email_retrieve.fetch())

    datastore_entity = datastore_entity[0]

    datastore_entity['Response_Flag'] = True
    datastore_entity['Response_Date'] = datetime.datetime.now()

    sg = sendgrid.SendGridAPIClient(SENDGRID_KEY)
    from_email = Email(SENDGRID_EMAIL, DISPLAY_NAME)
    to_email = data['email']
    subject_input = data['subject']
    message_input = data['message']

    datastore_entity['Response_Flag'] = True
    datastore_entity['Response_Date'] = datetime.datetime.now()
    datastore_entity['Response'] = message_input

    client.put(datastore_entity)

    retrieve = client.query(kind=kind)
    retrieve.add_filter("email", "=", to_email)    
    emails = list(retrieve.fetch())

    emails = emails[0]

    contact_lang = emails['lang']

    subject = f"In reply to: {subject_input}"

    # Translate subject and message of email

    default_message = f"Your assigned language is: {contact_lang}"

    subject = translate_client.translate(subject, target_language=contact_lang)['translatedText']
    default_message = translate_client.translate(default_message, target_language=contact_lang)['translatedText']
    message_input = translate_client.translate(message_input, target_language=contact_lang)['translatedText']

    message = f"{default_message}\n" \
            f"{message_input}" \

    content = Content("text/plain", message)

    mail = Mail(from_email, to_email, subject, content)
    mail.reply_to = REPLY_EMAIL
    mail_json = mail.get()

    # Send an HTTP POST request to /mail/send
    response = sg.client.mail.send.post(request_body=mail_json)

    # For debugging
    print(response.status_code)

#---------------------------------

# Server listening on port 8080
if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
    
