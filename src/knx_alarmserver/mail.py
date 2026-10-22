"""SMTP settings, safe templates and a durable per-recipient alarm outbox."""
import asyncio
import copy
from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
import json
import logging
import re
import secrets
import smtplib
import ssl
import string
import time

FIELDS={
    'vorgangsnummer':'Eindeutige Nummer des neuen Vorgangs', 'alarm_id':'Interne Alarm-ID',
    'meldung':'Meldungsbezeichnung', 'bereich':'Bereich', 'prioritaet':'Prioritätsnummer',
    'prioritaetsname':'Bezeichnung der Priorität', 'gruppenadresse':'KNX-Gruppenadresse',
    'dpt':'KNX-Datentyp', 'gekommen':'Beginn in lokaler Serverzeit', 'gekommen_iso':'Beginn mit Zeitzone (ISO)',
    'status':'Aktiv', 'wert':'Empfangener Wert', 'einheit':'Einheit', 'quelle':'KNX-Quelladresse',
    'operator':'Alarmoperator', 'schwellwert':'Schwellwert', 'hysterese':'Hysterese', 'feld':'Ausgewertetes Datenfeld',
    'server_name':'Konfigurierter Servername', 'server_url':'Konfigurierte Dashboard-Adresse',
    'empfaenger_vorname':'Vorname des Empfängers', 'empfaenger_nachname':'Nachname des Empfängers',
    'empfaenger_name':'Vollständiger Name des Empfängers', 'empfaenger_email':'E-Mail-Adresse des Empfängers',
}
DEFAULT_TEMPLATE={'subject':'[{prioritaetsname}] {meldung} · Vorgang #{vorgangsnummer}',
                  'body':'Hallo {empfaenger_name},\n\nes liegt eine neue Störung vor:\n\n{meldung}\nBereich: {bereich}\nPriorität: {prioritaet} · {prioritaetsname}\nGekommen: {gekommen}\nVorgang: #{vorgangsnummer}\nGA: {gruppenadresse} · DPT: {dpt}\nWert: {wert} {einheit}\n\n{server_name}\n{server_url}\n'}
DEFAULT_CONFIG={'enabled':False,'host':'','port':587,'security':'starttls','username':'','password':'',
                'from_email':'','from_name':'KNX Alarmserver','server_name':'KNX Alarmserver','server_url':'','templates':{}}


def validate_address(address):
    if not isinstance(address,str) or len(address)>254 or not re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)+",address):
        raise ValueError('Gültige E-Mail-Adresse erforderlich')
    local,domain=address.split('@')
    if len(local)>64 or local.startswith('.') or local.endswith('.') or '..' in local or any(len(label)>63 for label in domain.split('.')):
        raise ValueError('Gültige E-Mail-Adresse erforderlich')


def validate_template(template):
    if not isinstance(template,dict) or set(template)!={'subject','body'}:
        raise ValueError('Vorlage benötigt Betreff und Text')
    for key,limit in [('subject',200),('body',20000)]:
        value=template[key]
        if not isinstance(value,str) or not value.strip() or len(value)>limit or (key=='subject' and any(c in value for c in '\r\n')):
            raise ValueError('Ungültiger oder zu langer Betreff/Text')
        try:
            for _,field,spec,conversion in string.Formatter().parse(value):
                if field is not None and (field not in FIELDS or spec or conversion):
                    raise ValueError('Unbekannter Platzhalter oder Formatierung: '+str(field))
        except ValueError as error:
            raise ValueError('Ungültige Mailvorlage: '+str(error)) from None


def validate_config(proposed):
    if not isinstance(proposed,dict) or set(proposed)!=set(DEFAULT_CONFIG):
        raise ValueError('Unvollständige Mail-Konfiguration')
    if type(proposed['enabled']) is not bool or type(proposed['port']) is not int or not 1<=proposed['port']<=65535 or proposed['security'] not in ('starttls','ssl','plain'):
        raise ValueError('Aktivierung, SMTP-Port oder Verschlüsselung ungültig')
    for key,limit in [('host',253),('username',254),('password',1024),('from_email',254),('from_name',128),('server_name',128),('server_url',2048)]:
        value=proposed[key]
        if not isinstance(value,str) or len(value)>limit or (key!='password' and any(ord(c)<32 or ord(c)==127 for c in value)):
            raise ValueError('Ungültiges Feld: '+key)
    if proposed['host'] and (any(c.isspace() for c in proposed['host']) or '/' in proposed['host']):
        raise ValueError('SMTP-Host ohne Protokoll oder Pfad eingeben')
    if proposed['from_email']:validate_address(proposed['from_email'])
    if proposed['enabled'] and (not proposed['host'] or not proposed['from_email']):
        raise ValueError('SMTP-Host und Absenderadresse sind erforderlich')
    if proposed['server_url'] and not re.match(r'^https?://[^\s]+$',proposed['server_url']):
        raise ValueError('Dashboard-Adresse muss mit http:// oder https:// beginnen')
    if not isinstance(proposed['templates'],dict) or len(proposed['templates'])>100:
        raise ValueError('Ungültige Vorlagenliste')
    for priority,template in proposed['templates'].items():
        if not isinstance(priority,str) or not re.fullmatch(r'[1-9][0-9]{0,5}',priority):raise ValueError('Ungültige Vorlagen-Priorität')
        validate_template(template)


class MailStore:
    def _initialize_mail(self):
        with self.transaction():
            if 'mail_enabled' not in {row['name'] for row in self.db.execute('PRAGMA table_info(users)')}:
                self.db.execute('ALTER TABLE users ADD COLUMN mail_enabled INTEGER NOT NULL DEFAULT 0')
            self.db.execute('''CREATE TABLE IF NOT EXISTS mail_outbox (
                id INTEGER PRIMARY KEY AUTOINCREMENT, occurrence_id INTEGER NOT NULL, recipient TEXT NOT NULL,
                subject TEXT NOT NULL, body TEXT NOT NULL, message_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending', attempts INTEGER NOT NULL DEFAULT 0,
                next_attempt REAL NOT NULL DEFAULT 0, created_at TEXT NOT NULL, sent_at TEXT,
                last_error TEXT NOT NULL DEFAULT '', UNIQUE(occurrence_id,recipient))''')
            self.db.execute('CREATE INDEX IF NOT EXISTS mail_due ON mail_outbox(status,next_attempt,id)')

    def _mail_settings(self):
        row=self.db.execute("SELECT value FROM settings WHERE name='mail'").fetchone()
        return json.loads(row['value']) if row else {'revision':'initial','config':copy.deepcopy(DEFAULT_CONFIG)}

    def mail_settings(self):
        with self.lock:
            saved=self._mail_settings();config=copy.deepcopy(saved['config']);config['password_set']=bool(config['password']);config['password']=''
            priorities=self.priorities()['entries']
            for priority in priorities:config['templates'].setdefault(str(priority['priority']),copy.deepcopy(DEFAULT_TEMPLATE))
            counts={row['status']:row['total'] for row in self.db.execute('SELECT status,count(*) AS total FROM mail_outbox GROUP BY status')}
            jobs=[dict(row) for row in self.db.execute('SELECT id,occurrence_id,recipient,subject,status,attempts,created_at,sent_at,last_error FROM mail_outbox ORDER BY id DESC LIMIT 20')]
            return {'config':config,'revision':saved['revision'],'priorities':priorities,'placeholders':FIELDS,'counts':counts,'jobs':jobs}

    def save_mail_settings(self,proposed,revision,clear_password=False):
        if type(clear_password) is not bool:raise ValueError('Ungültige Passwortoption')
        with self.transaction():
            current=self._mail_settings()
            if revision!=current['revision']:raise RuntimeError('Mail-Konfiguration wurde geändert. Bitte neu laden.')
            proposed=copy.deepcopy(proposed)
            if isinstance(proposed,dict) and proposed.get('password')=='':proposed['password']='' if clear_password else current['config']['password']
            validate_config(proposed)
            self.db.execute("INSERT OR REPLACE INTO settings(name,value) VALUES ('mail',?)",(json.dumps({'revision':secrets.token_hex(16),'config':proposed},ensure_ascii=False),))
        return self.mail_settings()

    def set_mail_enabled(self,username,enabled):
        if type(enabled) is not bool:raise ValueError('Mail-Aktivierung muss wahr oder falsch sein')
        if enabled:validate_address(username)
        self.db.execute('UPDATE users SET mail_enabled=? WHERE username=?',(int(enabled),username))

    def queue_occurrence_mail(self,identifier,value,display,unit,source):
        from .store import now
        config=self._mail_settings()['config']
        if not config['enabled']:return
        row=dict(self.db.execute('SELECT * FROM occurrences WHERE id=?',(identifier,)).fetchone())
        alarm=self.alarms[row['alarm_id']]
        label=next((p['name'] for p in self.priorities()['entries'] if p['priority']==row['priority']),str(row['priority']))
        context={'vorgangsnummer':str(identifier),'alarm_id':row['alarm_id'],'meldung':row['name'],'bereich':row['area'],
                 'prioritaet':str(row['priority']),'prioritaetsname':label,'gruppenadresse':row['group_address'],'dpt':row['dpt'],
                 'gekommen':datetime.fromisoformat(row['came_at']).astimezone().strftime('%d.%m.%Y %H:%M:%S %Z'),
                 'gekommen_iso':row['came_at'],'status':'Aktiv','wert':str(value) if display is None else str(display),'einheit':unit or '',
                 'quelle':source or '', 'operator':alarm.operator,'schwellwert':str(alarm.threshold),'hysterese':str(alarm.hysteresis),'feld':alarm.field or '',
                 'server_name':config['server_name'],'server_url':config['server_url']}
        template=config['templates'].get(str(row['priority']),DEFAULT_TEMPLATE)
        for person in self.users():
            if not person['mail_enabled']:continue
            validate_address(person['username'])
            fields={**context,'empfaenger_vorname':person['first_name'],'empfaenger_nachname':person['last_name'],
                    'empfaenger_name':(person['first_name']+' '+person['last_name']).strip(),'empfaenger_email':person['username']}
            subject=template['subject'].format_map(fields).replace('\r',' ').replace('\n',' ')
            body=template['body'].format_map(fields)
            self.db.execute('''INSERT OR IGNORE INTO mail_outbox(occurrence_id,recipient,subject,body,message_id,created_at)
                VALUES (?,?,?,?,?,?)''',(identifier,person['username'],subject,body,make_msgid(domain='knx-alarmserver.local'),now()))

    def retry_failed_mail(self):
        with self.transaction():
            return self.db.execute("UPDATE mail_outbox SET status='pending',attempts=0,next_attempt=0,last_error='' WHERE status='failed'").rowcount

    def claim_mail(self):
        with self.transaction():
            config=self._mail_settings()['config']
            if not config['enabled']:return None
            self.db.execute("UPDATE mail_outbox SET status='pending' WHERE status='sending' AND next_attempt<=?",(time.time(),))
            self.db.execute("UPDATE mail_outbox SET status='cancelled',last_error='Empfänger nicht mehr aktiviert' WHERE status='pending' AND NOT EXISTS (SELECT 1 FROM users WHERE users.username=mail_outbox.recipient AND mail_enabled=1)")
            row=self.db.execute("SELECT * FROM mail_outbox WHERE status='pending' AND next_attempt<=? ORDER BY id LIMIT 1",(time.time(),)).fetchone()
            if row is None:return None
            self.db.execute("UPDATE mail_outbox SET status='sending',attempts=attempts+1,next_attempt=? WHERE id=?",(time.time()+300,row['id']))
            return dict(row),config


def send_smtp(config,job):
    message=EmailMessage();message['Subject']=job['subject'];message['From']=formataddr((config['from_name'],config['from_email']))
    message['To']=job['recipient'];message['Message-ID']=job['message_id'];message['Date']=datetime.now().astimezone();message.set_content(job['body'])
    factory=smtplib.SMTP_SSL if config['security']=='ssl' else smtplib.SMTP
    kwargs={'timeout':10}
    if config['security']=='ssl':kwargs['context']=ssl.create_default_context()
    with factory(config['host'],config['port'],**kwargs) as smtp:
        smtp.ehlo()
        if config['security']=='starttls':smtp.starttls(context=ssl.create_default_context());smtp.ehlo()
        if config['username']:smtp.login(config['username'],config['password'])
        smtp.send_message(message,from_addr=config['from_email'],to_addrs=[job['recipient']])


def mail_error(error):
    if isinstance(error,smtplib.SMTPAuthenticationError):return 'Anmeldung am Mailserver fehlgeschlagen'
    if isinstance(error,ssl.SSLError):return 'TLS-Verbindung oder Zertifikatsprüfung fehlgeschlagen'
    if isinstance(error,smtplib.SMTPRecipientsRefused):return 'Empfänger vom Mailserver abgelehnt'
    if isinstance(error,smtplib.SMTPSenderRefused):return 'Absender vom Mailserver abgelehnt'
    if isinstance(error,smtplib.SMTPException):return 'SMTP-Versand fehlgeschlagen ('+type(error).__name__+')'
    return 'Mailserver nicht erreichbar oder Versand fehlgeschlagen ('+type(error).__name__+')'


class MailWorker:
    def __init__(self,store,sender=None):self.store=store;self.sender=sender or send_smtp;self.stop_event=asyncio.Event();self.task=None

    async def start(self):
        with self.store.transaction():self.store.db.execute("UPDATE mail_outbox SET status='pending',next_attempt=0 WHERE status='sending'")
        self.task=asyncio.create_task(self.run())

    async def stop(self):
        self.stop_event.set()
        if self.task:await self.task

    async def run(self):
        while not self.stop_event.is_set():
            try:await asyncio.to_thread(self.tick)
            except Exception:logging.getLogger(__name__).warning('Mail-Warteschlange momentan nicht verfügbar')
            try:await asyncio.wait_for(self.stop_event.wait(),timeout=1)
            except asyncio.TimeoutError:pass

    def tick(self):
        from .store import now
        claimed=self.store.claim_mail()
        if claimed is None:return False
        job,config=claimed
        try:self.sender(config,job)
        except Exception as error:
            attempts=job['attempts']+1
            with self.store.transaction():self.store.db.execute("UPDATE mail_outbox SET status=?,next_attempt=?,last_error=? WHERE id=?",('failed' if attempts>=5 else 'pending',time.time()+min(3600,30*4**(attempts-1)),mail_error(error),job['id']))
        else:
            with self.store.transaction():self.store.db.execute("UPDATE mail_outbox SET status='sent',sent_at=?,last_error='' WHERE id=?",(now(),job['id']))
        return True
