import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app
from models import db, Notification
from datetime import datetime


def send_sms(recipient, message):
    username = current_app.config['AT_USERNAME']
    api_key = current_app.config['AT_API_KEY']
    sender = current_app.config['AT_SENDER_ID']

    n = Notification(channel='sms', recipient=recipient, message=message, status='pending')
    db.session.add(n)
    db.session.commit()

    if not username or not api_key:
        n.status = 'failed'
        n.error = 'SMS not configured'
        db.session.commit()
        return False

    try:
        url = 'https://api.africastalking.com/version1/messaging'
        headers = {'apiKey': api_key, 'Accept': 'application/json'}
        data = {'username': username, 'to': recipient, 'message': message}
        if sender:
            data['from'] = sender
        r = requests.post(url, headers=headers, data=data, timeout=15)
        r.raise_for_status()
        n.status = 'sent'
        n.sent_at = datetime.utcnow()
        db.session.commit()
        return True
    except Exception as e:
        n.status = 'failed'
        n.error = str(e)
        db.session.commit()
        return False


def send_email(recipient, subject, body_html):
    n = Notification(channel='email', recipient=recipient, subject=subject,
                     message=body_html, status='pending')
    db.session.add(n)
    db.session.commit()

    cfg = current_app.config
    if not cfg['MAIL_USERNAME'] or not cfg['MAIL_PASSWORD']:
        n.status = 'failed'
        n.error = 'Email not configured'
        db.session.commit()
        return False

    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = cfg['MAIL_DEFAULT_SENDER']
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(body_html, 'html'))

        with smtplib.SMTP(cfg['MAIL_SERVER'], cfg['MAIL_PORT'], timeout=20) as s:
            s.starttls()
            s.login(cfg['MAIL_USERNAME'], cfg['MAIL_PASSWORD'])
            s.send_message(msg)

        n.status = 'sent'
        n.sent_at = datetime.utcnow()
        db.session.commit()
        return True
    except Exception as e:
        n.status = 'failed'
        n.error = str(e)
        db.session.commit()
        return False


def notify_results_published(pupil, exam, average, grade):
    school = current_app.config['SCHOOL_NAME']
    msg = (f"{school}: {pupil.full_name}'s {exam.name} ({exam.term} {exam.year}) "
           f"results are ready. Average: {average}% ({grade}). Login to view.")

    if pupil.parent_phone:
        send_sms(pupil.parent_phone, msg)
    if pupil.parent_email:
        html = f"""
        <h2>{school}</h2>
        <p>Dear Parent/Guardian,</p>
        <p>Results for <b>{pupil.full_name}</b> for <b>{exam.name}
        ({exam.term} {exam.year})</b> are ready.</p>
        <p><b>Average:</b> {average}% &nbsp; <b>Grade:</b> {grade}</p>
        <p>Log into the parent portal to view the report card.</p>
        <p>Regards,<br>{school}</p>
        """
        send_email(pupil.parent_email, f'Results Ready - {pupil.full_name}', html)