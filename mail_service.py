import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

def send_reservation_confirmation(to, subject, body_email):
    from_ = 'gannamanenilakshmi1978@gmail.com'

    message = MIMEMultipart()
    message['From'] = from_
    message['To'] = to
    message['Subject'] = subject

    message.attach(MIMEText(body_email, 'plain'))

    s_e = smtplib.SMTP('smtp.gmail.com', 587)
    s_e.starttls()

    s_e.login(from_, 'upsprgwjgtxdbwki')
    text = message.as_string()
    s_e.sendmail(from_, to, text)
    print(f'Sent reservation confirmation to {to}')


