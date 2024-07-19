import imaplib
import os
from notion_client import Client
import email
from dotenv import load_dotenv
from fuzzywuzzy import fuzz
import re
from datetime import datetime, timezone
import requests
from transformers import pipeline

load_dotenv()

class JobApplicationReply:
    def __init__(self):
        self.mail = imaplib.IMAP4_SSL('imap.gmail.com')
        self.mail.login(os.getenv('EMAIL'), os.getenv('PASSWORD'))
        assert self.mail.select('inbox')[0] == 'OK', 'Unable to open mailbox'
        self.inbox = self.mail.select('inbox')
        self.result, self.data = self.mail.search(None, 'ALL')
        self.list_of_phrases = ["Thank you for applying", "Thank you for your application", "Thank you for your interest", "Thank you for your very interesting CV", "Unfortunately we have proceeded with other candidates"]
        self.dict_of_content = {}
        self.results = []  # Initialize results list
        self.processed_emails = 0
    
    
    def find_reply(self):
        assert self.result == 'OK', 'Error searching Inbox'
        email_ids = self.data[0].split()
        total_emails = len(email_ids)
        
        start = max(0, total_emails - self.processed_emails - 100)
        end = max(0, total_emails - self.processed_emails)
        
        for num in reversed(email_ids[start:end]):
            result, data = self.mail.fetch(num, '(RFC822)')
            assert result == 'OK', 'Error fetching mail'
            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)
            sender_email = self.extract_email_address(msg['from'])
            print(f"Checking email from: {sender_email}")
            content = self.decode_email(msg)
            subject = msg['subject']
            if content and self.is_job_application_reply(content, subject):
                print("Found job application reply")
                if sender_email not in self.dict_of_content:
                    self.dict_of_content[sender_email] = []
                first_line = content
                self.dict_of_content[sender_email].append(first_line)
            self.results.append(num)  # Add processed email to results
        self.mail.close()
        self.mail.logout()
        return self.dict_of_content

    def extract_email_address(self, from_field):
        return from_field.split("<")[-1].strip(">")

    def decode_email(self, msg, max_len= 1024):
        
        
        try:
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True).decode()
                        if len(payload) > max_len:
                            payload = payload[:max_len]
                        return payload
            else:
                payload = msg.get_payload(decode=True).decode()
                if len(payload) > max_len:
                    payload = payload[:max_len]
                return payload
        except Exception as e:
            print(f"Error decoding email: {e}")
        return None

    def is_job_application_reply(self, msg, subject):
        if not msg:
            return False
        
        score = 0
        
        for phrase in self.list_of_phrases:
            if fuzz.partial_ratio(phrase.lower(), msg.lower()) > 80:
                score += 2
        
        subject_keywords = ['application', 'job', 'position', 'candidacy', 'resume', 'rejection', 'status', "desværre", "ansøgning", "stilling", "kandidatur", "afslag", "status"]
        for keyword in subject_keywords:
            if keyword.lower() in subject.lower():
                print(f"Found keyword: {keyword}")
                score += 1
        
        patterns = [
            r'\b[Rr]e:.*[Aa]pplication\b',
            r'\b[Tt]hank you for your interest\b',
            r'\b[Ww]e have received your application\b',
            r'\b[Aa]pplication status\b'
        ]
        for pattern in patterns:
            if re.search(pattern, msg):
                score += 2
                print(f"Found pattern: {pattern}")
        print(f"Score: {score}")
        
        return score >= 1
    
    def summarize_email(self, email_content):
        summarizer = pipeline("summarization")
        summary = summarizer(email_content, max_length=20, min_length=10, do_sample=False)
        return summary[0]['summary_text']




    def assamble_payload(self):
        payload = []
        content = self.find_reply()
        for sender_email, content in content.items():   
            
            print("-----------------------------------")
            print(content)
            print("-----------------------------------")
            payload.append({
                "Email ": {"title": [{"text": {"content": sender_email}}]},  
                "Resume": {"rich_text": [{"text": {"content": self.summarize_email(content)}}]},
                "Tags": {"multi_select": [{"name": "diese"}]},  
                "Date": {"date": {"start":  datetime.now().astimezone(timezone.utc).isoformat(), "end": None}}  
            })  
        return payload



class NotionAPI:
    def __init__(self, token, database_id):
        self.token = token
        self.database_id = database_id
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json", 
            "Notion-Version": "2022-06-28"
        }

    def get_pages(self):
        url = f"https://api.notion.com/v1/databases/{self.database_id}/query"
        payload = {"page_size": 100}  
        response = requests.post(url, json=payload, headers=self.headers)
        data = response.json()
        
        import json
        with open('data.json', 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    
        return data["results"]

    
    def create_page(self, data:dict):
        url = "https://api.notion.com/v1/pages"
        payload = {"parent": {"database_id": self.database_id}, "properties": data}
        response = requests.post(url, headers=self.headers, json=payload)
        
        print(response.status_code)
        
        return response
        


if __name__ == '__main__':
    NOTION_TOKEN = os.getenv('NOTION_TOKEN')
    NOTION_DATABASE_ID = os.getenv('NOTION_DB_TOKE')


    napi = NotionAPI(NOTION_TOKEN, NOTION_DATABASE_ID)
    pages = napi.get_pages()
    
        

    Email = "test_email"
    Resume = "test_title"
    tag = "diese"
    published_date = datetime.now().astimezone(timezone.utc).isoformat()

    # data = {
    #     "Email ": {"title": [{"text": {"content": Email}}]},  # Korrigiere Feldname und Typ
    #     "Resume": {"rich_text": [{"text": {"content": Resume}}]},
    #     "Tags": {"multi_select": [{"name": tag}]},  # Korrigiere Feldname und Typ
    #     "Date": {"date": {"start": published_date, "end": None}}  
    # }
    
    # response = napi.create_page(data)
    # print(response.json())
    
    job_application_reply = JobApplicationReply()
    replies = job_application_reply.assamble_payload()
    for reply in replies:
        response = napi.create_page(reply)
        print(response.json())
    
