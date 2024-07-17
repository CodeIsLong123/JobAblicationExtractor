import imaplib
import os
import email
from dotenv import load_dotenv
import re

load_dotenv()

class JobApplicationReply:
    
    def __init__(self):
        self.mail = imaplib.IMAP4_SSL('imap.gmail.com')
        self.mail.login(os.getenv('EMAIL'), os.getenv('PASSWORD'))
        assert self.mail.select('inbox')[0] == 'OK', 'Unable to open mailbox'
        self.inbox = self.mail.select('inbox')  
        self.result, self.data = self.mail.search(None, 'ALL')  
        self.list_of_email = ["jobs-noreply@linkedin.com", "jobalerts-noreply@linkedin.com"]
        print("enter")
    
    
    
    def find_reply(self):
        assert self.result == 'OK', 'Error searching Inbox'
        
        # Durchsuche E-Mails in umgekehrter Reihenfolge (neueste zuerst)
        for num in reversed(self.data[0].split()):
            result, data = self.mail.fetch(num, '(RFC822)')
            assert result == 'OK', 'Error fetching mail'
            
            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)
            
            sender_email = self.extract_email_address(msg['from'])
            print(f"Checking email from: {sender_email}")
            
            if sender_email in self.list_of_email:
                content = self.decode_email(msg)

                self.mail.close()
                self.mail.logout()
                return content
        
        print("No matching email found")
        self.mail.close()
        self.mail.logout()
        return None

    def extract_email_address(self, from_field):

        return from_field.split("<")[-1].strip(">")

    def decode_email(self, msg):
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    return part.get_payload(decode=True).decode()
        else:
            return msg.get_payload(decode=True).decode()
        return "No plain text content found in email"
        

        
    def is_job_application_reply(self, msg) :
        
        # Check if the email is a job application reply
        
        pass
        
    
    def put_in_database(self, msg):
        # TODO: Implement this function
        # This function will put the email in the database
        # Maybe into Notion or something
        
        pass
    
    def put_in_notion(self, msg):
        # TODO: Implement this function 
        # Find out if Notion has an API to post articles
        pass
        
                
if __name__ == '__main__':
    cleaner = JobApplicationReply()
    print(cleaner.find_reply())